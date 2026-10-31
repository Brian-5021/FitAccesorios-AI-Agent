
from google import genai


def clasificar_tarea(client, pregunta):

    respuesta = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=f"""
Eres el clasificador de tareas de un agente comercial
especializado en FitAccesorios, una empresa colombiana.

Debes identificar qué tipo de tarea necesita ejecutar
el agente según la solicitud del usuario.

CATEGORÍAS DISPONIBLES:

- investigacion: investigación de mercado, competidores,
  tendencias, precios y análisis de empresas.

- contenido: creación de publicaciones, ideas para Instagram,
  Reels, campañas, copies y estrategias de redes sociales.

- seo: posicionamiento web, palabras clave, contenidos SEO
  y auditorías de posicionamiento.

- conversion: optimización de ventas, páginas de servicios,
  embudos comerciales y captación de clientes.

- prospeccion: identificación de clientes potenciales,
  empresas, contactos y oportunidades comerciales.

- general: preguntas generales sobre FitAccesorios
  que no correspondan a las categorías anteriores.

SOLICITUD DEL USUARIO:
{pregunta}

INSTRUCCIONES:

1. Selecciona únicamente una categoría.
2. No ejecutes la tarea.
3. No expliques tu decisión.
4. Devuelve únicamente el nombre de la categoría.
"""
    )

    tarea = respuesta.text.strip().lower()

    categorias = [
        "investigacion",
        "contenido",
        "seo",
        "conversion",
        "prospeccion",
        "general"
    ]

    if tarea not in categorias:
        return "general"

    return tarea
