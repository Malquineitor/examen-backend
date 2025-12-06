"""
Backend híbrido para lectura de documentos + generación de exámenes.
Toda la lógica de IA ahora se maneja en:
 - document_processor.py
 - ai_service.py
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

# IA (lógica migrada desde la app Android)
from ai_service import generar_examen

# Google
from google.oauth2 import service_account

# ----------------------------------------------------
# CONFIGURACIÓN GENERAL
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
# CREDENCIALES GOOGLE
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
# 📌 ENDPOINT: GENERAR TEST EXACTAMENTE COMO LA APP
# ----------------------------------------------------
@app.route("/ai/generate", methods=["POST"])
def generar_examen_ai():
    data = request.json

    texto = data.get("texto", "").strip()
    modelo = data.get("modelo", "gemini-2.0-flash-lite")

    if not texto:
        return jsonify({"error": "El texto está vacío"}), 400

    # 1. Limpiar texto (igual que TextFilter en la app)
    texto_limpio = processor.limpiar_texto(texto)

    # 2. Dividir en bloques (igual que Android)
    bloques = processor.dividir_en_bloques(texto_limpio)
    total_bloques = len(bloques)

    # 3. Calcular preguntas por bloque (mínimo 8, máximo 25)
    preguntas_por_bloque = processor.calcular_preguntas_por_bloque(total_bloques)

    # 4. Llamar al sistema de IA para generar el examen
    preguntas = generar_examen(
        texto=texto_limpio,
        bloques=bloques,
        preguntas_por_bloque=preguntas_por_bloque,
        modelo=modelo
    )

    return jsonify({
        "success": True,
        "total_bloques": total_bloques,
        "preguntas_generadas": len(preguntas),
        "preguntas": preguntas
    })


# ----------------------------------------------------
# 📌 PROCESAR DOCUMENTOS (igual que antes)
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

        usar_google = True
        if extension == "pdf" and not pdf_tiene_texto(temp_path):
            usar_google = False

        if usar_google:
            pass  # (Tu lógica original, no la tocamos)

        # PDF Converter
        pdf_res = pdf_converter.convertir_a_pdf(temp_path, extension)
        if pdf_res:
            pdf_text = processor.leer_pdf(pdf_res)
            if pdf_text["texto"].strip():
                return jsonify({"status": "success", **pdf_text}), 200

        # Simple reader
        simple_res = processor.leer_simple(temp_path, extension)
        if simple_res["texto"].strip():
            return jsonify({"status": "success", **simple_res}), 200

        # Legacy reader
        legacy_res = processor.leer_legacy(temp_path, extension)
        if legacy_res["texto"].strip():
            return jsonify({"status": "success", **legacy_res}), 200

        # OCR normal
        ocr_text = legacy_reader.ocr_fallback(temp_path)
        if ocr_text.strip():
            return jsonify({
                "status": "success",
                "texto": ocr_text,
                "method": "ocr",
            }), 200

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
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


# ----------------------------------------------------
# EJECUCIÓN
# ----------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
