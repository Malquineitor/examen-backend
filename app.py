"""
Backend para procesamiento inteligente de documentos
Orden de lectura:
1. Google (Drive / Docs / OCR con conversion directa)
2. Conversión a PDF (PDFConverter)
3. Lectura local simple (docx/xlsx/xls/pdf)
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename

import os
import tempfile
import logging
import json

from document_processor import DocumentProcessor
from pdf_converter import PDFConverter

# Librerías Google
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# -----------------------------------------
# CONFIGURACIÓN GENERAL
# -----------------------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB

processor = DocumentProcessor()
pdf_converter = PDFConverter()

# ID DE TU UNIDAD COMPARTIDA
SHARED_DRIVE_ID = "0APWpYgysES7jUk9PVA"

# -----------------------------------------
# CARGAR CREDENCIALES GOOGLE
# -----------------------------------------
google_credentials = None
GOOGLE_JSON = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")

if GOOGLE_JSON:
    try:
        google_credentials = service_account.Credentials.from_service_account_info(
            json.loads(GOOGLE_JSON),
            scopes=[
                "https://www.googleapis.com/auth/drive",
                "https://www.googleapis.com/auth/documents",
                "https://www.googleapis.com/auth/cloud-platform",
            ],
        )
        logger.info("Credenciales Google cargadas OK")
    except Exception as e:
        logger.error(f"ERROR cargando credenciales Google: {e}")
else:
    logger.warning("No se encontraron credenciales Google.")


# -----------------------------------------
# FUNCIÓN: PROCESAR CON GOOGLE
# -----------------------------------------

def procesar_con_google(file_path, extension):
    """
    Lee documentos usando Google Docs/Drive en Shared Drive.
    Retorna dict si tiene texto, o None si falla.
    """

    if google_credentials is None:
        return None

    try:
        drive = build("drive", "v3", credentials=google_credentials)
        docs = build("docs", "v1", credentials=google_credentials)

        # Subir archivo a la Unidad Compartida
        file_metadata = {
            "name": f"temp.{extension}",
            "parents": [SHARED_DRIVE_ID]
        }

        media = MediaFileUpload(file_path, resumable=False)

        uploaded = drive.files().create(
            body=file_metadata,
            media_body=media,
            fields="id",
            supportsAllDrives=True
        ).execute()

        file_id = uploaded["id"]
        logger.info(f"Archivo subido a unidad compartida: {file_id}")

        # Intentar leer como Google Doc
        try:
            doc = docs.documents().get(documentId=file_id).execute()
        except Exception as e:
            logger.error(f"Google Docs no pudo abrir el archivo: {e}")
            # borrar archivo antes de salir
            drive.files().delete(fileId=file_id, supportsAllDrives=True).execute()
            return None

        texto_google = ""

        for element in doc.get("body", {}).get("content", []):
            if "paragraph" in element:
                for p in element["paragraph"].get("elements", []):
                    texto_google += p.get("textRun", {}).get("content", "")

        # Borrar archivo temporal de la unidad compartida
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

        return None

    except Exception as e:
        logger.error(f"[GOOGLE ERROR] {e}")
        return None


# -----------------------------------------
# ENDPOINT PRINCIPAL
# -----------------------------------------

@app.route('/procesar', methods=['POST'])
def procesar_documento():

    try:
        if "file" not in request.files:
            return jsonify({"status": "error", "message": "No se envió archivo"}), 400

        file = request.files["file"]
        filename = secure_filename(file.filename)

        if filename == "":
            return jsonify({"status": "error", "message": "Archivo sin nombre"}), 400

        extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

        # Guardar archivo temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{extension}") as tmp:
            file.save(tmp.name)
            temp_path = tmp.name

        logger.info(f"Archivo recibido: {filename} ({extension})")

        # -----------------------------------------
        # 1️⃣ MÉTODO: GOOGLE DRIVE + DOCS
        # -----------------------------------------
        google_result = procesar_con_google(temp_path, extension)

        if google_result:
            logger.info("Google procesó correctamente el documento.")
            return jsonify({
                "status": "success",
                **google_result
            }), 200

        # -----------------------------------------
        # 2️⃣ MÉTODO: PDFConverter
        # -----------------------------------------
        logger.info("Google falló → usando PDFConverter...")

        pdf_result = processor.procesar_archivo(temp_path, extension)

        if pdf_result.get("texto") and pdf_result["texto"].strip():
            return jsonify({
                "status": "success",
                "method": "pdf_converter",
                **pdf_result
            }), 200

        # -----------------------------------------
        # 3️⃣ MÉTODO: LECTURA LOCAL SIMPLE
        # -----------------------------------------
        logger.info("PDFConverter falló → lector simple local...")

        simple_result = processor.procesar_archivo(temp_path, "simple")

        if simple_result.get("texto") and simple_result["texto"].strip():
            return jsonify({
                "status": "success",
                "method": "simple_local",
                **simple_result
            }), 200

        # -----------------------------------------
        # 4️⃣ TODO FALLÓ
        # -----------------------------------------
        return jsonify({
            "status": "success",
            "method": "none",
            "texto": "",
            "caracteres": 0,
            "paginas": 0,
            "warnings": ["Ningún método pudo extraer texto"]
        }), 200

    except Exception as e:
        logger.error(f"ERROR GENERAL: {e}")
        return jsonify({"status": "error", "message": "Error interno", "error": str(e)}), 500


# -----------------------------------------
# HEALTH CHECK
# -----------------------------------------

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"}), 200


# -----------------------------------------
# RUN
# -----------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
