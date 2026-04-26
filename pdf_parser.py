"""
PDF Parser Module
Extracts text and images from inspection and thermal PDFs
With smart filtering to remove UI elements and duplicates
"""

import fitz
import pdfplumber
from PIL import Image
import io
import os
import re
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from config import Config


@dataclass
class ImageInfo:
    """Dataclass for extracted image information"""
    page: int
    filename: str
    path: str
    hash: str
    width: int
    height: int
    size_bytes: int
    description: Optional[str] = None
    area: Optional[str] = None
    image_type: Optional[str] = None


class PDFParser:
    """Handles PDF parsing for both inspection reports and thermal images"""
    
    def __init__(self, pdf_path: str, pdf_type: str = "unknown"):
        self.pdf_path = pdf_path
        self.pdf_type = pdf_type
        self.pdf_name = Path(pdf_path).stem
        
        # Create temp directory
        self.temp_dir = Config.TEMP_DIR / self.pdf_name
        self.temp_dir.mkdir(exist_ok=True, parents=True)
        self.image_dir = self.temp_dir / "images"
        self.image_dir.mkdir(exist_ok=True)
        
        # Open PDF with both libraries
        try:
            self.doc_fitz = fitz.open(pdf_path)
            self.doc_plumber = pdfplumber.open(pdf_path)
            self.total_pages = len(self.doc_fitz)
        except Exception as e:
            raise RuntimeError(f"Failed to open PDF {pdf_path}: {e}")
    
    def extract_text(self) -> Dict[int, str]:
        """Extract text from all pages"""
        text_by_page = {}
        
        for page_num, page in enumerate(self.doc_plumber.pages, 1):
            try:
                text = page.extract_text()
                if text and text.strip():
                    text_by_page[page_num] = text.strip()
                else:
                    text_by_page[page_num] = ""
            except Exception as e:
                print(f"Warning: Failed to extract text from page {page_num}: {e}")
                text_by_page[page_num] = ""
        
        return text_by_page
    
    def extract_images(self, 
                       min_width: int = 200, 
                       min_height: int = 200,
                       max_aspect_ratio: float = 5.0,
                       min_size_bytes: int = 5000,
                       skip_duplicates: bool = True) -> List[ImageInfo]:
        """
        Extract images from PDF with smart filtering
        
        Args:
            min_width: Minimum image width in pixels (skip tiny icons)
            min_height: Minimum image height in pixels
            max_aspect_ratio: Maximum width/height ratio (skip banners)
            min_size_bytes: Minimum file size in bytes (skip tiny files)
            skip_duplicates: Skip images with duplicate hashes
        """
        images = []
        seen_hashes = set()
        
        for page_num in range(self.total_pages):
            page = self.doc_fitz[page_num]
            image_list = page.get_images(full=True)
            
            for img_idx, img in enumerate(image_list):
                try:
                    xref = img[0]
                    base_image = self.doc_fitz.extract_image(xref)
                    
                    if not base_image:
                        continue
                    
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]
                    
                    # === SMART FILTERING ===
                    
                    # Skip tiny files (likely UI elements, icons)
                    if len(image_bytes) < min_size_bytes:
                        continue
                    
                    # Generate hash for deduplication
                    img_hash = hashlib.md5(image_bytes).hexdigest()[:12]
                    
                    # Skip duplicates
                    if skip_duplicates and img_hash in seen_hashes:
                        continue
                    seen_hashes.add(img_hash)
                    
                    # Generate filename
                    img_filename = f"page{page_num+1:03d}_img{img_idx+1:03d}_{img_hash}.{image_ext}"
                    img_path = self.image_dir / img_filename
                    
                    # Save image if not exists
                    if not img_path.exists():
                        with open(img_path, "wb") as f:
                            f.write(image_bytes)
                    
                    # Get dimensions
                    try:
                        pil_img = Image.open(img_path)
                        width, height = pil_img.size
                    except:
                        width, height = 0, 0
                    
                    # Skip images that are too small
                    if width < min_width or height < min_height:
                        continue
                    
                    # Skip banner images (very wide but short)
                    if min(width, height) > 0:
                        aspect_ratio = max(width, height) / min(width, height)
                        if aspect_ratio > max_aspect_ratio:
                            continue
                    
                    # Determine image type
                    img_type = self.pdf_type
                    if self.pdf_type == "thermal":
                        img_type = "thermal"
                    elif self.pdf_type == "inspection":
                        img_type = "inspection"
                    
                    image_info = ImageInfo(
                        page=page_num + 1,
                        filename=img_filename,
                        path=str(img_path),
                        hash=img_hash,
                        width=width,
                        height=height,
                        size_bytes=len(image_bytes),
                        image_type=img_type
                    )
                    
                    images.append(image_info)
                    
                except Exception as e:
                    print(f"Warning: Failed to extract image {img_idx} from page {page_num+1}: {e}")
                    continue
        
        return images
    
    def extract_temperatures(self, text_by_page: Dict[int, str]) -> List[Dict]:
        """Extract temperature readings from text (for thermal reports)"""
        temperatures = []
        
        for page_num, text in text_by_page.items():
            temperatures_found = []
            
            # Look for temperature patterns
            temp_patterns = [
                r'(\d+\.?\d*)\s*°C',
                r'(\d+\.?\d*)\s*degrees?\s*celsius',
                r'Hotspot\s*:?\s*(\d+\.?\d*)\s*°C',
                r'Coldspot\s*:?\s*(\d+\.?\d*)\s*°C',
            ]
            
            for pattern in temp_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                temperatures_found.extend([float(m) for m in matches])
            
            # Look for date
            date_match = re.search(r'(\d{2}/\d{2}/\d{2,4})', text)
            
            # Look for metadata
            hotspot = None
            coldspot = None
            emissivity = None
            
            hotspot_match = re.search(r'Hotspot\s*:?\s*(\d+\.?\d*)\s*°C', text)
            coldspot_match = re.search(r'Coldspot\s*:?\s*(\d+\.?\d*)\s*°C', text)
            emissivity_match = re.search(r'Emissivity\s*:?\s*(\d+\.?\d*)', text)
            
            if hotspot_match:
                hotspot = float(hotspot_match.group(1))
            if coldspot_match:
                coldspot = float(coldspot_match.group(1))
            if emissivity_match:
                emissivity = float(emissivity_match.group(1))
            
            temperatures.append({
                "page": page_num,
                "temperatures": temperatures_found,
                "date": date_match.group(1) if date_match else None,
                "hotspot": hotspot,
                "coldspot": coldspot,
                "emissivity": emissivity,
                "has_reading": len(temperatures_found) > 0
            })
        
        return temperatures
    
    def get_summary(self) -> Dict:
        """Get PDF summary statistics"""
        return {
            "filename": self.pdf_name,
            "type": self.pdf_type,
            "total_pages": self.total_pages,
            "file_size_mb": round(os.path.getsize(self.pdf_path) / (1024 * 1024), 2)
        }
    
    def close(self):
        """Close PDF documents"""
        try:
            self.doc_fitz.close()
            self.doc_plumber.close()
        except:
            pass
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()