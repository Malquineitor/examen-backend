"""
Backend para procesamiento de documentos
Soporta TODOS los formatos mediante conversión a PDF: PDF, DOC, DOCX, XLS, XLSX, PPT, PPTX, ODT, RTF, CSV, TXT, imágenes, etc.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import tempfile
import logging

from document_processor import DocumentProcessor
from pdf_converter import PDFConverter

# ----------------------------------------------------------
# CONFIGURACIÓN GENERAL DEL SERVIDOR
# ----------------------------------------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB máximo

processor = DocumentProcessor()
pdf_converter = PDFConverter()


# ----------------------------------------------------------
# ENDPOINT PRINCIPAL /procesar (tu endpoint original)
# ----------------------------------------------------------

@app.route('/procesar', methods=['POST'])
def procesar_documento():
    """
    Endpoint para procesar documentos de forma flexible.
    Acepta cualquier formato, intenta convertir a PDF, extraer texto y devolverlo.
    """
    try:
        if 'file' not in request.files:
            return jsonify({"status": "error", "message": "No se envió archivo"}), 400

        file = request.files['file']
        if file.filename == "":
            return jsonify({"status": "error", "message": "Archivo sin nombre"}), 400

        filename_original = file.filename

        # Extraer extensión
        extension = filename_original.rsplit('.', 1)[-1].lower() if '.' in filename_original else ''

        logger.info(f"Archivo recibido: {filename_original} | Extensión detectada: {extension}")

        # Guardar archivo temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{extension}") as temp_file:
            file.save(temp_file.name)
            temp_path = temp_file.name

        try:
            # Procesar usando el procesador general
            resultado = processor.procesar_archivo(temp_path, extension)
            texto = resultado.get("texto", "")

            # Si hay texto → OK
            if texto.strip():
                return jsonify({
                    "status": "success",
                    "texto": texto,
                    "caracteres": len(texto),
                    "paginas": resultado.get("paginas", 0),
                    "method": resultado.get("method", "main"),
                    "warnings": resultado.get("warnings", [])
                }), 200

            logger.warning("No se pudo extraer texto directamente. Intentando conversión de emergencia...")

            # Intento de conversión a PDF
            if extension != "pdf":
                pdf_path = pdf_converter.convertir_a_pdf(temp_path, extension)
                if pdf_path and os.path.exists(pdf_path):
                    resultado_pdf = processor.procesar_archivo(pdf_path, "pdf")
                    texto_pdf = resultado_pdf.get("texto", "")

                    if texto_pdf.strip():
                        return jsonify({
                            "status": "success",
                            "texto": texto_pdf,
                            "caracteres": len(texto_pdf),
                            "paginas": resultado_pdf.get("paginas", 0),
                            "method": "emergency_pdf_conversion",
                            "warnings": resultado_pdf.get("warnings", [])
                        }), 200

            # Si todo falla, responder texto vacío
            return jsonify({
                "status": "success",
                "texto": "",
                "caracteres": 0,
                "paginas": 0,
                "method": "failed",
                "warnings": ["No se pudo extraer texto del documento"]
            }), 200

        finally:
            if os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except:
                    pass

    except Exception as e:
        logger.error(f"Error general en /procesar: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": "Error interno", "error": str(e)}), 500


# ----------------------------------------------------------
# NUEVO ENDPOINT: /procesarDocumentoOnline (ULTRA SIMPLE)
# PROCESA SIEMPRE TODO → PDF → TEXTO → OCR
# ----------------------------------------------------------

@app.route('/procesarDocumentoOnline', methods=['POST'])
def procesar_documento_online():
    """
    Modo ONLINE simplificado:
    1. Recibe archivo
    2. Convierte TODO a PDF
    3. Extrae texto
    4. Si no hay texto → OCR
    5. Devuelve respuesta siempre exitosa
    """
    try:
        if 'file' not in request.files:
            return jsonify({"status": "error", "message": "No se envió archivo"}), 400

        file = request.files['file']
        filename_original = file.filename

        if filename_original == "":
            return jsonify({"status": "error", "message": "Archivo vacío"}), 400

        extension = filename_original.split(".")[-1].lower()

        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{extension}") as temp_file:
            file.save(temp_file.name)
            temp_path = temp_file.name

        # 1. Convertir TODO a PDF
        if extension != "pdf":
            pdf_path = pdf_converter.convertir_a_pdf(temp_path, extension)
        else:
            pdf_path = temp_path

        # 2. Procesar PDF normal
        resultado = processor.procesar_archivo(pdf_path, "pdf")
        texto = resultado.get("texto", "")

        # 3. Si no hay texto → OCR
        if not texto.strip():
            logger.info("No hay texto. Intentando OCR...")
            resultado_ocr = processor.procesar_archivo(pdf_path, "ocr")
            texto = resultado_ocr.get("texto", "")

            if texto.strip():
                resultado = resultado_ocr

        return jsonify({
            "status": "success",
            "texto": texto,
            "caracteres": len(texto),
            "paginas": resultado.get("paginas", 1),
            "method": resultado.get("method", "online"),
            "warnings": resultado.get("warnings", [])
        }), 200

    except Exception as e:
        logger.error(f"Error en /procesarDocumentoOnline: {str(e)}")
        return jsonify({"status": "error", "message": "Error procesando archivo", "error": str(e)}), 500

    finally:
        try:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
        except:
            pass


# ----------------------------------------------------------
# ENDPOINT DE SALUD
# ----------------------------------------------------------

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "ok",
        "message": "Servidor funcionando correctamente",
        "conversion_available": True
    }), 200


# ----------------------------------------------------------
# EJECUCIÓN EN PRODUCCIÓN
# ----------------------------------------------------------

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
