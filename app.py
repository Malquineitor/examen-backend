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
INTEGRACIÓN COMPLETA CON GEMINI DESDE BACKEND
(Modelo: gemini-2.0-flash-lite → modo barato/casi gratis)
----------------------------------------------------
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename

import os
import tempfile
import json
import logging
import requests   # Para llamar a Gemini API

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
# ✨ GEMINI DESDE BACKEND – MODELO GRATIS (2.0 FLASH-LITE)
# ----------------------------------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

DEFAULT_MODEL = "models/gemini-2.0-flash-lite"  # ✔ modelo barato y disponible

def generar_test_con_gemini(texto, num_preguntas, model_name=None):

    if not GEMINI_API_KEY:
        return {"error": "GEMINI_API_KEY no configurada en Render"}

    if model_name is None:
        model_name = DEFAULT_MODEL

    ENDPOINT = (
        f"https://generativelanguage.googleapis.com/v1/models/"
        f"{model_name}:generateContent?key={GEMINI_API_KEY}"
    )

    prompt = f"""
Genera un examen de {num_preguntas} preguntas basado en este documento:

{texto}

Formato JSON:
{{
  "title": "",
  "questions": [
    {{
      "question": "",
      "options": ["", "", "", ""],
      "answer": ""
    }}
  ]
}}
"""

    body = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }

    try:
        response = requests.post(ENDPOINT, json=body)
        data = response.json()
    except Exception as e:
        return {"error": f"Error comunicando con Gemini: {e}"}

    if response.status_code != 200:
        return {
            "error": "Gemini API error",
            "status": response.status_code,
            "details": data
        }

    try:
        texto_generado = data["candidates"][0]["content"]["parts"][0]["text"]
    except:
        texto_generado = ""

    return {
        "success": True,
        "raw": data,
        "text": texto_generado
    }

# ----------------------------------------------------
# 📌 ENDPOINT: LISTAR MODELOS DISPONIBLES
# ----------------------------------------------------
@app.route('/ai/models', methods=['GET'])
def listar_modelos():
    if not GEMINI_API_KEY:
        return jsonify({"error": "GEMINI_API_KEY no configurada"}), 500

    url = f"https://generativelanguage.googleapis.com/v1/models?key={GEMINI_API_KEY}"

    try:
        response = requests.get(url)
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ----------------------------------------------------
# 📌 ENDPOINT: GENERAR TEST CON IA
# ----------------------------------------------------
@app.route('/ai/generate', methods=['POST'])
def generar_examen_ai():
    data = request.json

    texto = data.get("texto", "")
    num_preguntas = data.get("num_preguntas", 20)
    modelo = data.get("modelo", None)

    if not texto.strip():
        return jsonify({"error": "El campo 'texto' está vacío"}), 400

    resultado = generar_test_con_gemini(texto, num_preguntas, model_name=modelo)
    return jsonify(resultado)

# ----------------------------------------------------
# ENDPOINT PRINCIPAL (procesar documento)
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

        # 1️⃣ GOOGLE DOCS
        usar_google = True
        if extension == "pdf" and not pdf_tiene_texto(temp_path):
            usar_google = False

        if usar_google:
            google_result = procesar_con_google(temp_path, extension)
            if google_result and google_result["texto"].strip():
                return jsonify({"status": "success", **google_result}), 200

        # 2️⃣ PDF Converter
        try:
            pdf_res = pdf_converter.convertir_a_pdf(temp_path, extension)
            if pdf_res:
                pdf_text = processor.leer_pdf(pdf_res)
                if pdf_text["texto"].strip():
                    return jsonify({"status": "success", **pdf_text}), 200
        except:
            pass

        # 3️⃣ SIMPLE
        simple_res = processor.leer_simple(temp_path, extension)
        if simple_res["texto"].strip():
            return jsonify({"status": "success", **simple_res}), 200

        # 4️⃣ LEGACY
        legacy_res = processor.leer_legacy(temp_path, extension)
        if legacy_res["texto"].strip():
            return jsonify({"status": "success", **legacy_res}), 200

        # 5️⃣ OCR NORMAL
        ocr_text = legacy_reader.ocr_fallback(temp_path)

        if ocr_text.strip():
            return jsonify({
                "status": "success",
                "texto": ocr_text,
                "method": "ocr",
                "warnings": []
            }), 200

        # 6️⃣ OCR AGRESIVO
        ocr_text_agresivo = legacy_reader.ocr_agresivo(temp_path)

        if ocr_text_agresivo.strip():
            return jsonify({
                "status": "success",
                "texto": ocr_text_agresivo,
                "method": "ocr_aggressive",
                "warnings": ["Se usó OCR agresivo por baja calidad"]
            }), 200

        # 7️⃣ NADA FUNCIONÓ
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
