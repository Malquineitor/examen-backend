"""
Módulo para convertir cualquier formato de documento a PDF usando LibreOffice
Soporta: DOC, DOCX, XLS, XLSX, PPT, PPTX, ODT, RTF, CSV, TXT, imágenes, etc.
"""
import os
import subprocess
import tempfile
import logging
from typing import Optional, Tuple
import shutil
import chardet

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PDFConverter:
    """Convierte cualquier formato de documento a PDF usando LibreOffice"""
    
    def __init__(self):
        self.libreoffice_path = self._detectar_libreoffice()
        self.unoconv_path = self._detectar_unoconv()
    
    def _detectar_libreoffice(self) -> Optional[str]:
        """Detecta la ruta de LibreOffice en el sistema"""
        posibles_rutas = [
            'soffice',
            'libreoffice',
            '/usr/bin/soffice',
            '/usr/bin/libreoffice',
            '/Applications/LibreOffice.app/Contents/MacOS/soffice',
            'C:\\Program Files\\LibreOffice\\program\\soffice.exe',
            'C:\\Program Files (x86)\\LibreOffice\\program\\soffice.exe',
        ]
        
        for ruta in posibles_rutas:
            try:
                # Verificar si el comando existe
                result = subprocess.run(
                    [ruta, '--version'],
                    capture_output=True,
                    timeout=5,
                    text=True
                )
                if result.returncode == 0:
                    logger.info(f"LibreOffice detectado en: {ruta}")
                    return ruta
            except (FileNotFoundError, subprocess.TimeoutExpired, Exception) as e:
                continue
        
        logger.warning("LibreOffice no detectado. Algunos formatos pueden no convertirse.")
        return None
    
    def _detectar_unoconv(self) -> Optional[str]:
        """Detecta la ruta de unoconv como alternativa"""
        posibles_rutas = [
            'unoconv',
            '/usr/bin/unoconv',
            '/usr/local/bin/unoconv',
        ]
        
        for ruta in posibles_rutas:
            try:
                result = subprocess.run(
                    [ruta, '--version'],
                    capture_output=True,
                    timeout=5,
                    text=True
                )
                if result.returncode == 0:
                    logger.info(f"unoconv detectado en: {ruta}")
                    return ruta
            except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
                continue
        
        return None
    
    def convertir_a_pdf(self, file_path: str, extension: str) -> Optional[str]:
        """
        Convierte un archivo a PDF usando LibreOffice, unoconv, o métodos alternativos
        
        Args:
            file_path: Ruta al archivo a convertir
            extension: Extensión del archivo (sin punto)
        
        Returns:
            Ruta al archivo PDF convertido o None si falla
        """
        extension_lower = extension.lower().strip()
        
        # Si ya es PDF, no necesita conversión
        if extension_lower == 'pdf':
            return file_path
        
        # Formatos de texto plano: convertir a PDF usando reportlab
        if extension_lower in ['txt', 'csv']:
            try:
                return self._convertir_texto_a_pdf(file_path, extension_lower)
            except Exception as e:
                logger.warning(f"Error convirtiendo texto a PDF: {str(e)}. Intentando LibreOffice...")
        
        # Formatos de imagen: convertir a PDF usando Pillow
        formatos_imagen = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'tif', 'heic', 'heif', 'webp']
        if extension_lower in formatos_imagen:
            try:
                return self._convertir_imagen_a_pdf(file_path, extension_lower)
            except Exception as e:
                logger.warning(f"Error convirtiendo imagen a PDF: {str(e)}. Intentando LibreOffice...")
        
        # Intentar con LibreOffice primero
        if self.libreoffice_path:
            try:
                return self._convertir_con_libreoffice(file_path, extension_lower)
            except Exception as e:
                logger.warning(f"Error con LibreOffice: {str(e)}. Intentando unoconv...")
        
        # Intentar con unoconv como alternativa
        if self.unoconv_path:
            try:
                return self._convertir_con_unoconv(file_path, extension_lower)
            except Exception as e:
                logger.warning(f"Error con unoconv: {str(e)}")
        
        # Si ambos fallan, intentar métodos alternativos según el tipo
        if extension_lower in ['txt', 'csv']:
            try:
                return self._convertir_texto_a_pdf(file_path, extension_lower)
            except Exception as e:
                logger.warning(f"Conversión de texto a PDF falló: {str(e)}")
        
        if extension_lower in formatos_imagen:
            try:
                return self._convertir_imagen_a_pdf(file_path, extension_lower)
            except Exception as e:
                logger.warning(f"Conversión de imagen a PDF falló: {str(e)}")
        
        logger.warning(f"No se pudo convertir {extension_lower} a PDF con ningún método")
        return None
    
    def _convertir_con_libreoffice(self, file_path: str, extension: str) -> str:
        """Convierte usando LibreOffice headless"""
        if not self.libreoffice_path:
            raise ValueError("LibreOffice no está disponible")
        
        # Crear directorio temporal para el PDF
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Comando de conversión
            cmd = [
                self.libreoffice_path,
                '--headless',
                '--convert-to', 'pdf',
                '--outdir', temp_dir,
                file_path
            ]
            
            logger.info(f"Convirtiendo {extension} a PDF con LibreOffice...")
            logger.info(f"Comando: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=60,
                text=True
            )
            
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout or "Error desconocido"
                raise ValueError(f"LibreOffice falló: {error_msg}")
            
            # Buscar el archivo PDF generado
            # LibreOffice genera el PDF con el mismo nombre base
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            pdf_path = os.path.join(temp_dir, f"{base_name}.pdf")
            
            # Si no existe con ese nombre, buscar cualquier PDF en el directorio
            if not os.path.exists(pdf_path):
                pdf_files = [f for f in os.listdir(temp_dir) if f.endswith('.pdf')]
                if pdf_files:
                    pdf_path = os.path.join(temp_dir, pdf_files[0])
                else:
                    raise ValueError("No se generó el archivo PDF")
            
            # Mover el PDF a un archivo temporal permanente
            final_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf').name
            shutil.move(pdf_path, final_pdf)
            
            logger.info(f"Conversión exitosa: {extension} → PDF ({final_pdf})")
            return final_pdf
            
        except subprocess.TimeoutExpired:
            raise ValueError("Timeout al convertir con LibreOffice (más de 60 segundos)")
        except Exception as e:
            raise ValueError(f"Error convirtiendo con LibreOffice: {str(e)}")
        finally:
            # Limpiar directorio temporal
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
            except Exception as e:
                logger.warning(f"No se pudo limpiar directorio temporal: {str(e)}")
    
    def _convertir_con_unoconv(self, file_path: str, extension: str) -> str:
        """Convierte usando unoconv como alternativa"""
        if not self.unoconv_path:
            raise ValueError("unoconv no está disponible")
        
        # Crear archivo temporal para el PDF
        pdf_path = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf').name
        
        try:
            cmd = [
                self.unoconv_path,
                '-f', 'pdf',
                '-o', pdf_path,
                file_path
            ]
            
            logger.info(f"Convirtiendo {extension} a PDF con unoconv...")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=60,
                text=True
            )
            
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout or "Error desconocido"
                raise ValueError(f"unoconv falló: {error_msg}")
            
            if not os.path.exists(pdf_path) or os.path.getsize(pdf_path) == 0:
                raise ValueError("No se generó el archivo PDF o está vacío")
            
            logger.info(f"Conversión exitosa con unoconv: {extension} → PDF")
            return pdf_path
            
        except subprocess.TimeoutExpired:
            raise ValueError("Timeout al convertir con unoconv (más de 60 segundos)")
        except Exception as e:
            # Limpiar archivo si falló
            if os.path.exists(pdf_path):
                try:
                    os.unlink(pdf_path)
                except:
                    pass
            raise ValueError(f"Error convirtiendo con unoconv: {str(e)}")
    
    def necesita_conversion(self, extension: str) -> bool:
        """Determina si un formato necesita conversión a PDF"""
        extension_lower = extension.lower().strip()
        
        # Formatos que NO necesitan conversión (se procesan directamente)
        formatos_directos = {'pdf', 'txt', 'csv'}
        
        # Si es PDF, no necesita conversión
        if extension_lower == 'pdf':
            return False
        
        # Si es texto plano o CSV, se puede procesar directamente
        if extension_lower in formatos_directos:
            return False
        
        # Todos los demás formatos necesitan conversión
        return True
    
    def _convertir_texto_a_pdf(self, file_path: str, extension: str) -> str:
        """
        Convierte un archivo de texto (TXT o CSV) a PDF usando reportlab
        """
        try:
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.pdfgen import canvas
            from reportlab.lib.units import inch
            
            # Detectar codificación del archivo
            with open(file_path, 'rb') as f:
                raw_data = f.read()
                detected = chardet.detect(raw_data)
                encoding = detected.get('encoding', 'utf-8') or 'utf-8'
            
            # Leer el contenido del archivo
            try:
                with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                    contenido = f.read()
            except:
                # Si falla, intentar UTF-8
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    contenido = f.read()
            
            # Crear archivo PDF temporal
            pdf_path = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf').name
            
            # Crear PDF con reportlab
            c = canvas.Canvas(pdf_path, pagesize=A4)
            width, height = A4
            margin = inch
            x = margin
            y = height - margin
            line_height = 12
            max_width = width - 2 * margin
            
            # Dividir el contenido en líneas
            lineas = contenido.split('\n')
            
            for linea in lineas:
                # Si la línea es muy larga, dividirla
                if len(linea) > 100:
                    palabras = linea.split(' ')
                    linea_actual = ''
                    for palabra in palabras:
                        if len(linea_actual + ' ' + palabra) < 100:
                            linea_actual += ' ' + palabra if linea_actual else palabra
                        else:
                            if linea_actual:
                                c.drawString(x, y, linea_actual[:100])
                                y -= line_height
                                if y < margin:
                                    c.showPage()
                                    y = height - margin
                            linea_actual = palabra
                    if linea_actual:
                        linea = linea_actual
                
                # Dibujar la línea
                c.drawString(x, y, linea[:100])
                y -= line_height
                
                # Nueva página si es necesario
                if y < margin:
                    c.showPage()
                    y = height - margin
            
            c.save()
            logger.info(f"Texto convertido a PDF exitosamente: {extension} → PDF")
            return pdf_path
            
        except ImportError:
            logger.warning("reportlab no está instalado. Intentando con PyMuPDF...")
            # Fallback: usar PyMuPDF para crear PDF simple
            try:
                import fitz  # PyMuPDF
                doc = fitz.open()  # Crear documento PDF vacío
                page = doc.new_page()
                
                # Leer contenido
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    contenido = f.read()
                
                # Insertar texto en la página
                rect = fitz.Rect(50, 50, 550, 750)
                page.insert_text(rect.tl, contenido[:5000], fontsize=11)  # Limitar a 5000 caracteres
                
                pdf_path = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf').name
                doc.save(pdf_path)
                doc.close()
                
                logger.info(f"Texto convertido a PDF con PyMuPDF: {extension} → PDF")
                return pdf_path
            except Exception as e:
                raise ValueError(f"No se pudo convertir texto a PDF: {str(e)}")
        except Exception as e:
            raise ValueError(f"Error convirtiendo texto a PDF: {str(e)}")
    
    def _convertir_imagen_a_pdf(self, file_path: str, extension: str) -> str:
        """
        Convierte una imagen a PDF usando Pillow
        """
        try:
            from PIL import Image
            
            # Abrir imagen
            imagen = Image.open(file_path)
            
            # Convertir a RGB si es necesario (para formatos como PNG con transparencia)
            if imagen.mode in ('RGBA', 'LA', 'P'):
                fondo = Image.new('RGB', imagen.size, (255, 255, 255))
                if imagen.mode == 'P':
                    imagen = imagen.convert('RGBA')
                fondo.paste(imagen, mask=imagen.split()[-1] if imagen.mode in ('RGBA', 'LA') else None)
                imagen = fondo
            elif imagen.mode != 'RGB':
                imagen = imagen.convert('RGB')
            
            # Crear archivo PDF temporal
            pdf_path = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf').name
            
            # Guardar como PDF
            imagen.save(pdf_path, 'PDF', resolution=100.0)
            
            logger.info(f"Imagen convertida a PDF exitosamente: {extension} → PDF")
            return pdf_path
            
        except ImportError:
            raise ValueError("Pillow no está instalado. Instala con: pip install Pillow")
        except Exception as e:
            raise ValueError(f"Error convirtiendo imagen a PDF: {str(e)}")
    
    def esta_disponible(self) -> bool:
        """Verifica si hay alguna herramienta de conversión disponible"""
        return self.libreoffice_path is not None or self.unoconv_path is not None

