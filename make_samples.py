"""Generates 3 synthetic sample invoices (one has a deliberate arithmetic error to demo validation)."""
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

SAMPLES = [
    ("sample_invoices/invoice_cloud.pdf", "Nimbus Cloud Services Pvt Ltd", "NCS-2026-0142", "2026-09-03", "2026-10-03",
     [("Cloud hosting - Standard plan", 3, 4500.00), ("Priority support", 1, 1500.00)], 18),
    ("sample_invoices/invoice_clinic.pdf", "Sunrise Medical Supplies", "SMS-8891", "2026-09-10", "2026-09-25",
     [("Digital thermometer", 10, 250.00), ("Disposable gloves (box)", 20, 180.00), ("Pulse oximeter", 2, 1800.00)], 12),
    ("sample_invoices/invoice_error.pdf", "QuickMove Logistics", "QML-5521", "2026-09-15", "2026-09-30",
     [("Freight Pune-Mumbai", 2, 7200.00), ("Loading charges", 1, 800.00)], 18),
]
for path, vendor, no, d, due, items, rate in SAMPLES:
    c = canvas.Canvas(path, pagesize=A4); y = 800
    def line(t, dy=18):
        global y; c.drawString(50, y, t); y -= dy
    c.setFont("Helvetica-Bold", 14); line(vendor, 28); c.setFont("Helvetica", 11)
    line(f"Invoice No: {no}"); line(f"Invoice Date: {d}"); line(f"Due Date: {due}", 30)
    line("Description                         Qty   Unit Price   Amount")
    sub = 0
    for desc, q, p in items:
        amt = q * p; sub += amt
        line(f"{desc}   {q}   {p:,.2f}   {amt:,.2f}")
    tax = round(sub * rate / 100, 2)
    total = sub + tax + (500 if "error" in path else 0)  # deliberate mistake
    line("", 10); line(f"Subtotal: {sub:,.2f}"); line(f"GST ({rate}%): {tax:,.2f}"); line(f"Total Due: {total:,.2f}")
    c.save()
print("samples created")
