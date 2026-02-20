"""
AI Query Agent
==============
Generates smart SQL queries with context awareness and export capabilities with client branding.
"""

import streamlit as st
import anthropic
import pandas as pd
from io import BytesIO
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from utils.branding import get_brand


class QueryAgent:
    """
    AI-powered query agent that generates context-aware SQL and exports results with branding.
    """
    
    def __init__(self):
        self.claude = anthropic.Anthropic(api_key=st.secrets["anthropic"]["api_key"])
        self.brand = get_brand("kituwah_properties")
    
    def generate_smart_sql(self, user_question, project_id=None, database=None, schema=None):
        """
        Generate SQL query with project names and smart context.
        
        Args:
            user_question: Natural language question
            project_id: Optional specific project, or None for all projects
            database: Database name
            schema: Schema name
            
        Returns:
            dict with 'sql' and 'explanation'
        """
        
        scope = "across ALL projects" if not project_id else "for the current project"
        project_filter = f"WHERE project_id = '{project_id}'" if project_id else ""
        
        prompt = f"""
        User question: "{user_question}"
        
        Context: User is asking {scope}
        
        Database: SNOWFLAKE (use Snowflake SQL syntax)
        Current database: {database}
        Current schema: {schema}
        
        Schema:
        - PROJECTS: project_id, project_name, address, project_type, purchase_price, total_spent_ci, total_spent_mi
        - EXPENSES: expense_id, project_id, expense_date (DATE), amount, investment_type (CI/MI), vendor_name, description, category
        
        Available Categories: Acquisition, Closing Costs, Demo, Cleanup, Site Work, Permits & Inspections, 
        Plans & Engineering, Foundation, Concrete, Framing, Plumbing, Electrical, HVAC, Roofing, Siding, 
        Windows & Doors, Drywall, Painting, Flooring, Cabinets & Countertops, Appliances, Landscaping, 
        Utilities, Materials, Professional Services, Other
        
        MATERIAL CATEGORY INTELLIGENCE:
        When user asks about materials, include relevant categories:
        - "lumber" or "wood" → search description/vendor for 'lumber'/'wood' AND category 'Framing' or 'Materials'
        - "concrete" → search description for 'concrete' AND category 'Concrete' or 'Foundation'
        - "flooring materials" → category 'Flooring'
        - "framing materials" → category 'Framing'
        - "drywall" or "sheetrock" → category 'Drywall'
        - "paint" → category 'Painting'
        - Generic "materials" → category 'Materials'
        
        PROPERTY/PROJECT REFERENCES:
        When user mentions an address or property name, they're asking about THAT PROJECT, not a vendor:
        - "spent at Bonnell" or "on Bonnell" → search project_name LIKE '%Bonnell%'
        - "Oak Street property" → search project_name LIKE '%Oak%'
        - "the rental on Pine" → search project_name LIKE '%Pine%'
        DO NOT search vendor_name for property addresses!
        
        Example property query:
        WHERE p.project_name LIKE '%Bonnell%'
        NOT WHERE e.vendor_name LIKE '%Bonnell%'
        
        Example lumber query pattern:
        WHERE (LOWER(e.description) LIKE '%lumber%' 
               OR LOWER(e.description) LIKE '%wood%'
               OR LOWER(e.vendor_name) LIKE '%lumber%'
               OR e.category = 'Framing'
               OR e.category = 'Materials')
        
        CRITICAL RULES:
        1. ALWAYS JOIN with PROJECTS to include project_name in results
        2. If asking about spending/costs, GROUP BY project_name to show breakdown
        3. Always include a total row or column when aggregating
        4. Use DATEADD('month', -N, CURRENT_DATE()) for date math
        5. Use LOWER() for case-insensitive text search
        6. Search description, vendor_name, AND category for keywords
        7. Use smart category mapping for common materials
        
        WORKING EXAMPLES:
        
        Example 1 - Lumber/Materials spending (uses smart category mapping):
        Question: "How much spent on lumber?"
        SQL: SELECT 
                 p.project_name,
                 SUM(e.amount) as total_spent
             FROM EXPENSES e
             JOIN PROJECTS p ON e.project_id = p.project_id
             {project_filter}
             WHERE (LOWER(e.description) LIKE '%lumber%' 
                    OR LOWER(e.description) LIKE '%wood%'
                    OR LOWER(e.vendor_name) LIKE '%lumber%'
                    OR e.category = 'Framing'
                    OR e.category = 'Materials')
             GROUP BY p.project_name
             ORDER BY total_spent DESC
        
        Example 2 - Time-based with breakdown:
        Question: "Plumbing costs last 6 months?"
        SQL: SELECT 
                 p.project_name,
                 e.vendor_name,
                 e.expense_date,
                 e.amount
             FROM EXPENSES e
             JOIN PROJECTS p ON e.project_id = p.project_id
             {project_filter}
             WHERE e.category = 'Plumbing'
             AND e.expense_date >= DATEADD('month', -6, CURRENT_DATE())
             ORDER BY e.expense_date DESC
        
        Example 3 - Count queries (no grouping needed):
        Question: "How many active projects do I have?"
        SQL: SELECT 
                 COUNT(DISTINCT p.project_id) as active_projects,
                 LISTAGG(DISTINCT p.project_name, ', ') WITHIN GROUP (ORDER BY p.project_name) as project_list
             FROM PROJECTS p
             WHERE p.project_id IN (SELECT DISTINCT project_id FROM EXPENSES)
        
        Example 4 - Top vendors across projects:
        Question: "Who are my top vendors?"
        SQL: SELECT 
                 e.vendor_name,
                 COUNT(DISTINCT p.project_id) as num_projects,
                 COUNT(*) as num_transactions,
                 SUM(e.amount) as total_paid
             FROM EXPENSES e
             JOIN PROJECTS p ON e.project_id = p.project_id
             {project_filter}
             GROUP BY e.vendor_name
             ORDER BY total_paid DESC
             LIMIT 10
        
        Generate a SQL query that:
        - Includes project names (JOIN with PROJECTS)
        - Shows meaningful breakdown (not just a single number)
        - Orders results logically
        - Uses Snowflake syntax
        
        CRITICAL: Respond with ONLY valid JSON (no markdown, no text before/after):
        {{
            "sql": "SELECT ...",
            "explanation": "This query shows..."
        }}
        
        Do not include any text outside the JSON object.
        """
        
        try:
            response = self.claude.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            import json
            import re
            
            result_text = response.content[0].text.strip()
            
            # Remove markdown code blocks
            result_text = result_text.replace("```json", "").replace("```", "").strip()
            
            # Try to extract JSON if it's embedded in text
            json_match = re.search(r'\{[\s\S]*\}', result_text)
            if json_match:
                result_text = json_match.group(0)
            
            try:
                result = json.loads(result_text)
            except json.JSONDecodeError:
                # If JSON parsing fails, assume the whole response is SQL
                st.warning("AI didn't return JSON format, using raw SQL")
                result = {
                    "sql": result_text,
                    "explanation": "AI-generated query"
                }
            
            return result
        
        except Exception as e:
            st.error(f"Error generating query: {e}")
            return None
    
    def export_to_excel(self, df, query_text, user_question):
        """
        Export results to Excel with company branding.
        
        Returns:
            BytesIO object ready for download
        """
        
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Company Info sheet
            company_data = {
                'Field': ['Company', 'Owner', 'Phone', 'Email', 'Tagline'],
                'Value': [
                    self.brand['company'],
                    self.brand['contact']['owner'],
                    self.brand['contact']['phone'],
                    self.brand['contact']['email'],
                    self.brand['contact'].get('tagline', '')
                ]
            }
            pd.DataFrame(company_data).to_excel(writer, sheet_name='Company Info', index=False)
            
            # Summary sheet
            summary_data = {
                'Query': [user_question],
                'Generated': [datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
                'Rows Returned': [len(df)]
            }
            pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
            
            # Results sheet
            df.to_excel(writer, sheet_name='Results', index=False)
            
            # SQL sheet
            sql_data = {'SQL Query': [query_text]}
            pd.DataFrame(sql_data).to_excel(writer, sheet_name='SQL', index=False)
        
        output.seek(0)
        return output
    
    def export_to_pdf(self, df, query_text, user_question):
        """
        Export results to PDF with company branding.
        
        Returns:
            BytesIO object ready for download
        """
        
        output = BytesIO()
        doc = SimpleDocTemplate(output, pagesize=letter, 
                               leftMargin=72, rightMargin=72,
                               topMargin=72, bottomMargin=72)
        elements = []
        styles = getSampleStyleSheet()
        
        # Company Header (centered, no logo)
        company_title = Paragraph(
            f"<para align='center' fontSize='20'><b>{self.brand['company']}</b></para>", 
            styles['Title']
        )
        elements.append(company_title)
        
        tagline = Paragraph(
            f"<para align='center'><i>{self.brand['contact'].get('tagline', '')}</i></para>", 
            styles['Normal']
        )
        elements.append(tagline)
        elements.append(Spacer(1, 10))
        
        # Contact Info (centered)
        contact_info = Paragraph(
            f"<para align='center'><b>{self.brand['contact']['owner']}</b> | "
            f"{self.brand['contact']['phone']} | "
            f"{self.brand['contact']['email']}</para>", 
            styles['Normal']
        )
        elements.append(contact_info)
        elements.append(Spacer(1, 20))
        
        # Report Title
        title = Paragraph(f"<b>Data Intelligence Report</b>", styles['Heading1'])
        elements.append(title)
        elements.append(Spacer(1, 12))
        
        # Question
        question = Paragraph(f"<b>Question:</b> {user_question}", styles['Normal'])
        elements.append(question)
        elements.append(Spacer(1, 6))
        
        # Timestamp
        timestamp = Paragraph(f"<b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal'])
        elements.append(timestamp)
        elements.append(Spacer(1, 12))
        
        # Results table
        if len(df) > 0:
            # Convert dataframe to list for table
            # Handle None/NaN values
            df_clean = df.fillna('')
            data = [df_clean.columns.tolist()] + df_clean.values.tolist()
            
            # Convert all values to strings to avoid formatting issues
            data = [[str(cell) for cell in row] for row in data]
            
            # Limit rows for PDF (first 50)
            if len(data) > 51:
                data = data[:51]
                note = Paragraph(f"<i>Showing first 50 of {len(df)} rows</i>", styles['Normal'])
                elements.append(note)
                elements.append(Spacer(1, 6))
            
            # Create table with auto-sizing
            table = Table(data, colWidths=None)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('TOPPADDING', (0, 1), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'TOP')
            ]))
            
            elements.append(table)
        else:
            no_results = Paragraph("<i>No results found</i>", styles['Normal'])
            elements.append(no_results)
        
        elements.append(Spacer(1, 20))
        
        # SQL Query - HIDDEN for non-technical users
        # Uncomment below if you want to show SQL to technical users
        # sql_title = Paragraph("<b>SQL Query Used:</b>", styles['Heading2'])
        # elements.append(sql_title)
        # elements.append(Spacer(1, 6))
        # sql_text = Paragraph(f"<font face='Courier' size='8'>{query_text}</font>", styles['Code'])
        # elements.append(sql_text)
        
        # Build PDF
        doc.build(elements)
        output.seek(0)
        
        return output
