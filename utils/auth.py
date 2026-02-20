"""
Authentication Utility
=====================
Handles user login and session management.
"""

import streamlit as st
import hashlib
from utils.snowflake_connection import get_connection


def check_authentication():
    """
    Check if user is authenticated.
    If not, show login page.
    Returns True if authenticated, False otherwise.
    """
    
    # Check if already authenticated
    if st.session_state.get('authenticated', False):
        return True
    
    # Show login page
    show_login_page()
    return False


def show_login_page():
    """
    Display login form with client branding.
    """
    
    # Load Kituwah branding
    import json
    try:
        with open("images/kituwah_properties/brand_colors.json") as f:
            brand = json.load(f)
        primary_color = brand['colors']['primary_red']
    except:
        primary_color = "#D32F2F"  # Fallback
    
    # Custom CSS with brand colors
    st.markdown(f"""
    <style>
        .login-header {{
            text-align: center;
            margin-bottom: 2rem;
        }}
        .brand-title {{
            color: {primary_color};
            font-size: 2rem;
            font-weight: bold;
            margin-top: 1rem;
        }}
    </style>
    """, unsafe_allow_html=True)
    
    # Display logo
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        try:
            st.image("images/kituwah_properties/logo.svg", width=300)
        except:
            st.markdown('<h1 class="main-header">🏠 FlipTrack AI</h1>', unsafe_allow_html=True)
            st.markdown('<p class="subtitle">AI-First Property Investment Tracking</p>', unsafe_allow_html=True)
    
    st.divider()
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.subheader("🔐 Login")
        
        with st.form("login_form"):
            email = st.text_input("Email", placeholder="you@company.com")
            password = st.text_input("Password", type="password")
            
            submit = st.form_submit_button("Login", width="stretch", type="primary")
            
            if submit:
                if authenticate_user(email, password):
                    st.success("✅ Login successful!")
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials")
        
        st.divider()
        st.caption("FlipTrack AI - Powered by Claude & Snowflake")


def authenticate_user(email, password):
    """
    Authenticate user against FLIPTRACK_TENANTS.USERDATA.
    Returns True if successful, False otherwise.
    """
    
    if not email or not password:
        return False
    
    try:
        # Hash password
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        # Connect to Snowflake
        conn = get_connection()
        cursor = conn.cursor()
        
        # Switch to tenants database
        cursor.execute("USE DATABASE FLIPTRACK_TENANTS")
        cursor.execute("USE SCHEMA FLIPTRACK_TENANTS_SCH")
        
        # Query user
        query = """
            SELECT 
                u.user_id,
                u.email,
                u.first_name,
                u.last_name,
                c.client_id,
                c.client_name,
                c.database_name,
                c.schema_name
            FROM USERDATA u
            JOIN CLIENTS c ON u.client_id = c.client_id
            WHERE u.email = %s 
            AND u.password_hash = %s
            AND u.is_active = TRUE
            AND c.status = 'active'
        """
        
        cursor.execute(query, (email, password_hash))
        result = cursor.fetchone()
        cursor.close()
        
        if result:
            # Store user info in session
            st.session_state.authenticated = True
            st.session_state.user_info = {
                'user_id': result[0],
                'email': result[1],
                'first_name': result[2],
                'last_name': result[3],
                'client_id': result[4],
                'client_name': result[5],
                'database_name': result[6],
                'schema_name': result[7]
            }
            
            # Update last login
            update_last_login(result[0])
            
            return True
        
        return False
    
    except Exception as e:
        st.error(f"Authentication error: {e}")
        return False


def update_last_login(user_id):
    """
    Update last_login timestamp for user.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("USE DATABASE FLIPTRACK_TENANTS")
        cursor.execute("USE SCHEMA FLIPTRACK_TENANTS_SCH")
        
        cursor.execute("""
            UPDATE USERDATA 
            SET last_login = CURRENT_TIMESTAMP(),
                login_count = login_count + 1
            WHERE user_id = %s
        """, (user_id,))
        
        cursor.close()
    
    except Exception as e:
        # Don't fail authentication if this fails
        pass


def logout():
    """
    Log out the current user.
    """
    st.session_state.authenticated = False
    st.session_state.user_info = {}
    st.rerun()
