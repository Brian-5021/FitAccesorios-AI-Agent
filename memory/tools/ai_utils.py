import time


MODELO_GEMINI = "gemini-3.5-flash-lite"


def generar_con_reintentos(client, instrucciones, intentos=3):
    """
    Ejecuta una solicitud a Gemini con reintentos ante fallos temporales.
    Espera 2, 4 y 6 segundos entre intentos.
    """
    ultimo_error = None

    for intento in range(1, intentos + 1):
        try:
            respuesta = client.models.generate_content(
                model=MODELO_GEMINI,
                contents=instrucciones
            )
            texto = (respuesta.text or "").strip()

            if not texto:
                raise RuntimeError("Gemini devolvió una respuesta vacía.")

            return texto

        except Exception as error:
            ultimo_error = error
            print(
                f"Gemini no respondió (intento {intento}/{intentos}): "
                f"{error}"
            )

            if intento < intentos:
                espera = intento * 2
                print(f"Reintentando en {espera} segundos...")
                time.sleep(espera)

    raise RuntimeError(
        f"No fue posible obtener respuesta de Gemini tras "
        f"{intentos} intentos. Último error: {ultimo_error}"
    )


def guardar_informe_pdf(ruta, titulo, contenido):
    from xml.sax.saxutils import escape
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

    documento = SimpleDocTemplate(
        str(ruta),
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm
    )

    estilos = getSampleStyleSheet()
    estilo_titulo = ParagraphStyle(
        "TituloFit",
        parent=estilos["Title"],
        textColor=colors.HexColor("#9E1B1B"),
        spaceAfter=18
    )
    estilo_h2 = ParagraphStyle(
        "H2Fit",
        parent=estilos["Heading2"],
        textColor=colors.HexColor("#9E1B1B"),
        spaceBefore=12,
        spaceAfter=7
    )
    estilo_texto = ParagraphStyle(
        "TextoFit",
        parent=estilos["BodyText"],
        leading=14,
        spaceAfter=7
    )

    elementos = [Paragraph(escape(titulo), estilo_titulo)]

    for linea in contenido.splitlines():
        linea = linea.strip()
        if not linea:
            elementos.append(Spacer(1, 5))
        elif linea.startswith("## ") or linea.startswith("### "):
            elementos.append(Paragraph(escape(linea.lstrip("# ")), estilo_h2))
        elif linea.startswith("# "):
            elementos.append(Paragraph(escape(linea[2:]), estilo_h2))
        elif linea.startswith("- ") or linea.startswith("* "):
            elementos.append(Paragraph("• " + escape(linea[2:]), estilo_texto))
        else:
            elementos.append(Paragraph(escape(linea), estilo_texto))

    documento.build(elementos)
