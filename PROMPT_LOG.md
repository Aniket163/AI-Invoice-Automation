# Prompt Documentation — AI Invoice Automation
Candidate: Aniket Kolhe · Task: AI Growth & Automation Associate (Automation category)

## Part A — Prompts used with Claude to build the project
> Replace/extend these with your own exact wording and follow-ups from your chat history.

| # | Prompt (summary / exact) | Why | Result |
|---|---|---|---|
| A1 | "Using my existing AI Invoice Parser, help me turn it into the best possible submission for an AI Growth & Automation assessment (healthcare/technology, automation category)." | Define scope from the assessment criteria | Plan: add validation, self-repair, analytics, documentation |
| A2 | "Let's do the task and make my score 9.5." | Push beyond a basic parser | Added validation engine, self-repair loop, review queue, Excel export |
| A3 | (add) Your follow-up prompts, e.g. asking Claude to fix a bug or improve the UI | | |

**Real debugging iterations during the build (examples to mention in your video):**
- GST regex failed on `GST (18%): 2,736.00` because the pattern stopped at the digit in "18%" → the invalid invoice was not flagged; fixed regex, test now passes.
- Newer pandas rejected positional sheet names in `to_excel` → switched to `sheet_name=`.
- Folder creation failed because shell brace-expansion didn't run → recreated folders explicitly.

## Part B — Prompts inside the application (the extraction engine)

### V1 — baseline
```
Extract the invoice details from this text and give me JSON.
```
**Problem:** inconsistent keys, dates in mixed formats, prose around JSON, invented values.

### V2 — schema + rules
Added fixed JSON schema, "null if absent, never guess", ISO dates, plain numbers, "JSON only".
**Improvement:** parseable output. **Remaining problem:** arithmetic copied/"fixed" inconsistently; vague categories.

### V3 — production prompt
Added role ("meticulous accounts-payable analyst"), explicit rules (copy printed numbers, don't fix them), category rubric, and one worked example (few-shot).
**Improvement:** stable structure, consistent categories, honest numbers that let validation catch real errors.

### V4 — self-repair prompt
Used only when validation fails; feeds the exact failed checks + previous JSON back to the model and asks for a minimal, text-supported correction.
**Design reason:** separating "extract faithfully" (V3) from "fix what checks disprove" (V4) stops the model from silently altering source numbers.

Full text of every prompt version: `prompts.py`.

## Part C — Test results (fill in after running with your key)
| Invoice | V1 result | V3 result | Flags raised |
|---|---|---|---|
| invoice_cloud.pdf | (paste) | (paste) | none expected |
| invoice_clinic.pdf | (paste) | (paste) | none expected |
| invoice_error.pdf | (paste) | (paste) | subtotal + tax ≠ total |
