"""
document_processor.py
-----------------------------------------------------
Procesador simple y moderno para:
 - DOCX
 - XLSX
 - XLS
 - PDF
 - TXT
 - CSV

Compatible con Railway (sin LibreOffice).
-----------------------------------------------------
"""

from docx import Document
from openpyxl import load_workbook
from PyPDF2 import PdfReader
import os
import re
import xlrd   # Para XLS antiguos


class DocumentProcessor:

    # ------------------------------------------
    # LECTOR SIMPLE (formatos modernos)
    # ------------------------------------------
    def leer_simple(self, path, extension):
        try:
            # ------------------------------
            # DOCX
            # ------------------------------
            if extension == "docx":
                doc = Document(path)
                texto = "\n".join([p.text for p in doc.paragraphs])
                return {"texto": texto, "method": "docx", "warnings": []}

            # ------------------------------
            # XLSX
            # ------------------------------
            elif extension == "xlsx":
                libro = load_workbook(filename=path, data_only=True)
                texto = ""
                for hoja in libro.sheetnames:
                    ws = libro[hoja]
                    for row in ws.iter_rows():
                        texto += " ".join([str(c.value) if c.value is not None else "" for c in row]) + "\n"
                return {"texto": texto, "method": "xlsx", "warnings": []}

            # ------------------------------
            # XLS (antiguo)
            # ------------------------------
            elif extension == "xls":
                texto = ""
                libro = xlrd.open_workbook(path)
                for hoja in libro.sheets():
                    for row_idx in range(hoja.nrows):
                        fila = hoja.row_values(row_idx)
                        texto += " ".join([str(v) for v in fila]) + "\n"

                return {"texto": texto, "method": "xls", "warnings": []}

            # ------------------------------
            # TXT
            # ------------------------------
            elif extension == "txt":
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    return {"texto": f.read(), "method": "txt", "warnings": []}

            # ------------------------------
            # CSV
            # ------------------------------
            elif extension == "csv":
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    return {"texto": f.read(), "method": "csv", "warnings": []}

            return {"texto": "", "method": "simple_unknown", "warnings": ["Formato no compatible en simple"]}

        except Exception as e:
            return {"texto": "", "method": "simple_error", "warnings": [str(e)]}

    # ------------------------------------------
    # LECTOR PDF (moderno)
    # ------------------------------------------
    def leer_pdf(self, path):
        try:
            reader = PdfReader(path)
            texto = ""
            for page in reader.pages:
                texto += page.extract_text() or ""

            return {"texto": texto, "method": "pdf", "warnings": []}
        except Exception as e:
            return {"texto": "", "method": "pdf_error", "warnings": [str(e)]}

    # ------------------------------------------
    # FUNCIÓN PRINCIPAL
    # ------------------------------------------
    def procesar_archivo(self, path, extension):
        extension = extension.lower()

        # --------------------------------------
        # PDF
        # --------------------------------------
        if extension == "pdf":
            return self.leer_pdf(path)

        # --------------------------------------
        # SIMPLE (docx, xlsx, xls, txt, csv)
        # --------------------------------------
        simple_res = self.leer_simple(path, extension)
        if simple_res.get("texto") and simple_res["texto"].strip():
            return simple_res

        # Si simple falló, retorno lo que tenga
        return simple_res

    # ------------------------------------------
    # LIMPIAR TEXTO (opcional)
    # ------------------------------------------
    def limpiar_texto(self, texto):
        if not texto:
            return texto

        patrones = [
            r"ERROR_OCR_.*",
            r"OCR_.*",
            r"TESSERACT_.*",
            r"PAGINA_.*",
            r"MODO_.*",
            r"error.*",
            r"fail.*"
        ]
        for p in patrones:
            texto = re.sub(p, "", texto, flags=re.IGNORECASE)

        return texto.strip()
