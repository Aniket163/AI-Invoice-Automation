import glob, io, os
import pandas as pd
import streamlit as st
import parser_core as pc

st.set_page_config(page_title="AI Invoice Automation", page_icon="🧾", layout="wide")
st.title("🧾 AI Invoice Automation")
st.caption("Upload invoices → AI extracts structured data → automatic validation & self-repair → Excel export + spend analytics")

with st.sidebar:
    st.header("Settings")
    api_key = st.text_input("Groq API key (free at console.groq.com)", type="password",
                            value=os.getenv("GROQ_API_KEY", ""))
    st.info("No key? The app falls back to a basic rule-based parser so you can still try it (lower accuracy).")
    use_samples = st.checkbox("Use bundled sample invoices", value=False)

files = st.file_uploader("Invoices (PDF, PNG, JPG, TXT)", accept_multiple_files=True,
                         type=["pdf", "png", "jpg", "jpeg", "txt"])
inputs = [(f.name, f.read()) for f in files or []]
if use_samples:
    inputs += [(os.path.basename(p), open(p, "rb").read()) for p in sorted(glob.glob("sample_invoices/*.pdf"))]

if inputs and st.button("Process invoices", type="primary"):
    rows, seen = [], set()
    bar = st.progress(0.0)
    for n, (name, data) in enumerate(inputs, 1):
        try:
            res = pc.process(pc.extract_text(data, name), api_key or None, seen)
            seen.add(res.data.get("invoice_number"))
            d = res.data
            rows.append({"file": name, "invoice_number": d.get("invoice_number"), "vendor": d.get("vendor_name"),
                         "date": d.get("invoice_date"), "due_date": d.get("due_date"), "category": d.get("category"),
                         "subtotal": d.get("subtotal"), "tax": d.get("tax"), "total": d.get("total"),
                         "confidence": res.confidence, "status": "✅ OK" if not res.issues else "⚠️ Review",
                         "issues": "; ".join(res.issues), "method": res.method + (" + self-repair" if res.repaired else ""),
                         "line_items": d.get("line_items")})
        except Exception as e:
            rows.append({"file": name, "status": "❌ Failed", "issues": str(e)})
        bar.progress(n / len(inputs))
    st.session_state["df"] = pd.DataFrame(rows)

if "df" in st.session_state:
    df = st.session_state["df"]
    ok = (df["status"] == "✅ OK").sum()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Invoices", len(df)); c2.metric("Passed validation", int(ok))
    c3.metric("Need review", int(len(df) - ok))
    c4.metric("Total spend", f"{pd.to_numeric(df.get('total'), errors='coerce').sum():,.2f}")

    st.subheader("Extracted data (editable)")
    show = df.drop(columns=["line_items"], errors="ignore")
    edited = st.data_editor(show, width="stretch", num_rows="fixed")

    flagged = df[df["status"] != "✅ OK"]
    if len(flagged):
        st.subheader("⚠️ Flagged for human review")
        for _, r in flagged.iterrows():
            st.warning(f"**{r['file']}** — {r.get('issues', '')}")

    num = edited.copy(); num["total"] = pd.to_numeric(num["total"], errors="coerce")
    st.subheader("Spend analytics")
    a, b = st.columns(2)
    a.write("Spend by vendor"); a.bar_chart(num.groupby("vendor")["total"].sum())
    b.write("Spend by category"); b.bar_chart(num.groupby("category")["total"].sum())

    items = [dict(li, invoice_number=r["invoice_number"], vendor=r["vendor"])
             for _, r in df.iterrows() for li in (r.get("line_items") or [])]
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        edited.to_excel(xw, sheet_name="Invoices", index=False)
        pd.DataFrame(items).to_excel(xw, sheet_name="Line items", index=False)
    st.download_button("⬇️ Download Excel", buf.getvalue(), "invoices.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
