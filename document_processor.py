"""
document_processor.py
--------------------------------------------
Procesador simple y moderno para:
- DOCX
- XLSX
- PDF
- TXT
- CSV

NO usa LibreOffice.
Compatible con Railway.
--------------------------------------------
"""

import PyPDF2
from openpyxl import load_workbook
import python_docx
import pandas as pd
import os
import re


class DocumentProcessor:

    # ----------------------------------------
    # LECTOR SIMPLE (formatos modernos)
    # ----------------------------------------
    def leer_simple(self, path, extension):
        try:
            if extension == "docx":
                return self._leer_docx(path)

            if extension == "xlsx":
                return self._leer_xlsx(path)

            if extension == "csv":
                return self._leer_csv(path)

            if extension == "txt":
                return self._leer_txt(path)

            if extension == "pdf":
                return self._leer_pdf(path)

        except Exception as e:
            print(f"[simple_reader] Error: {e}")

        return None

    # ----------------------------------------
    # LECTORES INDIVIDUALES
    # ----------------------------------------

    def _leer_docx(self, path):
        try:
            doc = python_docx.Document(path)
            texto = "\n".join([p.text for p in doc.paragraphs])
            return self._limpiar(texto)
        except Exception as e:
            print(f"[DOCX] error: {e}")
            return None

    def _leer_xlsx(self, path):
        try:
            wb = load_workbook(path, read_only=True)
            texto = ""
            for sheet in wb.sheetnames:
                sh = wb[sheet]
                for row in sh.iter_rows(values_only=True):
                    texto += " ".join([str(v) for v in row]) + "\n"
            return self._limpiar(texto)
        except Exception as e:
            print(f"[XLSX] error: {e}")
            return None

    def _leer_csv(self, path):
        try:
            df = pd.read_csv(path)
            texto = df.to_string()
            return self._limpiar(texto)
        except Exception as e:
            print(f"[CSV] error: {e}")
            return None

    def _leer_txt(self, path):
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return self._limpiar(f.read())
        except Exception as e:
            print(f"[TXT] error: {e}")
            return None

    def _leer_pdf(self, path):
        try:
            texto = ""
            with open(path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    texto += page.extract_text() or ""
            return self._limpiar(texto)
        except Exception as e:
            print(f"[PDF] error: {e}")
            return None

    # ----------------------------------------
    # LIMPIAR TEXTO (quita logs, OCR, errores)
    # ----------------------------------------

    def _limpiar(self, texto):
        if not texto:
            return ""

        # Quitar logs de OCR que ensucian el documento
        patrones = [
            r"ERROR_OCR.*",
            r"OCR_FAILED.*",
            r"TESSERACT.*",
            r"PAGINA_\d+",
            r"MODO_RECUPERACION.*",
            r"error.*",
            r"failed.*"
        ]
        for p in patrones:
            texto = re.sub(p, "", texto, flags=re.IGNORECASE)

        texto = texto.replace("\x00", "")  # quitar caracteres nulos
        return texto.strip()
