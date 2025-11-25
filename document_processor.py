"""
Procesador de documentos con soporte universal mediante conversión a PDF
Soporta TODOS los formatos: PDF, DOC, DOCX, XLS, XLSX, PPT, PPTX, ODT, RTF, CSV, TXT, imágenes, etc.
"""
import os
import logging
from typing import Optional, Dict, List
from pdf_converter import PDFConverter

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DocumentProcessor:
    """Procesador de documentos que soporta múltiples formatos mediante conversión a PDF"""
    
    def __init__(self):
        self.pdf_converter = PDFConverter()
        
        # Formatos que se pueden procesar directamente (sin conversión)
        self.formatos_directos = {
            'pdf': self._procesar_pdf,
            'txt': self._procesar_txt,
            'csv': self._procesar_csv,
        }
        
        # Formatos de imagen que usan OCR o conversión a PDF
        self.formatos_imagen = {
            'jpg': self._procesar_imagen,
            'jpeg': self._procesar_imagen,
            'png': self._procesar_imagen,
            'gif': self._procesar_imagen,
            'bmp': self._procesar_imagen,
            'tiff': self._procesar_imagen,
            'tif': self._procesar_imagen,
            'heic': self._procesar_imagen,
            'heif': self._procesar_imagen,
            'webp': self._procesar_imagen,
        }
    
    def procesar_archivo(self, file_path: str, extension: str) -> Dict[str, any]:
        """
        Procesa un archivo y extrae su texto
        
        Args:
            file_path: Ruta al archivo temporal
            extension: Extensión del archivo (sin punto)
        
        Returns:
            Diccionario con: texto, caracteres, paginas, method, warnings
        """
        extension_lower = extension.lower().strip()
        warnings: List[str] = []
        
        if not extension_lower:
            extension_lower = self._detectar_extension_por_contenido(file_path)
            if extension_lower:
                warnings.append(f"Extensión detectada automáticamente: {extension_lower}")
            else:
                # Intentar como PDF genérico
                extension_lower = 'pdf'
                warnings.append("No se pudo detectar extensión, intentando como PDF")
        
        try:
            # 1. Si es imagen, convertir a PDF primero y luego extraer texto
            if extension_lower in self.formatos_imagen:
                logger.info(f"Procesando imagen {extension_lower}...")
                try:
                    # Intentar convertir imagen a PDF
                    pdf_path = self.pdf_converter.convertir_a_pdf(file_path, extension_lower)
                    if pdf_path and os.path.exists(pdf_path):
                        resultado = self._procesar_pdf_completo(pdf_path, warnings)
                        resultado["method"] = "image_to_pdf"
                        resultado["warnings"].append(f"Imagen {extension_lower} convertida a PDF")
                        
                        # Limpiar PDF temporal
                        if pdf_path != file_path and os.path.exists(pdf_path):
                            try:
                                os.unlink(pdf_path)
                            except Exception as e:
                                logger.warning(f"No se pudo eliminar PDF temporal: {str(e)}")
                        
                        return resultado
                except Exception as e:
                    logger.warning(f"Error convirtiendo imagen a PDF: {str(e)}. Intentando OCR directo...")
                
                # Fallback: intentar OCR directo
                try:
                    texto = self.formatos_imagen[extension_lower](file_path)
                    return {
                        "texto": texto,
                        "caracteres": len(texto),
                        "paginas": 1,
                        "method": "image_ocr",
                        "warnings": warnings
                    }
                except Exception as e2:
                    logger.warning(f"OCR también falló: {str(e2)}")
                    # Si todo falla, retornar texto vacío pero no error
                    return {
                        "texto": "",
                        "caracteres": 0,
                        "paginas": 1,
                        "method": "image_failed",
                        "warnings": warnings + [f"No se pudo procesar imagen: {str(e2)}"]
                    }
            
            # 2. Si es formato directo (PDF, TXT, CSV), procesar directamente
            if extension_lower in self.formatos_directos:
                logger.info(f"Procesando {extension_lower} directamente...")
                if extension_lower == 'pdf':
                    return self._procesar_pdf_completo(file_path, warnings)
                else:
                    # Para TXT y CSV, también podemos convertirlos a PDF para consistencia
                    # pero primero intentamos procesamiento directo
                    try:
                        texto = self.formatos_directos[extension_lower](file_path)
                        return {
                            "texto": texto,
                            "caracteres": len(texto),
                            "paginas": 1,
                            "method": extension_lower,
                            "warnings": warnings
                        }
                    except Exception as e:
                        logger.warning(f"Error procesando {extension_lower} directamente: {str(e)}. Intentando conversión a PDF...")
                        # Si falla, intentar convertir a PDF
                        pdf_path = self.pdf_converter.convertir_a_pdf(file_path, extension_lower)
                        if pdf_path and os.path.exists(pdf_path):
                            resultado = self._procesar_pdf_completo(pdf_path, warnings)
                            resultado["method"] = f"{extension_lower}_to_pdf"
                            resultado["warnings"].append(f"Archivo {extension_lower} convertido a PDF después de error")
                            
                            if pdf_path != file_path and os.path.exists(pdf_path):
                                try:
                                    os.unlink(pdf_path)
                                except:
                                    pass
                            
                            return resultado
                        raise
            
            # 3. Para todos los demás formatos, convertir a PDF primero
            logger.info(f"Convirtiendo {extension_lower} a PDF...")
            
            # Intentar conversión a PDF
            pdf_path = self.pdf_converter.convertir_a_pdf(file_path, extension_lower)
            
            if pdf_path and os.path.exists(pdf_path):
                # Procesar el PDF convertido
                resultado = self._procesar_pdf_completo(pdf_path, warnings)
                resultado["method"] = "pdf_conversion"
                resultado["warnings"].append(f"Archivo {extension_lower} convertido a PDF")
                
                # Limpiar PDF temporal si fue creado
                if pdf_path != file_path and os.path.exists(pdf_path):
                    try:
                        os.unlink(pdf_path)
                    except Exception as e:
                        logger.warning(f"No se pudo eliminar PDF temporal: {str(e)}")
                
                return resultado
            else:
                # Si la conversión falló, intentar extracción directa según el tipo
                warnings.append(f"No se pudo convertir {extension_lower} a PDF, intentando extracción directa")
                texto = self._intentar_extraccion_directa(file_path, extension_lower, warnings)
                
                if texto:
                    return {
                        "texto": texto,
                        "caracteres": len(texto),
                        "paginas": 1,
                        "method": f"direct_{extension_lower}",
                        "warnings": warnings
                    }
                else:
                    # Como último recurso, intentar procesar como PDF genérico
                    logger.warning(f"No se pudo procesar {extension_lower} con ningún método. Intentando como PDF...")
                    try:
                        resultado = self._procesar_pdf_completo(file_path, warnings)
                        resultado["method"] = "fallback_pdf"
                        resultado["warnings"].append(f"Archivo {extension_lower} procesado como PDF genérico")
                        return resultado
                    except Exception as e2:
                        # Si todo falla, retornar estructura válida pero vacía
                        logger.error(f"Todos los métodos fallaron para {extension_lower}: {str(e2)}")
                        return {
                            "texto": "",
                            "caracteres": 0,
                            "paginas": 0,
                            "method": "failed",
                            "warnings": warnings + [f"No se pudo procesar archivo {extension_lower}: {str(e2)}"]
                        }
                    
        except Exception as e:
            logger.error(f"Error procesando {extension_lower}: {str(e)}", exc_info=True)
            # Como último recurso, intentar como PDF
            try:
                logger.info(f"Intentando procesar {extension_lower} como PDF...")
                resultado = self._procesar_pdf_completo(file_path, warnings)
                resultado["method"] = "fallback_pdf"
                resultado["warnings"].append(f"Procesado como PDF después de error: {str(e)}")
                return resultado
            except Exception as e2:
                # Si todo falla, retornar estructura válida pero vacía en lugar de lanzar error
                logger.error(f"Todos los métodos de procesamiento fallaron: {str(e2)}")
                return {
                    "texto": "",
                    "caracteres": 0,
                    "paginas": 0,
                    "method": "failed",
                    "warnings": warnings + [f"Error procesando archivo: {str(e)}", f"Fallback también falló: {str(e2)}"]
                }
    
    def _procesar_pdf_completo(self, file_path: str, warnings: List[str]) -> Dict[str, any]:
        """Procesa un PDF y retorna información completa"""
        try:
            # Intentar con PyMuPDF primero (mejor calidad)
            try:
                import fitz  # PyMuPDF
                doc = fitz.open(file_path)
                texto = []
                paginas = len(doc)
                
                for page_num in range(paginas):
                    page = doc[page_num]
                    texto_pagina = page.get_text()
                    texto.append(texto_pagina)
                
                doc.close()
                texto_completo = '\n'.join(texto)
                
                return {
                    "texto": texto_completo,
                    "caracteres": len(texto_completo),
                    "paginas": paginas,
                    "method": "direct_pdf",
                    "warnings": warnings
                }
            except ImportError:
                # Fallback a pdfplumber
                try:
                    import pdfplumber
                    texto = []
                    paginas = 0
                    
                    with pdfplumber.open(file_path) as pdf:
                        paginas = len(pdf.pages)
                        for page in pdf.pages:
                            texto_pagina = page.extract_text()
                            if texto_pagina:
                                texto.append(texto_pagina)
                    
                    texto_completo = '\n'.join(texto) if texto else ""
                    warnings.append("Usando pdfplumber como alternativa a PyMuPDF")
                    
                    return {
                        "texto": texto_completo,
                        "caracteres": len(texto_completo),
                        "paginas": paginas,
                        "method": "direct_pdf",
                        "warnings": warnings
                    }
                except ImportError:
                    # Fallback a PyPDF2 (último recurso)
                    import PyPDF2
                    texto = []
                    with open(file_path, 'rb') as file:
                        pdf_reader = PyPDF2.PdfReader(file)
                        paginas = len(pdf_reader.pages)
                        for page in pdf_reader.pages:
                            texto.append(page.extract_text())
                    
                    texto_completo = '\n'.join(texto)
                    warnings.append("Usando PyPDF2 como último recurso (calidad puede ser menor)")
                    
                    return {
                        "texto": texto_completo,
                        "caracteres": len(texto_completo),
                        "paginas": paginas,
                        "method": "direct_pdf",
                        "warnings": warnings
                    }
        except Exception as e:
            logger.error(f"Error procesando PDF: {str(e)}")
            raise
    
    def _procesar_pdf(self, file_path: str) -> str:
        """Procesa archivos PDF (método simple para compatibilidad)"""
        resultado = self._procesar_pdf_completo(file_path, [])
        return resultado["texto"]
    
    def _procesar_txt(self, file_path: str) -> str:
        """Procesa archivos de texto plano"""
        try:
            # Intentar diferentes codificaciones
            codificaciones = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
            for encoding in codificaciones:
                try:
                    with open(file_path, 'r', encoding=encoding, errors='ignore') as file:
                        return file.read()
                except UnicodeDecodeError:
                    continue
            # Si todas fallan, usar utf-8 con errors='ignore'
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                return file.read()
        except Exception as e:
            logger.error(f"Error procesando TXT: {str(e)}")
            raise
    
    def _procesar_csv(self, file_path: str) -> str:
        """Procesa archivos CSV"""
        try:
            import csv
            texto = []
            codificaciones = ['utf-8', 'latin-1', 'cp1252']
            
            for encoding in codificaciones:
                try:
                    with open(file_path, 'r', encoding=encoding, errors='ignore', newline='') as file:
                        reader = csv.reader(file)
                        for row in reader:
                            texto.append('\t'.join(row))
                    return '\n'.join(texto)
                except UnicodeDecodeError:
                    continue
            
            # Si todas fallan, leer como texto plano
            return self._procesar_txt(file_path)
        except Exception as e:
            logger.error(f"Error procesando CSV: {str(e)}")
            # Fallback a texto plano
            return self._procesar_txt(file_path)
    
    def _procesar_imagen(self, file_path: str) -> str:
        """Procesa imágenes con OCR"""
        try:
            import pytesseract
            from PIL import Image
            
            imagen = Image.open(file_path)
            texto = pytesseract.image_to_string(imagen, lang='spa+eng')
            return texto
        except ImportError:
            logger.warning("pytesseract o Pillow no están instalados. Intentando convertir imagen a PDF...")
            # Si OCR no está disponible, intentar convertir imagen a PDF
            pdf_path = self.pdf_converter.convertir_a_pdf(file_path, 'png')
            if pdf_path:
                resultado = self._procesar_pdf_completo(pdf_path, [])
                return resultado["texto"]
            raise ImportError("pytesseract y Pillow no están instalados. Instala con: pip install pytesseract pillow")
        except Exception as e:
            logger.error(f"Error procesando imagen: {str(e)}")
            raise
    
    def _intentar_extraccion_directa(self, file_path: str, extension: str, warnings: List[str]) -> Optional[str]:
        """Intenta extraer texto directamente según el tipo de archivo"""
        extension_lower = extension.lower()
        
        try:
            # DOCX
            if extension_lower == 'docx':
                try:
                    from docx import Document
                    doc = Document(file_path)
                    texto = []
                    for paragraph in doc.paragraphs:
                        texto.append(paragraph.text)
                    return '\n'.join(texto)
                except ImportError:
                    warnings.append("python-docx no está instalado")
                    return None
            
            # XLSX
            if extension_lower == 'xlsx':
                try:
                    import openpyxl
                    workbook = openpyxl.load_workbook(file_path)
                    texto = []
                    for sheet_name in workbook.sheetnames:
                        sheet = workbook[sheet_name]
                        texto.append(f"=== Hoja: {sheet_name} ===")
                        for row in sheet.iter_rows(values_only=True):
                            fila = [str(cell) if cell is not None else '' for cell in row]
                            if any(fila):
                                texto.append('\t'.join(fila))
                    return '\n'.join(texto)
                except ImportError:
                    warnings.append("openpyxl no está instalado")
                    return None
            
            # XLS
            if extension_lower == 'xls':
                try:
                    import xlrd
                    workbook = xlrd.open_workbook(file_path)
                    texto = []
                    for sheet_name in workbook.sheet_names():
                        sheet = workbook.sheet_by_name(sheet_name)
                        texto.append(f"=== Hoja: {sheet_name} ===")
                        for row_idx in range(sheet.nrows):
                            fila = []
                            for col_idx in range(sheet.ncols):
                                cell = sheet.cell(row_idx, col_idx)
                                if cell.ctype == xlrd.XL_CELL_TEXT:
                                    fila.append(cell.value)
                                elif cell.ctype == xlrd.XL_CELL_NUMBER:
                                    fila.append(str(cell.value))
                                elif cell.ctype == xlrd.XL_CELL_DATE:
                                    fecha = xlrd.xldate_as_datetime(cell.value, workbook.datemode)
                                    fila.append(fecha.strftime('%Y-%m-%d %H:%M:%S'))
                                elif cell.ctype == xlrd.XL_CELL_BOOLEAN:
                                    fila.append('TRUE' if cell.value else 'FALSE')
                                else:
                                    fila.append(str(cell.value) if cell.value else '')
                            if any(fila):
                                texto.append('\t'.join(fila))
                    return '\n'.join(texto)
                except ImportError:
                    warnings.append("xlrd no está instalado")
                    return None
            
            # PPTX
            if extension_lower == 'pptx':
                try:
                    from pptx import Presentation
                    prs = Presentation(file_path)
                    texto = []
                    for slide_num, slide in enumerate(prs.slides, 1):
                        texto.append(f"=== Diapositiva {slide_num} ===")
                        for shape in slide.shapes:
                            if hasattr(shape, "text") and shape.text:
                                texto.append(shape.text)
                            if shape.has_table:
                                for row in shape.table.rows:
                                    fila = []
                                    for cell in row.cells:
                                        if cell.text:
                                            fila.append(cell.text.strip())
                                    if fila:
                                        texto.append('\t'.join(fila))
                    return '\n'.join(texto)
                except ImportError:
                    warnings.append("python-pptx no está instalado")
                    return None
            
        except Exception as e:
            logger.warning(f"Error en extracción directa de {extension_lower}: {str(e)}")
            warnings.append(f"Extracción directa falló: {str(e)}")
        
        return None
    
    def _detectar_extension_por_contenido(self, file_path: str) -> Optional[str]:
        """Intenta detectar la extensión analizando el contenido del archivo"""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(8)
                
                # PDF
                if header.startswith(b'%PDF'):
                    return 'pdf'
                
                # ZIP (DOCX, XLSX, PPTX son ZIP)
                if header.startswith(b'PK\x03\x04'):
                    # Leer más para determinar el tipo
                    f.seek(0)
                    content = f.read(1024)
                    if b'word/' in content:
                        return 'docx'
                    elif b'xl/' in content or b'worksheets/' in content:
                        return 'xlsx'
                    elif b'ppt/' in content or b'presentation' in content:
                        return 'pptx'
                    return 'zip'
                
                # Office antiguo (OLE)
                if header.startswith(b'\xd0\xcf\x11\xe0'):
                    return 'doc'  # Puede ser DOC, XLS, PPT, pero asumimos DOC
                
                # Imágenes
                if header.startswith(b'\xff\xd8\xff'):
                    return 'jpg'
                if header.startswith(b'\x89PNG'):
                    return 'png'
                if header.startswith(b'GIF'):
                    return 'gif'
                
        except Exception:
            pass
        
        return None
