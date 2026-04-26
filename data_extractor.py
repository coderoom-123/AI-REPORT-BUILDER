import json
import re
from typing import Dict, List, Optional, Any
from openai import OpenAI
from config import Config
from prompts import (
    INSPECTION_EXTRACTION_PROMPT,
    THERMAL_EXTRACTION_PROMPT,
    DATA_MERGING_PROMPT,
    DDR_GENERATION_PROMPT,
    FALLBACK_EXTRACTION_PROMPT
)


class LLMExtractor:
    
    def __init__(self):
        self.provider = Config.LLM_PROVIDER
        self.model = Config.LLM_MODEL
        self.temperature = Config.LLM_TEMPERATURE
        self.max_tokens = Config.LLM_MAX_TOKENS
        
        print(f"  Initializing LLM: provider={self.provider}, model={self.model}")
        
        if self.provider == "openai":
            if not Config.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY not set")
            self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
            
        elif self.provider == "groq":
            if not Config.GROQ_API_KEY:
                raise ValueError("GROQ_API_KEY not set")
            self.client = OpenAI(
                api_key=Config.GROQ_API_KEY,
                base_url="https://api.groq.com/openai/v1"
            )
            print("  Using Groq API")
            
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
    
    def _call_llm(self, prompt, system_prompt=None):
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )
        return response.choices[0].message.content
    
    def _parse_json_response(self, response):
        response = response.strip()
        if response.startswith("```"):
            first_newline = response.find('\n')
            if first_newline != -1:
                response = response[first_newline + 1:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
        if response.lower().startswith("json"):
            response = response[4:].strip()
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    pass
            return {"error": "Parse failed", "raw": response[:500]}
    
    def extract_inspection_data(self, text_by_page):
        full_text = "\n\n".join([
            f"=== PAGE {page} ===\n{text}" 
            for page, text in sorted(text_by_page.items())
            if text.strip()
        ])
        if not full_text.strip():
            return {"error": "No text", "impacted_areas": []}
        if len(full_text) > 100000:
            full_text = full_text[:100000]
        
        prompt = INSPECTION_EXTRACTION_PROMPT.format(text=full_text)
        try:
            response = self._call_llm(prompt, "Extract structured data from building inspection reports. Return ONLY valid JSON.")
            return self._parse_json_response(response)
        except Exception as e:
            return {"error": str(e), "impacted_areas": []}
    
    def extract_thermal_data(self, text_by_page, temperatures):
        all_temps = []
        for t in temperatures:
            all_temps.extend(t.get("temperatures", []))
        
        return {
            "temperature_range": {
                "min_c": min(all_temps) if all_temps else None,
                "max_c": max(all_temps) if all_temps else None,
                "avg_c": round(sum(all_temps) / len(all_temps), 1) if all_temps else None
            },
            "readings": temperatures
        }
    
    def merge_data(self, inspection_data, thermal_data, thermal_mapping=None):
        if thermal_mapping is None:
            thermal_mapping = {}
        prompt = DATA_MERGING_PROMPT.format(
            inspection_data=json.dumps(inspection_data, indent=2, default=str),
            thermal_data=json.dumps(thermal_data, indent=2, default=str),
            thermal_mapping=json.dumps(thermal_mapping, indent=2)
        )
        try:
            response = self._call_llm(prompt, "Merge building inspection data with thermal data. Return ONLY valid JSON.")
            return self._parse_json_response(response)
        except Exception as e:
            return {"merged_areas": [], "error": str(e)}
    
    def _clean_report(self, report: str) -> str:
        """Clean up common LLM issues in the generated report"""
        
        # Remove photo number lists
        report = re.sub(r'\*\*Images?\*\*:\s*Photo\s*[\d,\s]+', '**Images:** See attached photos below', report)
        report = re.sub(r'\*\*Images?\*\*:\s*Not Available', '**Images:** Not Available', report)
        
        # Remove stray photo reference lines
        report = re.sub(r'^\s*[-•]\s*Photo\s+\d+.*$', '', report, flags=re.MULTILINE)
        report = re.sub(r'^\s*Photo\s+\d+.*$', '', report, flags=re.MULTILINE)
        
        # Fix duplicate area headings
        report = re.sub(r'(### \w+)\s*\n+### \1', r'\1', report)
        
        # Remove "First Entry", "Second Entry" artifacts
        report = re.sub(r'\*\*Observation\s*\([^)]*\)\*\*', '**Observation**', report)
        
        # Collapse multiple blank lines
        report = re.sub(r'\n{3,}', '\n\n', report)
        
        # Fix common formatting issues
        report = report.replace('** **', '')
        report = report.replace('****', '**')
        
        return report.strip()
    
    def generate_ddr(self, merged_data):
        prompt = DDR_GENERATION_PROMPT.format(
            merged_data=json.dumps(merged_data, indent=2, default=str)
        )
        
        system_instructions = """You are a senior building diagnostics engineer creating a client-ready DDR report.

CRITICAL RULES:
1. Only use facts from the provided data - never invent information
2. Never list photo numbers like "Photo 1, Photo 2" - photos are handled separately
3. If information is missing, write "Not Available" - never guess
4. Keep language simple and client-friendly
5. One observation entry per area - combine related issues
6. Use clean markdown formatting with proper headings
7. Be concise but thorough
8. Include temperature data only if available in the data"""
        
        try:
            response = self._call_llm(prompt, system_instructions)
            return self._clean_report(response)
        except Exception as e:
            return "# DDR Generation Error\n\n" + str(e)