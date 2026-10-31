from datetime import datetime
from pathlib import Path

from .content import cargar_informacion_comercial
from .ai_utils import generar_con_reintentos, guardar_informe_pdf


BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = BASE_DIR / "reports"


def analizar_conversion(client, pregunta):
    print("\nIniciando análisis de conversión...")

    informacion = cargar_informacion_comercial()
    if not informacion.strip():
        print("No se encontró información comercial.")
        return

    instrucciones = f"""
Actúa como consultor senior de CRO y estrategia comercial para FitAccesorios.

PRIORIDAD:
Captar clientes para entrenamiento personalizado virtual en Colombia.
La venta de accesorios es complementaria.

INFORMACIÓN COMERCIAL AUTORIZADA:
{informacion}

SOLICITUD:
{pregunta}

Entrega un plan accionable que incluya:
1. Diagnóstico de la oportunidad y supuestos que deban validarse.
2. Perfil de cliente potencial, diferenciando hechos e hipótesis.
3. Propuesta de valor sin inventar beneficios.
4. Embudo: captación, contacto, calificación, seguimiento y cierre.
5. Estrategia de WhatsApp.
6. Cinco mensajes listos para usar en distintas etapas.
7. Objeciones y respuestas.
8. Recomendaciones para landing page y llamadas a la acción.
9. KPI a medir, con fórmulas; no inventes benchmarks.
10. Plan de ejecución de 30 días.

REGLAS:
- No inventes precios, descuentos, características, testimonios,
  credenciales, resultados ni condiciones.
- El Plan Inicio cuesta $89.900 COP y su duración se indica como
  "desde un mes"; no lo describas como suscripción mensual recurrente.
- No atribuyas plataforma online, seguimiento semanal, corrección
  de técnica ni ajustes progresivos al Plan Inicio.
- No atribuyas credenciales de nutricionista o profesional sanitario
  si no están documentadas.
- No inventes nombres ni precios de kits o accesorios.
- No inventes porcentajes ni condiciones del descuento por compra conjunta.
- No describas como flexible o sin horarios una condición que no esté
  expresamente documentada para el plan correspondiente.
- No prometas resultados físicos.
- No afirmes que una táctica garantizará ventas.
- Prioriza acciones prácticas y de bajo costo.
- Escribe en español colombiano claro.
- Distingue recomendaciones de información documentada.
"""

    try:
        print("Generando estrategia con Gemini...")
        informe = generar_con_reintentos(client, instrucciones)

        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
        md = REPORTS_DIR / f"conversion_{fecha}.md"
        pdf = REPORTS_DIR / f"conversion_{fecha}.pdf"

        md.write_text(
            f"# Estrategia de conversión FitAccesorios\n\n"
            f"Fecha: {datetime.now():%Y-%m-%d %H:%M:%S}\n\n"
            f"Solicitud: {pregunta}\n\n---\n\n{informe}",
            encoding="utf-8"
        )
        guardar_informe_pdf(pdf, "Estrategia de conversión FitAccesorios", informe)

        print("\nESTRATEGIA DE CONVERSIÓN\n")
        print(informe)
        print(f"\nInforme Markdown: {md}")
        print(f"Informe PDF: {pdf}")

    except Exception as error:
        print(f"\nNo se pudo completar el análisis de conversión: {error}")
