# Backend de Procesamiento de Documentos

Backend Flask para procesar documentos y extraer texto de múltiples formatos.

## Formatos Soportados

- ✅ **PDF** - Usando PyPDF2
- ✅ **DOCX** - Usando python-docx
- ✅ **XLSX** - Usando openpyxl
- ✅ **PPTX** - Convertido a PDF usando Google Drive (NUEVO)
- ✅ **XLS** - Usando xlrd
- ✅ **PPT** - Convertido a PDF usando Google Drive (NUEVO)
- ✅ **TXT** - Texto plano
- ✅ **Imágenes** (JPG, PNG) - Usando OCR con pytesseract

## Conversión PPT/PPTX a PDF

Los archivos PPT y PPTX se convierten automáticamente a PDF usando Google Drive antes de procesarlos:

1. El archivo se sube temporalmente a Google Drive
2. Google Drive lo convierte a PDF automáticamente
3. Se descarga el PDF convertido
4. Se procesa el PDF normalmente
5. Se eliminan los archivos temporales de Google Drive

## Instalación

```bash
pip install -r requirements.txt
```

## Ejecución Local

```bash
python app.py
```

O con gunicorn (producción):

```bash
gunicorn app:app
```

## Endpoints

### POST /procesar

Procesa un documento y extrae su texto.

**Request:**
- Method: POST
- Content-Type: multipart/form-data
- Campo: `file` (archivo a procesar)

**Response (éxito):**
```json
{
  "texto": "Contenido extraído del documento...",
  "status": "success"
}
```

**Response (error):**
```json
{
  "status": "error",
  "code": 400,
  "message": "Mensaje de error",
  "error": "Descripción detallada del error"
}
```

### GET /health

Verifica que el servidor está funcionando.

**Response:**
```json
{
  "status": "ok",
  "message": "Servidor funcionando correctamente"
}
```

## Despliegue en Railway

1. Conecta tu repositorio de GitHub a Railway
2. Railway detectará automáticamente el archivo `requirements.txt`
3. El comando de inicio es: `gunicorn app:app`
4. El puerto se configura automáticamente con la variable de entorno `PORT`

## Variables de Entorno

- `PORT`: Puerto en el que se ejecutará la aplicación (Railway lo configura automáticamente)
- `CUENTA_DE_SERVICIO_DE_GOOGLE`: Ruta al archivo JSON de service account de Google, o contenido JSON directo. **REQUERIDO para conversión PPT/PPTX**

## Notas Importantes

### PPTX y PPT (Conversión a PDF)
- **NUEVO**: Se convierten automáticamente a PDF usando Google Drive
- Requiere configurar la variable de entorno `CUENTA_DE_SERVICIO_DE_GOOGLE`
- El archivo se sube temporalmente a Google Drive, se convierte y se elimina
- Si Google Drive no está disponible, se intenta procesar directamente (puede fallar)

### XLS
- Requiere la librería `xlrd` (versión 2.0.1)
- Soporta números, texto, fechas y booleanos
- Convierte fechas de Excel a formato legible

### PDF, DOCX, XLSX
- Funcionan normalmente sin conversión
- No requieren Google Drive

## Solución de Problemas

### Error: "Formato no soportado"
- Verifica que la extensión del archivo sea correcta
- Asegúrate de que el formato esté en la lista de soportados

### Error: "Módulo no encontrado"
- Ejecuta `pip install -r requirements.txt`
- Verifica que todas las dependencias estén instaladas

### Error: "No se pudo extraer texto"
- El documento puede estar vacío o ser una imagen escaneada
- Para imágenes, usa OCR (el backend lo hace automáticamente)

### Error: "Google Drive no está disponible" (para PPT/PPTX)
- Verifica que la variable de entorno `CUENTA_DE_SERVICIO_DE_GOOGLE` esté configurada
- Asegúrate de que el service account JSON sea válido
- Verifica que el service account tenga permisos de Google Drive
- Revisa los logs para más detalles del error

### Error: "Error al convertir PPT/PPTX a PDF"
- Verifica que el service account tenga permisos para crear y eliminar archivos en Google Drive
- Asegúrate de que el archivo PPT/PPTX no esté corrupto
- Verifica que Google Drive API esté habilitada en tu proyecto de Google Cloud

