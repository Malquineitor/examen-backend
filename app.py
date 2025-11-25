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

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Habilitar CORS para todas las rutas
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB máximo

# Inicializar el procesador de documentos
processor = DocumentProcessor()

# Inicializar el convertidor de PDF
pdf_converter = PDFConverter()

@app.route('/procesar', methods=['POST'])
def procesar_documento():
    """
    Endpoint para procesar documentos
    Acepta multipart/form-data con campo 'file'
    Devuelve JSON: {"texto": "contenido extraído", "caracteres": int, "paginas": int, "method": str, "warnings": []}
    """
    try:
        # Verificar que se haya enviado un archivo
        if 'file' not in request.files:
            return jsonify({
                "status": "error",
                "code": 400,
                "message": "No se envió ningún archivo",
                "error": "No se envió ningún archivo. Asegúrate de enviar el archivo en el campo 'file'."
            }), 400
        
        file = request.files['file']
        
        # Verificar que el archivo tenga nombre
        if file.filename == '':
            return jsonify({
                "status": "error",
                "code": 400,
                "message": "Archivo sin nombre",
                "error": "El archivo enviado no tiene nombre."
            }), 400
        
        # Obtener el nombre del archivo y su extensión
        filename_original = file.filename
        filename = secure_filename(file.filename)
        
        # Detectar extensión del nombre original primero, luego del nombre seguro
        if '.' in filename_original:
            extension = filename_original.rsplit('.', 1)[1].lower()
        elif '.' in filename:
            extension = filename.rsplit('.', 1)[1].lower()
        else:
            extension = ''
        
        # Log para diagnóstico
        logger.info(f"Archivo recibido: {filename_original}")
        logger.info(f"Nombre seguro: {filename}")
        logger.info(f"Extensión detectada: {extension}")
        
        # Crear archivo temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{extension}' if extension else '') as temp_file:
            file.save(temp_file.name)
            temp_path = temp_file.name
        
        try:
            # ✅ NUEVA ESTRATEGIA: Procesar TODOS los formatos mediante conversión a PDF
            logger.info(f"Procesando archivo {extension or 'sin extensión'}: {filename_original}")
            
            # Procesar el archivo (el procesador maneja la conversión automáticamente)
            resultado = processor.procesar_archivo(temp_path, extension)
            
            # Verificar que se haya extraído texto
            texto_extraido = resultado.get("texto", "")
            
            # SIEMPRE retornar JSON válido, incluso si el texto está vacío
            # NUNCA retornar 400 por formato no soportado
            if texto_extraido and texto_extraido.strip():
                logger.info(f"Texto extraído exitosamente: {resultado.get('caracteres', 0)} caracteres, {resultado.get('paginas', 0)} páginas")
                
                # Retornar JSON completo con toda la información
                return jsonify({
                    "texto": texto_extraido,
                    "caracteres": resultado.get("caracteres", len(texto_extraido)),
                    "paginas": resultado.get("paginas", 0),
                    "method": resultado.get("method", "unknown"),
                    "warnings": resultado.get("warnings", []),
                    "status": "success"
                }), 200
            else:
                logger.warning(f"No se pudo extraer texto del archivo {extension}")
                
                # Intentar como último recurso convertir a PDF y procesar
                if extension and extension.lower() != 'pdf':
                    logger.info(f"Intentando conversión de emergencia a PDF para {extension}...")
                    try:
                        pdf_path = pdf_converter.convertir_a_pdf(temp_path, extension)
                        if pdf_path and os.path.exists(pdf_path):
                            resultado_pdf = processor.procesar_archivo(pdf_path, 'pdf')
                            texto_pdf = resultado_pdf.get("texto", "")
                            
                            if texto_pdf and texto_pdf.strip():
                                # Limpiar PDF temporal
                                if pdf_path != temp_path and os.path.exists(pdf_path):
                                    try:
                                        os.unlink(pdf_path)
                                    except:
                                        pass
                                
                                return jsonify({
                                    "texto": texto_pdf,
                                    "caracteres": resultado_pdf.get("caracteres", len(texto_pdf)),
                                    "paginas": resultado_pdf.get("paginas", 0),
                                    "method": "emergency_pdf_conversion",
                                    "warnings": resultado_pdf.get("warnings", []) + ["Conversión de emergencia aplicada"],
                                    "status": "success"
                                }), 200
                    except Exception as e:
                        logger.warning(f"Conversión de emergencia falló: {str(e)}")
                
                # Si todo falla, retornar JSON válido con texto vacío (NO 400)
                # El procesador ya intentó todos los métodos posibles
                return jsonify({
                    "texto": texto_extraido or "",
                    "caracteres": resultado.get("caracteres", 0),
                    "paginas": resultado.get("paginas", 0),
                    "method": resultado.get("method", "unknown"),
                    "warnings": resultado.get("warnings", []) + ["No se pudo extraer texto del documento. Se intentaron múltiples métodos de conversión."],
                    "status": "success"
                }), 200
                
        except ValueError as e:
            # Error de formato o procesamiento
            logger.error(f"Error de procesamiento: {str(e)}")
            
            # Intentar conversión de emergencia
            if extension and extension.lower() != 'pdf':
                logger.info(f"Intentando conversión de emergencia después de error: {extension}...")
                try:
                    pdf_path = pdf_converter.convertir_a_pdf(temp_path, extension)
                    if pdf_path and os.path.exists(pdf_path):
                        resultado_pdf = processor.procesar_archivo(pdf_path, 'pdf')
                        texto_pdf = resultado_pdf.get("texto", "")
                        
                        if texto_pdf and texto_pdf.strip():
                            # Limpiar PDF temporal
                            if pdf_path != temp_path and os.path.exists(pdf_path):
                                try:
                                    os.unlink(pdf_path)
                                except:
                                    pass
                            
                            return jsonify({
                                "texto": texto_pdf,
                                "caracteres": resultado_pdf.get("caracteres", len(texto_pdf)),
                                "paginas": resultado_pdf.get("paginas", 0),
                                "method": "emergency_pdf_conversion",
                                "warnings": resultado_pdf.get("warnings", []) + [f"Recuperado después de error: {str(e)}"],
                                "status": "success"
                            }), 200
                except Exception as e2:
                    logger.warning(f"Conversión de emergencia falló: {str(e2)}")
            
            # NO retornar 400, siempre retornar JSON válido
            return jsonify({
                "texto": "",
                "caracteres": 0,
                "paginas": 0,
                "method": "failed",
                "warnings": [f"Error de procesamiento: {str(e)}"],
                "status": "success"
            }), 200
        except Exception as e:
            # Otros errores
            logger.error(f"Error procesando archivo: {str(e)}", exc_info=True)
            
            # Último intento: procesar como PDF
            try:
                logger.info("Último intento: procesando como PDF genérico...")
                resultado_pdf = processor.procesar_archivo(temp_path, 'pdf')
                texto_pdf = resultado_pdf.get("texto", "")
                
                if texto_pdf and texto_pdf.strip():
                    return jsonify({
                        "texto": texto_pdf,
                        "caracteres": resultado_pdf.get("caracteres", len(texto_pdf)),
                        "paginas": resultado_pdf.get("paginas", 0),
                        "method": "fallback_pdf",
                        "warnings": resultado_pdf.get("warnings", []) + [f"Procesado como PDF después de error: {str(e)}"],
                        "status": "success"
                    }), 200
            except Exception as e2:
                logger.error(f"Fallback a PDF también falló: {str(e2)}")
            
            return jsonify({
                "status": "error",
                "code": 500,
                "message": "Error al procesar el documento",
                "error": f"Error interno: {str(e)}"
            }), 500
        finally:
            # Limpiar archivos temporales
            if os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except Exception as e:
                    logger.warning(f"No se pudo eliminar archivo temporal {temp_path}: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error general: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "code": 500,
            "message": "Error interno del servidor",
            "error": str(e)
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint de salud para verificar que el servidor está funcionando"""
    # Verificar disponibilidad de herramientas
    libreoffice_ok = pdf_converter.libreoffice_path is not None
    unoconv_ok = pdf_converter.unoconv_path is not None
    
    return jsonify({
        "status": "ok",
        "message": "Servidor funcionando correctamente",
        "libreoffice_available": libreoffice_ok,
        "unoconv_available": unoconv_ok,
        "conversion_available": libreoffice_ok or unoconv_ok
    }), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
