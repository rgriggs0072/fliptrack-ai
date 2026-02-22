# utils/page_shell.py
# -*- coding: utf-8 -*-
"""
Shared Page Shell

Page Overview (for future devs)
------------------------------
Provides a consistent app shell across all pages:
- set_page_config
- branding + CSS
- authentication gate
- sidebar navigation rendering

Usage:
    from utils.page_shell import init_page
    brand, user_info = init_page("kituwah_properties")
"""

from __future__ import annotations

import streamlit as st

from utils.auth import check_authentication
from utils.branding import get_brand, apply_custom_css
from utils.sidebar import render_sidebar


def init_page(brand_key: str):
    """
    Initialize page shell (branding + auth + sidebar) for every page.

    Important:
    - Must be called before the page renders content.
    - Should be called near the top of each page script.
    """
    brand = get_brand(brand_key)

    # Must be first Streamlit call (before most other st.* rendering)
    st.set_page_config(
        page_title=f"{brand['company']} - FlipTrack AI",
        page_icon="🏠",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    apply_custom_css(brand)

    # Auth gate
    if not check_authentication():
        st.stop()

    # Sidebar must be rendered on every page
    render_sidebar(brand)

    user_info = st.session_state.get("user_info", {}) or {}
    return brand, user_info
