"""
Vendor Intelligence Agent
=========================
Autonomous agent that analyzes vendor relationships and provides actionable insights.
Uses multi-step reasoning to identify savings opportunities and optimization strategies.
"""

import anthropic
import streamlit as st
import pandas as pd
from datetime import datetime
import json
import re


class VendorIntelligenceAgent:
    """
    Agentic AI that autonomously analyzes vendor data and generates business insights.

    Demonstrates:
    - Multi-step reasoning with richer data context
    - Autonomous analysis tailored to house flipping / rental rehab
    - Tool use (database queries)
    - Actionable recommendations with real dollar estimates
    """

    def __init__(self):
        self.claude = anthropic.Anthropic(api_key=st.secrets["anthropic"]["api_key"])

    # ------------------------------------------------------------------
    # ONE-TIME TABLE SETUP  (call this during app init or first run)
    # ------------------------------------------------------------------
    def ensure_tables(self, cursor):
        """Create AGENT_INSIGHTS table if it doesn't exist. Call once at startup."""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS AGENT_INSIGHTS (
                insight_id    VARCHAR        PRIMARY KEY,
                insight_type  VARCHAR,
                generated_at  TIMESTAMP,
                data          VARIANT,
                recommendations VARIANT,
                estimated_savings NUMBER(10,2)
            )
        """)

    # ------------------------------------------------------------------
    # DATA GATHERING  (multiple targeted queries for richer context)
    # ------------------------------------------------------------------
    def _gather_vendor_data(self, cursor):
        """
        Run several focused queries so the AI has enough signal to give
        specific, actionable recommendations rather than generic advice.
        """

        # --- 1. Vendor-level summary ---
        cursor.execute("""
            SELECT
                vendor_name,
                COUNT(*)                                                    AS transaction_count,
                SUM(amount)                                                 AS total_spent,
                AVG(amount)                                                 AS avg_transaction,
                MIN(amount)                                                 AS min_transaction,
                MAX(amount)                                                 AS max_transaction,
                MIN(expense_date)                                           AS first_date,
                MAX(expense_date)                                           AS last_date,
                DATEDIFF('day', MIN(expense_date), MAX(expense_date))       AS span_days,
                LISTAGG(DISTINCT category, ', ')
                    WITHIN GROUP (ORDER BY category)                        AS categories
            FROM EXPENSES
            GROUP BY vendor_name
            ORDER BY total_spent DESC
        """)
        vendor_rows = cursor.fetchall()
        df_vendors = pd.DataFrame(vendor_rows, columns=[
            'vendor', 'transactions', 'total_spent', 'avg_transaction',
            'min_transaction', 'max_transaction', 'first_date', 'last_date',
            'span_days', 'categories'
        ])
        for col in ['total_spent', 'avg_transaction', 'min_transaction', 'max_transaction']:
            df_vendors[col] = pd.to_numeric(df_vendors[col])

        # --- 2. Category-level spending ---
        cursor.execute("""
            SELECT
                category,
                COUNT(DISTINCT vendor_name)  AS vendor_count,
                COUNT(*)                     AS transaction_count,
                SUM(amount)                  AS total_spent
            FROM EXPENSES
            GROUP BY category
            ORDER BY total_spent DESC
        """)
        cat_rows = cursor.fetchall()
        df_categories = pd.DataFrame(cat_rows, columns=[
            'category', 'vendor_count', 'transaction_count', 'total_spent'
        ])
        df_categories['total_spent'] = pd.to_numeric(df_categories['total_spent'])

        # --- 3. Project context ---
        cursor.execute("""
            SELECT
                COUNT(DISTINCT project_id)  AS project_count,
                SUM(amount)                 AS grand_total,
                MIN(expense_date)           AS earliest_date,
                MAX(expense_date)           AS latest_date
            FROM EXPENSES
        """)
        row = cursor.fetchone()
        project_meta = {
            'project_count': int(row[0]),
            'grand_total':   float(row[1]) if row[1] else 0,
            'earliest_date': str(row[2]),
            'latest_date':   str(row[3]),
        }

        # --- 4. Vendors with many small transactions (trip-consolidation signal) ---
        cursor.execute("""
            SELECT
                vendor_name,
                COUNT(*)        AS trips,
                SUM(amount)     AS total,
                AVG(amount)     AS avg_per_trip
            FROM EXPENSES
            GROUP BY vendor_name
            HAVING COUNT(*) >= 3
            ORDER BY COUNT(*) DESC
            LIMIT 10
        """)
        high_freq_rows = cursor.fetchall()
        df_high_freq = pd.DataFrame(high_freq_rows, columns=[
            'vendor', 'trips', 'total', 'avg_per_trip'
        ])

        return df_vendors, df_categories, project_meta, df_high_freq

    # ------------------------------------------------------------------
    # MAIN ANALYSIS ENTRY POINT
    # ------------------------------------------------------------------
    def analyze_vendors(self, cursor):
        """
        Main agentic loop — gathers rich data, sends to Claude with a
        sharp persona prompt, returns structured intelligence report.

        Returns:
            dict with keys: generated_at, vendor_analysis, opportunities,
                            recommendations, estimated_savings
        """
        try:
            df_vendors, df_categories, meta, df_high_freq = self._gather_vendor_data(cursor)
        except Exception as e:
            st.error(f"Data gathering error: {e}")
            return None

        if df_vendors.empty:
            return None

        total = meta['grand_total']
        project_count = meta['project_count']

        # Build prompt with real numbers already woven in
        prompt = f"""You are a seasoned construction cost consultant and business advisor
specializing in residential house flipping and rental rehab projects.
You have reviewed hundreds of project budgets and know exactly where
contractors overpay and how to negotiate better rates with suppliers.

Your client is a small property investment company (Kituwah Properties).
They have {project_count} project(s) with a total spend of ${total:,.0f}
recorded between {meta['earliest_date']} and {meta['latest_date']}.

---
VENDOR SUMMARY (sorted by spend):
{df_vendors.to_string(index=False)}

---
SPENDING BY CATEGORY:
{df_categories.to_string(index=False)}

---
HIGH-FREQUENCY VENDORS (3+ transactions — trip consolidation candidates):
{df_high_freq.to_string(index=False) if not df_high_freq.empty else "None identified"}

---
YOUR TASK — perform the following analysis and respond ONLY with the
JSON block described at the end. Do NOT add prose outside the JSON.

ANALYSIS STEPS:

1. TOP VENDOR INSIGHTS
   For each of the top 5 vendors by spend, identify ONE specific insight:
   - Is the avg transaction suspiciously low? (many small trips = consolidation opportunity)
   - Do they overlap with another vendor in the same category? (duplication)
   - Is the span_days short but spend high? (negotiate a project rate)
   - Can high total spend be leveraged for a contractor discount or net-30 terms?

2. SAVINGS OPPORTUNITIES — find at least 3 of these specific types:
   a) TRIP CONSOLIDATION: vendor with 3+ trips where batching saves fuel/time.
      Formula: (trips - 1) × $35 estimated trip cost
   b) DUPLICATE VENDORS: two vendors in same category (e.g., two lumber yards,
      two plumbers). Estimate 8-12% savings by consolidating volume.
   c) VOLUME NEGOTIATION: top vendor where total spend justifies asking for
      5-10% contractor discount. Calculate on their actual total.
   d) PAYMENT TERMS: vendors paid in many small invoices who could offer
      net-30 or project-rate pricing.
   e) CATEGORY OVERSPEND: any category where spend seems disproportionate
      relative to total project spend — flag for budget review.

3. RECOMMENDATIONS — rank by impact, give EXACT action steps:
   - Name the specific vendor
   - State the exact ask ("Call Home Depot Pro desk, reference account #,
     ask for 8% contractor pricing on orders over $500")
   - Give a realistic dollar range for savings

4. SAVINGS MATH — be conservative (use lower end of ranges).
   Total estimated savings must reflect actual numbers, not wishful thinking.

RESPOND WITH THIS EXACT JSON (no text before or after):
{{
  "top_vendors": [
    {{
      "vendor": "Vendor Name",
      "spend": 12400.00,
      "transactions": 7,
      "insight": "One specific, concrete observation about this vendor",
      "leverage": "What gives the owner power to negotiate or optimize"
    }}
  ],
  "opportunities": [
    {{
      "type": "trip_consolidation | duplicate_vendor | volume_negotiation | payment_terms | category_overspend",
      "vendor_or_category": "Name",
      "description": "Specific description referencing actual numbers from the data",
      "estimated_savings": 450,
      "action": "Exact step-by-step action the owner should take"
    }}
  ],
  "recommendations": [
    {{
      "priority": "high | medium | low",
      "action": "Specific action with vendor name and exact ask",
      "expected_impact": "$X–$Y saved",
      "effort": "low | medium | high"
    }}
  ],
  "key_insights": [
    "One-sentence insight #1 with a real number from the data",
    "One-sentence insight #2 with a real number from the data",
    "One-sentence insight #3 with a real number from the data"
  ],
  "total_estimated_savings": 2850
}}"""

        try:
            response = self.claude.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=2500,
                messages=[{"role": "user", "content": prompt}]
            )

            result_text = response.content[0].text.strip()

            # Strip markdown code fences if present
            result_text = re.sub(r"```json\s*", "", result_text)
            result_text = re.sub(r"```\s*", "", result_text)

            # Extract outermost JSON object
            json_match = re.search(r'\{[\s\S]*\}', result_text)
            if not json_match:
                st.error("Agent returned no parseable JSON.")
                return None

            analysis = json.loads(json_match.group(0))

            return {
                'generated_at':    datetime.now(),
                'vendor_analysis': analysis,
                'opportunities':   analysis.get('opportunities', []),
                'recommendations': analysis.get('recommendations', []),
                'estimated_savings': float(analysis.get('total_estimated_savings', 0))
            }

        except json.JSONDecodeError as e:
            st.error(f"Failed to parse agent response as JSON: {e}")
            return None
        except Exception as e:
            st.error(f"Agent analysis error: {e}")
            return None

    # ------------------------------------------------------------------
    # PERSISTENCE
    # ------------------------------------------------------------------
    def save_insights(self, cursor, insights):
        """Save agent insights to AGENT_INSIGHTS for historical tracking."""
        try:
            insight_id = f"vendor_intel_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            cursor.execute("""
                INSERT INTO AGENT_INSIGHTS
                    (insight_id, insight_type, generated_at, data, recommendations, estimated_savings)
                VALUES (%s, %s, %s, PARSE_JSON(%s), PARSE_JSON(%s), %s)
            """, (
                insight_id,
                'vendor_intelligence',
                insights['generated_at'],
                json.dumps(insights['vendor_analysis']),
                json.dumps(insights['recommendations']),
                insights['estimated_savings']
            ))
            return True

        except Exception as e:
            st.warning(f"Could not save insights: {e}")
            return False

    def get_latest_insights(self, cursor):
        """Retrieve most recent vendor intelligence insights."""
        try:
            cursor.execute("""
                SELECT generated_at, data, recommendations, estimated_savings
                FROM AGENT_INSIGHTS
                WHERE insight_type = 'vendor_intelligence'
                ORDER BY generated_at DESC
                LIMIT 1
            """)
            result = cursor.fetchone()
            if result:
                return {
                    'generated_at':    result[0],
                    'vendor_analysis': json.loads(result[1]) if result[1] else {},
                    'recommendations': json.loads(result[2]) if result[2] else [],
                    'estimated_savings': float(result[3]) if result[3] else 0
                }
            return None

        except Exception as e:
            st.warning(f"Could not retrieve insights: {e}")
            return None
