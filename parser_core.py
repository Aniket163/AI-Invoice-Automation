"""Core logic: text extraction -> LLM extraction (with regex fallback) -> validation -> self-repair."""
import io, json, os, re
from dataclasses import dataclass, field
import prompts

MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


# ---------- 1. text extraction ----------
def extract_text(data: bytes, filename: str) -> str:
    name = filename.lower()
    if name.endswith(".pdf"):
        import pdfplumber
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            return "\n".join((p.extract_text() or "") for p in pdf.pages).strip()
    if name.endswith((".png", ".jpg", ".jpeg")):
        try:
            import pytesseract
            from PIL import Image
            return pytesseract.image_to_string(Image.open(io.BytesIO(data))).strip()
        except Exception as e:  # OCR is optional
            raise RuntimeError(f"OCR unavailable ({e}). Install tesseract or upload a PDF/TXT.")
    return data.decode("utf-8", errors="ignore").strip()


# ---------- 2. extraction ----------
def _parse_json(raw: str) -> dict:
    raw = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.M).strip()
    start, end = raw.find("{"), raw.rfind("}")
    return json.loads(raw[start:end + 1])


def llm_extract(text: str, api_key: str, template: str = None, extra: dict = None) -> dict:
    from groq import Groq
    client = Groq(api_key=api_key)
    prompt = (template or prompts.ACTIVE).format(text=text, **(extra or {}))
    resp = client.chat.completions.create(
        model=MODEL, temperature=0,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    return _parse_json(resp.choices[0].message.content)


def _num(s):
    try:
        return float(str(s).replace(",", "").replace("$", "").replace("₹", ""))
    except ValueError:
        return None


def rule_extract(text: str) -> dict:
    """Offline fallback so the app works with no API key (lower accuracy, clearly labelled)."""
    def find(pattern):
        m = re.search(pattern, text, re.I)
        return m.group(1).strip() if m else None
    items = []
    for m in re.finditer(r"^(?P<d>[A-Za-z][^\n\d]{2,}?)\s+(?P<q>\d+(?:\.\d+)?)\s+(?P<p>[\d,]+\.\d{2})\s+(?P<a>[\d,]+\.\d{2})$",
                         text, re.M):
        items.append({"description": m["d"].strip(), "quantity": _num(m["q"]),
                      "unit_price": _num(m["p"]), "amount": _num(m["a"])})
    first_line = next((l.strip() for l in text.splitlines() if l.strip()), None)
    return {
        "invoice_number": find(r"invoice\s*(?:no\.?|number|#)\s*[:#]?\s*([\w\-/]+)"),
        "vendor_name": first_line,
        "invoice_date": find(r"(?:invoice\s*)?date\s*[:]\s*(\d{4}-\d{2}-\d{2})"),
        "due_date": find(r"due\s*date\s*[:]\s*(\d{4}-\d{2}-\d{2})"),
        "currency": None,
        "line_items": items,
        "subtotal": _num(find(r"sub\s*total\s*[:]?\s*[^\d\n]*([\d,]+\.\d{2})")),
        "tax": _num(find(r"(?:tax|gst|vat)[^\n]*?([\d,]+\.\d{2})")),
        "total": _num(find(r"(?<!sub)total(?:\s*due)?\s*[:]?\s*[^\d\n]*([\d,]+\.\d{2})")),
        "category": "Other",
    }


# ---------- 3. validation ----------
@dataclass
class Result:
    data: dict
    issues: list = field(default_factory=list)
    confidence: float = 1.0
    method: str = "llm"
    repaired: bool = False


REQUIRED = ["invoice_number", "vendor_name", "invoice_date", "total"]


def validate(inv: dict, seen_numbers: set = None) -> tuple:
    issues = []
    for f in REQUIRED:
        if not inv.get(f):
            issues.append(f"Missing required field: {f}")
    items = inv.get("line_items") or []
    for i, it in enumerate(items, 1):
        q, p, a = it.get("quantity"), it.get("unit_price"), it.get("amount")
        if None not in (q, p, a) and abs(q * p - a) > 0.02:
            issues.append(f"Line {i}: {q} x {p} != {a}")
    if items and inv.get("subtotal") is not None:
        s = sum(it.get("amount") or 0 for it in items)
        if abs(s - inv["subtotal"]) > 0.02:
            issues.append(f"Line items sum {s:.2f} != subtotal {inv['subtotal']}")
    if None not in (inv.get("subtotal"), inv.get("tax"), inv.get("total")):
        if abs(inv["subtotal"] + inv["tax"] - inv["total"]) > 0.02:
            issues.append(f"subtotal + tax ({inv['subtotal'] + inv['tax']:.2f}) != total ({inv['total']})")
    for f in ("invoice_date", "due_date"):
        v = inv.get(f)
        if v and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(v)):
            issues.append(f"{f} not in YYYY-MM-DD: {v}")
    if inv.get("invoice_date") and inv.get("due_date") and inv["due_date"] < inv["invoice_date"]:
        issues.append("Due date is before invoice date")
    if seen_numbers is not None and inv.get("invoice_number") in seen_numbers:
        issues.append(f"Possible duplicate invoice number: {inv['invoice_number']}")
    confidence = max(0.0, round(1 - 0.2 * len(issues), 2))
    return issues, confidence


# ---------- 4. pipeline ----------
def process(text: str, api_key: str = None, seen_numbers: set = None, max_repairs: int = 1) -> Result:
    if not api_key:
        inv = rule_extract(text)
        issues, conf = validate(inv, seen_numbers)
        return Result(inv, issues, min(conf, 0.6), method="rule-based (no API key)")
    inv = llm_extract(text, api_key)
    issues, conf = validate(inv, seen_numbers)
    repaired = False
    for _ in range(max_repairs):
        calc = [i for i in issues if not i.startswith("Possible duplicate")]
        if not calc:
            break
        inv2 = llm_extract(text, api_key, prompts.REPAIR,
                           {"issues": "\n".join(calc), "previous": json.dumps(inv)})
        issues2, conf2 = validate(inv2, seen_numbers)
        if len(issues2) <= len(issues):
            inv, issues, conf, repaired = inv2, issues2, conf2, True
    return Result(inv, issues, conf, "llm", repaired)
