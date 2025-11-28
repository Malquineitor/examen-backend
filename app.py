"""
Backend para procesamiento inteligente de documentos
Orden de lectura:
1. Google (Drive / Docs / Vision OCR)
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
                "https://www.googleapis.com/auth/cloud-platform"
            ]
        )
        logger.info("Credenciales de Google cargadas correctamente.")
    except Exception as e:
        logger.error(f"Error cargando credenciales Google: {e}")
else:
    logger.warning("No se encontraron credenciales Google.")


# -----------------------------------------
# FUNCIÓN: PROCESAR CON GOOGLE
# -----------------------------------------

def procesar_con_google(file_path, extension):
    """
    Lee documentos usando Google Docs/Drive.
    Retorna dict con texto o None si falla.
    """
    try:
        if google_credentials is None:
            return None

        drive = build("drive", "v3", credentials=google_credentials)
        docs = build("docs", "v1", credentials=google_credentials)

        # Subir archivo temporal a Google
        file_metadata = {"name": f"temp.{extension}"}
        media = MediaFileUpload(file_path, resumable=False)

        uploaded = drive.files().create(
            body=file_metadata,
            media_body=media,
            fields="id"
        ).execute()

        file_id = uploaded["id"]

        # Convertir usando Google Docs
        doc = docs.documents().get(documentId=file_id).execute()

        texto_google = ""

        for element in doc.get("body").get("content", []):
            if "paragraph" in element:
                for p in element["paragraph"].get("elements", []):
                    texto_google += p.get("textRun", {}).get("content", "")

        # Borrar archivo de Google
        drive.files().delete(fileId=file_id).execute()

        if texto_google.strip():
            return {
                "texto": texto_google,
                "method": "google",
                "warnings": []
            }

        return None

    except Exception as e:
        logger.error(f"[GOOGLE FALLÓ] {str(e)}")
        return None


# -----------------------------------------
# ENDPOINT PRINCIPAL
# -----------------------------------------

@app.route('/procesar', methods=['POST'])
def procesar_documento():

    try:
        # 1. Validar archivo
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
        # 1️⃣ PRIMER MÉTODO: GOOGLE
        # -----------------------------------------
        google_result = procesar_con_google(temp_path, extension)

        if google_result:
            logger.info("Google procesó el documento correctamente.")
            return jsonify({
                "status": "success",
                **google_result
            }), 200

        # -----------------------------------------
        # 2️⃣ SEGUNDO MÉTODO: PDFConverter
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
        # 3️⃣ TERCER MÉTODO: LECTOR LOCAL SIMPLE
        # -----------------------------------------
        logger.info("PDFConverter falló → intentando lector local simple...")

        simple_result = processor.procesar_archivo(temp_path, "simple")

        if simple_result.get("texto") and simple_result["texto"].strip():
            return jsonify({
                "status": "success",
                "method": "simple_local",
                **simple_result
            }), 200

        # -----------------------------------------
        # 4️⃣ TODO FALLÓ → RESPUESTA VACÍA
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
        logger.error(f"Error general: {str(e)}")
        return jsonify({"status": "error", "message": "Error interno", "error": str(e)}), 500


# -----------------------------------------
# ENDPOINT DE SALUD
# -----------------------------------------
@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"}), 200


# -----------------------------------------
# EJECUCIÓN EN PRODUCCIÓN
# -----------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
