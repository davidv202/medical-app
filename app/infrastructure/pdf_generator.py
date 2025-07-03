import re
from datetime import datetime
from weasyprint import HTML, CSS
from typing import Dict, Any


class PdfGenerator:
    def __init__(self, css_path: str):
        self.css_path = css_path

    def create_pdf(self, content: str, metadata: Dict[str, Any], output_path: str, doctor_name: str = None):
        generated_date = datetime.now().strftime("%d.%m.%Y %H:%M")
        current_year = datetime.now().strftime("%Y")

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
                            doctor_name: str = None, current_year: str = None, selected_title: str = None) -> str:

        # Extrage datele din metadata
        patient_name = patient_metadata.get("Nume pacient", "")
        cnp = patient_metadata.get("CNP", "")
        dosar_nr = patient_metadata.get("Dosar nr.", "")
        gamma_camera = patient_metadata.get("Model echipament", "")
        investigation = patient_metadata.get("Tip examinare", "")
        diagnosis = patient_metadata.get("Diagnostic de trimitere", "")
        dose_mbq = patient_metadata.get("Doză administrată", "")
        radiopharmaceutical = patient_metadata.get("Radiofarmaceutic", "")
        exam_date = patient_metadata.get("Data examinării", "")

        exam_title = selected_title if selected_title else "Scintigrama renală statică cu <sup>99m</sup>Tc- DMSA"

        return f"""
        <!DOCTYPE html>
        <html lang="ro">
        <head>
            <meta charset="UTF-8">
            <title>{exam_title}</title>
        </head>
        <body>
            <div class="page-container">
                <!-- PARTEA STÂNGĂ - IDENTICĂ CU IMAGINEA -->
                <div class="left-panel">
                    <div class="lab-title">
                        <strong>Laborator<br>MEDICINA<br>NUCLEARĂ</strong>
                    </div>

                    <div class="prof-name">
                        <strong>Prof. dr.<br>Valeriu Rusu</strong>
                    </div>

                    <div class="address">
                        B-dul Independentei<br>
                        nr. 1, etaj, cod 700111<br>
                        tel./programări:<br>
                        <strong>0232 240 822,<br>
                        int.120</strong><br>
                        sau <strong>0770 936 586</strong><br>
                        e-mail:<br>
                        <strong>laboratornucleara<br>
                        @spitalspiridon.ro</strong>
                    </div>

                    <div class="section-header">
                        <strong>Sef laborator</strong><br>
                        <strong>Prof. dr. Cipriana<br>
                        STEFANESCU –</strong><br>
                        medic primar<br>
                        medicina nucleara si<br>
                        endocrinologie
                    </div>

                    <div class="section-header">
                        <strong><u>Medici</u></strong><br>
                        <strong>Ana Maria STATESCU</strong><br>
                        – medic primar med.<br>
                        nucl.<br>
                        <strong>Irena GRIEROSU</strong><br>
                        – sef lucr. dr., medic<br>
                        primar med. nucl.<br>
                        <strong>Cati-Raluca<br>
                        STOLNICEANU</strong><br>
                        – asist. univ. dr., medic<br>
                        specialist med.nucl.<br>
                        <strong>Wael JALLOUL</strong><br>
                        – asist. univ. dr., medic<br>
                        specialist med.nucl.
                    </div>

                    <div class="section-header">
                        <strong><u>Fizician</u></strong><br>
                        <strong>Vlad GHIZDOVAT</strong>
                    </div>

                    <div class="section-header">
                        <strong><u>Medici rezidenti</u></strong><br>
                        <strong>Laura PINTILIE<br>
                        Radu CONSTANTIN<br>
                        Larisa Elena RAU<br>
                        Angela OARZA<br>
                        Oana OLARIU<br>
                        Raluca Rafaela ION<br>
                        Ana Maria NISTOR<br>
                        Sabina DEJMASU<br>
                        Malina EPURE</strong>
                    </div>

                    <div class="section-header">
                        <strong><u>Asistenta sefa</u></strong><br>
                        <strong>Alina TIMOFTI</strong>
                    </div>

                    <div class="section-header">
                        <strong><u>Asistenti</u></strong><br>
                        <strong>Ofelia PERJU<br>
                        Alina STEFAN<br>
                        Monica PENISOARA<br>
                        Otilia LISMAN<br>
                        Laura VARZAR</strong>
                    </div>

                    <div class="section-header">
                        <strong><u>Personal auxiliar</u></strong><br>
                        <strong>Irina ATASIEI<br>
                        Genoveva SPATARU</strong>
                    </div>

                    <div class="section-header">
                        <strong><u>Registrator medical</u></strong><br>
                        <strong>Lupascu Adrian</strong>
                    </div>
                </div>

                <!-- PARTEA DREAPTĂ - IDENTICĂ CU IMAGINEA -->
                <div class="right-panel">
                    <!-- SPAȚIU PENTRU ANTETUL SPITALULUI -->
                    <div class="hospital-header-space">
                        <!-- TU VEI PUNE AICI ANTETUL -->
                    </div>

                    <!-- DATELE PACIENTULUI -->
                    <div class="patient-section">
                        <div class="patient-data">
                            <strong>Nume:</strong> {patient_name}<br>
                            <strong>CNP:</strong> {cnp}<br>
                            <strong>Dosar nr.:</strong> {dosar_nr}<br>
                            <strong>Gamma camera:</strong> {gamma_camera}<br>
                            <strong>Investigație la recomandarea:</strong><br>
                            <strong>Diagnostic de trimitere:</strong> {diagnosis}<br>
                            <strong>Doza:</strong> {dose_mbq} <strong>Radiofarmaceutic:</strong> <strong>{radiopharmaceutical}</strong>
                        </div>

                        <div class="exam-date-right">
                            <strong>Data {exam_date}</strong>
                        </div>
                    </div>

                    <!-- TITLUL EXAMINĂRII -->
                    <div class="main-title">
                        <h1>{exam_title}</h1>
                    </div>

                    <!-- CONȚINUTUL EXAMINĂRII -->
                    <div class="examination-content">
                        {self._format_content_for_html(content)}
                    </div>

                    <!-- SEMNĂTURILE -->
                    <div class="signatures-section">
                        <div class="signature-left-bottom">
                            <strong>Sef laborator</strong><br>
                            Medic primar Medicina Nucleara<br>
                            <strong>Prof. dr. Cipriana STEFANESCU</strong>
                        </div>

                        <div class="signature-right-bottom">
                            Medic specialist Medicina Nucleara<br>
                            <strong>Asist. univ. Dr. Wael JALLOUL</strong>
                        </div>
                    </div>

                    <div class="resident-signature-bottom">
                        <strong>Medic rezident Medicina Nucleara</strong>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

    def _format_content_for_html(self, content: str) -> str:
        if not content.strip():
            return "<p><em style='color: #94a3b8; font-size: 11px; font-style: italic;'>Nu a fost introdus niciun rezultat al investigației.</em></p>"

        # Dacă conținutul vine deja formatat ca HTML, procesează-l minimal
        if '<p>' in content or '<strong>' in content or '<em>' in content:
            # Doar asigură-te că paragrafele au stilul corect
            content = re.sub(r'<p>', '<p style="margin: 12px 0; line-height: 1.5;">', content)
            return content

        # Altfel, procesează ca text normal
        import html
        content = html.escape(content)

        paragraphs = content.split('\n\n')
        formatted_paragraphs = []

        for paragraph in paragraphs:
            if paragraph.strip():
                paragraph = paragraph.replace('\n', '<br>')
                formatted_paragraphs.append(f'<p style="margin: 12px 0; line-height: 1.5;">{paragraph}</p>')

        return ''.join(
            formatted_paragraphs) if formatted_paragraphs else f'<p style="margin: 12px 0; line-height: 1.5;">{content}</p>'