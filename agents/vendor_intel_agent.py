# ---------------- vendor_intel_agent.py ----------------
# -*- coding: utf-8 -*-
"""
Vendor Intelligence Agent
=========================

Page Overview (for future devs)
------------------------------
This module powers the "Vendor Intelligence" feature.

Flow:
1) Pull vendor + category spend summaries from Snowflake EXPENSES
2) Compute a deterministic input_hash from the summarized prompt inputs
3) If latest saved run has the same input_hash, reuse it (prevents LLM drift)
4) Otherwise call an LLM to generate strict JSON vendor intelligence
5) Persist results to AGENT_INSIGHTS.DATA (VARIANT) + RECOMMENDATIONS + ESTIMATED_SAVINGS
6) Return a consistent dict payload to the Streamlit UI

Why input_hash matters:
- LLMs are probabilistic. Even with the same data, outputs can drift.
- For "same inputs => same outputs", we reuse the prior saved analysis
  when the summarized inputs haven't changed.

Important:
- Runtime code should not attempt schema migrations (no ALTER TABLE).
- We store input_hash inside DATA JSON; no schema changes required.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st

import anthropic  # Claude fallback

try:
    from openai import OpenAI  # OpenAI primary
except Exception:
    OpenAI = None


class VendorIntelligenceAgent:
    """
    Agent that analyzes vendor spend and generates actionable insights.
    """

    # -----------------------------
    # Init / config
    # -----------------------------
    def __init__(self) -> None:
        # Claude fallback client
        self.claude_client = anthropic.Anthropic(api_key=st.secrets["anthropic"]["api_key"])

        # OpenAI primary client (optional)
        self.openai_client = None
        if OpenAI and "openai" in st.secrets and st.secrets["openai"].get("api_key"):
            self.openai_client = OpenAI(api_key=st.secrets["openai"]["api_key"])

        llm_cfg = st.secrets.get("llm", {})
        self.openai_model = llm_cfg.get("openai_model", "gpt-4.1-mini")
        self.claude_model = llm_cfg.get("claude_model", "claude-sonnet-4-6")

        self.top_vendors_in_prompt = int(llm_cfg.get("top_vendors_in_prompt", 15))
        self.top_categories_in_prompt = int(llm_cfg.get("top_categories_in_prompt", 10))
        self.claude_max_tokens = int(llm_cfg.get("claude_max_tokens", 5000))

        # Determinism controls: keep these at 0 to reduce drift when we must call LLM
        self.temperature = float(llm_cfg.get("temperature", 0))

    # ---------------------------------------------------------------------
    # Table setup / persistence
    # ---------------------------------------------------------------------
    def ensure_tables(self, cursor) -> None:
        """
        Ensure AGENT_INSIGHTS exists (idempotent) using the current, real schema.

        Table columns:
          - INSIGHT_ID (string)
          - INSIGHT_TYPE (string)
          - GENERATED_AT (timestamp)
          - DATA (variant)  <-- full analysis JSON (includes input_hash)
          - RECOMMENDATIONS (variant)
          - ESTIMATED_SAVINGS (number)
        """
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS AGENT_INSIGHTS (
                INSIGHT_ID STRING NOT NULL,
                INSIGHT_TYPE STRING,
                GENERATED_AT TIMESTAMP_NTZ,
                DATA VARIANT,
                RECOMMENDATIONS VARIANT,
                ESTIMATED_SAVINGS NUMBER(10,2)
            )
            """
        )

    def save_insights(self, cursor, analysis: Dict[str, Any]) -> str:
        """
        Persist the latest analysis to Snowflake.

        Stores:
          - DATA: full JSON payload (analysis)
          - RECOMMENDATIONS: analysis["recommendations"]
          - ESTIMATED_SAVINGS: analysis["total_estimated_savings"]

        Returns:
            insight_id (string)
        """
        insight_id = f"VENDOR-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        recommendations = analysis.get("recommendations", [])
        est_savings = float(analysis.get("total_estimated_savings", 0) or 0)

        cursor.execute(
            """
            INSERT INTO AGENT_INSIGHTS
                (INSIGHT_ID, INSIGHT_TYPE, GENERATED_AT, DATA, RECOMMENDATIONS, ESTIMATED_SAVINGS)
            SELECT
                %s,
                'vendor_intelligence',
                CURRENT_TIMESTAMP(),
                PARSE_JSON(%s),
                PARSE_JSON(%s),
                %s
            """,
            (
                insight_id,
                json.dumps(analysis),
                json.dumps(recommendations),
                est_savings,
            ),
        )
        return insight_id

    def get_latest_insights(self, cursor) -> Optional[Dict[str, Any]]:
        """
        Retrieve the most recent vendor intelligence record (read-only).
        """
        try:
            cursor.execute(
                """
                SELECT
                    INSIGHT_ID,
                    DATA,
                    RECOMMENDATIONS,
                    ESTIMATED_SAVINGS,
                    GENERATED_AT
                FROM AGENT_INSIGHTS
                WHERE INSIGHT_TYPE = 'vendor_intelligence'
                ORDER BY GENERATED_AT DESC
                LIMIT 1
                """
            )
            row = cursor.fetchone()
            if not row:
                return None

            insight_id, data_raw, recs_raw, est_savings, generated_at = row

            vendor_analysis = self._variant_to_obj(data_raw, expected=dict, default={})
            recs = self._variant_to_obj(recs_raw, expected=list, default=[])

            return {
                "insight_id": insight_id,
                "generated_at": generated_at,
                "vendor_analysis": vendor_analysis,
                "recommendations": recs,
                "estimated_savings": float(est_savings or 0),
                "opportunities": vendor_analysis.get("opportunities", []),
            }

        except Exception as e:
            st.warning(f"Could not load latest vendor insights: {e}")
            return None

    @staticmethod
    def _variant_to_obj(value: Any, expected: type, default: Any):
        """
        Convert Snowflake VARIANT-like value to Python object safely.

        Args:
            value: dict/list OR JSON string OR None
            expected: dict or list
            default: fallback if conversion fails
        """
        if value is None:
            return default
        if isinstance(value, expected):
            return value
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                return parsed if isinstance(parsed, expected) else default
            except Exception:
                return default
        if expected is dict and isinstance(value, dict):
            return value
        if expected is list and isinstance(value, list):
            return value
        return default

    # ---------------------------------------------------------------------
    # Data gathering (EXPENSES)
    # ---------------------------------------------------------------------
    def _gather_vendor_data(
        self, cursor
    ) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any], pd.DataFrame]:
        """
        Collect vendor + category + metadata summaries from EXPENSES.

        EXPENSES columns (confirmed):
        - VENDOR_NAME
        - CATEGORY
        - AMOUNT
        - PROJECT_ID
        - EXPENSE_DATE

        Internal aliases:
        - VENDOR (from VENDOR_NAME)
        - DATE (from EXPENSE_DATE)
        """
        cursor.execute(
            """
            SELECT
                VENDOR_NAME,
                CATEGORY,
                AMOUNT,
                PROJECT_ID,
                EXPENSE_DATE
            FROM EXPENSES
            WHERE AMOUNT IS NOT NULL
            """
        )

        rows = cursor.fetchall()
        if not rows:
            return (
                pd.DataFrame(),
                pd.DataFrame(),
                {"grand_total": 0, "project_count": 0, "earliest_date": None, "latest_date": None},
                pd.DataFrame(),
            )

        df = pd.DataFrame(rows, columns=["VENDOR", "CATEGORY", "AMOUNT", "PROJECT_ID", "DATE"])
        df["AMOUNT"] = pd.to_numeric(df["AMOUNT"], errors="coerce").fillna(0)

        df_vendors = (
            df.groupby("VENDOR", dropna=False)
            .agg(
                total_spend=("AMOUNT", "sum"),
                transaction_count=("AMOUNT", "count"),
                avg_transaction=("AMOUNT", "mean"),
            )
            .reset_index()
            .sort_values("total_spend", ascending=False)
        )

        df_categories = (
            df.groupby("CATEGORY", dropna=False)
            .agg(
                total_spend=("AMOUNT", "sum"),
                transaction_count=("AMOUNT", "count"),
            )
            .reset_index()
            .sort_values("total_spend", ascending=False)
        )

        df_high_freq = (
            df.groupby("VENDOR", dropna=False)
            .agg(transaction_count=("AMOUNT", "count"), total_spend=("AMOUNT", "sum"))
            .reset_index()
            .sort_values("transaction_count", ascending=False)
        )

        meta = {
            "grand_total": float(df["AMOUNT"].sum()),
            "project_count": int(df["PROJECT_ID"].nunique()),
            "earliest_date": str(df["DATE"].min()) if df["DATE"].notna().any() else None,
            "latest_date": str(df["DATE"].max()) if df["DATE"].notna().any() else None,
        }

        return df_vendors, df_categories, meta, df_high_freq

    # ---------------------------------------------------------------------
    # Deterministic input hashing (prevents drift)
    # ---------------------------------------------------------------------
    @staticmethod
    def _stable_df_records(df: pd.DataFrame, cols: List[str], max_rows: int) -> List[Dict[str, Any]]:
        """
        Convert a DataFrame into a stable list of dict records for hashing.

        Notes:
        - Rounds floats to cents
        - Forces strings to trimmed str
        - Limits row count
        """
        if df is None or df.empty:
            return []

        safe = df.copy().head(max_rows)
        records: List[Dict[str, Any]] = []

        for _, row in safe.iterrows():
            item: Dict[str, Any] = {}
            for c in cols:
                v = row.get(c)
                if pd.isna(v):
                    item[c] = None
                elif isinstance(v, (int,)):
                    item[c] = int(v)
                elif isinstance(v, (float,)):
                    item[c] = round(float(v), 2)
                else:
                    item[c] = str(v).strip()
            records.append(item)

        return records

    def _compute_input_hash(
        self,
        vendors_for_prompt: pd.DataFrame,
        cats_for_prompt: pd.DataFrame,
        high_freq_for_prompt: pd.DataFrame,
        meta: Dict[str, Any],
    ) -> str:
        """
        Compute a deterministic SHA-256 hash for the summarized inputs.

        If these inputs haven't changed, the analysis should not change.
        """
        payload = {
            "meta": {
                "grand_total": round(float(meta.get("grand_total", 0) or 0), 2),
                "project_count": int(meta.get("project_count", 0) or 0),
                "earliest_date": meta.get("earliest_date"),
                "latest_date": meta.get("latest_date"),
            },
            "vendors": self._stable_df_records(
                vendors_for_prompt, cols=["VENDOR", "total_spend", "transaction_count", "avg_transaction"], max_rows=50
            ),
            "categories": self._stable_df_records(
                cats_for_prompt, cols=["CATEGORY", "total_spend", "transaction_count"], max_rows=50
            ),
            "high_freq": self._stable_df_records(
                high_freq_for_prompt, cols=["VENDOR", "transaction_count", "total_spend"], max_rows=50
            ),
        }

        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    # ---------------------------------------------------------------------
    # Prompting + analysis
    # ---------------------------------------------------------------------
    def analyze_vendors(self, cursor, force_rerun: bool = False) -> Optional[Dict[str, Any]]:
        """
        Main analysis entry point. Returns a normalized payload for the UI.

        Args:
            force_rerun:
                If True, bypass input_hash reuse and call the LLM again.
                Default False to keep results stable for identical inputs.
        """
        try:
            df_vendors, df_categories, meta, df_high_freq = self._gather_vendor_data(cursor)
            if df_vendors.empty:
                st.info("No EXPENSES data found for vendor analysis.")
                return None

            vendors_for_prompt = df_vendors.head(self.top_vendors_in_prompt)
            cats_for_prompt = df_categories.head(self.top_categories_in_prompt)
            high_freq_for_prompt = df_high_freq.head(10)

            input_hash = self._compute_input_hash(vendors_for_prompt, cats_for_prompt, high_freq_for_prompt, meta)

            # 1) Reuse latest saved analysis if inputs match (prevents drift + saves tokens)
            if not force_rerun:
                latest = self.get_latest_insights(cursor)
                if latest:
                    latest_analysis = latest.get("vendor_analysis") or {}
                    if str(latest_analysis.get("input_hash", "")).strip() == input_hash:
                        return {
                            "generated_at": latest.get("generated_at"),
                            "vendor_analysis": latest_analysis,
                            "opportunities": latest_analysis.get("opportunities", []),
                            "recommendations": latest_analysis.get("recommendations", []),
                            "estimated_savings": float(latest.get("estimated_savings", 0) or 0),
                        }

            prompt = self._build_prompt(vendors_for_prompt, cats_for_prompt, high_freq_for_prompt, meta)

            analysis = self._run_openai_json(prompt)
            if analysis is None:
                analysis = self._run_claude_json(prompt)

            if analysis is None:
                st.error("Vendor Intelligence: both OpenAI and Claude failed to produce valid JSON.")
                return None

            # 2) Attach deterministic metadata (no schema changes required)
            analysis["input_hash"] = input_hash
            analysis["meta"] = meta

            # 3) Ensure totals are internally consistent
            analysis = self._normalize_analysis_totals(analysis)

            result = {
                "generated_at": datetime.now(),
                "vendor_analysis": analysis,
                "opportunities": analysis.get("opportunities", []),
                "recommendations": analysis.get("recommendations", []),
                "estimated_savings": float(analysis.get("total_estimated_savings", 0) or 0),
            }

            # Persist (best-effort). Caller should have ensured table exists once.
            try:
                self.save_insights(cursor, analysis)
            except Exception as e:
                st.warning(f"Vendor Intelligence generated but not persisted to Snowflake: {e}")

            return result

        except Exception as e:
            st.error(f"Vendor analysis error: {e}")
            return None

    @staticmethod
    def _normalize_analysis_totals(analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize analysis so total_estimated_savings matches sum(opportunities[].estimated_savings).

        This prevents silly internal mismatch like:
        - opps sum to 3,900 but total_estimated_savings says 3,800
        """
        try:
            opps = analysis.get("opportunities") or []
            total = 0.0
            cleaned_opps = []

            for opp in opps:
                if not isinstance(opp, dict):
                    continue
                savings = float(opp.get("estimated_savings", 0) or 0)
                opp["estimated_savings"] = round(savings, 2)
                total += opp["estimated_savings"]
                cleaned_opps.append(opp)

            analysis["opportunities"] = cleaned_opps
            analysis["total_estimated_savings"] = round(float(analysis.get("total_estimated_savings", total) or 0), 2)

            # If model gave something different, override with deterministic sum
            if abs(float(analysis["total_estimated_savings"]) - round(total, 2)) > 0.01:
                analysis["total_estimated_savings"] = round(total, 2)

            return analysis
        except Exception:
            return analysis

    def _build_prompt(
        self,
        df_vendors: pd.DataFrame,
        df_categories: pd.DataFrame,
        df_high_freq: pd.DataFrame,
        meta: Dict[str, Any],
    ) -> str:
        """
        Build a compact prompt that produces strict JSON.

        Note:
        - Savings numbers are inherently subjective. We stabilize the UI via input_hash reuse.
        - If you want fully deterministic savings, move savings computation into Python.
        """
        total = meta.get("grand_total", 0)
        project_count = meta.get("project_count", 0)

        return f"""You are a construction procurement consultant for a house-flip / rentals business.
Return ONLY valid JSON. No markdown. No commentary.

Client: Kituwah Properties
Projects: {project_count}
Total spend: ${total:,.0f}
Date range: {meta.get("earliest_date")} to {meta.get("latest_date")}

VENDOR SUMMARY (top):
{df_vendors.to_string(index=False)}

CATEGORY SUMMARY (top):
{df_categories.to_string(index=False)}

HIGH-FREQUENCY VENDORS:
{df_high_freq.to_string(index=False)}

Return this JSON shape exactly:
{{
  "top_vendors": [
    {{
      "vendor": "",
      "spend": 0,
      "transactions": 0,
      "insight": "",
      "leverage": ""
    }}
  ],
  "opportunities": [
    {{
      "type": "trip_consolidation|duplicate_vendor|volume_negotiation|payment_terms|category_overspend",
      "vendor_or_category": "",
      "description": "",
      "estimated_savings": 0,
      "action": ""
    }}
  ],
  "recommendations": [
    {{
      "priority": "high|medium|low",
      "action": "",
      "expected_impact": "$X-$Y saved",
      "effort": "low|medium|high"
    }}
  ],
  "key_insights": ["", "", ""],
  "total_estimated_savings": 0
}}
"""

    # ---------------------------------------------------------------------
    # LLM calls
    # ---------------------------------------------------------------------
    def _run_openai_json(self, prompt: str) -> Optional[Dict[str, Any]]:
        """
        OpenAI primary call with strict JSON output.
        """
        if not self.openai_client:
            return None

        try:
            completion = self.openai_client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": "Return ONLY valid JSON. No markdown. No extra text."},
                    {"role": "user", "content": prompt},
                ],
                temperature=self.temperature,
                response_format={"type": "json_object"},
            )
            text = completion.choices[0].message.content.strip()
            obj = json.loads(text)
            return obj if isinstance(obj, dict) else None
        except Exception as e:
            st.warning(f"OpenAI vendor intel failed; attempting Claude fallback. ({e})")
            return None

    def _run_claude_json(self, prompt: str) -> Optional[Dict[str, Any]]:
        """
        Claude fallback call (best-effort JSON extraction).
        """
        try:
            resp = self.claude_client.messages.create(
                model=self.claude_model,
                max_tokens=self.claude_max_tokens,
                temperature=self.temperature,
                messages=[{"role": "user", "content": prompt}],
            )
            text = self._concat_claude_text(resp)
            text = self._strip_code_fences(text)

            obj = self._extract_first_valid_json_object(text)
            if obj is None:
                repaired = self._repair_json(text)
                obj = self._extract_first_valid_json_object(repaired)

            return obj
        except Exception as e:
            st.warning(f"Claude vendor intel failed. ({e})")
            return None

    # ---------------------------------------------------------------------
    # Claude text + JSON helpers
    # ---------------------------------------------------------------------
    @staticmethod
    def _concat_claude_text(resp) -> str:
        """
        Concatenate all Claude 'text' blocks into one string.
        """
        parts: List[str] = []
        for block in getattr(resp, "content", []):
            if getattr(block, "type", None) == "text" and getattr(block, "text", None):
                parts.append(block.text)
        return "\n".join(parts).strip()

    @staticmethod
    def _strip_code_fences(text: str) -> str:
        text = re.sub(r"```json\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"```\s*", "", text)
        return text.strip()

    @staticmethod
    def _extract_first_valid_json_object(text: str) -> Optional[Dict[str, Any]]:
        """
        Try direct JSON parse, then scan for a valid JSON object slice.
        """
        t = text.strip()

        try:
            obj = json.loads(t)
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass

        starts = [m.start() for m in re.finditer(r"\{", t)]
        for s in starts:
            for e in range(len(t), s, -1):
                if t[e - 1] != "}":
                    continue
                chunk = t[s:e]
                try:
                    obj = json.loads(chunk)
                    if isinstance(obj, dict):
                        return obj
                except Exception:
                    continue

        return None

    @staticmethod
    def _repair_json(json_text: str) -> str:
        """
        Attempt to repair common JSON issues from LLMs:
        - Unescaped newlines inside JSON string values
        - Trailing commas before } or ]
        """

        def _escape_newlines_in_strings(s: str) -> str:
            out: List[str] = []
            in_str = False
            esc = False

            for ch in s:
                if in_str:
                    if esc:
                        esc = False
                        out.append(ch)
                        continue
                    if ch == "\\":
                        esc = True
                        out.append(ch)
                        continue
                    if ch == '"':
                        in_str = False
                        out.append(ch)
                        continue
                    if ch == "\n":
                        out.append("\\n")
                        continue
                    out.append(ch)
                else:
                    if ch == '"':
                        in_str = True
                    out.append(ch)

            return "".join(out)

        repaired = _escape_newlines_in_strings(json_text)
        repaired = re.sub(r",\s*}", "}", repaired)
        repaired = re.sub(r",\s*]", "]", repaired)
        return repaired