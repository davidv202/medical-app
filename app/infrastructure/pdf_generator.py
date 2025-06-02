from datetime import datetime
from weasyprint import HTML, CSS
from typing import Dict, Any


class PdfGenerator:
    def __init__(self, css_path: str):
        self.css_path = css_path

    def create_pdf(self, content: str, metadata: Dict[str, Any], output_path: str):
        generated_date = datetime.now().strftime("%d.%m.%Y %H:%M")

        html_content = self._build_html_content(content, metadata, generated_date)

        stylesheets = []
        if self.css_path:
            stylesheets.append(CSS(self.css_path))

        HTML(string=html_content).write_pdf(output_path, stylesheets=stylesheets)

    def _build_html_content(self, content: str, metadata: Dict[str, Any], generated_date: str) -> str:
        return f"""
        <html>
        <head>
            <style>
                body {{
                    font-family: 'DejaVu Sans', sans-serif;
                    margin: 40px;
                    font-size: 14px;
                }}
                h1 {{
                    text-align: center;
                    font-size: 22px;
                    margin-bottom: 10px;
                }}
                .section {{
                    margin-top: 25px;
                }}
                .meta-table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 10px;
                }}
                .meta-table td {{
                    border: 1px solid #999;
                    padding: 8px;
                }}
                .meta-table td.label {{
                    font-weight: bold;
                    background-color: #f0f0f0;
                    width: 30%;
                }}
                .text-block {{
                    margin-top: 15px;
                    white-space: pre-wrap;
                    line-height: 1.6;
                }}
            </style>
        </head>
        <body>
            <h1>Rezultat Explorare Radiologica</h1>
            <p><strong>Data generarii:</strong> {generated_date}</p>

            <div class="section">
                <h2>Date pacient si studiu</h2>
                <table class="meta-table">
                    {''.join(f'<tr><td class="label">{key}</td><td>{value or ""}</td></tr>' for key, value in metadata.items())}
                </table>
            </div>

            <div class="section">
                <h2>Rezultatul explorarii</h2>
                <div class="text-block">{content.strip() or "Nu a fost introdus niciun rezultat al explorarii."}</div>
            </div>

        </body>
        </html>
        """