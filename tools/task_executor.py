
from .research import investigar
from .content import generar_contenido
from .seo import analizar_seo
from .conversion import analizar_conversion
from .prospeccion import prospectar_empresas


def ejecutar_tarea(client, tarea, pregunta):
    print(f"\nEjecutando tarea: {tarea}")

    try:
        if tarea == "investigacion":
            investigar(pregunta)

        elif tarea == "contenido":
            generar_contenido(client, pregunta)

        elif tarea == "seo":
            analizar_seo(client, pregunta)

        elif tarea == "conversion":
            analizar_conversion(client, pregunta)

        elif tarea == "prospeccion":
            prospectar_empresas(client, pregunta)

        elif tarea == "general":
            respuesta = client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=f"""
                Eres el asistente general de FitAccesorios.
                Utiliza el contexto comercial cuando corresponda.

                Consulta del usuario:
                {pregunta}
                """
            )
            print(respuesta.text or "No se obtuvo respuesta.")

        else:
            print("No se reconoce el tipo de tarea.")

    except Exception as error:
        print(f"\nError ejecutando la tarea: {error}")
