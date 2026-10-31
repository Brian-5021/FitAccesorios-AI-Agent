import json
import re

from .ai_utils import MODELO_GEMINI
from .evidence import leer_memoria


HERRAMIENTAS_PERMITIDAS = {
    "investigacion",
    "contenido",
    "seo",
    "conversion",
    "prospeccion",
}


def _extraer_json(texto):
    texto = (texto or "").strip()
    texto = re.sub(r"^```(?:json)?\s*", "", texto, flags=re.I)
    texto = re.sub(r"\s*```$", "", texto)
    inicio, fin = texto.find("{"), texto.rfind("}")
    if inicio < 0 or fin <= inicio:
        raise ValueError("El planificador no devolvió un objeto JSON válido.")
    return json.loads(texto[inicio:fin + 1])


def planificar_objetivo(client, objetivo):
    """Convierte un objetivo de negocio en un plan acotado de herramientas."""
    historial = leer_memoria(3)
    contexto_historial = json.dumps(
        [{"objetivo": x.get("objetivo"), "status": x.get("status"),
          "issues": x.get("issues", [])} for x in historial],
        ensure_ascii=False
    )

    prompt = f"""
Eres el planificador de un agente comercial de FitAccesorios.
Convierte el objetivo del usuario en un plan de ejecución concreto.

OBJETIVO:
{objetivo}

HISTORIAL RECIENTE (úsalo para evitar repetir errores, no como fuente de verdad):
{contexto_historial}

HERRAMIENTAS DISPONIBLES:
- investigacion: investigación de mercado, competencia y tendencias.
- contenido: creación de contenido para redes y campañas.
- seo: auditoría de una URL o análisis SEO. Requiere que el usuario haya proporcionado una URL.
- conversion: estrategia comercial, embudo y optimización de conversión.
- prospeccion: búsqueda de empresas/clientes potenciales.

REGLAS:
1. Devuelve exclusivamente JSON válido, sin Markdown.
2. Máximo 4 pasos. Usa solo las herramientas disponibles.
3. Evita pasos redundantes. Ordena por dependencias.
4. No incluyas SEO si no hay URL en el objetivo.
5. No uses prospección si el objetivo no implica identificar prospectos.
6. Cada paso debe contener "tool" y "task".
7. "task" debe ser una instrucción autónoma, específica y ejecutable.
8. No incluyas pasos para enviar mensajes, comprar, publicar o contactar a terceros.
9. Si el objetivo es sencillo y solo necesita una herramienta, crea un solo paso.
10. Prioriza Colombia y el entrenamiento personalizado virtual, salvo que el objetivo indique otra cosa.

FORMATO EXACTO:
{{
  "objective": "objetivo resumido",
  "steps": [
    {{"tool": "investigacion", "task": "instrucción concreta"}}
  ]
}}
"""
    respuesta = client.models.generate_content(model=MODELO_GEMINI, contents=prompt)
    plan = _extraer_json(respuesta.text)

    pasos = plan.get("steps")
    if not isinstance(pasos, list) or not pasos:
        raise ValueError("El plan generado no contiene pasos ejecutables.")
    if len(pasos) > 4:
        pasos = pasos[:4]

    validados = []
    for paso in pasos:
        if not isinstance(paso, dict):
            continue
        herramienta = str(paso.get("tool", "")).strip().lower()
        tarea = str(paso.get("task", "")).strip()
        if herramienta not in HERRAMIENTAS_PERMITIDAS or not tarea:
            continue
        validados.append({"tool": herramienta, "task": tarea})

    if not validados:
        raise ValueError("El plan no contiene herramientas permitidas.")
    plan["steps"] = validados
    return plan
