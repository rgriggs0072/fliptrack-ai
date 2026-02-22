# ---------------- Home.py ----------------
# -*- coding: utf-8 -*-
"""
FlipTrack AI - Home Page
========================
AI-first property investment tracking for house flippers and rental rehab companies.

Page Overview (for future devs)
------------------------------
- Initializes the page shell (branding, config, auth, sidebar/nav)
- Shows a home dashboard (quick stats, projects table, getting started)
- Shows Vendor Intelligence:
    - Reads latest persisted analysis from Snowflake
    - Allows running analysis on demand
    - Displays a human-readable output
    - Allows exporting the latest results to a PDF

Important implementation notes:
- Snowflake connection is cached (st.cache_resource) — DO NOT close it here.
- DO close cursors.
- Streamlit deprecation:
    - use width="stretch" instead of use_container_width=True
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

# Keep legacy import behavior stable
import sys
sys.path.append(str(Path(__file__).parent))

from agents.vendor_intel_agent import VendorIntelligenceAgent
from utils.snowflake_connection import get_connection, switch_to_client_database
from utils.page_shell import init_page
from utils.pdf_exports import build_vendor_intelligence_pdf

# If init_page does NOT render sidebar, uncomment:
# from utils.sidebar import render_sidebar


# -----------------------------------------------------------------------------
# Formatting helpers
# -----------------------------------------------------------------------------
def _clean_expected_impact(text: str) -> str:
    """
    Force-normalize LLM expected_impact into a consistent money range.

    Output examples:
      "$800-$1,200 saved"
      "$1,500-$2,000 saved"
      "$300-$500 saved"
    """
    if not text:
        return ""

    s = str(text).replace("–", "-").replace("−", "-")
    s = re.sub(r"\s+", " ", s).strip()

    raw_nums = re.findall(r"\d[\d,]*", s)
    nums = []
    for n in raw_nums:
        try:
            nums.append(int(n.replace(",", "")))
        except Exception:
            pass

    if not nums:
        return s

    suffix = " saved" if re.search(r"\bsav", s, flags=re.IGNORECASE) else ""

    if len(nums) >= 3 and nums[0] == nums[1]:
        low, high = nums[0], nums[-1]
    elif len(nums) >= 2:
        low, high = nums[0], nums[1]
    else:
        low, high = nums[0], None

    def money(x: int) -> str:
        return f"${x:,.0f}"

    if high is None or high == low:
        return f"{money(low)}{suffix}".strip()

    return f"{money(low)}-{money(high)}{suffix}".strip()


def _ensure_vendor_tables_once(agent: VendorIntelligenceAgent, cursor) -> None:
    """
    Ensure AGENT_INSIGHTS exists once per Streamlit session.
    Avoids repeated DDL calls on every rerun.
    """
    if st.session_state.get("vendor_intel_tables_ready"):
        return
    agent.ensure_tables(cursor)
    st.session_state["vendor_intel_tables_ready"] = True


# -----------------------------------------------------------------------------
# Vendor Intelligence renderer
# -----------------------------------------------------------------------------
def _render_vendor_intelligence(agent: VendorIntelligenceAgent, cursor, company_name: str) -> None:
    """
    Vendor Intelligence section UI.

    UX goals:
    - Clear action button for running analysis
    - Always show latest saved analysis if it exists
    - Avoid noisy reruns (use button triggers + st.rerun())
    - Provide PDF export for the latest saved results
    """
    st.subheader("🤖 AI Vendor Intelligence")
    st.markdown("*Autonomous business insights from your vendor data*")

    _ensure_vendor_tables_once(agent, cursor)

    # Header actions row
    left, right = st.columns([3, 1])
    with left:
        latest_peek = agent.get_latest_insights(cursor)
        if latest_peek and latest_peek.get("generated_at"):
            try:
                gen_at = latest_peek["generated_at"]
                hrs = (datetime.now() - gen_at).total_seconds() / 3600
                st.caption(f"Last analyzed: {int(hrs)} hours ago")
            except Exception:
                pass

    with right:
        refresh_clicked = st.button("🔄 Refresh Insights", type="secondary", width="stretch")

    if refresh_clicked:
        st.rerun()

    run_clicked = st.button("Run Vendor Analysis", type="primary", width="stretch")
    if run_clicked:
        with st.spinner("🤖 Agent is analyzing vendor data..."):
            result = agent.analyze_vendors(cursor)
            if result:
                st.success("✅ Analysis complete!")
                st.rerun()

    latest = agent.get_latest_insights(cursor)
    if not latest:
        st.info("No vendor analysis yet. Run your first analysis to get started.")
        return

    st.divider()

    generated_at = latest.get("generated_at")
    estimated_savings = float(latest.get("estimated_savings", 0) or 0)
    analysis = latest.get("vendor_analysis") or {}

    st.caption(f"Latest run: {generated_at}")
    st.metric("Estimated Savings", f"${estimated_savings:,.0f}")

    # PDF export (latest saved)
    try:
        pdf_bytes = build_vendor_intelligence_pdf(
            company_name=company_name,
            generated_at=generated_at,
            estimated_savings=estimated_savings,
            analysis=analysis,
        )
        fname_ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        st.download_button(
            "⬇️ Download Vendor Intelligence PDF",
            data=pdf_bytes,
            file_name=f"{company_name}_vendor_intelligence_{fname_ts}.pdf",
            mime="application/pdf",
            type="secondary",
            width="stretch",
        )
    except Exception as e:
        st.warning(f"PDF export unavailable: {e}")

    st.divider()

    # ---------------------------
    # Top Vendors (Spend Concentration)
    # ---------------------------
    st.write("### 🧾 Top Vendors (Spend Concentration)")
    top_vendors = analysis.get("top_vendors") or []
    grand_total = float((analysis.get("meta") or {}).get("grand_total", 0) or 0)

    if not top_vendors:
        st.info("No top vendor breakdown returned.")
    else:
        df_top = pd.DataFrame(top_vendors)

        for col, default in {
            "vendor": "",
            "spend": 0,
            "transactions": 0,
            "insight": "",
        }.items():
            if col not in df_top.columns:
                df_top[col] = default

        df_top["spend"] = pd.to_numeric(df_top["spend"], errors="coerce").fillna(0.0)
        df_top["transactions"] = pd.to_numeric(df_top["transactions"], errors="coerce").fillna(0).astype(int)

        computed_total = float(df_top["spend"].sum())
        denom = grand_total if grand_total > 0 else computed_total

        top1 = float(df_top.iloc[0]["spend"]) if len(df_top) else 0.0
        top5 = float(df_top["spend"].head(5).sum())

        c1, c2, c3 = st.columns(3)
        c1.metric("Top vendor spend", f"${top1:,.0f}")
        c2.metric("Top vendor share", f"{(top1 / denom * 100):.1f}%" if denom > 0 else "—")
        c3.metric("Top 5 share", f"{(top5 / denom * 100):.1f}%" if denom > 0 else "—")

        df_show = df_top[["vendor", "spend", "transactions", "insight"]].copy()
        df_show.rename(columns={"vendor": "Vendor", "spend": "Spend", "transactions": "Txns", "insight": "Insight"}, inplace=True)
        df_show["Spend"] = df_show["Spend"].map(lambda x: f"${float(x):,.0f}")

        st.dataframe(df_show, width="stretch", hide_index=True)

    # ---------------------------
    # Executive Summary
    # ---------------------------
    st.write("### 🔎 Executive Summary")
    insights = (analysis.get("key_insights") or [])[:3]
    if insights:
        for insight in insights:
            st.markdown(f"- {insight}")
    else:
        st.info("No insights returned.")

    # ---------------------------
    # Opportunities + total
    # ---------------------------
    st.write("### 💡 Cost-Saving Opportunities")
    opps = analysis.get("opportunities") or []

    total_opportunity = 0.0
    if not opps:
        st.info("No specific cost-saving opportunities identified.")
    else:
        for opp in opps:
            opp_type = str(opp.get("type", "") or "").replace("_", " ").title()
            area = str(opp.get("vendor_or_category", "N/A") or "N/A")
            why = str(opp.get("description", "") or "").strip()
            action = str(opp.get("action", "") or "").strip()

            savings = float(opp.get("estimated_savings", 0) or 0)
            total_opportunity += savings

            st.markdown(f"#### {opp_type or 'Opportunity'}")
            st.write(f"Area: {area}")
            if why:
                st.write(f"Why it matters: {why}")
            if action:
                st.write(f"Recommended Action: {action}")
            st.write(f"Estimated Savings: ${savings:,.0f}")
            st.divider()

    st.success(f"Total Identified Opportunity: ${total_opportunity:,.0f}")

    # ---------------------------
    # Recommendations
    # ---------------------------
    st.write("### 📋 Strategic Recommendations")
    recs = analysis.get("recommendations") or []
    if not recs:
        st.info("No strategic recommendations returned.")
        return

    for rec in recs:
        priority = str(rec.get("priority", "medium") or "medium").upper()
        icon = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(priority, "🟡")

        action = (rec.get("action") or "").strip()
        expected = _clean_expected_impact(rec.get("expected_impact") or "")
        effort = str(rec.get("effort", "") or "").strip().title()

        st.markdown(f"{icon} **Priority: {priority}**")
        if action:
            st.write(f"Action: {action}")
        if expected:
            st.text(f"Expected Impact: {expected}")
        if effort:
            st.write(f"Effort Level: {effort}")
        st.divider()


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
def main() -> None:
    # Init shell (branding + config + auth + sidebar/nav)
    brand, user_info = init_page("kituwah_properties")

    # If init_page does NOT render sidebar/nav, do it here:
    # render_sidebar(brand)

    company_name = brand.get("company", "FlipTrack AI")
    client_name = (user_info or {}).get("client_name", "Guest")

    # Header (keeps your original look)
    st.markdown(f'<h1 class="main-header">{company_name}</h1>', unsafe_allow_html=True)
    st.markdown(f'<p class="subtitle">Welcome back, {client_name}!</p>', unsafe_allow_html=True)
    st.divider()

    # Quick Stats (placeholders as-is)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Active Projects", "1", delta="+0 this month")
    with col2:
        st.metric("Total Invested", "$146.5K", delta="+$0 this month")
    with col3:
        st.metric("CI / MI Split", "90% / 10%", delta="Cash heavy")
    with col4:
        st.metric("Days Active", "1,237", delta="41 months")
    st.divider()

    # Vendor Intelligence (Snowflake-backed)
    cursor = None
    try:
        conn = get_connection()

        if not switch_to_client_database(conn):
            st.error("No client database context found. Please log in again.")
            st.stop()

        cursor = conn.cursor()
        agent = VendorIntelligenceAgent()
        _render_vendor_intelligence(agent, cursor, company_name=company_name)

    except Exception as e:
        st.error(f"Home page error: {e}")

    finally:
        try:
            if cursor:
                cursor.close()
        except Exception:
            pass

    st.divider()

    # Projects table (original demo data)
    st.subheader("📊 Your Projects")
    project_data = {
        "Project": ["5122 Bonnell Ave"],
        "Type": ["Rental Rehab"],
        "Status": ["In Progress"],
        "Purchase": ["$86,271"],
        "Invested": ["$146,546"],
        "Days": [1237],
        "Budget %": ["N/A"],
    }
    st.dataframe(pd.DataFrame(project_data), width="stretch", hide_index=True)

    st.divider()

    info_col1, info_col2 = st.columns(2)
    with info_col1:
        st.info(
            """
**🎯 Getting Started**

1. **Add your first expense** — voice, receipt scan, or manual entry
2. **Import existing data** — upload your Excel spreadsheet
3. **Set budgets** — track spending vs. budget
4. **Generate reports** — export for investors/lenders
"""
        )

    with info_col2:
        st.success(
            """
**✨ AI Features**

- 🎤 **Voice Entry** — just speak your expenses
- 📸 **Receipt OCR** — snap a photo, auto-extract data
- 🤖 **Smart Categories** — AI categorizes automatically
- 💡 **Budget Alerts** — get notified when over budget
"""
        )

    st.divider()
    st.caption("FlipTrack AI — Powered by Claude & Snowflake | © 2026")


if __name__ == "__main__":
    main()