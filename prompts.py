"""
Prompt templates for the DDR Generator system.
Each prompt is carefully designed for a specific extraction/generation task.
"""

# ============================================================
# PROMPT 1: Extract structured data from inspection report
# ============================================================
INSPECTION_EXTRACTION_PROMPT = """You are an AI assistant specialized in analyzing building inspection reports.
Extract ALL information from the following inspection document text into structured JSON.

## DOCUMENT TEXT:
{text}

## EXTRACTION RULES:
1. Extract every observation, issue, and finding - do not skip anything
2. Group by the impacted area/room (Hall, Bedroom, Kitchen, Master Bedroom, etc.)
3. For each area, separate:
   - "negative_side": The problem/damage observed (WHAT is wrong)
   - "positive_side": The source/cause (WHERE it's coming from)
4. Extract ALL photo references with their descriptions and photo numbers
5. Extract checklist/responses data if present (WC, External Wall checklists)
6. Extract property info (customer details, address, inspection date, etc.)
7. If information is blank, missing, or marked "No", use null

## OUTPUT FORMAT - Return ONLY this JSON structure:
{{
  "property_info": {{
    "customer_name": "value or null",
    "mobile": "value or null",
    "email": "value or null",
    "address": "value or null",
    "property_age_years": "value or null",
    "property_type": "value or null",
    "floors": "value or null",
    "previous_structural_audit": "value or null",
    "previous_repair_work": "value or null",
    "inspection_datetime": "value or null",
    "inspected_by": []
  }},
  "site_areas": ["list of rooms/areas covered"],
  "impacted_areas": [
    {{
      "area_id": 1,
      "area_name": "name of area/room",
      "negative_side": {{
        "description": "detailed description of the problem",
        "photos": ["Photo X", "Photo Y"]
      }},
      "positive_side": {{
        "description": "identified source of the problem",
        "photos": ["Photo Z"]
      }}
    }}
  ],
  "checklist_data": {{
    "wc": {{
      "leakage_adjacent_walls": "Yes/No/null",
      "leakage_during": "All time/During use/No/null",
      "concealed_plumbing_leakage": "Yes/No/null",
      "nahani_trap_damage": "Yes/No/null",
      "gaps_tile_joints": "Yes/No/null",
      "gaps_nahani_trap": "Yes/No/null",
      "tiles_broken_loose": "Yes/No/null",
      "loose_plumbing_joints": "Yes/No/null",
      "tile_type": "value or null",
      "additional_notes": []
    }},
    "external_wall": {{
      "interior_leakage": "Yes/No/null",
      "leakage_during": "value or null",
      "concealed_plumbing_leakage": "Yes/No/null",
      "internal_wc_bath_leakage": "Yes/No/null",
      "paint_type": "value or null",
      "rcc_cracks_condition": "Moderate/Major/Minor/N/A or null",
      "rust_marks_rcc": "value or null",
      "corrosion_spalling": "value or null",
      "expansion_joints": "value or null",
      "external_cracks": "Moderate/Major/Minor/N/A or null",
      "sealants_window": "value or null",
      "ac_frames_drain_pipes": "value or null",
      "external_plumbing_cracks": "Moderate/Major/Minor/N/A or null",
      "pipe_openings_grouted": "value or null",
      "vegetation_antennas": "value or null",
      "paint_chalking_flaking": "value or null",
      "algae_fungus_moss": "Moderate/Major/Minor/N/A or null",
      "bird_droppings": "value or null",
      "metal_corrosion": "value or null",
      "plaster_patchwork_required": "value or null",
      "entire_replaster_required": "value or null",
      "separation_cracks_beam_column": "value or null",
      "overhead_tank_leakage": "value or null",
      "loose_plaster_hollow": "value or null"
    }}
  }},
  "flagged_items": "description or null",
  "overall_score": "value or null"
}}

Return ONLY the JSON. No markdown code fences, no explanations. Just the JSON object.
"""


# ============================================================
# PROMPT 2: Extract thermal imaging data
# ============================================================
THERMAL_EXTRACTION_PROMPT = """You are an AI assistant analyzing thermal imaging reports.
Extract all temperature readings and metadata from the following text.

## THERMAL REPORT TEXT:
{text}

## EXTRACTION RULES:
1. Extract all temperature readings (in °C) with their page numbers
2. Extract dates if present
3. Note any hotspot/coldspot values
4. Extract emissivity and reflected temperature if available
5. Note which pages lack temperature readings

## OUTPUT FORMAT:
{{
  "thermal_readings": [
    {{
      "page": 1,
      "temperature_c": 28.8,
      "date": null,
      "has_reading": true
    }}
  ],
  "temperature_range": {{
    "min_c": 25.2,
    "max_c": 28.8
  }},
  "pages_without_readings": [],
  "metadata": {{
    "hotspot": null,
    "coldspot": null,
    "emissivity": null,
    "reflected_temperature": null
  }}
}}

Return ONLY the JSON. No markdown, no explanations.
"""


# ============================================================
# PROMPT 3: Merge inspection + thermal data
# ============================================================
DATA_MERGING_PROMPT = """You are an AI assistant merging building inspection data with thermal imaging data.

## INSPECTION DATA:
{inspection_data}

## THERMAL DATA:
{thermal_data}

## THERMAL-AREA MAPPING:
{thermal_mapping}

## INSTRUCTIONS:
1. Combine observations from both sources logically
2. Where thermal images match inspection areas, link them
3. Where thermal data is missing for an area, note it
4. Identify any conflicts between the two data sources
5. Do NOT remove any inspection observations
6. Add thermal insights where they support findings

## OUTPUT FORMAT:
{{
  "merged_areas": [
    {{
      "area_name": "Hall",
      "inspection_findings": {{
        "negative_side": "...",
        "positive_side": "..."
      }},
      "thermal_findings": {{
        "available": true/false,
        "temperature_readings": [],
        "thermal_image_count": 0,
        "notes": "explanation if not available"
      }},
      "combined_assessment": "summary combining both data sources",
      "conflicts": []
    }}
  ],
  "overall_thermal_assessment": "summary of thermal findings relevance",
  "areas_missing_thermal_data": ["list"],
  "data_conflicts": []
}}

Return ONLY the JSON.
"""


# ============================================================
# PROMPT 4: Generate final DDR report
# ============================================================
DDR_GENERATION_PROMPT = """You are a senior building diagnostics engineer creating a professional Detailed Diagnostic Report (DDR) for a client.

## DATA TO USE:
{merged_data}

## STRICT FORMATTING RULES:

### 1. PROPERTY ISSUE SUMMARY
Write 2-3 paragraphs summarizing what problems were found across the property, which areas are affected, the overall severity level, and the primary cause if identified.

### 2. AREA-WISE OBSERVATIONS
For EACH affected area, use this exact format:

**Area Name Here**
- **Observation:** Clearly describe the problem seen during inspection
- **Source:** Where the problem originates, or "Not clearly identified in the report"
- **Thermal Data:** Temperature reading if available, or "Thermal Image Not Available"
- **Severity:** Low / Moderate / High

Do NOT list photo numbers. Photos are embedded separately in the final report.
One entry per area. If an area has multiple issues, combine them into one observation.

### 3. PROBABLE ROOT CAUSE
Explain the likely causes in simple, client-friendly terms. Include:
- Primary cause of the issues
- Contributing factors
- How different issues may be connected

### 4. SEVERITY ASSESSMENT
Create a table with columns: Area | Severity | Reason

### 5. RECOMMENDED ACTIONS
Organize by timeframe:
- Immediate Actions (0-2 weeks)
- Short-term Actions (2-4 weeks)
- Medium-term Actions (1-3 months)
- Monitoring Recommendations

### 6. ADDITIONAL NOTES
Any important context, limitations of the inspection, or observations about data quality.

### 7. MISSING OR UNCLEAR INFORMATION
Create a table with columns: Information Item | Status
List all missing fields explicitly. Write "Not Available" where information is missing.

## ABSOLUTE RULES:
- Use ONLY information from the provided data
- If information is missing, write "Not Available" - NEVER guess or invent
- Do NOT invent or list photo numbers anywhere in the text
- Keep language simple and client-friendly
- No unnecessary technical jargon
- Be honest about what you don't know

Generate the complete DDR now:"""


# ============================================================
# PROMPT 5: Fallback/error handling extraction
# ============================================================
FALLBACK_EXTRACTION_PROMPT = """The primary extraction failed. Please extract whatever information you can from this text.
Focus on:
1. Any room/area names mentioned
2. Any problems or issues described
3. Any temperature readings
4. Any photo references

## TEXT:
{text}

Return as JSON with whatever fields you can populate. Use null for unknown values.
"""