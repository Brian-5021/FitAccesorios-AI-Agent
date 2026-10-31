
from ddgs import DDGS
from ddgs.exceptions import DDGSException
from google import genai
from dotenv import load_dotenv
from .web_reader import leer_pagina

import os
from pathlib import Path
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm
from xml.sax.saxutils import escape


load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def buscar_web(consultas):
    resultados_unicos = {}

    try:
        with DDGS() as buscador:
            for consulta in consultas:
                try:
                    resultados = buscador.text(
                        consulta,
                        region="co-es",
                        max_results=5
                    )

                    for resultado in resultados:
                        url = resultado.get("href")

                        if url and url not in resultados_unicos:
                            resultados_unicos[url] = resultado

                except DDGSException as error:
                    print(f"Consulta fallida: {consulta}")
                    print(f"Detalle: {error}")
                    continue

    except DDGSException as error:
        print(f"Error general del buscador: {error}")

    return list(resultados_unicos.values())


def guardar_informe(pregunta, contenido):
    carpeta_reports = Path(__file__).parent.parent / "reports"
    carpeta_reports.mkdir(exist_ok=True)

    fecha = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    archivo = carpeta_reports / f"investigacion_{fecha}.md"

    contenido_archivo = f"""# Investigación FitAccesorios

**Fecha:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

**Consulta:** {pregunta}

---

{contenido}
"""

    archivo.write_text(contenido_archivo, encoding="utf-8")

    print(f"\nInforme Markdown guardado en: {archivo}")


def guardar_pdf(pregunta, contenido):
    carpeta_reports = Path(__file__).parent.parent / "reports"
    carpeta_reports.mkdir(exist_ok=True)

    fecha = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    archivo = carpeta_reports / f"investigacion_{fecha}.pdf"

    documento = SimpleDocTemplate(
        str(archivo),
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm
    )

    estilos = getSampleStyleSheet()

    titulo = ParagraphStyle(
        "TituloFit",
        parent=estilos["Title"],
        textColor=colors.HexColor("#9E1B1B"),
        fontSize=20,
        spaceAfter=20
    )

    subtitulo = ParagraphStyle(
        "SubtituloFit",
        parent=estilos["Heading2"],
        textColor=colors.HexColor("#9E1B1B"),
        spaceBefore=12,
        spaceAfter=8
    )

    texto = ParagraphStyle(
        "TextoFit",
        parent=estilos["BodyText"],
        leading=14,
        spaceAfter=8
    )

    elementos = [
        Paragraph("Investigación FitAccesorios", titulo),
        Paragraph(
            f"<b>Consulta:</b> {escape(pregunta)}",
            texto
        ),
        Spacer(1, 15)
    ]

    for linea in contenido.splitlines():
        linea = linea.strip()

        if not linea:
            elementos.append(Spacer(1, 6))

        elif linea.startswith("### "):
            elementos.append(
                Paragraph(escape(linea[4:]), subtitulo)
            )

        elif linea.startswith("## "):
            elementos.append(
                Paragraph(escape(linea[3:]), subtitulo)
            )

        elif linea.startswith("# "):
            elementos.append(
                Paragraph(escape(linea[2:]), titulo)
            )

        elif linea.startswith("- "):
            elementos.append(
                Paragraph(f"• {escape(linea[2:])}", texto)
            )

        else:
            elementos.append(
                Paragraph(escape(linea), texto)
            )

    documento.build(elementos)

    print(f"PDF generado correctamente: {archivo}")


def investigar(pregunta):
    consultas = [
        "empresas entrenamiento personal virtual Colombia",
        "entrenador personal online Colombia planes precios",
        "asesoría entrenamiento personalizado online Colombia"
    ]

    print("\nBuscando información en internet...")

    resultados = buscar_web(consultas)

    if not resultados:
        print("No fue posible obtener resultados web.")
        print("Intenta nuevamente más tarde.")
        return

    print(f"Resultados encontrados: {len(resultados)}")
    print("\nExtrayendo contenido de las páginas...")

    paginas = []

    for resultado in resultados:
        url = resultado.get("href")

        if not url:
            continue

        pagina = leer_pagina(url)

        if "contenido" in pagina:
            paginas.append(pagina)

    if not paginas:
        print("No fue posible extraer contenido de las páginas.")
        return

    contexto = ""

    for pagina in paginas:
        contexto += f"""
FUENTE: {pagina['url']}
TÍTULO: {pagina['titulo']}
CONTENIDO:
{pagina['contenido']}

-------------------------
"""

    print(f"Páginas analizadas: {len(paginas)}")
    print("\nAnalizando información con Gemini...")

    respuesta = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=f"""
Eres el analista comercial de FitAccesorios.

CONTEXTO:
FitAccesorios opera en Colombia y tiene dos líneas:
1. Entrenamiento personalizado virtual.
2. Venta de accesorios fitness.

La prioridad comercial es conseguir clientes
para el entrenamiento personalizado.

SOLICITUD:
{pregunta}

INFORMACIÓN EXTRAÍDA DE PÁGINAS WEB:
{contexto}

INSTRUCCIONES:

1. Identifica empresas que realmente ofrezcan
entrenamiento personal virtual en Colombia.
2. Clasifica cada empresa como competidor directo,
indirecto o referencia de mercado.
3. Extrae precios exactamente como aparecen.
4. No inventes información faltante.
5. Identifica servicios, modalidades, frecuencia,
seguimiento y canales de comunicación.
6. Incluye la URL que respalda cada dato.
7. No confundas blogs o directorios con competidores.
8. Diferencia hechos de recomendaciones.
9. Finaliza con oportunidades para FitAccesorios.

FORMATO:

- Resumen ejecutivo.
- Competidores directos.
- Competidores indirectos.
- Tabla comparativa de precios.
- Diferenciadores.
- Oportunidades comerciales.
- Limitaciones de la investigación.
"""
    )

    informe = respuesta.text

    if not informe:
        print("Gemini no devolvió contenido para el informe.")
        return

    print("\nANÁLISIS DE FITACCESORIOS\n")
    print(informe)

    guardar_informe(pregunta, informe)
    guardar_pdf(pregunta, informe)


if __name__ == "__main__":
    pregunta = input("¿Qué quieres investigar?: ")
    investigar(pregunta)
