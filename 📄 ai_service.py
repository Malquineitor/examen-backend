import requests
import os

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

MODEL = "gemini-1.5-flash-latest"
ENDPOINT = f"https://generativelanguage.googleapis.com/v1/models/{MODEL}:generateContent?key={GEMINI_API_KEY}"

def call_gemini(prompt: str):
    if not GEMINI_API_KEY:
        return {"error": "GEMINI_API_KEY not configured"}

    body = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }

    response = requests.post(ENDPOINT, json=body)

    try:
        data = response.json()
    except:
        return {"error": "Invalid JSON from Gemini"}

    if response.status_code != 200:
        return {
            "error": "Gemini API error",
            "status": response.status_code,
            "details": data
        }

    # Extract the text safely
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except:
        text = None

    return {
        "success": True,
        "raw": data,
        "text": text
    }

def generate_test(text: str, num_questions: int = 20):
    prompt = f"""
Genera un examen de {num_questions} preguntas basado en el siguiente documento:

{text}

Formato JSON:
{{
  "title": "",
  "questions": [
    {{
      "question": "",
      "options": ["","", "", ""],
      "answer": ""
    }}
  ]
}}
"""

    result = call_gemini(prompt)
    return result
