# AI-REPORT-BUILDER

# 🏗️ DDR Generator — AI-Powered Building Diagnostics

An end-to-end AI workflow that converts technical inspection data into structured, client-ready Detailed Diagnostic Reports (DDR). Built for reliability, handles imperfect data, and never hallucinates facts.

---

## 📋 Overview

Building inspectors produce messy PDFs — scattered observations, missing fields, unlabeled thermal images. Turning this into a professional report takes hours of manual work.

This system automates the entire process in under 2 minutes. It takes two PDFs as input — an inspection report and thermal images — and generates a complete DDR with embedded images, root cause analysis, severity assessment, and prioritized recommendations.

**Core Principle:** When information is missing, the system says "Not Available" — never invents facts.

---

## 🧩 Architecture
INPUT PDFs → PDF PARSER → DATA EXTRACTOR → THERMAL MATCHER → DDR COMPILER → OUTPUT REPORT
↓ ↓ ↓ ↓
text+images structured JSON image matching HTML+PDF



### 5-Stage Pipeline

| Stage | File | Purpose |
|-------|------|---------|
| 1 | `pdf_parser.py` | Extract text + images, filter duplicates and UI elements |
| 2 | `data_extractor.py` | AI-powered extraction of structured data via LLM |
| 3 | `thermal_matcher.py` | Match thermal images to inspection areas using vision AI |
| 4 | `ddr_compiler.py` | Generate professional HTML/PDF report with embedded images |
| 5 | `main.py` | Orchestrate all stages sequentially |

### Supporting Files

| File | Purpose |
|------|---------|
| `prompts.py` | All AI prompts — makes the system generalizable to any inspection domain |
| `config.py` | Central configuration — API keys, paths, model settings |
| `.env` | Secure API key storage |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Groq API key (free tier available)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/ddr-generator.git
cd ddr-generator

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Mac/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```


## Output
The system generates a DDR with 7 standardized sections:

Property Issue Summary — Executive overview

Area-wise Observations — Room-by-room with embedded images

Probable Root Cause — AI-reasoned analysis

Severity Assessment — Table with ratings and justification

Recommended Actions — Prioritized by urgency

Additional Notes — Context and limitations

Missing or Unclear Information — Explicitly flagged gaps

Output formats: HTML (with embedded base64 images) and PDF.


## Tech Stack

Component	Technology
Language	Python 3.11
PDF Processing	PyMuPDF, pdfplumber
AI Model	Groq + Llama 3.3 70B
Vision Model	OpenAI CLIP (ViT-B/32)
Image Handling	Pillow
Report Generation	Jinja2, Markdown, WeasyPrint
Configuration	python-dotenv


## Key Design Decisions

Prompt Chaining — Multiple focused prompts instead of one monolithic prompt for better reliability

Explicit Null Handling — Every missing field defaults to "Not Available", never empty string or guess

Provider Agnostic — Works with OpenAI, Groq, or Anthropic by changing one config value

Smart Image Filtering — Hash-based deduplication, aspect ratio checks, minimum size thresholds

Prompt-Driven Architecture — Same code works for electrical, plumbing, or structural inspections



## Limitations

Thermal image matching is probabilistic without labeled training data

Groq free tier rate limits (30 requests/minute)

No human-in-the-loop review interface yet

English language only

## Future Improvements

Streamlit web interface for drag-and-drop usage

Fine-tuned smaller model (Llama 3 8B) on inspection terminology

OCR support for handwritten inspection notes

Review dashboard with confidence scores

Support for video walkthrough inputs

FastAPI backend for production deployment
