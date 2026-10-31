from datetime import datetime
from pathlib import Path

from .research import buscar_web
from .web_reader import leer_pagina
from .ai_utils import generar_con_reintentos, guardar_informe_pdf


BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = BASE_DIR / "reports"


def prospectar_empresas(client, pregunta):
    print("\nIniciando prospección comercial...")

    consultas = [
    "gimnasios Medellín Colombia",
    "estudios de entrenamiento personal Medellín",
    "centros deportivos Medellín Antioquia",
    "distribuidores accesorios fitness Medellín",
    "tiendas implementos deportivos Medellín",
    "empresas bienestar corporativo Medellín",
    "proveedores equipos accesorios gimnasio Medellín",
    "academias fitness Medellín Colombia"
]

    print("\nBuscando empresas potenciales...")
    resultados = buscar_web(consultas)

    if not resultados:
        print("No se encontraron resultados web.")
        return

    paginas = []
    urls_vistas = set()

    for resultado in resultados:
        url = resultado.get("href") or resultado.get("url")
        if not url or url in urls_vistas:
            continue
        urls_vistas.add(url)

        titulo_busqueda = resultado.get("title", "")
        resumen_busqueda = resultado.get("body", "")

        try:
            pagina = leer_pagina(url)
            contenido = pagina.get("contenido", "")

            paginas.append({
                "url": url,
                "titulo": pagina.get("titulo") or titulo_busqueda,
                "resumen_busqueda": resumen_busqueda,
                "contenido": contenido[:4500]
            })
        except Exception as error:
            paginas.append({
                "url": url,
                "titulo": titulo_busqueda,
                "resumen_busqueda": resumen_busqueda,
                "contenido": f"No fue posible extraer la página: {error}"
            })

    if not paginas:
        print("No fue posible obtener fuentes para analizar.")
        return

    contexto = "\n\n".join(
        f"""FUENTE {i}
URL: {p['url']}
TÍTULO: {p['titulo']}
RESUMEN DEL BUSCADOR: {p['resumen_busqueda']}
CONTENIDO EXTRAÍDO:
{p['contenido']}
"""
        for i, p in enumerate(paginas, start=1)
    )

    instrucciones = f"""
Eres un analista de prospección B2B para FitAccesorios, Colombia.

SOLICITUD:
{pregunta}

FUENTES RECOLECTADAS:
{contexto}

OBJETIVO:
Identificar prospectos empresariales y oportunidades posibles para:
- Venta o dotación de accesorios fitness.
- Alianzas comerciales.
- Programas de entrenamiento virtual o bienestar corporativo.

REGLAS DE EVIDENCIA OBLIGATORIAS:
1. Usa únicamente empresas que aparezcan identificadas en las fuentes.
2. Cada empresa debe incluir su URL fuente exacta.
3. No inventes sucursales, direcciones, teléfonos, correos,
   nombres de empleados, presupuestos ni necesidades de compra.
4. Solo incluye datos de contacto si aparecen literalmente
   en el contenido de una fuente; cita esa URL junto al dato.
5. Si un dato no aparece, escribe "No encontrado en las fuentes".
6. No conviertas el tamaño o fama de una cadena en evidencia
   de que necesita comprar o está interesada.
7. El potencial alto/medio/bajo es una hipótesis comercial,
   no un hecho. Explica la razón y la evidencia disponible.
8. Si hay menos empresas verificables que las solicitadas,
   presenta solo las verificables; no rellenes la lista.
9. No afirmes que se verificó la vigencia de teléfonos o direcciones.
10. Separa claramente HECHOS DE FUENTE e INFERENCIAS COMERCIALES.

FORMATO:
- Resumen ejecutivo y cantidad de fuentes consultadas.
- Tabla de prospectos verificables: empresa, tipo, oportunidad,
  potencial hipotético, evidencia y URL.
- Ficha individual de cada prospecto.
- Contactos publicados y su fuente, o "No encontrado".
- Mensaje de primer contacto adaptable, sin afirmar relaciones previas.
- Próximas acciones de validación humana.
- Limitaciones.

No uses información externa a las fuentes proporcionadas.
Redacta en español.
"""

    try:
        print(f"\nFuentes recopiladas: {len(paginas)}")
        print("Evaluando prospectos con Gemini...")
        informe = generar_con_reintentos(client, instrucciones)

        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
        md = REPORTS_DIR / f"prospeccion_{fecha}.md"
        pdf = REPORTS_DIR / f"prospeccion_{fecha}.pdf"

        md.write_text(
            f"# Prospección comercial FitAccesorios\n\n"
            f"Fecha: {datetime.now():%Y-%m-%d %H:%M:%S}\n\n"
            f"Solicitud: {pregunta}\n\n"
            f"Fuentes consultadas: {len(paginas)}\n\n---\n\n{informe}",
            encoding="utf-8"
        )
        guardar_informe_pdf(pdf, "Prospección comercial FitAccesorios", informe)

        print("\nINFORME DE PROSPECCIÓN\n")
        print(informe)
        print(f"\nInforme Markdown: {md}")
        print(f"Informe PDF: {pdf}")

    except Exception as error:
        print(f"\nNo se pudo completar la prospección: {error}")
