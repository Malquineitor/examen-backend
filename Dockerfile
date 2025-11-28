# Imagen base
FROM python:3.10-slim

# Evitar prompts
ENV DEBIAN_FRONTEND=noninteractive

# Instalar dependencias necesarias para DOC, PPT, XLS antiguos + OCR
RUN apt-get update && apt-get install -y \
    libreoffice \
    unoconv \
    antiword \
    tesseract-ocr \
    tesseract-ocr-spa \
    poppler-utils \
    ghostscript \
    build-essential \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Crear directorio de trabajo
WORKDIR /app

# Copiar proyecto
COPY . .

# Instalar librerías Python
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Puerto expuesto
EXPOSE 8080

# Comando para iniciar
CMD ["gunicorn", "-b", "0.0.0.0:8080", "app:app"]
