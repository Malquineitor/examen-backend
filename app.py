"""
Backend híbrido para lectura de documentos:
1. Google Docs (Shared Drive)
2. PDFConverter (si existiera)
3. Lector simple (docx, xlsx, pdf, txt)
4. Legacy Reader (ppt/doc/xls antiguos)
5. OCR universal
6. OCR agresivo (último recurso REAL)

Compatible con Railway sin LibreOffice
Compatible con Google Workspace Shared Drive
----------------------------------------------------
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename

import os
import tempfile
import json
import logging

# Procesadores
from document_processor import DocumentProcessor
from pdf_converter import PDFConverter
import legacy_reader

# Google
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ----------------------------------------------------
# CONFIGURACIÓN
# ----------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

processor = DocumentProcessor()
pdf_converter = PDFConverter()

SHARED_DRIVE_ID = "0APWpYgysES7jUk9PVA"

# ----------------------------------------------------
# DETECTAR SI EL PDF TIENE TEXTO REAL
# ----------------------------------------------------
from PyPDF2 import PdfReader

def pdf_tiene_texto(file_path):
    """Devuelve True si el PDF contiene texto interno."""
    try:
        reader = PdfReader(file_path)
        for page in reader.pages:
            t = page.extract_text()
            if t and t.strip():
                return True
        return False
    except:
        return False

# ----------------------------------------------------
# CARGAR CREDENCIALES GOOGLE
# ----------------------------------------------------
google_credentials = None
GOOGLE_JSON = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")

if GOOGLE_JSON:
    try:
        google_credentials = service_account.Credentials.from_service_account_info(
            json.loads(GOOGLE_JSON),
            scopes=[
                "https://www.googleapis.com/auth/drive",
                "https://www.googleapis.com/auth/documents",
                "https://www.googleapis.com/auth/cloud-platform"
            ]
        )
        logger.info("Credenciales Google cargadas OK")
    except Exception as e:
        logger.error(f"Error cargando credenciales Google: {e}")
else:
    logger.warning("No se encontraron credenciales Google.")

# ----------------------------------------------------
# PROCESAR CON GOOGLE DOCS
# ----------------------------------------------------
def procesar_con_google(file_path, extension):
    if google_credentials is None:
        return None

    try:
        drive = build("drive", "v3", credentials=google_credentials)
        docs = build("docs", "v1", credentials=google_credentials)

        file_metadata = {
            "name": f"temp.{extension}",
            "parents": [SHARED_DRIVE_ID]
        }
        media = MediaFileUpload(file_path, resumable=False)

        subida = drive.files().create(
            body=file_metadata,
            media_body=media,
            fields="id",
            supportsAllDrives=True
        ).execute()

        file_id = subida["id"]
        logger.info(f"Archivo subido a unidad compartida: {file_id}")

        try:
            doc = docs.documents().get(documentId=file_id).execute()
        except Exception as e:
            logger.error(f"Google Docs no pudo abrir el archivo: {e}")
            try:
                drive.files().delete(fileId=file_id, supportsAllDrives=True).execute()
            except:
                pass
            return None

        texto_google = ""

        # Extraer texto
        for element in doc.get("body", {}).get("content", []):
            if "paragraph" in element:
                for e in element["paragraph"]["elements"]:
                    texto_google += e.get("textRun", {}).get("content", "")

        try:
            drive.files().delete(fileId=file_id, supportsAllDrives=True).execute()
        except:
            pass

        if texto_google.strip():
            return {
                "texto": texto_google,
                "method": "google",
                "warnings": []
            }

    except Exception as e:
        logger.error(f"[GOOGLE ERROR] {e}")

    return None

# ----------------------------------------------------
# ENDPOINT PRINCIPAL
# ----------------------------------------------------
@app.route('/procesar', methods=['POST'])
def procesar_documento():

    try:
        if "file" not in request.files:
            return jsonify({"status": "error", "message": "No se envió archivo"}), 400

        file = request.files["file"]
        filename = secure_filename(file.filename)

        if filename == "":
            return jsonify({"status": "error", "message": "Archivo sin nombre"}), 400

        extension = filename.rsplit(".", 1)[-1].lower()

        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{extension}") as tmp:
            file.save(tmp.name)
            temp_path = tmp.name

        logger.info(f"Archivo recibido: {filename} ({extension})")

        # ------------------------------------------------
        # 1️⃣ GOOGLE DOCS (solo si el PDF tiene texto)
        # ------------------------------------------------
        usar_google = True

        if extension == "pdf":
            if not pdf_tiene_texto(temp_path):
                logger.info("PDF sin texto interno → saltando Google Docs.")
                usar_google = False

        if usar_google:
            google_result = procesar_con_google(temp_path, extension)
            if google_result and google_result["texto"].strip():
                return jsonify({"status": "success", **google_result}), 200

        # ------------------------------------------------
        # 2️⃣ PDF Converter
        # ------------------------------------------------
        try:
            pdf_res = pdf_converter.convertir_a_pdf(temp_path, extension)
            if pdf_res:
                pdf_text = processor.leer_pdf(pdf_res)
                if pdf_text["texto"].strip():
                    return jsonify({"status": "success", **pdf_text}), 200
        except:
            pass

        # ------------------------------------------------
        # 3️⃣ SIMPLE
        # ------------------------------------------------
        simple_res = processor.leer_simple(temp_path, extension)
        if simple_res["texto"].strip():
            return jsonify({"status": "success", **simple_res}), 200

        # ------------------------------------------------
        # 4️⃣ LEGACY
        # ------------------------------------------------
        legacy_res = processor.leer_legacy(temp_path, extension)
        if legacy_res["texto"].strip():
            return jsonify({"status": "success", **legacy_res}), 200

        # ------------------------------------------------
        # 5️⃣ OCR NORMAL
        # ------------------------------------------------
        ocr_text = legacy_reader.ocr_fallback(temp_path)

        if ocr_text.strip():
            return jsonify({
                "status": "success",
                "texto": ocr_text,
                "method": "ocr",
                "warnings": []
            }), 200

        logger.info("OCR normal no extrajo texto → activando OCR agresivo...")

        # ------------------------------------------------
        # 6️⃣ OCR AGRESIVO
        # ------------------------------------------------
        ocr_text_agresivo = legacy_reader.ocr_agresivo(temp_path)

        if ocr_text_agresivo.strip():
            return jsonify({
                "status": "success",
                "texto": ocr_text_agresivo,
                "method": "ocr_aggressive",
                "warnings": ["Se usó OCR agresivo por baja calidad del documento"]
            }), 200

        # ------------------------------------------------
        # 7️⃣ NADA FUNCIONÓ
        # ------------------------------------------------
        return jsonify({
            "status": "success",
            "texto": "",
            "method": "none",
            "warnings": ["No se pudo extraer texto del documento"]
        }), 200

    except Exception as e:
        logger.error(f"ERROR GENERAL: {e}")
        return jsonify({"status": "error", "message": "Error interno", "error": str(e)}), 500

# ----------------------------------------------------
# HEALTH CHECK
# ----------------------------------------------------
@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"}), 200

# ----------------------------------------------------
# EJECUCIÓN
# ----------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
