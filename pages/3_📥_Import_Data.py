"""
FlipTrack AI - Import Data (Excel Upload with AI Agent)
=======================================================
Upload Excel files and let AI automatically categorize and import expenses.
"""

import streamlit as st
import pandas as pd
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from utils.auth import check_authentication
from agents.excel_import_agent import ExcelImportAgent

# Page config
st.set_page_config(
    page_title="Import Data - FlipTrack AI",
    page_icon="📥",
    layout="wide"
)

# Check authentication
if not check_authentication():
    st.stop()

# Header
st.title("📥 Import Data")
st.markdown("Upload your Excel spreadsheet and let AI do the heavy lifting!")

st.divider()

# Upload section
st.subheader("📁 Upload Excel File")

uploaded_file = st.file_uploader(
    "Choose an Excel file (.xlsx, .xls, .csv)",
    type=['xlsx', 'xls', 'csv'],
    help="Upload your existing expense tracking spreadsheet"
)

if uploaded_file:
    st.success(f"✅ File uploaded: {uploaded_file.name}")
    
    # Preview the data
    st.subheader("👀 Preview")
    
    try:
        # Read file
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            # Skip first 2 rows (title row and blank row), use row 3 as header
            df = pd.read_excel(uploaded_file, header=2)
        
        st.dataframe(df.head(10), use_container_width=True)
        st.caption(f"Showing first 10 of {len(df)} rows")
        
        st.divider()
        
        # AI Analysis Section
        st.subheader("🤖 AI Analysis")
        
        with st.spinner("🔍 AI is analyzing your spreadsheet..."):
            agent = ExcelImportAgent()
            analysis = agent.analyze_structure(df)
        
        # Show analysis
        col1, col2 = st.columns(2)
        
        with col1:
            st.info(f"""
            **📊 File Structure**
            
            - **Rows**: {analysis['row_count']}
            - **Columns**: {len(analysis['columns'])}
            - **Detected Columns**: {', '.join(analysis['columns'])}
            """)
        
        with col2:
            st.success(f"""
            **✨ AI Recommendations**
            
            - **Date Column**: {analysis.get('date_column', 'Not found')}
            - **Amount Column**: {analysis.get('amount_column', 'Not found')}
            - **Description Column**: {analysis.get('description_column', 'Not found')}
            - **CI/M Column**: {analysis.get('ci_m_column', 'Not found')}
            """)
        
        st.divider()
        
        # Import Configuration
        st.subheader("⚙️ Import Configuration")
        
        # Select project
        project = st.selectbox(
            "Import to which project?",
            ["5122 Bonnell Ave"]  # Will be dynamic from Snowflake
        )
        
        # Confirm mapping
        with st.expander("🔧 Column Mapping (optional - AI detected automatically)", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                date_col = st.selectbox("Date Column", analysis['columns'], 
                                       index=analysis['columns'].index(analysis.get('date_column', analysis['columns'][0])) if analysis.get('date_column') in analysis['columns'] else 0)
                amount_col = st.selectbox("Amount Column", analysis['columns'],
                                         index=analysis['columns'].index(analysis.get('amount_column', analysis['columns'][0])) if analysis.get('amount_column') in analysis['columns'] else 0)
            
            with col2:
                desc_col = st.selectbox("Description Column", analysis['columns'],
                                       index=analysis['columns'].index(analysis.get('description_column', analysis['columns'][0])) if analysis.get('description_column') in analysis['columns'] else 0)
                ci_m_col = st.selectbox("CI/M Column (if available)", ['Auto-detect'] + analysis['columns'],
                                       index=(['Auto-detect'] + analysis['columns']).index(analysis.get('ci_m_column', 'Auto-detect')) if analysis.get('ci_m_column') else 0)
        
        # Import button
        st.divider()
        
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col2:
            if st.button("🚀 Start AI Import", type="primary", use_container_width=True):
                with st.spinner("🤖 AI is importing and categorizing..."):
                    
                    # Progress bar
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    # Import with AI
                    result = agent.import_with_ai(
                        df=df,
                        date_col=date_col,
                        amount_col=amount_col,
                        desc_col=desc_col,
                        ci_m_col=ci_m_col if ci_m_col != 'Auto-detect' else None,
                        project=project,
                        progress_callback=lambda p, msg: (progress_bar.progress(p), status_text.text(msg))
                    )
                    
                    progress_bar.progress(100)
                    status_text.text("✅ Import complete!")
                    
                    # Show results
                    st.success(f"""
                    **✅ Import Successful!**
                    
                    - **{result['imported']}** expenses imported
                    - **{result['categorized']}** auto-categorized by AI
                    - **{result['vendors_extracted']}** vendors identified
                    - **${result['total_amount']:,.2f}** total amount
                    """)
                    
                    # Show sample categorizations
                    if result.get('sample_categorizations'):
                        with st.expander("🔍 Sample AI Categorizations"):
                            sample_df = pd.DataFrame(result['sample_categorizations'])
                            st.dataframe(sample_df, use_container_width=True)
        
        with col3:
            if st.button("❌ Cancel", use_container_width=True):
                st.rerun()
    
    except Exception as e:
        st.error(f"❌ Error reading file: {e}")
        st.info("💡 Make sure your Excel file has headers in the first row")

else:
    # Show example
    st.info("""
    **📚 How It Works:**
    
    1. **Upload** your Excel file (any format)
    2. **AI analyzes** the structure and detects columns
    3. **AI categorizes** each expense automatically
    4. **AI extracts** vendor names from descriptions
    5. **Import** directly to Snowflake
    
    **No manual mapping required!** 🎉
    """)
    
    # Example format
    st.subheader("📋 Example Format")
    
    example_data = {
        'Date': ['2022-09-26', '2023-06-23', '2023-12-08'],
        'Description': ['Purchase', 'Edgar Tellez (Demo)', 'Ricardo Nava (Plans)'],
        'Amount': [86271.08, 1700.00, 2202.20],
        'CI/M': ['CI', 'CI', 'CI']
    }
    
    st.dataframe(pd.DataFrame(example_data), use_container_width=True)
    st.caption("Your file can have any column names - AI will figure it out!")
