"""
Sidebar Utility
===============
Call render_sidebar() at the top of every page for a consistent branded
sidebar with logo, navigation, and logout.

Uses ONLY native Streamlit components — no st.markdown HTML — to avoid
the HTML-escaping and CSS-bleed issues inside st.sidebar.

Usage:
    from utils.sidebar import render_sidebar
    render_sidebar()
"""

import streamlit as st
from pathlib import Path


def render_sidebar(brand: dict | None = None, client_name: str = "kituwah_properties"):
    """
    Render branded sidebar on any page.

    Args:
        brand:       Brand config dict from get_brand(). Auto-loaded if None.
        client_name: Folder name under images/ containing logo.svg
    """
    if brand is None:
        from utils.branding import get_brand
        brand = get_brand(client_name)

    # ── Hide Streamlit's auto-generated pages nav ──────────────────────────
    # Placed outside st.sidebar — CSS is global regardless of injection point.
    # Multiple selectors for compatibility across Streamlit versions.
    st.markdown(
        """
        <style>
            [data-testid="stSidebarNav"]          { display: none !important; }
            [data-testid="stSidebarNavItems"]      { display: none !important; }
            [data-testid="stSidebarNavSeparator"]  { display: none !important; }
            ul[data-testid="stSidebarNavItems"]    { display: none !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:

        # ── Logo ──────────────────────────────────────────────────────────
        _render_logo(client_name, brand)

        st.divider()

        # ── Navigation — st.page_link renders natively, no HTML needed ────
        st.caption("NAVIGATION")

        st.page_link("Home.py",                             label="Home",                 icon="🏠")
        st.page_link("pages/1_📊_Dashboard.py",             label="Dashboard",            icon="📊")
        st.page_link("pages/2_➕_Add_Expense.py",           label="Add Expense",          icon="➕")
        st.page_link("pages/3_📥_Import_Data.py",           label="Import Data",          icon="📥")
        st.page_link("pages/4_📄_Export_Report.py",         label="Export Report",        icon="📄")
        st.page_link("pages/5_🧠_AI_Data_Intelligence.py",  label="AI Data Intelligence", icon="🧠")

        st.divider()

        # ── User info ─────────────────────────────────────────────────────
        user_info    = st.session_state.get("user_info", {})
        display_name = user_info.get("client_name", "")
        if display_name:
            st.caption("Logged in as")
            st.write(f"**{display_name}**")

        # ── Logout ────────────────────────────────────────────────────────
        if st.button("🚪 Logout", key="sidebar_logout", use_container_width=True):
            st.session_state.clear()
            st.rerun()


# ── Logo helper ───────────────────────────────────────────────────────────────

def _render_logo(client_name: str, brand: dict):
    """
    Display logo using st.image() — Streamlit renders SVG files natively
    without any HTML injection, so there is zero risk of CSS bleed.
    """
    logo_path = Path(f"images/{client_name}/logo.svg")

    if logo_path.exists():
        st.image(str(logo_path), width=160)
    else:
        company = brand.get("company", "FlipTrack AI")
        st.markdown(f"### {company}")
