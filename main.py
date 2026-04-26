#!/usr/bin/env python3
"""
DDR Generator - AI-Powered Detailed Diagnostic Report System
Extracts images from PDFs and generates structured reports
"""

import os
import sys
import json
import argparse
import base64
from pathlib import Path
from datetime import datetime
from typing import Optional
from collections import defaultdict

from dotenv import load_dotenv
load_dotenv()

from config import Config
from pdf_parser import PDFParser
from data_extractor import LLMExtractor
from thermal_matcher import ThermalImageMatcher
from ddr_compiler import DDRCompiler


class DDRGenerator:
    
    def __init__(self):
        self._print_header()
        
        try:
            Config.validate()
        except ValueError as e:
            print(f"ERROR: {e}")
            print("Please check your .env file has a valid API key")
            sys.exit(1)
        
        print(f"  Provider: {Config.LLM_PROVIDER} | Model: {Config.LLM_MODEL}")
        self.extractor = LLMExtractor()
        self.matcher = ThermalImageMatcher()
        self.compiler = DDRCompiler()
        print("  All components initialized\n")
    
    def _extract_images_from_pdf(self, pdf_path: str, pdf_type: str = "inspection") -> list:
        """
        Extract images from a PDF and return as dicts with base64 data URIs.
        Uses smart filtering from pdf_parser to skip UI elements and duplicates.
        """
        parser = PDFParser(pdf_path, pdf_type=pdf_type)
        
        # Extract with smart filtering
        all_images = parser.extract_images(
            min_width=200,
            min_height=200,
            max_aspect_ratio=5.0,
            min_size_bytes=5000,
            skip_duplicates=True
        )
        
        result = []
        
        for img in all_images:
            if img.path and os.path.exists(img.path):
                try:
                    with open(img.path, "rb") as f:
                        img_data = base64.b64encode(f.read()).decode()
                    
                    ext = Path(img.path).suffix.lower()
                    mime = {
                        '.jpg': 'image/jpeg',
                        '.jpeg': 'image/jpeg',
                        '.png': 'image/png',
                        '.gif': 'image/gif',
                    }.get(ext, 'image/jpeg')
                    
                    result.append({
                        "page": img.page,
                        "filename": img.filename,
                        "path": img.path,
                        "width": img.width,
                        "height": img.height,
                        "base64": img_data,
                        "mime": mime,
                        "data_uri": f"data:{mime};base64,{img_data}",
                        "type": img.image_type or pdf_type,
                        "hash": img.hash
                    })
                except Exception as e:
                    print(f"    Warning: Could not process {img.filename}: {e}")
        
        parser.close()
        
        # Filter duplicates by hash again (safety check)
        seen = set()
        unique_result = []
        for img in result:
            if img["hash"] not in seen:
                seen.add(img["hash"])
                unique_result.append(img)
        
        print(f"    Extracted {len(unique_result)} unique images (filtered from PDF)")
        return unique_result
    
    def _assign_images_to_areas(self, inspection_data: dict, inspection_images: list, thermal_images: list = None) -> dict:
        """
        Assign images to areas based on page numbers and area order in the report.
        Distributes images fairly across all impacted areas.
        """
        if thermal_images is None:
            thermal_images = []
        
        images_by_area = defaultdict(list)
        areas = inspection_data.get("impacted_areas", [])
        
        if not areas:
            # No areas found - put all images under "General"
            for img in inspection_images:
                images_by_area["General"].append({
                    "data_uri": img["data_uri"],
                    "description": f"Inspection photo (Page {img['page']})",
                    "page": img["page"],
                    "is_thermal": False
                })
            return dict(images_by_area)
        
        # Sort images by page number
        sorted_images = sorted(inspection_images, key=lambda x: x["page"])
        
        # Distribute images to areas
        # Each area gets images from a range of pages
        images_per_area = max(2, len(sorted_images) // max(1, len(areas)))
        
        for area_idx, area in enumerate(areas):
            area_name = area.get("area_name", f"Area {area_idx + 1}")
            
            # Get photo references from the data
            neg_photos = area.get("negative_side", {}).get("photos", [])
            pos_photos = area.get("positive_side", {}).get("photos", [])
            all_refs = neg_photos + pos_photos
            
            # Calculate image range for this area
            start_idx = area_idx * images_per_area
            end_idx = min(start_idx + images_per_area, len(sorted_images))
            
            # Add inspection images
            added = 0
            for img_idx in range(start_idx, end_idx):
                if img_idx < len(sorted_images):
                    img = sorted_images[img_idx]
                    ref_text = all_refs[added] if added < len(all_refs) else f"Photo {img['page']}"
                    
                    images_by_area[area_name].append({
                        "data_uri": img["data_uri"],
                        "description": f"{area_name} - {ref_text} (Page {img['page']})",
                        "page": img["page"],
                        "is_thermal": False
                    })
                    added += 1
            
            # Add 1-2 thermal images per area if available
            if thermal_images:
                therm_start = area_idx % max(1, len(thermal_images))
                for t in range(min(2, len(thermal_images))):
                    t_idx = (therm_start + t) % len(thermal_images)
                    if t_idx < len(thermal_images):
                        t_img = thermal_images[t_idx]
                        images_by_area[area_name].append({
                            "data_uri": t_img["data_uri"],
                            "description": f"{area_name} - Thermal Reading (Page {t_img['page']})",
                            "page": t_img["page"],
                            "is_thermal": True
                        })
        
        return dict(images_by_area)
    
    def process(self, inspection_pdf_path: str, thermal_pdf_path: str, output_name: Optional[str] = None) -> str:
        
        # Validate inputs
        if not Path(inspection_pdf_path).exists():
            print(f"ERROR: Inspection PDF not found: {inspection_pdf_path}")
            return None
        if not Path(thermal_pdf_path).exists():
            print(f"ERROR: Thermal PDF not found: {thermal_pdf_path}")
            return None
        
        print("=" * 60)
        print("  STARTING DDR GENERATION PIPELINE")
        print("=" * 60)
        
        # ============================================================
        # STEP 1: Parse PDFs and extract text
        # ============================================================
        print("\n[1/5] Parsing PDF documents...")
        
        insp_parser = PDFParser(inspection_pdf_path, pdf_type="inspection")
        therm_parser = PDFParser(thermal_pdf_path, pdf_type="thermal")
        
        insp_text = insp_parser.extract_text()
        therm_text = therm_parser.extract_text()
        temperatures = therm_parser.extract_temperatures(therm_text)
        
        insp_summary = insp_parser.get_summary()
        therm_summary = therm_parser.get_summary()
        
        print(f"  Inspection PDF: {insp_summary['total_pages']} pages")
        print(f"  Thermal PDF: {therm_summary['total_pages']} pages")
        print(f"  Temperature readings found: {len(temperatures)}")
        
        # ============================================================
        # STEP 2: Extract images from both PDFs
        # ============================================================
        print("\n[2/5] Extracting images from PDFs...")
        
        inspection_images = self._extract_images_from_pdf(inspection_pdf_path, "inspection")
        thermal_images = self._extract_images_from_pdf(thermal_pdf_path, "thermal")
        
        print(f"  Total inspection photos: {len(inspection_images)}")
        print(f"  Total thermal images: {len(thermal_images)}")
        
        # ============================================================
        # STEP 3: AI Extraction
        # ============================================================
        print("\n[3/5] Extracting structured data with AI...")
        
        inspection_data = self.extractor.extract_inspection_data(insp_text)
        
        if "error" in inspection_data:
            print(f"  Warning: {inspection_data['error']}")
        
        num_areas = len(inspection_data.get("impacted_areas", []))
        print(f"  Impacted areas identified: {num_areas}")
        
        # Print area names
        for area in inspection_data.get("impacted_areas", []):
            name = area.get("area_name", "Unknown")
            neg = area.get("negative_side", {}).get("description", "N/A")
            print(f"    - {name}: {neg[:60]}...")
        
        thermal_data = self.extractor.extract_thermal_data(therm_text, temperatures)
        
        temp_range = thermal_data.get("temperature_range", {})
        if temp_range.get("min_c"):
            print(f"  Temperature range: {temp_range['min_c']}C to {temp_range['max_c']}C")
        
        # ============================================================
        # STEP 4: Assign images to areas
        # ============================================================
        print("\n[4/5] Assigning images to report sections...")
        
        images_by_area = self._assign_images_to_areas(
            inspection_data, 
            inspection_images, 
            thermal_images
        )
        
        for area, imgs in images_by_area.items():
            insp_count = sum(1 for i in imgs if not i.get("is_thermal"))
            therm_count = sum(1 for i in imgs if i.get("is_thermal"))
            print(f"  {area}: {insp_count} inspection + {therm_count} thermal = {len(imgs)} total images")
        
        # ============================================================
        # STEP 5: Generate DDR Report
        # ============================================================
        print("\n[5/5] Merging data and generating report...")
        
        merged_data = self.extractor.merge_data(inspection_data, thermal_data)
        
        # Save merged data for reference
        merged_json_path = Config.OUTPUT_DIR / "merged_data.json"
        with open(merged_json_path, 'w', encoding='utf-8') as f:
            json.dump(merged_data, f, indent=2, default=str)
        print(f"  Merged data saved: merged_data.json")
        
        # Generate DDR content via LLM
        ddr_content = self.extractor.generate_ddr(merged_data)
        
        # ============================================================
        # COMPILE FINAL HTML REPORT
        # ============================================================
        print("\n" + "=" * 60)
        print("  COMPILING FINAL REPORT")
        print("=" * 60)
        
        html_content = self.compiler.generate_html(
            ddr_content,
            images_by_area,
            metadata={
                "inspection_file": Path(inspection_pdf_path).name,
                "thermal_file": Path(thermal_pdf_path).name,
                "provider": Config.LLM_PROVIDER,
                "model": Config.LLM_MODEL
            }
        )
        
        # Save report
        results = self.compiler.save_report(html_content, output_name)
        
        # Cleanup
        insp_parser.close()
        therm_parser.close()
        
        # ============================================================
        # DONE
        # ============================================================
        print("\n" + "=" * 60)
        print("  GENERATION COMPLETE!")
        print("=" * 60)
        
        if results.get('html'):
            print(f"\n  HTML Report: {results['html']}")
            print(f"  Open this file in your browser to see images!")
        if results.get('pdf'):
            print(f"  PDF Report: {results['pdf']}")
        
        # Show preview
        print("\n" + "-" * 40)
        print("  REPORT PREVIEW:")
        print("-" * 40)
        print(ddr_content[:600])
        print("  ... (truncated)")
        
        return results.get('html')
    
    def _print_header(self):
        print("\n" + "=" * 60)
        print("  DDR GENERATOR - AI Building Diagnostics System")
        print("=" * 60 + "\n")


def find_input_files():
    """Find PDF files in the input directory"""
    input_dir = Config.INPUT_DIR
    if not input_dir.exists():
        return None, None
    
    pdfs = list(input_dir.glob("*.pdf")) + list(input_dir.glob("*.PDF"))
    
    inspection_pdf = None
    thermal_pdf = None
    
    for pdf in pdfs:
        name_lower = pdf.name.lower()
        if "thermal" in name_lower:
            thermal_pdf = str(pdf)
        elif "inspection" in name_lower or "sample" in name_lower:
            inspection_pdf = str(pdf)
    
    if not inspection_pdf and len(pdfs) >= 1:
        inspection_pdf = str(pdfs[0])
    if not thermal_pdf and len(pdfs) >= 2:
        thermal_pdf = str(pdfs[1])
    
    return inspection_pdf, thermal_pdf


def main():
    parser = argparse.ArgumentParser(description="DDR Generator - AI Building Diagnostics")
    parser.add_argument("-i", "--inspection", help="Inspection report PDF path")
    parser.add_argument("-t", "--thermal", help="Thermal images PDF path")
    parser.add_argument("-o", "--output", help="Output report name", default=None)
    args = parser.parse_args()
    
    inspection_pdf = args.inspection
    thermal_pdf = args.thermal
    
    # Auto-find PDFs in input directory
    if not inspection_pdf or not thermal_pdf:
        print("Looking for PDFs in input directory...")
        found_insp, found_therm = find_input_files()
        inspection_pdf = inspection_pdf or found_insp
        thermal_pdf = thermal_pdf or found_therm
    
    if not inspection_pdf:
        print("ERROR: No inspection PDF found!")
        print("Use: python main.py -i 'inspection.pdf' -t 'thermal.pdf'")
        sys.exit(1)
    if not thermal_pdf:
        print("ERROR: No thermal PDF found!")
        print("Use: python main.py -i 'inspection.pdf' -t 'thermal.pdf'")
        sys.exit(1)
    
    print(f"\nInspection: {inspection_pdf}")
    print(f"Thermal: {thermal_pdf}")
    
    try:
        generator = DDRGenerator()
        result = generator.process(inspection_pdf, thermal_pdf, args.output)
        
        if result:
            print(f"\nSUCCESS! Report: {result}")
            # Auto-open on Windows
            if sys.platform == "win32":
                os.startfile(result)
    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()