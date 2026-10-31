
import re
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from datetime import datetime


REPORTS_DIR = Path(__file__).parent.parent / "reports"


def extraer_url(pregunta):
    coincidencia = re.search(
        r"https?://[^\s]+",
        pregunta
    )

    if not coincidencia:
        raise ValueError(
            "Incluye la URL completa del sitio que quieres analizar."
        )

    url = coincidencia.group(0).rstrip(".,);]")

    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("La URL no es válida.")

    return url


def analizar_elementos_seo(url):
    encabezados = {
        "User-Agent": "Mozilla/5.0 FitAccesoriosSEO/1.0"
    }

    respuesta = requests.get(
        url,
        headers=encabezados,
        timeout=20
    )

    respuesta.raise_for_status()

    soup = BeautifulSoup(respuesta.text, "html.parser")

    def obtener_meta(nombre, atributo="name"):
        elemento = soup.find(
            "meta",
            attrs={atributo: nombre}
        )
        return elemento.get("content", "") if elemento else ""

    titulo = soup.title.get_text(strip=True) if soup.title else ""

    descripcion = obtener_meta("description")

    canonical = soup.find("link", rel="canonical")
    canonical = canonical.get("href", "") if canonical else ""

    encabezados_html = {}

    for nivel in range(1, 7):
        etiquetas = soup.find_all(f"h{nivel}")
        encabezados_html[f"H{nivel}"] = [
            etiqueta.get_text(" ", strip=True)
            for etiqueta in etiquetas
        ]

    imagenes = soup.find_all("img")

    imagenes_sin_alt = [
        imagen.get("src", "")
        for imagen in imagenes
        if not imagen.get("alt", "").strip()
    ]

    enlaces = soup.find_all("a", href=True)

    robots = obtener_meta("robots")
    viewport = obtener_meta("viewport")
    og_title = obtener_meta("og:title", "property")
    og_description = obtener_meta("og:description", "property")

    texto = soup.get_text(" ", strip=True)
    palabras = len(texto.split())

    return {
        "url": url,
        "status_code": respuesta.status_code,
        "title": titulo,
        "title_length": len(titulo),
        "meta_description": descripcion,
        "meta_description_length": len(descripcion),
        "canonical": canonical,
        "headings": encabezados_html,
        "images_total": len(imagenes),
        "images_without_alt": imagenes_sin_alt,
        "links_total": len(enlaces),
        "robots": robots,
        "viewport": viewport,
        "og_title": og_title,
        "og_description": og_description,
        "word_count": palabras
    }


def generar_reporte_seo(client, datos):
    respuesta = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=f"""
Eres un especialista SEO técnico y estratégico.

Analiza los siguientes datos reales extraídos de una página web.

DATOS:
{datos}

CONTEXTO:
El negocio es FitAccesorios, cuya prioridad comercial es Colombia.
Sus líneas son entrenamiento personalizado virtual y accesorios fitness.


INSTRUCCIONES:
1. No inventes datos que no estén en el análisis.
2. Diferencia problemas confirmados, indicios y recomendaciones.
3. Evalúa SEO técnico y SEO on-page.
4. Revisa title, metadescripción, encabezados, imágenes,
   canonical, robots, viewport y Open Graph.
5. No clasifiques automáticamente un contenido como Thin Content
   por tener pocas palabras. Evalúa su profundidad y utilidad.
6. No consideres que una cantidad elevada de enlaces es un
   problema SEO por sí sola. Evalúa su relevancia y contexto.
7. No uses límites rígidos de caracteres para afirmar que
   un título o descripción incumple las directrices de Google.
8. No afirmes que una página está posicionada en Google:
   estos datos no incluyen rankings ni Search Console.
9. No inventes precios de competidores ni datos de mercado.
10. Prioriza las mejoras por impacto: alto, medio o bajo.
11. Explica cómo corregir cada problema.
12. Finaliza con un plan de acción ordenado.

FORMATO:
- Resumen ejecutivo.
- Hallazgos técnicos.
- SEO on-page.
- Problemas confirmados.
- Indicios y oportunidades.
- Plan de acción priorizado.
- Limitaciones del análisis.

"""
    )

    return respuesta.text or "Gemini no generó el informe."


def guardar_reporte(url, contenido):
    REPORTS_DIR.mkdir(exist_ok=True)

    fecha = datetime.now().strftime("%Y%m%d_%H%M%S")

    archivo = REPORTS_DIR / f"seo_{fecha}.md"

    archivo.write_text(
        f"# Informe SEO\n\n"
        f"**URL analizada:** {url}\n\n"
        f"**Fecha:** {datetime.now():%Y-%m-%d %H:%M:%S}\n\n"
        f"---\n\n{contenido}",
        encoding="utf-8"
    )

    print(f"\nInforme guardado en: {archivo}")


def analizar_seo(client, pregunta):
    print("\nIniciando análisis SEO...")

    url = extraer_url(pregunta)

    print(f"Analizando: {url}")

    datos = analizar_elementos_seo(url)

    print("\nDatos SEO extraídos correctamente.")
    print("Generando diagnóstico con Gemini...")

    informe = generar_reporte_seo(client, datos)

    print("\nINFORME SEO FITACCESORIOS\n")
    print(informe)

    guardar_reporte(url, informe)
