
from .research import investigar
from .content import generar_contenido


def ejecutar_tarea(client, tarea, pregunta):

    print(f"\nEjecutando tarea: {tarea}")

    if tarea == "investigacion":
        investigar(pregunta)

    elif tarea == "contenido":
        generar_contenido(client, pregunta)

    elif tarea == "seo":
        print("El módulo SEO todavía está pendiente.")

    elif tarea == "conversion":
        print("El módulo de conversión todavía está pendiente.")

    elif tarea == "prospeccion":
        print("El módulo de prospección todavía está pendiente.")

    elif tarea == "general":
        print("La consulta será atendida por el asistente general.")

    else:
        print("No se reconoce el tipo de tarea.")
