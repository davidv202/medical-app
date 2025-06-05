# PdfGenerator actualizat cu semnătură elegantă și discretă (app/infrastructure/pdf_generator.py)

from datetime import datetime
from weasyprint import HTML, CSS
from typing import Dict, Any


class PdfGenerator:
    def __init__(self, css_path: str):
        self.css_path = css_path

    def create_pdf(self, content: str, metadata: Dict[str, Any], output_path: str, doctor_name: str = None):
        generated_date = datetime.now().strftime("%d.%m.%Y %H:%M")
        html_content = self._build_html_content(content, metadata, generated_date, doctor_name)

        stylesheets = []
        if self.css_path:
            stylesheets.append(CSS(self.css_path))

        HTML(string=html_content).write_pdf(output_path, stylesheets=stylesheets)

    def _build_html_content(self, content: str, metadata: Dict[str, Any], generated_date: str,
                            doctor_name: str = None) -> str:
        # Construiește semnătura discretă a doctorului
        doctor_signature = ""
        if doctor_name:
            doctor_signature = f"""
            <div class="doctor-signature-container">
                <div class="doctor-signature-line"></div>
                <div class="doctor-signature-text">
                    <span class="doctor-name">{doctor_name}</span>
                    <span class="doctor-title">Medic Radiolog</span>
                </div>
            </div>
            """

        # Template HTML complet
        return f"""
        <!DOCTYPE html>
        <html lang="ro">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Rezultat Explorare Radiologică</title>
        </head>
        <body>
            <div class="main-content">
                <h1>Rezultat Explorare Radiologică</h1>
                <p style="text-align: right; font-size: 11px; color: #6c757d; margin: 0 0 20px 0; font-style: italic;">
                    <strong>Data generării:</strong> {generated_date}
                </p>

                <div class="section">
                    <h2>Date Pacient și Studiu</h2>
                    <table class="meta-table">
                        {''.join(f'<tr><td class="label">{key}</td><td>{value or "N/A"}</td></tr>' for key, value in metadata.items())}
                    </table>
                </div>

                <div class="section">
                    <h2>Rezultatul Explorării</h2>
                    <div class="text-block">
                        {self._format_content_for_html(content)}
                    </div>
                </div>

                {doctor_signature}
            </div>

            <!-- Spacer pentru a împinge footer-ul jos -->
            <div class="content-spacer"></div>

            <div class="document-footer">
                <div class="footer-content">
                    <div class="footer-left">
                        <div class="footer-title">Sistemul Medical PACS</div>
                        <div class="footer-subtitle">Departamentul de Radiologie</div>
                    </div>
                    <div class="footer-right">
                        <div class="footer-date">Generat: {generated_date}</div>
                        <div class="footer-system">Document electronic autentificat</div>
                    </div>
                </div>
            </div>

        </body>
        </html>
        """

    def _format_content_for_html(self, content: str) -> str:
        """Formatează conținutul pentru HTML, păstrând formatarea text"""
        if not content.strip():
            return "<em style='color: #94a3b8; font-size: 11px;'>Nu a fost introdus niciun rezultat al explorării.</em>"

        # Escape HTML characters
        content = content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

        # Convertește line breaks în paragraphs
        paragraphs = content.split('\n\n')
        formatted_paragraphs = []

        for paragraph in paragraphs:
            if paragraph.strip():
                # Înlocuiește line breaks simple cu <br>
                paragraph = paragraph.replace('\n', '<br>')
                formatted_paragraphs.append(f'<p>{paragraph}</p>')

        return ''.join(formatted_paragraphs) if formatted_paragraphs else f'<p>{content}</p>'

    def generate_preview_html(self, content: str, metadata: Dict[str, Any], doctor_name: str = None) -> str:
        """Generează HTML pentru previzualizare (fără a salva PDF-ul)"""
        generated_date = datetime.now().strftime("%d.%m.%Y %H:%M")
        return self._build_html_content(content, metadata, generated_date, doctor_name)