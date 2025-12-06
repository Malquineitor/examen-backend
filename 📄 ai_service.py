"""
ai_service.py – Versión COMPLETA (2025)
-------------------------------------
Replica EXACTAMENTE la lógica de generación de tests de la app Android:

✔ Construcción avanzada de prompts
✔ Limpieza profunda del texto
✔ Corrección de JSON incompleto
✔ Extracción estable del array JSON
✔ Reordenar alternativas aleatoriamente
✔ Normalización de campos
✔ Reintentos con tolerancia a errores
✔ Manejo de modelos Gemini 2.0 / 2.5 / Flash-Lite
"""

import os
import json
import re
import time
import random
import requests


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DEFAULT_MODEL = "gemini-2.0-flash-lite"


# ======================================================
# 🔥 1. LLAMAR A GEMINI CON REINTENTOS
# ======================================================
def call_gemini(prompt: str, model_name: str = DEFAULT_MODEL, retries: int = 2):
    if not GEMINI_API_KEY:
        raise Exception("GEMINI_API_KEY no configurada")

    endpoint = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model_name}:generateContent?key={GEMINI_API_KEY}"
    )

    payload = {
        "contents": [
            {"parts": [{"text": prompt}]}
        ]
    }

    for intento in range(retries):
        try:
            r = requests.post(endpoint, json=payload, timeout=60)
            data = r.json()

            if r.status_code == 200:
                try:
                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                    if text:
                        return text
                except:
                    pass

        except Exception as e:
            print(f"[Gemini Error] Intento {intento+1}: {e}")

        time.sleep(1.1)

    return None


# ======================================================
# 🔥 2. LIMPIAR RESPUESTA Y EXTRAER SOLO EL JSON
# ======================================================
def extract_clean_json(text):
    if not text:
        return "[]"

    # Remove markdown
    text = text.replace("```json", "").replace("```", "")
    text = text.strip()

    # Search for JSON array
    start = text.find("[")
    end = text.rfind("]")

    if start == -1 or end == -1:
        return "[]"

    return text[start:end+1]


# ======================================================
# 🔥 3. CORREGIR JSON INCOMPLETO
# ======================================================
def fix_json(json_text):
    """
    Igual que en la app: intenta reparar JSON parcial
    """
    # Remove emojis
    json_text = re.sub(r"[\U00010000-\U0010ffff]", "", json_text)

    # Fix missing closing brackets
    opens = json_text.count("[")
    closes = json_text.count("]")
    if closes < opens:
        json_text += "]" * (opens - closes)

    return json_text


# ======================================================
# 🔥 4. NORMALIZAR CAMPOS (igual a la app)
# ======================================================
def normalize_question(raw):
    """
    Acepta variantes: pregunta/texto, alternativas/opciones, correcta/resp_correcta
    """
    texto = raw.get("texto") or raw.get("pregunta") or ""
    alternativas = raw.get("alternativas") or raw.get("opciones") or []
    correcta = raw.get("correcta") or raw.get("respuesta_correcta") or ""

    if not texto or not alternativas or not correcta:
        return None

    return {
        "texto": texto.strip(),
        "alternativas": alternativas,
        "correcta": correcta.lower()
    }


# ======================================================
# 🔥 5. REORDENAR ALTERNATIVAS (igual que Android)
# ======================================================
def shuffle_alternatives(question):
    opciones = question["alternativas"]
    correcta = question["correcta"]

    # Identificar texto correcto
    texto_correcto = None
    for opt in opciones:
        if opt.lower().startswith(correcta):
            texto_correcto = opt
            break

    random.shuffle(opciones)

    nueva_correcta = None
    for opt in opciones:
        if opt == texto_correcto:
            letra = opt.split(")")[0].lower()
            nueva_correcta = letra

    question["alternativas"] = opciones
    question["correcta"] = nueva_correcta

    return question


# ======================================================
# 🔥 6. CONSTRUIR PROMPT COMPLETO
# ======================================================
def build_prompt(bloque, num, total, preguntas):
    return f"""
Eres un generador de preguntas tipo test. 
Tu tarea es crear preguntas basadas únicamente en el siguiente bloque de texto.

CONTEXTO:
- Este es el bloque {num} de {total}.
- Evita repetir información generada anteriormente.

INSTRUCCIONES CRÍTICAS:
1. Genera al menos {preguntas} preguntas.
2. EXACTAMENTE 4 alternativas: a, b, c, d.
3. Solo UNA alternativa correcta.
4. No inventes datos.
5. NO agregues texto fuera del JSON.
6. SOLO devuelve el ARRAY JSON.

FORMATO:
[
  {{
    "texto": "",
    "alternativas": ["a) ...", "b) ...", "c) ...", "d) ..."],
    "correcta": "b"
  }}
]

BLOQUE:
{bloque}
""".strip()


# ======================================================
# 🔥 7. GENERAR PREGUNTAS POR BLOQUE
# ======================================================
def generar_preguntas_por_bloque(block_text, block_num, total_blocks, questions_goal, model=DEFAULT_MODEL):

    prompt = build_prompt(block_text, block_num, total_blocks, questions_goal)
    raw = call_gemini(prompt, model_name=model)

    if not raw:
        return []

    clean = extract_clean_json(raw)
    fixed = fix_json(clean)

    try:
        arr = json.loads(fixed)
    except:
        return []

    final = []
    for q in arr:
        qn = normalize_question(q)
        if qn:
            qn = shuffle_alternatives(qn)
            final.append(qn)

    return final


# ======================================================
# 🔥 8. GENERAR EXAMEN COMPLETO (para app.py)
# ======================================================
def generar_examen(texto, bloques, preguntas_por_bloque, modelo=DEFAULT_MODEL):
    todo = []

    for i, bloque in enumerate(bloques, start=1):
        preguntas = generar_preguntas_por_bloque(
            block_text=bloque,
            block_num=i,
            total_blocks=len(bloques),
            questions_goal=preguntas_por_bloque,
            model=modelo
        )

        todo.extend(preguntas)

    return todo
