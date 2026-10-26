"""Versioned prompts. Each version is kept so the iteration is visible (see PROMPT_LOG.md)."""

SCHEMA = """{
  "invoice_number": string|null,
  "vendor_name": string|null,
  "invoice_date": "YYYY-MM-DD"|null,
  "due_date": "YYYY-MM-DD"|null,
  "currency": string|null,
  "line_items": [{"description": string, "quantity": number, "unit_price": number, "amount": number}],
  "subtotal": number|null,
  "tax": number|null,
  "total": number|null,
  "category": "Software"|"Healthcare"|"Logistics"|"Office"|"Utilities"|"Other"
}"""

# v1 - first attempt: vague, unreliable output (kept for documentation)
V1 = "Extract the invoice details from this text and give me JSON.\n\n{text}"

# v2 - added fixed schema, null rules and JSON-only instruction
V2 = f"""You are an invoice data extraction engine.
Return ONLY valid JSON matching this schema (no prose, no markdown):
{SCHEMA}
Rules:
- Use null when a field is not present. Never guess.
- Dates must be ISO format YYYY-MM-DD.
- Numbers must be plain numbers (no currency symbols or thousands separators).

INVOICE TEXT:
{{text}}"""

# v3 (production) - adds role, worked example, category rubric and self-check instructions
V3 = f"""You are a meticulous accounts-payable analyst. Extract structured data from the invoice text.
Return ONLY valid JSON matching this schema (no prose, no markdown fences):
{SCHEMA}

Rules:
1. Use null for anything not explicitly present. Never invent values.
2. Dates -> YYYY-MM-DD. Numbers -> plain numbers (strip symbols, commas).
3. Each line item: amount must equal quantity * unit_price.
4. subtotal + tax should equal total. If the text contradicts this, copy the numbers AS PRINTED; do not fix them.
5. category: choose the single best fit. Medical/clinic/pharma -> Healthcare; SaaS/cloud/licences -> Software;
   shipping/freight -> Logistics; stationery/furniture -> Office; electricity/internet -> Utilities; else Other.

Example
TEXT: "Acme Cloud Inv #A-77 12 Mar 2026 Hosting 2 x 50.00 = 100.00 Tax 18.00 Total 118.00"
JSON: {{"invoice_number":"A-77","vendor_name":"Acme Cloud","invoice_date":"2026-03-12","due_date":null,
"currency":null,"line_items":[{{"description":"Hosting","quantity":2,"unit_price":50.0,"amount":100.0}}],
"subtotal":100.0,"tax":18.0,"total":118.0,"category":"Software"}}

INVOICE TEXT:
{{text}}"""

# v4 - self-repair prompt, used only when validation finds problems
REPAIR = """Your previous extraction failed these automated checks:
{issues}

Re-read the invoice text and return a corrected JSON object with the same schema. Fix only what the
text supports; keep null where the text is silent. Return ONLY JSON.

INVOICE TEXT:
{text}

PREVIOUS JSON:
{previous}"""

ACTIVE = V3
