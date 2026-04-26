
### **7. `thermal_matcher.py`**

# ```python
"""
Thermal Image Matcher Module
Matches thermal images to inspection areas using computer vision
"""

import os
import json
from typing import List, Dict, Tuple, Optional
from pathlib import Path
import numpy as np
from PIL import Image
from config import Config

# Optional: Use CLIP for semantic image matching
try:
    import torch
    import torch.nn.functional as F
    from transformers import CLIPModel, CLIPProcessor
    from sklearn.metrics.pairwise import cosine_similarity
    CLIP_AVAILABLE = True
except ImportError:
    CLIP_AVAILABLE = False
    print("Warning: CLIP not available. Install torch, transformers, and scikit-learn for image matching.")


class ThermalImageMatcher:
    """
    Matches thermal images to inspection report areas.
    
    Since thermal images often lack labels, this module:
    1. Attempts visual similarity matching (if CLIP is available)
    2. Uses page order heuristics
    3. Falls back to "Not Available" when matching is inconclusive
    """
    
    def __init__(self, threshold: float = None):
        """
        Initialize the matcher
        
        Args:
            threshold: Similarity threshold for matching (0.0-1.0)
        """
        self.threshold = threshold or Config.IMAGE_SIMILARITY_THRESHOLD
        self.device = "cuda" if torch.cuda.is_available() else "cpu" if CLIP_AVAILABLE else "cpu"
        
        if CLIP_AVAILABLE:
            self._init_clip()
        else:
            self.model = None
            self.processor = None
    
    def _init_clip(self):
        """Initialize CLIP model for image comparison"""
        try:
            self.model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(self.device)
            self.processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
            self.model.eval()
            print(f"CLIP model loaded on {self.device}")
        except Exception as e:
            print(f"Failed to load CLIP: {e}")
            self.model = None
            self.processor = None
    
    def compute_image_similarity(self, img_path1: str, img_path2: str) -> float:
        """
        Compute similarity between two images
        
        Args:
            img_path1: Path to first image
            img_path2: Path to second image
            
        Returns:
            Similarity score (0.0-1.0)
        """
        if not CLIP_AVAILABLE or self.model is None:
            return self._compute_basic_similarity(img_path1, img_path2)
        
        try:
            img1 = Image.open(img_path1).convert("RGB")
            img2 = Image.open(img_path2).convert("RGB")
            
            inputs = self.processor(
                images=[img1, img2],
                return_tensors="pt",
                padding=True
            ).to(self.device)
            
            with torch.no_grad():
                image_features = self.model.get_image_features(**inputs)
                image_features = F.normalize(image_features, dim=-1)
            
            similarity = cosine_similarity(
                image_features[0:1].cpu().numpy(),
                image_features[1:2].cpu().numpy()
            )[0][0]
            
            return float(similarity)
        except Exception as e:
            print(f"CLIP similarity computation failed: {e}")
            return 0.0
    
    def _compute_basic_similarity(self, img_path1: str, img_path2: str) -> float:
        """
        Basic image similarity using histogram comparison
        Falls back when CLIP is not available
        """
        try:
            img1 = Image.open(img_path1).convert("RGB").resize((256, 256))
            img2 = Image.open(img_path2).convert("RGB").resize((256, 256))
            
            hist1 = np.array(img1).flatten()
            hist2 = np.array(img2).flatten()
            
            # Normalized cross-correlation
            correlation = np.corrcoef(hist1, hist2)[0, 1]
            return max(0.0, float(correlation)) if not np.isnan(correlation) else 0.0
        except:
            return 0.0
    
    def match_thermal_to_areas(
        self,
        inspection_images: List[Dict],
        thermal_images: List[Dict]
    ) -> Dict[str, List[Dict]]:
        """
        Match thermal images to inspection areas
        
        Args:
            inspection_images: List of inspection image info dicts
            thermal_images: List of thermal image info dicts
            
        Returns:
            Dictionary mapping area names to matched thermal images
        """
        matches = {}
        
        if not thermal_images:
            return {"_note": "No thermal images provided"}
        
        # Group inspection images by area
        area_inspection_images = {}
        for img in inspection_images:
            area = img.get("area", "Unknown")
            if area not in area_inspection_images:
                area_inspection_images[area] = []
            area_inspection_images[area].append(img)
        
        # For each area, try to find matching thermal images
        for area, insp_imgs in area_inspection_images.items():
            matches[area] = []
            
            for insp_img in insp_imgs:
                best_match = None
                best_score = 0.0
                
                for therm_img in thermal_images:
                    score = self.compute_image_similarity(
                        insp_img.get("path", ""),
                        therm_img.get("path", "")
                    )
                    
                    if score > best_score and score >= self.threshold:
                        best_score = score
                        best_match = {
                            "thermal_image_path": therm_img.get("path"),
                            "thermal_page": therm_img.get("page"),
                            "similarity_score": round(score, 3)
                        }
                
                if best_match:
                    matches[area].append({
                        "inspection_image": insp_img,
                        "thermal_match": best_match
                    })
        
        # Add note for areas with no matches
        for area in area_inspection_images:
            if not matches.get(area):
                matches[area] = [{
                    "note": "No matching thermal image found",
                    "thermal_available": False
                }]
        
        return matches
    
    def generate_mapping_report(self, matches: Dict[str, List[Dict]]) -> str:
        """
        Generate a human-readable mapping report
        
        Args:
            matches: Match results from match_thermal_to_areas
            
        Returns:
            Formatted string report
        """
        report_lines = ["## Thermal-Image-to-Area Mapping Report", ""]
        
        for area, match_list in matches.items():
            if area.startswith("_"):
                continue
            
            report_lines.append(f"### {area}")
            
            matched_count = sum(1 for m in match_list if "thermal_match" in m)
            total = len(match_list)
            
            report_lines.append(f"- Matched: {matched_count}/{total} images")
            
            for i, match in enumerate(match_list):
                if "thermal_match" in match:
                    score = match["thermal_match"]["similarity_score"]
                    report_lines.append(f"  - Image {i+1}: Matched (score: {score})")
                else:
                    report_lines.append(f"  - Image {i+1}: {match.get('note', 'No match')}")
            
            report_lines.append("")
        
        return "\n".join(report_lines)