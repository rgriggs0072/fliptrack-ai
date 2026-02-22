# ---------------- utils/pdf_exports.py ----------------
# -*- coding: utf-8 -*-
"""
PDF Exports Utility
===================

Page Overview (for future devs)
------------------------------
Central place for generating PDFs used throughout the app.

Current exports:
- Vendor Intelligence PDF summary (LLM output)

Design rules:
- Return PDF as bytes (so Streamlit can download via st.download_button).
- Avoid tight coupling to Streamlit UI components.
- Keep formatting predictable and defensive against missing keys.
"""

from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List, Optional

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER


def build_vendor_intelligence_pdf(
    *,
    company_name: str,
    generated_at: Optional[Any],
    estimated_savings: float,
    analysis: Dict[str, Any],
) -> bytes:
    """
    Build a Vendor Intelligence PDF as bytes.

    Args:
        company_name: Header title (tenant/company)
        generated_at: Timestamp (datetime or string-ish)
        estimated_savings: Displayed savings metric
        analysis: LLM JSON dict (top_vendors, key_insights, opportunities, recommendations, etc.)

    Returns:
        PDF bytes
    """
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=LETTER,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.7 * inch,
        title=f"{company_name} - Vendor Intelligence",
    )

    styles = getSampleStyleSheet()
    h1 = styles["Heading1"]
    h2 = styles["Heading2"]
    body = styles["BodyText"]

    # Minor tuning
    h1.alignment = TA_CENTER
    h2.spaceBefore = 10
    h2.spaceAfter = 6
    body.leading = 14
    body.alignment = TA_LEFT

    story: List[Any] = []

    # ---------------- Header ----------------
    story.append(Paragraph(f"{company_name}", h1))
    story.append(Paragraph("Vendor Intelligence Summary", styles["Title"]))
    story.append(Spacer(1, 10))

    # Metadata
    ts = _safe_str_timestamp(generated_at)
    story.append(Paragraph(f"<b>Latest run:</b> {ts or '—'}", body))
    story.append(Paragraph(f"<b>Estimated Savings:</b> ${float(estimated_savings or 0):,.0f}", body))
    story.append(Spacer(1, 10))

    # ---------------- Executive Summary ----------------
    story.append(Paragraph("Executive Summary", h2))
    key_insights = (analysis.get("key_insights") or [])[:5]
    if key_insights:
        for i in key_insights:
            story.append(Paragraph(f"• { _safe_text(i) }", body))
    else:
        story.append(Paragraph("No insights returned.", body))
    story.append(Spacer(1, 10))

    # ---------------- Top Vendors ----------------
    story.append(Paragraph("Top Vendors (Spend Concentration)", h2))
    top_vendors = analysis.get("top_vendors") or []
    if top_vendors:
        vendor_rows = [["Vendor", "Spend", "Txns", "Insight"]]
        for v in top_vendors[:10]:
            vendor_rows.append(
                [
                    _safe_text(v.get("vendor", "")),
                    _money(v.get("spend", 0)),
                    str(int(float(v.get("transactions", 0) or 0))),
                    _safe_text(v.get("insight", "")),
                ]
            )
        story.append(_styled_table(vendor_rows))
    else:
        story.append(Paragraph("No top vendor breakdown returned.", body))
    story.append(Spacer(1, 10))

    # ---------------- Opportunities ----------------
    story.append(Paragraph("Cost-Saving Opportunities", h2))
    opps = analysis.get("opportunities") or []
    total_opportunity = 0.0

    if not opps:
        story.append(Paragraph("No specific cost-saving opportunities identified.", body))
    else:
        for opp in opps[:12]:
            opp_type = _safe_text(str(opp.get("type", "")).replace("_", " ").title())
            area = _safe_text(opp.get("vendor_or_category", "N/A"))
            why = _safe_text(opp.get("description", ""))
            action = _safe_text(opp.get("action", ""))
            savings = float(opp.get("estimated_savings", 0) or 0)
            total_opportunity += savings

            story.append(Paragraph(f"<b>{opp_type}</b>", body))
            story.append(Paragraph(f"<b>Area:</b> {area}", body))
            if why:
                story.append(Paragraph(f"<b>Why it matters:</b> {why}", body))
            if action:
                story.append(Paragraph(f"<b>Recommended Action:</b> {action}", body))
            story.append(Paragraph(f"<b>Estimated Savings:</b> ${savings:,.0f}", body))
            story.append(Spacer(1, 8))

    story.append(Paragraph(f"<b>Total Identified Opportunity:</b> ${total_opportunity:,.0f}", body))
    story.append(Spacer(1, 10))

    # ---------------- Recommendations ----------------
    story.append(Paragraph("Strategic Recommendations", h2))
    recs = analysis.get("recommendations") or []
    if not recs:
        story.append(Paragraph("No strategic recommendations returned.", body))
    else:
        rec_rows = [["Priority", "Action", "Expected Impact", "Effort"]]
        for r in recs[:12]:
            rec_rows.append(
                [
                    _safe_text(str(r.get("priority", "medium")).upper()),
                    _safe_text(r.get("action", "")),
                    _safe_text(r.get("expected_impact", "")),
                    _safe_text(str(r.get("effort", ""))).title(),
                ]
            )
        story.append(_styled_table(rec_rows, col_widths=[0.9 * inch, 3.0 * inch, 1.7 * inch, 0.9 * inch]))

    story.append(Spacer(1, 12))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles["Italic"]))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# -------------------------
# Helpers
# -------------------------
def _safe_text(x: Any) -> str:
    if x is None:
        return ""
    s = str(x)
    # Avoid ReportLab choking on odd control chars
    return " ".join(s.replace("\r", " ").replace("\n", " ").split()).strip()


def _safe_str_timestamp(ts: Any) -> str:
    if ts is None:
        return ""
    try:
        # Snowflake connector often returns datetime already
        return str(ts)
    except Exception:
        return ""


def _money(x: Any) -> str:
    try:
        return f"${float(x or 0):,.0f}"
    except Exception:
        return "$0"


def _styled_table(rows: List[List[str]], col_widths: Optional[List[float]] = None) -> Table:
    tbl = Table(rows, colWidths=col_widths)
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("ALIGN", (0, 0), (-1, 0), "LEFT"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cccccc")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTSIZE", (0, 1), (-1, -1), 9),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fafafa")]),
            ]
        )
    )
    return tbl