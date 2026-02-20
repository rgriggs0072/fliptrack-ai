"""
FlipTrack AI - Add Expense (Voice Entry)
========================================
Add expenses via voice, receipt scan, or manual entry.
"""

import streamlit as st
import pandas as pd
import sys
from pathlib import Path
from datetime import date
import json
from audio_recorder_streamlit import audio_recorder

sys.path.append(str(Path(__file__).parent.parent))

from utils.auth import check_authentication
from utils.snowflake_connection import get_connection, get_client_database
from agents.voice_agent import VoiceAgent
from utils.branding import get_brand, apply_custom_css

# Load brand
brand = get_brand("kituwah_properties")

# Page config
st.set_page_config(
    page_title=f"Add Expense - {brand['company']}",
    page_icon="➕",
    layout="wide"
)

# Apply branding
apply_custom_css(brand)

# Check authentication
if not check_authentication():
    st.stop()

# Header
st.title("➕ Add Expense")
st.markdown("Use voice, receipt scan, or manual entry")

st.divider()

# Get projects for selection
conn = get_connection()
database, schema = get_client_database()

cursor = conn.cursor()
cursor.execute(f"USE DATABASE {database}")
cursor.execute(f"USE SCHEMA {schema}")

cursor.execute("SELECT project_id, project_name FROM PROJECTS ORDER BY created_at DESC")
projects = cursor.fetchall()

if not projects:
    st.warning("No projects found. Create a project first!")
    st.stop()

project_options = {p[1]: p[0] for p in projects}

# Three entry methods
tab1, tab2, tab3 = st.tabs(["🎤 Voice Entry", "📸 Receipt Scan", "✍️ Manual Entry"])

# ============================================================================
# TAB 1: VOICE ENTRY
# ============================================================================
with tab1:
    st.subheader("🎤 Voice Entry")
    st.markdown("**Click the mic and speak your expense!**")
    
    st.info("""
    **Examples:**
    - "Add $2,500 cash payment to Ray Tallant for plumbing on Bonnell, still owe him 8 grand"
    - "Paid Home Depot $450 for framing lumber on 5122 Bonnell, cash"
    - "Add $1,200 financed payment to Juan Rivera for concrete"
    """)
    
    st.divider()
    
    # Browser audio recording
    st.markdown("### 🎙️ Record Your Expense")
    st.caption("Click the microphone, speak clearly, then click stop")
    
    audio_bytes = audio_recorder(
        text="Click to record",
        recording_color="#e8b62c",
        neutral_color="#6aa36f",
        icon_name="microphone",
        icon_size="3x"
    )
    
    if audio_bytes:
        st.audio(audio_bytes, format="audio/wav")
        
        if st.button("🚀 Process Voice Recording", type="primary", width="stretch"):
            
            with st.spinner("🎧 Transcribing audio..."):
                voice_agent = VoiceAgent()
                transcript = voice_agent.transcribe_audio_bytes(audio_bytes)
            
            if transcript:
                st.success(f"✅ Transcribed: *\"{transcript}\"*")
                
                with st.spinner("🤖 AI is parsing the expense..."):
                    parsed = voice_agent.parse_expense(transcript, list(project_options.keys()))
                
                if parsed:
                    # Store in session state so it persists across reruns
                    st.session_state.voice_parsed = parsed
                    st.session_state.voice_transcript = transcript
    
    # Check if we have parsed data in session state
    if 'voice_parsed' in st.session_state:
        parsed = st.session_state.voice_parsed
        transcript = st.session_state.voice_transcript
        
        st.divider()
        st.subheader("✅ Confirm Expense Details")
        
        # Show parsed data in columns
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Amount", f"${parsed.get('amount', 0):,.2f}")
            st.metric("Project", parsed.get('project', 'Unknown'))
        
        with col2:
            st.metric("Vendor", parsed.get('vendor', 'Unknown'))
            st.metric("Category", parsed.get('category', 'Other'))
        
        with col3:
            st.metric("CI/M", parsed.get('investment_type', 'CI'))
            if parsed.get('remaining_balance'):
                st.metric("Remaining Balance", f"${parsed.get('remaining_balance', 0):,.2f}")
        
        # Allow edits
        with st.expander("✏️ Edit Details (Optional)"):
            edited_amount = st.number_input("Amount", value=float(parsed.get('amount', 0)))
            edited_vendor = st.text_input("Vendor", value=parsed.get('vendor', ''))
            
            # Category list
            categories = ['Acquisition', 'Closing Costs', 'Demo', 'Cleanup', 'Site Work',
                         'Permits & Inspections', 'Plans & Engineering', 'Foundation',
                         'Concrete', 'Framing', 'Plumbing', 'Electrical', 'HVAC',
                         'Roofing', 'Siding', 'Windows & Doors', 'Drywall', 'Painting',
                         'Flooring', 'Cabinets & Countertops', 'Appliances', 'Landscaping',
                         'Utilities', 'Materials', 'Professional Services', 'Other']
            
            # Find index of parsed category
            try:
                default_category_index = categories.index(parsed.get('category', 'Other'))
            except ValueError:
                default_category_index = len(categories) - 1  # Default to 'Other'
            
            edited_category = st.selectbox("Category", categories, index=default_category_index)
            edited_ci_m = st.radio("Investment Type", ['CI', 'MI'], 
                index=0 if parsed.get('investment_type') == 'CI' else 1)
                    
        # Save button
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            if st.button("❌ Cancel", width="stretch"):
                # Clear session state
                del st.session_state.voice_parsed
                del st.session_state.voice_transcript
                st.rerun()
        
        with col3:
            if st.button("💾 Save Expense", type="primary", width="stretch"):
                
                project_id = project_options[parsed['project']]
                
                try:
                    cursor.execute("""
                        INSERT INTO EXPENSES (
                            project_id, expense_date, amount, investment_type,
                            vendor_name, description, category, entry_method
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'voice')
                    """, (
                        project_id,
                        date.today(),
                        edited_amount,
                        edited_ci_m,
                        edited_vendor,
                        transcript,  # Original voice transcription
                        edited_category
                    ))
                    
                    # Update project totals
                    cursor.execute("CALL UPDATE_PROJECT_TOTALS(%s)", (project_id,))
                    
                    st.success("✅ Expense saved successfully!")
                    st.balloons()
                    
                    # Clear session state
                    del st.session_state.voice_parsed
                    del st.session_state.voice_transcript
                    
                    # Reload page
                    st.rerun()
                
                except Exception as e:
                    st.error(f"Error saving expense: {e}")

# ============================================================================
# TAB 2: RECEIPT SCAN (Coming Soon)
# ============================================================================
with tab2:
    st.subheader("📸 Receipt Scan")
    st.info("🚧 Coming Soon! Upload receipt photos and AI will extract all data automatically.")

# ============================================================================
# TAB 3: MANUAL ENTRY
# ============================================================================
with tab3:
    st.subheader("✍️ Manual Entry")
    
    with st.form("manual_expense_form"):
        
        col1, col2 = st.columns(2)
        
        with col1:
            selected_project = st.selectbox("Project", list(project_options.keys()))
            expense_date = st.date_input("Date", value=date.today())
            amount = st.number_input("Amount ($)", min_value=0.01, step=0.01)
        
        with col2:
            vendor = st.text_input("Vendor")
            category = st.selectbox("Category", [
                'Acquisition', 'Closing Costs', 'Demo', 'Cleanup', 'Site Work',
                'Permits & Inspections', 'Plans & Engineering', 'Foundation',
                'Concrete', 'Framing', 'Plumbing', 'Electrical', 'HVAC',
                'Roofing', 'Siding', 'Windows & Doors', 'Drywall', 'Painting',
                'Flooring', 'Cabinets & Countertops', 'Appliances', 'Landscaping',
                'Utilities', 'Materials', 'Professional Services', 'Other'
            ])
            investment_type = st.radio("Investment Type", ['CI', 'MI'], horizontal=True)
        
        description = st.text_area("Description (optional)")
        
        submitted = st.form_submit_button("💾 Save Expense", type="primary", width="stretch")
        
        if submitted:
            if amount and vendor:
                project_id = project_options[selected_project]
                
                try:
                    cursor.execute("""
                        INSERT INTO EXPENSES (
                            project_id, expense_date, amount, investment_type,
                            vendor_name, description, category, entry_method
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'manual')
                    """, (
                        project_id, expense_date, amount, investment_type,
                        vendor, description or f"{vendor} - {category}",
                        category
                    ))
                    
                    # Update project totals
                    cursor.execute("CALL UPDATE_PROJECT_TOTALS(%s)", (project_id,))
                    
                    st.success("✅ Expense saved successfully!")
                    st.rerun()
                
                except Exception as e:
                    st.error(f"Error saving expense: {e}")
            else:
                st.error("Please fill in amount and vendor!")

cursor.close()

# Footer
st.divider()
st.caption("FlipTrack AI - Voice-powered expense tracking")
