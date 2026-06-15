"""
Prompts del sistema ResumidorAI
"""

TRANSCRIPT_CLEANER_PROMPT = """Eres un especialista en procesamiento de transcripciones de video.

Limpia y estructura la siguiente transcripción bruta:
- Elimina repeticiones, muletillas y palabras sin sentido
- Corrige errores evidentes de transcripción automática
- Añade puntuación correcta
- Mantén el significado original intacto
- No añadas ni inventes contenido

Transcripción bruta:
{raw_transcript}

Devuelve SOLO la transcripción limpia, sin comentarios adicionales."""


SUMMARY_GENERATOR_PROMPT = """Eres un experto en síntesis de contenido multimedia.

INFORMACIÓN DEL VIDEO:
- Título: {title}
- Duración: {duration}
- Idioma objetivo: {language}

TRANSCRIPCIÓN:
{transcript}

INSTRUCCIONES:
- Crea un resumen de longitud {length}: {length_guide}
- Idioma del resumen: {language_name}
- Captura la idea principal, argumentos clave y conclusiones
- Usa lenguaje claro y accesible
- Estructura el resumen en párrafos coherentes
- NO uses listas con viñetas en el resumen principal
- Comienza directamente con el contenido

RESUMEN:"""

SUMMARY_LENGTH_GUIDES = {
    "short": "aproximadamente 150 palabras, solo lo esencial",
    "medium": "aproximadamente 300 palabras, balance entre profundidad y brevedad",
    "detailed": "aproximadamente 600 palabras, análisis completo con contexto",
}


KEY_POINTS_PROMPT = """Analiza esta transcripción y extrae los puntos más importantes.

Título: {title}
Transcripción: {transcript}

Extrae entre 5 y 8 puntos clave en {language_name}.
- Sean los insights más valiosos
- Concisos (máximo 2 líneas cada uno)
- Empiecen con verbo de acción cuando sea posible

Responde ÚNICAMENTE con JSON válido:
{{
  "key_points": [
    "Punto clave 1",
    "Punto clave 2"
  ]
}}"""


CHAPTER_DETECTOR_PROMPT = """Analiza esta transcripción con timestamps y detecta los capítulos temáticos.

Título: {title}
Transcripción: {transcript_with_timestamps}

Identifica entre 3 y 8 secciones temáticas. Para cada una crea un título en {language_name}.

Responde ÚNICAMENTE con JSON válido:
{{
  "chapters": [
    {{
      "start_seconds": 0,
      "title": "Título del capítulo",
      "summary": "Breve descripción de 1-2 frases"
    }}
  ]
}}"""
