"""
Voice Agent
===========
Uses OpenAI Whisper for transcription and Claude for parsing.
"""

import streamlit as st
from openai import OpenAI
import anthropic
import json
import re


class VoiceAgent:
    """
    Voice expense entry agent.
    Transcribes audio and extracts expense details.
    """
    
    def __init__(self):
        self.openai_client = OpenAI(api_key=st.secrets["openai"]["api_key"])
        self.claude_client = anthropic.Anthropic(api_key=st.secrets["anthropic"]["api_key"])
    
    def transcribe_audio(self, audio_file):
        """
        Transcribe audio file using OpenAI Whisper.
        
        Args:
            audio_file: Streamlit UploadedFile object
            
        Returns:
            str: Transcribed text
        """
        try:
            # Reset file pointer
            audio_file.seek(0)
            
            # Call Whisper API
            transcript = self.openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="en"
            )
            
            return transcript.text
        
        except Exception as e:
            st.error(f"Transcription error: {e}")
            return None
    
    def transcribe_audio_bytes(self, audio_bytes):
        """
        Transcribe audio bytes from browser recording using OpenAI Whisper.
        
        Args:
            audio_bytes: Raw audio bytes from browser recording
            
        Returns:
            str: Transcribed text
        """
        try:
            from io import BytesIO
            
            # Create file-like object from bytes
            audio_file = BytesIO(audio_bytes)
            audio_file.name = "recording.wav"
            
            # Call Whisper API
            transcript = self.openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="en"
            )
            
            return transcript.text
        
        except Exception as e:
            st.error(f"Transcription error: {e}")
            return None
    
    def parse_expense(self, transcript, available_projects):
        """
        Parse expense details from transcript using Claude.
        
        Args:
            transcript: Text from voice transcription
            available_projects: List of project names user has access to
            
        Returns:
            dict: Parsed expense details
        """
        
        prompt = f"""
Parse this expense entry from voice transcription:

"{transcript}"

Available projects: {', '.join(available_projects)}

Extract the following information:
1. **amount** - Dollar amount (extract numbers, e.g., "2,500" or "two thousand five hundred" → 2500)
2. **vendor** - Who was paid (company or person name)
3. **category** - Best fit category from this list:
   - Acquisition, Closing Costs, Demo, Cleanup, Site Work, Permits & Inspections,
     Plans & Engineering, Foundation, Concrete, Framing, Plumbing, Electrical,
     HVAC, Roofing, Siding, Windows & Doors, Drywall, Painting, Flooring,
     Cabinets & Countertops, Appliances, Landscaping, Utilities, Materials,
     Professional Services, Other
4. **investment_type** - "CI" (cash) or "MI" (financed/maintenance)
5. **project** - Which project (match to available projects, look for addresses or property names)
6. **remaining_balance** (optional) - If they mention "still owe" or "balance remaining"

Examples:
- "Add $2,500 cash payment to Ray Tallant for plumbing on Bonnell, still owe him 8 grand"
  → amount: 2500, vendor: Ray Tallant, category: Plumbing, investment_type: CI, 
     project: 5122 Bonnell Ave, remaining_balance: 8000

- "Paid Home Depot $450 for framing lumber, cash"
  → amount: 450, vendor: Home Depot, category: Framing, investment_type: CI,
     project: [first available project]

- "Add twelve hundred dollars financed to Juan Rivera for concrete work"
  → amount: 1200, vendor: Juan Rivera, category: Concrete, investment_type: MI

Respond ONLY with valid JSON (no markdown):
{{
    "amount": 2500,
    "vendor": "vendor_name",
    "category": "exact_category_from_list",
    "investment_type": "CI",
    "project": "project_name",
    "remaining_balance": 8000,
    "confidence": 0.95
}}

If project is not mentioned, use the first available project: "{available_projects[0]}"
"""
        
        try:
            response = self.claude_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Extract JSON from response
            response_text = response.content[0].text.strip()
            
            # Remove markdown code blocks if present
            response_text = re.sub(r'```json\s*|\s*```', '', response_text)
            
            parsed = json.loads(response_text)
            
            return parsed
        
        except json.JSONDecodeError as e:
            st.error(f"Could not parse AI response: {e}")
            st.code(response_text)
            return None
        
        except Exception as e:
            st.error(f"Error parsing expense: {e}")
            return None
    
    def extract_vendor_from_description(self, description):
        """
        Extract vendor name from description using heuristics.
        Fallback if AI parsing fails.
        """
        # Look for text before parenthesis
        match = re.match(r'^([^(]+)', description)
        if match:
            return match.group(1).strip()
        
        # Take first few words
        words = description.split()
        return ' '.join(words[:3]) if len(words) >= 3 else description
