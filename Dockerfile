FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive

# Paquetes compatibles en Debian Trixie
RUN apt-get update && apt-get install -y \
    libreoffice \
    catdoc \
    tesseract-ocr \
    tesseract-ocr-spa \
    poppler-utils \
    ghostscript \
    imagemagick \
    build-essential \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Crear directorio de trabajo
WORKDIR /app

# Copiar archivos del proyecto
COPY . .

# Instalar dependencias Python
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Exponer puerto
EXPOSE 8080

# Iniciar servidor
CMD ["gunicorn", "-b", "0.0.0.0:8080", "app:app"]
