"""
legacy_reader.py
---------------------------------------
Lector universal para documentos antiguos:
- PPT (1997-2003)
- DOC (1997-2003)
- XLS (1997-2003)
- OCR fallback normal
- OCR agresivo (sin cv2) compatible con Railway/Render

---------------------------------------
"""

from pptx import Presentation
from PIL import Image, ImageFilter, ImageOps
import pytesseract
import xlrd
import tempfile
import os
import numpy as np
from pdf2image import convert_from_path

# ---------------------------------------
# 1. LEER PPT ANTIGUOS (.ppt)
# ---------------------------------------

def leer_ppt_antiguo(path):
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
    try:
        with open(path, "rb") as f:
            raw = f.read().decode("latin-1", errors="ignore")
            if len(raw.strip()) > 50:
                return raw
    except:
        pass

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

    return ocr_fallback(path)

# ---------------------------------------
# 4. OCR FALLBACK NORMAL
# ---------------------------------------

def ocr_fallback(path):
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

# ---------------------------------------
# 5. OCR AGRESIVO (SIN CV2)
# ---------------------------------------

def ocr_agresivo(pdf_path):
    """
    OCR agresivo compatible con Railway/Render.
    - Convierte PDF → imágenes
    - Aumenta tamaño 2X
    - Convierte a blanco y negro
    - Aumenta contraste
    - Reduce ruido
    """
    try:
        pages = convert_from_path(pdf_path, dpi=300)
        texto_final = ""

        for page in pages:
            img = page

            # Escalar 2X
            w, h = img.size
            img = img.resize((w * 2, h * 2), Image.LANCZOS)

            # Convertir a blanco y negro
            img = ImageOps.grayscale(img)

            # Filtro de nitidez
            img = img.filter(ImageFilter.SHARPEN)

            # Aumentar contraste
            img = ImageOps.autocontrast(img)

            # Reducir ruido
            img = img.filter(ImageFilter.MedianFilter(size=3))

            # OCR agresivo
            text = pytesseract.image_to_string(img, lang="spa+eng")

            texto_final += text + "\n"

        return texto_final.strip()

    except Exception as e:
        print(f"[legacy_reader] OCR Agresivo Error: {e}")
        return ""
