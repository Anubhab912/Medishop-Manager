import os
import tempfile
from reportlab.lib.pagesizes import A5
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                 Table, TableStyle, HRFlowable)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

from utils.helpers import format_currency, format_datetime


def generate_bill_pdf(bill, items):
    tmp  = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf",
                                       prefix=f"{bill['bill_number']}_")
    path = tmp.name
    tmp.close()

    doc  = SimpleDocTemplate(path, pagesize=A5,
                              leftMargin=12*mm, rightMargin=12*mm,
                              topMargin=10*mm,  bottomMargin=10*mm)

    blue  = colors.HexColor("#1a73e8")
    dark  = colors.HexColor("#1e2a3a")
    gray  = colors.HexColor("#f8f9fa")
    muted = colors.HexColor("#5f6368")
    W     = 121*mm

    def S(name, **kw):
        return ParagraphStyle(name, **kw)

    sShop  = S("shop",  fontSize=14, fontName="Helvetica-Bold",    textColor=colors.white, alignment=TA_CENTER)
    sSub   = S("sub",   fontSize=8,  fontName="Helvetica",         textColor=colors.white, alignment=TA_CENTER)
    sBody  = S("body",  fontSize=8,  fontName="Helvetica",         textColor=dark,  leading=12)
    sCode  = S("code",  fontSize=8,  fontName="Helvetica",         textColor=dark)
    sTotal = S("total", fontSize=11, fontName="Helvetica-Bold",    textColor=blue)
    sFoot  = S("foot",  fontSize=7,  fontName="Helvetica-Oblique", textColor=muted, alignment=TA_CENTER)

    story = []

    header = Table([
        [Paragraph("💊 MediShop Manager", sShop)],
        [Paragraph("Your Trusted Medical Shop",  sSub)],
    ], colWidths=[W])
    header.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), dark),
        ("TOPPADDING",    (0,0),(-1,-1), 8),
        ("BOTTOMPADDING", (0,0),(-1,-1), 8),
    ]))
    story.append(header)
    story.append(Spacer(1, 6))

    info_l = f"<b>Bill No:</b> {bill['bill_number']}<br/><b>Date:</b> {format_datetime(bill['created_at'])}"
    info_r = f"<b>Customer:</b> {bill.get('customer_name') or 'Walk-in'}<br/><b>Payment:</b> {bill['payment_method']}"
    info   = Table([[Paragraph(info_l, sBody), Paragraph(info_r, sBody)]], colWidths=[W/2, W/2])
    info.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), gray),
        ("LEFTPADDING",   (0,0),(-1,-1), 8),
        ("RIGHTPADDING",  (0,0),(-1,-1), 8),
        ("TOPPADDING",    (0,0),(-1,-1), 6),
        ("BOTTOMPADDING", (0,0),(-1,-1), 6),
        ("BOX",           (0,0),(-1,-1), 0.5, colors.HexColor("#dadce0")),
    ]))
    story.append(info)
    story.append(Spacer(1, 6))

    rows = [["#", "Medicine", "Qty", "Rate", "Amount"]]
    for i, item in enumerate(items, 1):
        rows.append([str(i), item["medicine_name"], str(item["quantity"]),
                     format_currency(item["unit_price"]),
                     format_currency(item["subtotal"])])

    tbl = Table(rows, colWidths=[8*mm, 55*mm, 14*mm, 22*mm, 22*mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1, 0), blue),
        ("TEXTCOLOR",     (0,0),(-1, 0), colors.white),
        ("FONTNAME",      (0,0),(-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0),(-1,-1), 8),
        ("ALIGN",         (2,0),(-1,-1), "RIGHT"),
        ("ALIGN",         (0,0),(0, -1), "CENTER"),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LEFTPADDING",   (0,0),(-1,-1), 4),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [colors.white, gray]),
        ("BOX",           (0,0),(-1,-1), 0.5, colors.HexColor("#dadce0")),
        ("LINEBELOW",     (0,0),(-1, 0), 1, blue),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 6))

    totals = [["Subtotal", format_currency(bill["subtotal"])]]
    if float(bill["discount"]) > 0:
        totals.append(["Discount", f"-{format_currency(bill['discount'])}"])
    if float(bill["tax_percent"]) > 0:
        totals.append([f"GST ({bill['tax_percent']}%)", format_currency(bill["tax_amount"])])
    totals.append(["TOTAL", format_currency(bill["total_amount"])])

    tot_rows = []
    for i, (label, value) in enumerate(totals):
        last = i == len(totals) - 1
        lp   = Paragraph(f"<b>{label}</b>" if last else label,
                          sTotal if last else sBody)
        vp   = Paragraph(f"<b>{value}</b>" if last else value,
                          S("v", fontSize=11 if last else 8,
                            fontName="Helvetica-Bold" if last else "Helvetica",
                            textColor=blue if last else dark,
                            alignment=TA_RIGHT))
        tot_rows.append(["", lp, vp])

    tot_tbl = Table(tot_rows, colWidths=[60*mm, 35*mm, 26*mm])
    tot_tbl.setStyle(TableStyle([
        ("TOPPADDING",    (0,0),(-1,-1), 3),
        ("BOTTOMPADDING", (0,0),(-1,-1), 3),
        ("LINEABOVE",     (1,-1),(-1,-1), 1, blue),
    ]))
    story.append(tot_tbl)
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=0.5,
                             color=colors.HexColor("#dadce0"), spaceAfter=6))
    story.append(Paragraph("Thank you for your purchase! Get well soon.", sFoot))

    doc.build(story)
    return path
