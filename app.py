from flask import Flask, request, jsonify
import tempfile
import os
import pytesseract
from PIL import Image
import docx
import pandas as pd
import pdfplumber

app = Flask(__name__)

@app.route("/procesar", methods=["POST"])
def procesar():
    if "file" not in request.files:
        return jsonify({"error": "No se envió archivo"}), 400

    archivo = request.files["file"]

    # Guardar archivo temporal
    temp = tempfile.NamedTemporaryFile(delete=False)
    archivo.save(temp.name)

    nombre = (archivo.filename or "").lower()

    try:
        if nombre.endswith(".pdf"):
            texto = leer_pdf(temp.name)

        elif nombre.endswith(".docx"):
            texto = leer_docx(temp.name)

        elif nombre.endswith(".xlsx") or nombre.endswith(".xls"):
            texto = leer_excel(temp.name)

        elif nombre.endswith((".jpg", ".jpeg", ".png", ".heic", ".webp")):
            texto = leer_imagen(temp.name)

        else:
            return jsonify({"error": f"Formato no soportado: {nombre}"}), 400

        texto = (texto or "").strip()

        if not texto:
            return jsonify({"error": "No se pudo extraer texto del archivo"}), 422

        return jsonify({"texto": texto})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        try:
            os.unlink(temp.name)
        except Exception:
            pass


def leer_pdf(ruta):
    texto = ""
    with pdfplumber.open(ruta) as pdf:
        for pagina in pdf.pages:
            contenido = pagina.extract_text() or ""
            texto += contenido + "\n"
    return texto


def leer_docx(ruta):
    doc = docx.Document(ruta)
    return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])


def leer_excel(ruta):
    # Lee todas las hojas y concatena
    texto = ""
    xls = pd.read_excel(ruta, sheet_name=None, header=None)
    for nombre_hoja, df in xls.items():
        texto += f"\n--- Hoja: {nombre_hoja} ---\n"
        for fila in df.values:
            celdas = [str(c) for c in fila if str(c) != 'nan']
            if celdas:
                texto += " ".join(celdas) + "\n"
    return texto


def leer_imagen(ruta):
    img = Image.open(ruta)
    # Podrías ajustar idioma aquí si usas textos en español: lang="spa"
    return pytesseract.image_to_string(img)


@app.route("/", methods=["GET"])
def home():
    return "Backend Examen Naval funcionando ✔️"


if __name__ == "__main__":
    # Para uso local, en Railway se usará gunicorn
    app.run(host="0.0.0.0", port=10000)
