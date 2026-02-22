"""
Excel Import AI Agent
====================
Uses Claude AI to analyze Excel structure, categorize expenses, and import data.
"""

import pandas as pd
import anthropic
import streamlit as st
from datetime import datetime
from utils.snowflake_connection import get_connection, get_client_database


class ExcelImportAgent:
    """
    AI agent that intelligently imports Excel expense data.
    """
    
    def __init__(self):
        self.client = anthropic.Anthropic(
            api_key=st.secrets.get("anthropic", {}).get("api_key", "")
        )
    
    def analyze_structure(self, df):
        """
        Use AI to analyze Excel structure and detect columns.
        """
        
        # Get column names and sample data
        columns = df.columns.tolist()
        sample_rows = df.head(3).to_dict('records')
        
        # Ask Claude to analyze
        prompt = f"""
        Analyze this Excel spreadsheet structure and identify the columns:
        
        Columns: {columns}
        Sample data: {sample_rows}
        
        Please identify which column contains:
        - date (expense date)
        - amount (dollar amount)
        - description (what was purchased/paid for)
        - ci_m (if there's a column for CI/M or Cash/Financed classification)
        - vendor (if separate from description)
        
        Respond in JSON format:
        {{
            "date_column": "column_name",
            "amount_column": "column_name", 
            "description_column": "column_name",
            "ci_m_column": "column_name or null",
            "vendor_column": "column_name or null"
        }}
        """
        
        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            import json
            result = json.loads(response.content[0].text)
            
            return {
                'row_count': len(df),
                'columns': columns,
                **result
            }
        
        except Exception as e:
            # Fallback to heuristic detection
            return {
                'row_count': len(df),
                'columns': columns,
                'date_column': self._detect_date_column(columns),
                'amount_column': self._detect_amount_column(columns),
                'description_column': self._detect_description_column(columns),
                'ci_m_column': self._detect_ci_m_column(columns)
            }
    
    def _detect_date_column(self, columns):
        """Heuristic date column detection"""
        for col in columns:
            if any(word in col.lower() for word in ['date', 'when', 'day']):
                return col
        return columns[0]
    
    def _detect_amount_column(self, columns):
        """Heuristic amount column detection"""
        for col in columns:
            if any(word in col.lower() for word in ['amount', 'cost', 'price', 'total', '$']):
                return col
        return columns[2] if len(columns) > 2 else columns[-1]
    
    def _detect_description_column(self, columns):
        """Heuristic description column detection"""
        for col in columns:
            if any(word in col.lower() for word in ['desc', 'detail', 'note', 'memo', 'what']):
                return col
        return columns[1] if len(columns) > 1 else columns[0]
    
    def _detect_ci_m_column(self, columns):
        """Heuristic CI/M column detection"""
        for col in columns:
            if any(word in col.lower() for word in ['ci', 'cash', 'finance', 'type']):
                return col
        return None
    
    def categorize_expense(self, description, vendor=None):
        """
        Use AI to categorize an expense based on description.
        """
        
        prompt = f"""
Categorize this property renovation/construction expense:

Description: "{description}"
{f"Vendor: {vendor}" if vendor else ""}

Choose the BEST category from this list:
- Acquisition (property purchase, down payment)
- Closing Costs (title, survey, escrow fees)
- Demo (demolition, teardown)
- Cleanup (debris removal, cleanup, mowing, hauling)
- Site Work (grading, fill dirt, excavation, erosion control, silt fence)
- Permits & Inspections (building permits, inspections)
- Plans & Engineering (blueprints, architectural plans, engineering)
- Foundation (foundation work, piers, drilling, footings)
- Concrete (concrete work, flatwork, slabs, driveways)
- Framing (lumber, studs, framing materials)
- Plumbing (plumbing work, pipes, fixtures)
- Electrical (electrical work, wiring, panels, temp pole)
- HVAC (heating, cooling, AC, furnace)
- Roofing (roof work, shingles, gutters)
- Siding (exterior siding, hardie board)
- Windows & Doors (windows, doors, installation)
- Drywall (drywall, sheetrock, taping, mudding)
- Painting (paint, primer, painting work)
- Flooring (flooring, tile, carpet, hardwood)
- Cabinets & Countertops (cabinets, countertops, vanities)
- Appliances (appliances, fridge, stove, washer, dryer)
- Landscaping (landscaping, grass, sod, plants, trees)
- Utilities (water bill, electric bill, gas, ongoing utilities)
- Materials (general materials from Home Depot, Lowe's, lumber yards)
- Professional Services (attorney, accountant, appraiser)
- Other (if truly doesn't fit above)

Examples:
- "Purchase" → Acquisition
- "The Title Company (survey)" → Closing Costs
- "Edgar Tellez (Demo)" → Demo
- "Fort Worth Water" → Utilities
- "TXU" → Utilities
- "Ricardo Nava (Plans)" → Plans & Engineering
- "Ross Inspections (permit)" → Permits & Inspections
- "Home Depot (framing)" → Framing
- "Lowe's (cabinets)" → Cabinets & Countertops
- "Juan Rivera (concrete)" → Concrete
- "Ray Tallant (Plumbing)" → Plumbing

Also extract the vendor name (the company/person being paid).

Respond ONLY with valid JSON (no markdown):
{{
    "category": "exact_category_name_from_list",
    "vendor": "vendor_name",
    "confidence": 0.95
}}
"""
        
        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )
            
            import json
            return json.loads(response.content[0].text)
        
        except:
            # Fallback
            return {
                "category": "Other",
                "vendor": vendor or self._extract_vendor_heuristic(description),
                "confidence": 0.5
            }
    
    def _extract_vendor_heuristic(self, description):
        """Extract vendor name using simple heuristics"""
        import re
        
        # Look for text before parenthesis
        match = re.match(r'^([^(]+)', description)
        if match:
            return match.group(1).strip()
        
        # Take first few words
        words = description.split()
        return ' '.join(words[:3]) if len(words) >= 3 else description
    
    def import_with_ai(self, df, date_col, amount_col, desc_col, ci_m_col=None, 
                      project=None, progress_callback=None):
        """
        Import Excel data with AI categorization.
        """
        
        conn = get_connection()
        database, schema = get_client_database()
        
        cursor = conn.cursor()
        cursor.execute(f"USE DATABASE {database}")
        cursor.execute(f"USE SCHEMA {schema}")
        
        # Get project_id
        cursor.execute("SELECT project_id FROM PROJECTS WHERE project_name = %s", (project,))
        project_result = cursor.fetchone()
        project_id = project_result[0] if project_result else None
        
        if not project_id:
            raise Exception(f"Project '{project}' not found")
        
        imported = 0
        categorized = 0
        vendors_extracted = 0
        total_amount = 0
        sample_categorizations = []
        
        for idx, row in df.iterrows():
            # Progress callback
            if progress_callback:
                progress = int((idx / len(df)) * 100)
                progress_callback(progress, f"Processing row {idx+1}/{len(df)}...")
            
            # Extract data
            try:
                expense_date = pd.to_datetime(row[date_col]).date()
                amount = float(row[amount_col])
                description = str(row[desc_col])
                
                # Get CI/M from column if available
                if ci_m_col and ci_m_col != 'Auto-detect' and ci_m_col in df.columns:
                    ci_m = str(row[ci_m_col]).strip().upper()
                    # Normalize variations
                    if ci_m in ['MI', 'M', 'FINANCED', 'FINANCE']:
                        ci_m = 'MI'
                    else:
                        ci_m = 'CI'
                else:
                    ci_m = 'CI'  # Default
                
                # AI categorization
                cat_result = self.categorize_expense(description)
                category = cat_result['category']
                vendor = cat_result['vendor']
                
                # Insert into database
                cursor.execute("""
                    INSERT INTO EXPENSES (
                        project_id, expense_date, amount, investment_type,
                        vendor_name, description, category, entry_method
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'import_ai')
                """, (project_id, expense_date, amount, ci_m, vendor, description, category))
                
                imported += 1
                total_amount += amount
                
                if cat_result['confidence'] > 0.8:
                    categorized += 1
                
                if vendor and vendor != description[:20]:
                    vendors_extracted += 1
                
                # Save sample for display
                if len(sample_categorizations) < 5:
                    sample_categorizations.append({
                        'Description': description[:50],
                        'Amount': f"${amount:,.2f}",
                        'Category': category,
                        'Vendor': vendor,
                        'CI/M': ci_m
                    })
            
            except Exception as e:
                st.warning(f"Skipped row {idx+1}: {e}")
                continue
        
        cursor.close()
        
        return {
            'imported': imported,
            'categorized': categorized,
            'vendors_extracted': vendors_extracted,
            'total_amount': total_amount,
            'sample_categorizations': sample_categorizations
        }
