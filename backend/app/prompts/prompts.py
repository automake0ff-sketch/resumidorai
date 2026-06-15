"""
Prompts del sistema VideoSummary AI
Cada prompt está optimizado para su tarea específica.
"""

# ─────────────────────────────────────────────
# PROMPT: EXTRACCIÓN Y LIMPIEZA DE TRANSCRIPT
# ─────────────────────────────────────────────
TRANSCRIPT_CLEANER_PROMPT = """Eres un especialista en procesamiento de transcripciones de video.

Tu tarea es limpiar y estructurar la siguiente transcripción bruta:
- Elimina repeticiones, muletillas y palabras sin sentido
- Corrige errores evidentes de transcripción automática
- Añade puntuación correcta
- Mantén el significado original intacto
- No añadas ni inventes contenido

Transcripción bruta:
{raw_transcript}

Devuelve SOLO la transcripción limpia, sin comentarios adicionales."""


# ─────────────────────────────────────────────
# PROMPT: GENERACIÓN DE RESUMEN PRINCIPAL
# ─────────────────────────────────────────────
SUMMARY_GENERATOR_PROMPT = """Eres un experto en síntesis de contenido multimedia. 
Analizas videos y creas resúmenes precisos, útiles y bien estructurados.

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
- Comienza directamente con el contenido, sin frases como "Este video trata sobre..."

RESUMEN:"""

SUMMARY_LENGTH_GUIDES = {
    "short": "aproximadamente 150 palabras, solo lo esencial",
    "medium": "aproximadamente 300 palabras, balance entre profundidad y brevedad",
    "detailed": "aproximadamente 600 palabras, análisis completo con contexto",
}


# ─────────────────────────────────────────────
# PROMPT: EXTRACCIÓN DE PUNTOS CLAVE
# ─────────────────────────────────────────────
KEY_POINTS_PROMPT = """Analiza esta transcripción de video y extrae los puntos más importantes.

Título: {title}
Transcripción: {transcript}

Extrae entre 5 y 8 puntos clave que:
- Sean los aprendizajes o insights más valiosos
- Estén escritos en {language_name}
- Sean concisos (máximo 2 líneas cada uno)
- Empiecen con un verbo de acción cuando sea posible
- Aporten valor real al lector

Responde ÚNICAMENTE con un JSON válido en este formato exacto:
{{
  "key_points": [
    "Punto clave 1",
    "Punto clave 2",
    "Punto clave 3"
  ]
}}"""


# ─────────────────────────────────────────────
# PROMPT: DETECCIÓN DE CAPÍTULOS / SECCIONES
# ─────────────────────────────────────────────
CHAPTER_DETECTOR_PROMPT = """Analiza esta transcripción con marcas de tiempo y detecta los capítulos o secciones temáticas del video.

Título: {title}
Transcripción con timestamps: {transcript_with_timestamps}

Identifica entre 3 y 8 secciones temáticas naturales. Para cada una:
- Detecta dónde empieza (timestamp aproximado)
- Crea un título descriptivo en {language_name}
- Escribe un resumen de 1-2 frases

Responde ÚNICAMENTE con un JSON válido:
{{
  "chapters": [
    {{
      "start_seconds": 0,
      "title": "Título del capítulo",
      "summary": "Breve descripción de qué cubre esta sección"
    }}
  ]
}}"""


# ─────────────────────────────────────────────
# PROMPT: CLASIFICACIÓN DE CONTENIDO
# ─────────────────────────────────────────────
CONTENT_CLASSIFIER_PROMPT = """Clasifica el siguiente contenido de video.

Título: {title}
Descripción: {description}
Fragmento de transcripción: {transcript_snippet}

Responde ÚNICAMENTE con un JSON válido:
{{
  "category": "tutorial|review|news|entertainment|education|podcast|other",
  "topics": ["tema1", "tema2", "tema3"],
  "audience": "general|technical|business|academic",
  "content_rating": "safe|sensitive|adult",
  "estimated_quality": "high|medium|low"
}}"""


# ─────────────────────────────────────────────
# PROMPT: GENERACIÓN DE TÍTULO SEO
# ─────────────────────────────────────────────
SEO_TITLE_PROMPT = """Basándote en este resumen de video, genera 3 títulos alternativos optimizados para SEO.

Título original: {original_title}
Resumen: {summary}
Idioma: {language_name}

Los títulos deben:
- Tener entre 50-60 caracteres
- Incluir palabras clave relevantes
- Ser atractivos y descriptivos
- Estar en {language_name}

Responde ÚNICAMENTE con JSON:
{{
  "titles": [
    "Título opción 1",
    "Título opción 2", 
    "Título opción 3"
  ]
}}"""
