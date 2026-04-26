import os
import base64
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
from jinja2 import Template
import markdown
from config import Config

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Detailed Diagnostic Report (DDR)</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Segoe UI', system-ui, sans-serif;
            line-height: 1.7;
            color: #2d3748;
            max-width: 1100px;
            margin: 0 auto;
            padding: 20px;
            background: #edf2f7;
        }
        .report-container {
            background: white;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            border-radius: 8px;
            overflow: hidden;
        }
        .report-header {
            background: linear-gradient(135deg, #1a365d, #2c5282);
            color: white;
            padding: 40px;
            text-align: center;
            border-bottom: 4px solid #3182ce;
        }
        .report-header h1 { font-size: 32px; margin-bottom: 8px; }
        .report-body { padding: 40px; }
        h2 {
            color: #1a365d;
            border-bottom: 3px solid #3182ce;
            padding-bottom: 10px;
            margin: 35px 0 15px;
        }
        h3 { color: #2c5282; margin: 25px 0 12px; }
        
        /* IMAGE GALLERY STYLES */
        .image-gallery {
            margin: 25px 0;
            padding: 20px;
            background: #f7fafc;
            border-radius: 8px;
            border: 2px solid #e2e8f0;
        }
        .image-gallery h4 {
            color: #2c5282;
            margin-bottom: 15px;
            font-size: 16px;
        }
        .image-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
        }
        .image-card {
            background: white;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            transition: transform 0.2s;
        }
        .image-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 6px 12px rgba(0,0,0,0.1);
        }
        .image-card img {
            width: 100%;
            height: 250px;
            object-fit: cover;
            cursor: pointer;
            display: block;
        }
        .image-card .caption {
            padding: 12px 16px;
            font-size: 13px;
            color: #718096;
            background: #f7fafc;
            border-top: 1px solid #e2e8f0;
        }
        .thermal-badge {
            display: inline-block;
            background: #e53e3e;
            color: white;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            margin-left: 8px;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        th {
            background: #1a365d;
            color: white;
            padding: 14px 16px;
            text-align: left;
        }
        td {
            padding: 12px 16px;
            border-bottom: 1px solid #e2e8f0;
        }
        tr:nth-child(even) { background: #f7fafc; }
        
        .severity-high { color: #e53e3e; font-weight: bold; }
        .severity-moderate { color: #dd6b20; font-weight: bold; }
        .severity-low { color: #38a169; font-weight: bold; }
        .not-available { color: #e53e3e; font-style: italic; }
        
        .report-footer {
            background: #f7fafc;
            padding: 25px 40px;
            border-top: 2px solid #e2e8f0;
            font-size: 12px;
            color: #718096;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="report-container">
        <header class="report-header">
            <h1>Detailed Diagnostic Report</h1>
            <div>Property Inspection & Thermal Analysis</div>
            <div style="font-size:13px;opacity:0.7;margin-top:8px;">Generated: {{ date }} at {{ time }}</div>
        </header>
        <main class="report-body">
            {{ content }}
        </main>
        <footer class="report-footer">
            <p>DDR Generator v1.0 | Generated using {{ metadata.provider }}/{{ metadata.model }}</p>
            <p>Confidential - For Client Use Only</p>
        </footer>
    </div>
</body>
</html>
'''


class DDRCompiler:
    
    def __init__(self, output_dir=None):
        self.output_dir = Path(output_dir or Config.OUTPUT_DIR)
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.template = Template(HTML_TEMPLATE)
    
    def generate_html(self, ddr_content, images_by_area=None, metadata=None):
        if images_by_area is None:
            images_by_area = {}
        if metadata is None:
            metadata = {}
        
        # Convert markdown to HTML
        content_html = markdown.markdown(ddr_content, extensions=['tables', 'fenced_code'])
        
        # EMBED IMAGES after area headings
        content_html = self._embed_images(content_html, images_by_area)
        
        template_vars = {
            "date": datetime.now().strftime("%B %d, %Y"),
            "time": datetime.now().strftime("%H:%M"),
            "content": content_html,
            "metadata": metadata
        }
        
        return self.template.render(**template_vars)
    
    def _embed_images(self, html_content, images_by_area):
        import re
        
        for area_name, image_list in images_by_area.items():
            if not image_list:
                continue
            
            # Build image gallery HTML
            gallery = f'<div class="image-gallery">\n'
            gallery += f'<h4>Inspection Images - {area_name}</h4>\n'
            gallery += '<div class="image-grid">\n'
            
            for img in image_list:
                data_uri = img.get("data_uri", "")
                description = img.get("description", "Image")
                is_thermal = img.get("is_thermal", False)
                
                badge = '<span class="thermal-badge">THERMAL</span>' if is_thermal else ''
                
                if data_uri:
                    gallery += f'''
                    <div class="image-card">
                        <img src="{data_uri}" alt="{description}" loading="lazy">
                        <div class="caption">{description}{badge}</div>
                    </div>\n'''
                else:
                    gallery += f'''
                    <div class="image-card">
                        <div style="height:250px;display:flex;align-items:center;justify-content:center;background:#edf2f7;color:#a0aec0;">
                            Image Not Available
                        </div>
                        <div class="caption">{description}</div>
                    </div>\n'''
            
            gallery += '</div>\n</div>\n'
            
            # Insert after area heading
            # Find heading containing the area name
            pattern = re.compile(
                f'(<h[23][^>]*>[^<]*{re.escape(area_name)}[^<]*</h[23]>)',
                re.IGNORECASE
            )
            
            match = pattern.search(html_content)
            if match:
                insert_pos = match.end()
                html_content = html_content[:insert_pos] + gallery + html_content[insert_pos:]
            else:
                # If no heading found, append at the end
                html_content += gallery
        
        return html_content
    
    def save_report(self, html_content, filename=None):
        if filename is None:
            filename = f"DDR_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        html_path = self.output_dir / f"{filename}.html"
        
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        result = {'html': str(html_path)}
        
        # Try PDF
        try:
            from weasyprint import HTML
            pdf_path = self.output_dir / f"{filename}.pdf"
            HTML(string=html_content).write_pdf(str(pdf_path))
            result['pdf'] = str(pdf_path)
        except:
            pass
        
        return result
