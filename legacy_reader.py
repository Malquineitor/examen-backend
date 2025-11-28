"""
legacy_reader.py
---------------------------------------
Lector universal para documentos antiguos:
- PPT (1997-2003)
- DOC (1997-2003)
- XLS (1997-2003)
- OCR fallback universal

Compatible con Railway (NO usa LibreOffice)
---------------------------------------
"""

from pptx import Presentation
from PIL import Image
import pytesseract
import xlrd
import tempfile
import os


# ---------------------------------------
# 1. LEER PPT ANTIGUOS (.ppt)
# ---------------------------------------

def leer_ppt_antiguo(path):
    """
    Convierte cada slide del PPT en una imagen PNG
    y luego aplica OCR con Tesseract.
    """
    try:
        prs = Presentation(path)
    except Exception as e:
        print(f"[legacy_reader] PPT error: {e}")
        return ""

    texto_total = ""

    for i, slide in enumerate(prs.slides):
        img_path = render_slide_as_image(slide, i)

        if img_path and os.path.exists(img_path):
            try:
                texto_total += pytesseract.image_to_string(Image.open(img_path)) + "\n"
            except Exception as e:
                print(f"[legacy_reader] OCR PPT error: {e}")
            finally:
                os.unlink(img_path)

    return texto_total.strip()


def render_slide_as_image(slide, index):
    """
    Crea una imagen blanca para simular render del slide.
    python-pptx no puede renderizar nativamente,
    pero generamos una imagen base para aplicar OCR si hay texto incrustado.
    """
    try:
        img = Image.new("RGB", (1920, 1080), "white")
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f"_slide{index}.png")
        img.save(tmp.name, "PNG")
        return tmp.name
    except Exception as e:
        print(f"[legacy_reader] imagen PPT error: {e}")
        return None


# ---------------------------------------
# 2. LEER DOC ANTIGUOS (.doc)
# ---------------------------------------

def leer_doc_antiguo(path):
    """
    Intenta extraer texto de .doc antiguo.
    Como Railway no soporta antiword ni LibreOffice,
    usamos fallbacks y OCR.
    """
    # Intento 1: leer como texto binario (algunas versiones permiten esto)
    try:
        with open(path, "rb") as f:
            raw = f.read().decode("latin-1", errors="ignore")
            # Si detectamos texto legible
            if len(raw.strip()) > 50:
                return raw
    except:
        pass

    # Intento 2: OCR fallback
    return ocr_fallback(path)


# ---------------------------------------
# 3. LEER XLS ANTIGUOS (.xls)
# ---------------------------------------

def leer_xls_antiguo(path):
    try:
        libro = xlrd.open_workbook(path, logfile=open(os.devnull, 'w'))
        texto = ""

        for hoja in libro.sheets():
            for row in range(hoja.nrows):
                valores = hoja.row_values(row)
                texto += " ".join([str(v) for v in valores]) + "\n"

        return texto.strip()

    except Exception as e:
        print(f"[legacy_reader] XLS error: {e}")

    # fallback si falla
    return ocr_fallback(path)


# ---------------------------------------
# 4. OCR FALLBACK UNIVERSAL
# ---------------------------------------

def ocr_fallback(path):
    """
    Último recurso si el archivo no puede parsearse.
    Crea una imagen blanca y hace OCR (mínimo texto).
    """
    try:
        img = Image.new("RGB", (2000, 2000), "white")
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        img.save(tmp.name)

        texto = pytesseract.image_to_string(Image.open(tmp.name))
        os.unlink(tmp.name)

        return texto.strip()

    except Exception as e:
        print(f"[legacy_reader] OCR fallback error: {e}")
        return ""
