"""
ai_service.py – Versión 2025
-------------------------------------
Reemplaza 100% la lógica que antes vivía en la app Android:
 - Construcción avanzada de prompts
 - División en bloques (ahora viene desde document_processor)
 - Reintentos automáticos
 - Limpieza de la respuesta
 - Extracción estricta del JSON
 - Generación múltiple por bloque
-------------------------------------
Compatible con Gemini 2.0 / 2.5 / Flash-Lite
"""

import os
import requests
import json
import time
import re

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

DEFAULT_MODEL = "gemini-2.0-flash-lite"

# ==============================================
# 🔹 LLAMAR A GEMINI CON RETRY Y MANEJO DE ERRORES
# ==============================================
def call_gemini(prompt: str, model_name: str = DEFAULT_MODEL, retries: int = 2):
    if not GEMINI_API_KEY:
        raise Exception("GEMINI_API_KEY no está configurada en Render/Railway")

    endpoint = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model_name}:generateContent?key={GEMINI_API_KEY}"
    )

    payload = {
        "contents": [
            {"parts": [{"text": prompt}]}
        ]
    }

    for attempt in range(retries):
        try:
            r = requests.post(endpoint, json=payload, timeout=60)
            data = r.json()

            if r.status_code == 200:
                # Extraer texto con seguridad
                try:
                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                    return text
                except:
                    pass

        except Exception as e:
            print(f"[Gemini ERROR] Attempt {attempt+1} → {e}")

        time.sleep(1.2)

    return None


# ==============================================
# 🔹 LIMPIAR RESPUESTA Y EXTRAER SOLO EL JSON
# ==============================================
def extract_clean_json(text):
    if not text:
        return "[]"

    # Eliminar código markdown
    text = text.replace("```json", "").replace("```", "")

    # Buscar array [
    start = text.find("[")
    end = text.rfind("]")

    if start == -1 or end == -1:
        return "[]"

    return text[start:end+1]


# ==============================================
# 🔹 PROMPT EXACTO COMO EL DE LA APP ANDROID
# ==============================================
def build_prompt(block_text, block_num, total_blocks, questions_goal):
    return f"""
Eres un generador de preguntas tipo test. Tu tarea es crear preguntas basadas únicamente en el siguiente bloque de texto.

CONTEXTO:
- Este es el bloque {block_num} de {total_blocks} bloques totales.
- Evita repetir información generada en bloques anteriores.

INSTRUCCIONES CRÍTICAS:
1. Genera al menos {questions_goal} preguntas (más si el contenido lo permite).
2. Cada pregunta debe tener EXACTAMENTE 4 alternativas (a, b, c, d).
3. Solo UNA alternativa es correcta.
4. Analiza TODO el contenido y crea preguntas sobre CADA concepto relevante.
5. Crea preguntas variadas: definición, comprensión, aplicación, análisis.
6. NO agregues texto explicativo antes o después del JSON.
7. Devuelve ÚNICAMENTE el array JSON, sin markdown, sin explicaciones.

FORMATO JSON CORRECTO:
[
  {{
    "texto": "¿Ejemplo de pregunta?",
    "alternativas": ["a) A", "b) B", "c) C", "d) D"],
    "correcta": "c"
  }}
]

NO INCLUYAS NINGÚN TEXTO FUERA DEL JSON.

BLOQUE A PROCESAR:
{block_text}
""".strip()


# ==============================================
# 🔹 FUNCIÓN PRINCIPAL PARA GENERAR PREGUNTAS
# ==============================================
def generar_preguntas_por_bloque(block_text, block_num, total_blocks, questions_goal, model=DEFAULT_MODEL):
    prompt = build_prompt(block_text, block_num, total_blocks, questions_goal)

    raw_response = call_gemini(prompt, model_name=model)

    if not raw_response:
        return []

    clean_json = extract_clean_json(raw_response)

    try:
        arr = json.loads(clean_json)
        return arr
    except:
        return []


# ==============================================
# 🔹 GENERADOR COMPLETO (USADO POR app.py)
# ==============================================
def generar_examen(texto, bloques, preguntas_por_bloque, modelo=DEFAULT_MODEL):

    todas = []

    for i, bloque in enumerate(bloques, start=1):
        preguntas = generar_preguntas_por_bloque(
            block_text=bloque,
            block_num=i,
            total_blocks=len(bloques),
            questions_goal=preguntas_por_bloque,
            model=modelo
        )

        todas.extend(preguntas)

    return todas
