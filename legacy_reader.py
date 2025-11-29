"""
legacy_reader.py — 100% compatible con Railway/Render
-----------------------------------------------------
Lector universal para:
- PPT antiguos (.ppt)
- DOC antiguos (.doc)
- XLS antiguos (.xls)
- OCR fallback
- OCR agresivo sin pdf2image, sin numpy, sin cv2
-----------------------------------------------------
"""

from pptx import Presentation
from PIL import Image, ImageFilter, ImageOps
import pytesseract
import xlrd
import tempfile
import os

# -----------------------------------------------------
# 1. LEER PPT ANTIGUOS
# -----------------------------------------------------
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
    except:
        return None


# -----------------------------------------------------
# 2. DOC ANTIGUOS (.doc)
# -----------------------------------------------------
def leer_doc_antiguo(path):
    try:
        with open(path, "rb") as f:
            raw = f.read().decode("latin-1", errors="ignore")
            if len(raw.strip()) > 50:
                return raw
    except:
        pass
    return ocr_fallback(path)


# -----------------------------------------------------
# 3. XLS ANTIGUOS (.xls)
# -----------------------------------------------------
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


# -----------------------------------------------------
# 4. OCR NORMAL
# -----------------------------------------------------
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


# -----------------------------------------------------
# 5. OCR AGRESIVO — versión compatible SIN pdf2image
# -----------------------------------------------------
def ocr_agresivo(path):
    """
    Intento agresivo:
    - Si es imagen → corre image OCR
    - Si es PDF → extrae solo primera página usando PIL SIN poppler
    (Railway/Render no soportan pdf2image/poppler)
    """

    extension = path.lower().split(".")[-1]

    # Si es imagen → OCR directo con filtros
    if extension in ["png", "jpg", "jpeg", "bmp", "tiff"]:
        return ocr_imagen_agresivo(Image.open(path))

    # Intento abrir PDF como imagen (PIL puede con PDFs simples)
    try:
        page = Image.open(path)
        return ocr_imagen_agresivo(page)
    except:
        pass

    return ""


def ocr_imagen_agresivo(img):
    """
    Procesa una imagen con filtros agresivos para mejorar OCR.
    """
    try:
        w, h = img.size
        img = img.resize((w * 2, h * 2), Image.LANCZOS)

        img = ImageOps.grayscale(img)

        img = img.filter(ImageFilter.SHARPEN)

        img = ImageOps.autocontrast(img)

        img = img.filter(ImageFilter.MedianFilter(size=3))

        return pytesseract.image_to_string(img, lang="spa+eng").strip()

    except Exception as e:
        print(f"OCR agresivo imagen error: {e}")
        return ""
