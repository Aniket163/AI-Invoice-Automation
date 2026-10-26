# 🧾 AI Invoice Automation

An AI-powered workflow that turns messy invoices (PDF / image / text) into clean, validated, analysis-ready data.

**Problem:** Manual invoice entry is slow, error-prone and hard to audit.
**Solution:** LLM extraction → automatic math/date/duplicate validation → **self-repair prompt** when checks fail → human-review queue → Excel export + spend analytics.

## Features
- Batch upload (PDF, PNG/JPG with optional OCR, TXT)
- Structured JSON extraction with a versioned, engineered prompt (`prompts.py`)
- Validation: required fields, line-item math, subtotal + tax = total, date logic, duplicate invoice numbers
- **Self-repair loop:** failed checks are fed back to the model for one corrective pass
- Confidence score + "Needs review" flags (human-in-the-loop)
- Editable results table, spend by vendor/category charts, Excel export (invoices + line items)
- Works offline with a rule-based fallback if no API key is set (clearly labelled, lower accuracy)

## Run
```bash
pip install -r requirements.txt
export GROQ_API_KEY=your_key   # free key: console.groq.com  (optional)
streamlit run app.py
```
Tick **"Use bundled sample invoices"** in the sidebar and press **Process invoices**.
`invoice_error.pdf` has a deliberate arithmetic error to demonstrate validation.

## Tests
`python make_samples.py` (regenerates samples) then `pytest -q`

## Structure
| File | Purpose |
|---|---|
| `app.py` | Streamlit UI, analytics, Excel export |
| `parser_core.py` | Text extraction, LLM call, fallback parser, validation, self-repair pipeline |
| `prompts.py` | Prompt versions V1 → V3 + repair prompt |
| `PROMPT_LOG.md` | Full prompt documentation |
| `tests/` | Unit tests |

## Tools used
Claude (design, code generation, prompt iteration), Groq Llama-3.3-70B (runtime extraction), Streamlit, pdfplumber, pandas.
