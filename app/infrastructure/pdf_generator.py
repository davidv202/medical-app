from datetime import datetime
from weasyprint import HTML, CSS
from typing import Dict, Any


class PdfGenerator:
    def __init__(self, css_path: str):
        self.css_path = css_path

    def create_pdf(self, content: str, metadata: Dict[str, Any], output_path: str, doctor_name: str = None):
        generated_date = datetime.now().strftime("%d.%m.%Y %H:%M")
        current_year = datetime.now().strftime("%Y")

        # Filtrează și organizează metadatele pentru pacient
        patient_metadata = self._filter_patient_metadata(metadata)

        html_content = self._build_html_content(
            content, patient_metadata, generated_date, doctor_name, current_year
        )

        stylesheets = []
        if self.css_path:
            stylesheets.append(CSS(self.css_path))

        HTML(string=html_content).write_pdf(output_path, stylesheets=stylesheets)

    def _filter_patient_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:

        patient_fields = {
            # Patient information
            "Patient Name": "Nume pacient",
            "Patient Birth Date": "Data nașterii",
            "Patient Sex": "Sex",
            "Patient Age": "Vârsta",

            # Examination information
            "Study Date": "Data examinării",
            "Description": "Tip examinare",
            "Body Part Examined": "Zona examinată",
            "Referring Physician": "Medic trimițător",

            # Institution information
            "Institution Name": "Instituția medicală"
        }

        filtered_metadata = {}

        for original_key, friendly_name in patient_fields.items():
            value = metadata.get(original_key)
            if value and value != 'N/A' and value.strip():
                if original_key == "Study Time" and len(value) >= 6:
                    try:
                        formatted_time = f"{value[:2]}:{value[2:4]}:{value[4:6]}"
                        filtered_metadata[friendly_name] = formatted_time
                    except:
                        filtered_metadata[friendly_name] = value
                elif original_key == "Patient Sex":
                    sex_mapping = {"M": "Masculin", "F": "Feminin", "O": "Altul"}
                    filtered_metadata[friendly_name] = sex_mapping.get(value.upper(), value)
                else:
                    filtered_metadata[friendly_name] = value

        return filtered_metadata

    def _build_html_content(self, content: str, patient_metadata: Dict[str, Any], generated_date: str,
                            doctor_name: str = None, current_year: str = None) -> str:

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

        metadata_rows = ""
        for key, value in patient_metadata.items():
            metadata_rows += f'<tr><td class="label">{key}</td><td>{value}</td></tr>'

        return f"""
        <!DOCTYPE html>
        <html lang="ro">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Rezultat Investigație Medicală</title>
        </head>
        <body data-generation-date="{generated_date}" data-current-year="{current_year}">
            <div class="main-content">
                <h1>Rezultat Investigație Medicală</h1>
                <p class="generation-date">
                    <strong>Document generat:</strong> {generated_date}
                </p>

                <div class="section">
                    <h2>Informații despre Pacient și Investigație</h2>
                    <table class="meta-table">
                        {metadata_rows}
                    </table>
                </div>

                <div class="section">
                    <h2>Rezultatul Investigației</h2>
                    <div class="text-block">
                        {self._format_content_for_html(content)}
                    </div>
                </div>
                {doctor_signature}
            </div>

        </body>
        </html>
        """

    def _format_content_for_html(self, content: str) -> str:
        if not content.strip():
            return "<em style='color: #94a3b8; font-size: 11px; font-style: italic;'>Nu a fost introdus niciun rezultat al investigației.</em>"

        content = content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

        paragraphs = content.split('\n\n')
        formatted_paragraphs = []

        for paragraph in paragraphs:
            if paragraph.strip():
                paragraph = paragraph.replace('\n', '<br>')
                formatted_paragraphs.append(f'<p>{paragraph}</p>')

        return ''.join(formatted_paragraphs) if formatted_paragraphs else f'<p>{content}</p>'