"""
Branding Utility
================
Centralized client branding system for multi-tenant white-label app.
"""

import streamlit as st
import json
from pathlib import Path


def load_client_branding(client_name="kituwah_properties"):
    """
    Load client branding configuration.
    
    Args:
        client_name: Client folder name in images/
        
    Returns:
        dict: Brand configuration
    """
    
    try:
        brand_path = Path(f"images/{client_name}/brand_colors.json")
        with open(brand_path) as f:
            return json.load(f)
    except Exception as e:
        # Fallback branding
        return {
            "company": "FlipTrack AI",
            "colors": {
                "primary_red": "#667eea",
                "dark_red": "#764ba2"
            },
            "contact": {
                "owner": "Support",
                "email": "support@fliptrack.ai"
            }
        }


def apply_custom_css(brand):
    """
    Apply custom CSS with client brand colors and professional styling.
    
    Args:
        brand: Brand configuration dict
    """
    
    # Kituwah Color Palette
    primary_red = "#D32F2F"
    sidebar_blue = "#1E88E5"
    bg_light_gray = "#E0E0E0"
    text_black = "#121212"
    success_green = "#66BB6A"
    warning_amber = "#FFC107"
    alert_orange = "#F4511E"
    medium_gray = "#9E9E9E"
    
    css = f"""
    <style>
        /* Main app background */
        .main {{
            background-color: {bg_light_gray} !important;
        }}
        
        /* Sidebar styling */
        [data-testid="stSidebar"] {{
            background: linear-gradient(180deg, {sidebar_blue} 0%, #1565C0 100%) !important;
        }}
        
        [data-testid="stSidebar"] * {{
            color: white !important;
        }}
        
        [data-testid="stSidebar"] .css-1d391kg {{
            color: white !important;
        }}
        
        /* Headers */
        .main-header {{
            color: {primary_red};
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 0;
        }}
        
        .subtitle {{
            color: {text_black};
            font-size: 1.1rem;
            margin-top: 0;
        }}
        
        /* All headings */
        h1, h2, h3 {{
            color: {primary_red} !important;
        }}
        
        /* Primary buttons */
        .stButton>button[kind="primary"] {{
            background-color: {primary_red} !important;
            border-color: {primary_red} !important;
            color: white !important;
            font-weight: 600 !important;
        }}
        
        .stButton>button[kind="primary"]:hover {{
            background-color: #B71C1C !important;
            border-color: #B71C1C !important;
            box-shadow: 0 4px 8px rgba(211, 47, 47, 0.3) !important;
        }}
        
        /* Secondary buttons */
        .stButton>button {{
            border-color: {primary_red} !important;
            color: {primary_red} !important;
        }}
        
        .stButton>button:hover {{
            background-color: {bg_light_gray} !important;
            border-color: {primary_red} !important;
        }}
        
        /* Text inputs and text areas */
        .stTextInput input, .stTextArea textarea {{
            background-color: white !important;
            border: 2px solid {medium_gray} !important;
            border-radius: 8px !important;
            color: {text_black} !important;
        }}
        
        .stTextInput input:focus, .stTextArea textarea:focus {{
            border-color: {primary_red} !important;
            box-shadow: 0 0 0 2px rgba(211, 47, 47, 0.2) !important;
        }}
        
        /* Select boxes and other inputs */
        .stSelectbox select, .stMultiSelect {{
            background-color: white !important;
            border: 2px solid {medium_gray} !important;
            border-radius: 8px !important;
        }}
        
        /* Number inputs */
        .stNumberInput input {{
            background-color: white !important;
            border: 2px solid {medium_gray} !important;
            border-radius: 8px !important;
        }}
        
        /* Metrics */
        [data-testid="stMetricValue"] {{
            color: {primary_red} !important;
            font-weight: 700 !important;
        }}
        
        [data-testid="stMetricLabel"] {{
            color: {text_black} !important;
            font-weight: 500 !important;
        }}
        
        [data-testid="stMetricDelta"] {{
            color: {success_green} !important;
        }}
        
        /* Success messages */
        .stSuccess {{
            background-color: {success_green} !important;
            color: white !important;
        }}
        
        /* Warning messages */
        .stWarning {{
            background-color: {warning_amber} !important;
            color: {text_black} !important;
        }}
        
        /* Error messages */
        .stError {{
            background-color: {alert_orange} !important;
            color: white !important;
        }}
        
        /* Info messages */
        .stInfo {{
            background-color: {sidebar_blue} !important;
            color: white !important;
        }}
        
        /* Links */
        a {{
            color: {primary_red} !important;
            font-weight: 500 !important;
        }}
        
        a:hover {{
            color: {sidebar_blue} !important;
        }}
        
        /* Dividers */
        hr {{
            border-color: {primary_red} !important;
            opacity: 0.3;
        }}
        
        /* Cards/Containers */
        .stContainer {{
            background-color: white !important;
            border-radius: 10px !important;
            padding: 20px !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1) !important;
        }}
        
        /* Dataframes */
        .stDataFrame {{
            background-color: white !important;
            border-radius: 8px !important;
        }}
        
        /* Expanders */
        .streamlit-expanderHeader {{
            background-color: white !important;
            border: 1px solid {medium_gray} !important;
            border-radius: 8px !important;
            color: {primary_red} !important;
            font-weight: 600 !important;
        }}
        
        .streamlit-expanderHeader:hover {{
            background-color: {bg_light_gray} !important;
        }}
        
        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 8px;
        }}
        
        .stTabs [data-baseweb="tab"] {{
            background-color: white !important;
            border-radius: 8px 8px 0 0 !important;
            color: {text_black} !important;
            font-weight: 500 !important;
        }}
        
        .stTabs [aria-selected="true"] {{
            background-color: {primary_red} !important;
            color: white !important;
        }}
        
        /* File uploader */
        [data-testid="stFileUploader"] {{
            background-color: white !important;
            border: 2px dashed {primary_red} !important;
            border-radius: 8px !important;
        }}
        
        /* Progress bars */
        .stProgress > div > div {{
            background-color: {primary_red} !important;
        }}
        
        /* Spinners */
        .stSpinner > div {{
            border-top-color: {primary_red} !important;
        }}
    </style>
    """
    
    st.markdown(css, unsafe_allow_html=True)


def display_logo(brand, client_name="kituwah_properties", size="medium"):
    """
    Display client logo.
    
    Args:
        brand: Brand configuration
        client_name: Client folder name
        size: 'small', 'medium', 'large'
    """
    
    sizes = {
        'small': 150,
        'medium': 250,
        'large': 400
    }
    
    width = sizes.get(size, 250)
    
    try:
        logo_path = f"images/{client_name}/logo.svg"
        st.image(logo_path, width=width)
    except:
        # Fallback to text
        st.markdown(f"<h1 style='color: {brand['colors']['primary_red']}'>{brand['company']}</h1>", 
                   unsafe_allow_html=True)


def get_header_html(brand, client_name="kituwah_properties"):
    """
    Generate branded header HTML for reports.
    
    Returns:
        str: HTML header with logo and company info
    """
    
    primary = brand['colors']['primary_red']
    company = brand['company']
    tagline = brand.get('contact', {}).get('tagline', '')
    
    return f"""
    <div style="text-align: center; margin-bottom: 30px;">
        <h1 style="color: {primary}; font-family: Georgia, serif; font-size: 36px; margin-bottom: 5px;">
            {company}
        </h1>
        <p style="color: {primary}; font-style: italic; font-size: 18px; margin-top: 0;">
            "{tagline}"
        </p>
    </div>
    """


def get_footer_html(brand):
    """
    Generate branded footer HTML for reports.
    
    Returns:
        str: HTML footer with contact info
    """
    
    contact = brand.get('contact', {})
    owner = contact.get('owner', '')
    phone = contact.get('phone', '')
    email = contact.get('email', '')
    
    return f"""
    <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 2px solid #ccc;">
        <p style="margin: 5px 0;"><strong>{owner}</strong></p>
        <p style="margin: 5px 0;">{phone}</p>
        <p style="margin: 5px 0;">{email}</p>
    </div>
    """


# Global brand instance
_brand_cache = None

def get_brand(client_name="kituwah_properties"):
    """
    Get cached brand configuration.
    """
    global _brand_cache
    if _brand_cache is None:
        _brand_cache = load_client_branding(client_name)
    return _brand_cache
