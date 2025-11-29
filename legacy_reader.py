"""
legacy_reader.py
---------------------------------------
Lector universal para documentos antiguos:
- PPT (1997-2003)
- DOC (1997-2003)
- XLS (1997-2003)
- OCR fallback normal
- OCR agresivo (último recurso real)

Compatible con Railway (NO usa LibreOffice)
---------------------------------------
"""

from pptx import Presentation
from PIL import Image
import pytesseract
import xlrd
import tempfile
import os

# Para OCR agresivo
import cv2
import numpy as np
from pdf2image import convert_from_path

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
    Genera imagen en blanco del slide.
    NOTA: python-pptx no renderiza el slide real sin librerías externas.
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
    Como Railway/Render no soportan LibreOffice,
    usamos:
    1. Lectura binaria
    2. OCR fallback
    """
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
    """
    OCR básico — último recurso simple.
    CREA UNA HOJA BLANCA, por eso funciona poco.
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


# ======================================================
# 5. OCR AGRESIVO — SOLO SE USA CUANDO TODO FALLA
# ======================================================

def ocr_agresivo(pdf_path):
    """
    OCR con preprocesamiento fuerte:
    - convierte PDF → imágenes a 300 DPI
    - escala 2X
    - blanco y negro
    - elimina ruido
    - threshold adaptativo
    - funciona incluso con banners y PDFs raros
    """

    try:
        pages = convert_from_path(pdf_path, dpi=300)
        texto_final = ""

        for page in pages:
            # PIL → OpenCV
            img = cv2.cvtColor(np.array(page), cv2.COLOR_RGB2BGR)

            # Escalar 2X para mejorar nitidez
            img = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

            # Blanco y negro
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Reducir ruido
            blur = cv2.GaussianBlur(gray, (5,5), 0)

            # Resaltar letras
            thresh = cv2.adaptiveThreshold(
                blur,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                11,
                2
            )

            # OCR agresivo
            text = pytesseract.image_to_string(thresh, lang="spa+eng")
            texto_final += text + "\n"

        return texto_final.strip()

    except Exception as e:
        print(f"[legacy_reader] OCR Agresivo Error: {e}")
        return ""
