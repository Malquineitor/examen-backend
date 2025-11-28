"""
Backend para procesamiento inteligente de documentos
------------------------------------------
ORDEN PRINCIPAL ONLINE:
1. Google Docs + Drive API
2. Simple Reader (docx, xlsx, pdf modernos)
3. Legacy Reader (ppt, doc, xls antiguos)
4. OCR Fallback universal
------------------------------------------
Compatible con Railway (sin LibreOffice)
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename

import os
import tempfile
import json
import logging

# Processor principal
from document_processor import DocumentProcessor
from legacy_reader import (
    leer_ppt_antiguo,
    leer_doc_antiguo,
    leer_xls_antiguo,
    ocr_fallback
)

# Google APIs
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ------------------------------------------
# CONFIG GLOBAL
# ------------------------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)
app.config['MAX_CONTENT_LENGTH'] = 80 * 1024 * 1024  # 80MB

processor = DocumentProcessor()

# ------------------------------------------
# LOAD GOOGLE CREDENTIALS
# ------------------------------------------

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
    logger.warning("No se encontraron credenciales Google")


# ------------------------------------------
# MÉTODO GOOGLE
# ------------------------------------------

def procesar_con_google(path, extension):
    if not google_credentials:
        return None

    try:
        drive = build("drive", "v3", credentials=google_credentials)
        docs = build("docs", "v1", credentials=google_credentials)

        metadata = {"name": f"upload.{extension}"}
        media = MediaFileUpload(path, resumable=False)

        file_uploaded = drive.files().create(
            body=metadata,
            media_body=media,
            fields="id"
        ).execute()

        file_id = file_uploaded["id"]

        # Intentar convertir/documento
        document = docs.documents().get(documentId=file_id).execute()

        texto = ""
        for element in document.get("body", {}).get("content", []):
            if "paragraph" in element:
                for p in element["paragraph"].get("elements", []):
                    texto += p.get("textRun", {}).get("content", "")

        # Borrar archivo temporal de Google
        drive.files().delete(fileId=file_id).execute()

        if texto.strip():
            return {
                "texto": texto,
                "method": "google",
                "warnings": []
            }
        return None

    except Exception as e:
        logger.error(f"[GOOGLE ERROR] {e}")
        return None


# ------------------------------------------
# ENDPOINT PRINCIPAL
# ------------------------------------------

@app.route("/procesar", methods=["POST"])
def procesar_documento():
    try:
        if "file" not in request.files:
            return jsonify({"status": "error", "msg": "No file sent"}), 400

        file = request.files["file"]
        filename = secure_filename(file.filename)

        if filename == "":
            return jsonify({"status": "error", "msg": "Empty filename"}), 400

        extension = filename.rsplit(".", 1)[-1].lower()

        # Guardar archivo temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{extension}") as tmp:
            file.save(tmp.name)
            path = tmp.name

        logger.info(f"Archivo recibido: {filename} ({extension})")

        # 1. GOOGLE
        google_result = procesar_con_google(path, extension)
        if google_result:
            return jsonify({
                "status": "success",
                **google_result
            }), 200

        # 2. SIMPLE Modern Reader (docx, xlsx, pdf)
        simple_result = processor.leer_simple(path, extension)
        if simple_result:
            return jsonify({
                "status": "success",
                "method": "simple_reader",
                "texto": simple_result,
                "caracteres": len(simple_result),
                "paginas": simple_result.count("\n") // 20 + 1,
                "warnings": []
            }), 200

        # 3. LEGACY READER
        legacy_text = ""
        if extension == "ppt":
            legacy_text = leer_ppt_antiguo(path)
        elif extension == "doc":
            legacy_text = leer_doc_antiguo(path)
        elif extension == "xls":
            legacy_text = leer_xls_antiguo(path)

        if legacy_text.strip():
            return jsonify({
                "status": "success",
                "method": "legacy_reader",
                "texto": legacy_text,
                "caracteres": len(legacy_text),
                "paginas": legacy_text.count("\n") // 20 + 1,
                "warnings": []
            }), 200

        # 4. OCR fallback
        fallback_text = ocr_fallback(path)
        return jsonify({
            "status": "success",
            "method": "ocr_fallback",
            "texto": fallback_text,
            "caracteres": len(fallback_text),
            "paginas": fallback_text.count("\n") // 20 + 1,
            "warnings": ["OCR fallback used"]
        }), 200

    except Exception as e:
        logger.error(f"ERROR GENERAL: {e}")
        return jsonify({"status": "error", "msg": str(e)}), 500
    finally:
        if "path" in locals() and os.path.exists(path):
            try:
                os.unlink(path)
            except:
                pass


# ------------------------------------------
# HEALTH CHECK
# ------------------------------------------

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
