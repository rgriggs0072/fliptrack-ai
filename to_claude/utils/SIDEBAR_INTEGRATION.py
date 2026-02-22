"""
SIDEBAR INTEGRATION — paste this into each page file
=====================================================
Add these lines near the TOP of every file in pages/, right after
st.set_page_config() (if present) and after check_authentication().

─────────────────────────────────────────────────────────────────────────────
COPY-PASTE BLOCK (same for every page):
─────────────────────────────────────────────────────────────────────────────

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))  # ensures utils/ is on path

from utils.sidebar import render_sidebar
from utils.branding import get_brand

brand = get_brand("kituwah_properties")
render_sidebar(brand)

─────────────────────────────────────────────────────────────────────────────
FULL TEMPLATE — top of each page file should look like this:
─────────────────────────────────────────────────────────────────────────────

import streamlit as st
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from utils.auth import check_authentication
from utils.branding import get_brand, apply_custom_css
from utils.sidebar import render_sidebar

# ── Config & branding ─────────────────────────────────────────────────────────
st.set_page_config(page_title="Page Title - FlipTrack AI", page_icon="📊", layout="wide")

brand = get_brand("kituwah_properties")
apply_custom_css(brand)

# ── Auth ──────────────────────────────────────────────────────────────────────
if not check_authentication():
    st.stop()

# ── Sidebar ───────────────────────────────────────────────────────────────────
render_sidebar(brand)

# ── Page content below ────────────────────────────────────────────────────────
st.title("Your Page Title")
...

─────────────────────────────────────────────────────────────────────────────
PAGE-SPECIFIC VALUES:
─────────────────────────────────────────────────────────────────────────────

1_📊_Dashboard.py         → page_title="Dashboard - FlipTrack AI",       page_icon="📊"
2_➕_Add_Expense.py       → page_title="Add Expense - FlipTrack AI",      page_icon="➕"
3_📥_Import_Data.py       → page_title="Import Data - FlipTrack AI",      page_icon="📥"
4_📄_Export_Report.py     → page_title="Export Report - FlipTrack AI",    page_icon="📄"
5_🧠_AI_Data_Intelligence.py → page_title="AI Intelligence - FlipTrack AI", page_icon="🧠"
"""
