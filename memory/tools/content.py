
from pathlib import Path
from datetime import datetime
from xml.sax.saxutils import escape
import json
import re

from pypdf import PdfReader

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
)


# ============================================================
# CONFIGURACIÓN
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = BASE_DIR / "knowledge"
REPORTS_DIR = BASE_DIR / "reports"

MODELO_GEMINI = "gemini-3.5-flash-lite"


# ============================================================
# CARGAR INFORMACIÓN COMERCIAL
# ============================================================

def cargar_informacion_comercial():
    """
    Carga los documentos de conocimiento de FitAccesorios.
    """

    archivos = [
        "01_PERFIL_EMPRESA.md",
        "02_SERVICIOS_Y_OFERTA.md",
        "03_Informe_Ejecutivo_FitAccesorios_Oportunidades_Internacionales.pdf",
        "04_CANAL_DIGITAL_FITACCESORIOS.md",
        "05_DETALLES_ENTRENAMIENTO.md",
    ]

    informacion = []

    for nombre_archivo in archivos:
        ruta = KNOWLEDGE_DIR / nombre_archivo

        if not ruta.exists():
            print(f"Advertencia: no se encontró {nombre_archivo}.")
            continue

        try:
            if ruta.suffix.lower() == ".pdf":
                lector = PdfReader(str(ruta))
                contenido = "\n".join(
                    pagina.extract_text() or ""
                    for pagina in lector.pages
                )
            else:
                contenido = ruta.read_text(encoding="utf-8")

            informacion.append(
                f"\n\nDOCUMENTO: {nombre_archivo}\n{contenido}"
            )

        except Exception as error:
            print(
                f"No fue posible leer {nombre_archivo}: {error}"
            )

    return "\n".join(informacion)


# ============================================================
# VALIDACIÓN DETERMINISTA CON PYTHON
# ============================================================

def validar_reglas_python(contenido):
    """
    Comprueba reglas comerciales que no deben depender
    de la interpretación del modelo de IA.
    """

    texto = contenido.lower()

    errores = []
    advertencias = []

    # --------------------------------------------------------
    # 1. PROMESAS COMERCIALES NO AUTORIZADAS
    # --------------------------------------------------------

    expresiones_prohibidas = [
        "resultados garantizados",
        "resultados garantizados en",
        "garantizamos resultados",
        "garantizamos que lograrás",
        "eliminamos todas las lesiones",
        "sin riesgo de lesiones",
        "resultados asegurados",
    ]

    for expresion in expresiones_prohibidas:
        if expresion in texto:
            errores.append(
                f"Promesa comercial no autorizada: '{expresion}'"
            )

    # --------------------------------------------------------
    # 2. PRECIO DEL PLAN INICIO
    # --------------------------------------------------------

    patron_precio = (
        r"\$?\s*89[.,]900"
        r"(?:\s*cop)?"
        r"\s*(?:al\s+mes|mensual(?:es)?)\b"
    )

    if re.search(patron_precio, texto, re.IGNORECASE):
        errores.append(
            "El precio del Plan Inicio se presenta como "
            "una tarifa mensual fija no confirmada."
        )

    # --------------------------------------------------------
    # 3. NOMBRE DE MARCA Y HASHTAGS
    # --------------------------------------------------------

    hashtags = re.findall(
        r"#[a-záéíóúñ0-9_]+",
        texto,
        re.IGNORECASE
    )

    hashtags_incorrectos = {
    "#fitaccces",
    "#fitacccces",
    "#fitacccesesorios",
    "#fitacccesorios",
    "#fitaccesorioss",
    "#fitaccesorios_",
}

    for hashtag in hashtags:
        if hashtag.lower() in hashtags_incorrectos:
            errores.append(
                f"Nombre de marca incorrecto: '{hashtag}'. "
                "La escritura correcta es #FitAccesorios."
            )

    # --------------------------------------------------------
    # 4. AFIRMACIONES QUE REQUIEREN REVISIÓN
    # --------------------------------------------------------

    expresiones_sensibles = [
        "cálculo exacto",
        "mejora tu seguridad",
        "el primer paso seguro",
        "cambio físico real",
        "transforma tu cuerpo",
        "resultados reales",
    ]

    for expresion in expresiones_sensibles:
        if expresion in texto:
            advertencias.append(
                f"Revisar afirmación comercial: '{expresion}'"
            )

    # --------------------------------------------------------
    # 5. EVITAR INFORMACIÓN NO DOCUMENTADA
    # --------------------------------------------------------

    expresiones_no_documentadas = [
        "atención las 24 horas",
        "disponible las 24 horas",
        "respuesta inmediata",
        "garantía de resultados",
        "nutricionista certificado",
        "nutricionista profesional certificado",
        "videollamadas ilimitadas",
    ]

    for expresion in expresiones_no_documentadas:
        if expresion in texto:
            errores.append(
                "Afirmación no respaldada por la información "
                f"comercial: '{expresion}'."
            )

    # --------------------------------------------------------
    # 6. RESULTADO
    # --------------------------------------------------------

    aprobado = len(errores) == 0

    print("\nVALIDACIÓN DETERMINISTA DE PYTHON")

    if errores:
        print("\nErrores:")
        for error in errores:
            print(f"- {error}")

    if advertencias:
        print("\nAdvertencias:")
        for advertencia in advertencias:
            print(f"- {advertencia}")

    if not errores and not advertencias:
        print("No se encontraron problemas.")

    return {
        "aprobado": aprobado,
        "errores": errores,
        "advertencias": advertencias,
    }


# ============================================================
# VALIDACIÓN CON GEMINI
# ============================================================

def validar_contenido(client, contenido, informacion):
    """
    Utiliza Gemini como segunda capa de auditoría comercial.
    """

    instrucciones = f"""
Actúa como auditor de contenido comercial de FitAccesorios.

Tu tarea es revisar el siguiente contenido y determinar
si respeta la información comercial documentada.

REGLAS:

1. No inventar precios, descuentos ni condiciones.
2. No inventar características de los planes.
3. No inventar resultados garantizados.
4. No inventar testimonios ni experiencias de clientes.
5. No inventar credenciales profesionales.
6. No inventar tiempos de respuesta ni disponibilidad.
7. No presentar como incluidos servicios que dependen
   de un plan específico.
8. No convertir un precio de referencia en una tarifa mensual
   si esa condición no está documentada.
9. Identificar afirmaciones que puedan inducir a error.
10. Comparar el contenido con la información comercial.

INFORMACIÓN COMERCIAL:

{informacion}

CONTENIDO QUE DEBES AUDITAR:

{contenido}

Responde exclusivamente con un JSON válido que tenga esta estructura:

{{
    "aprobado": true,
    "errores": [],
    "advertencias": [],
    "observaciones": "Explicación breve"
}}

Si encuentras información comercial inventada o contradictoria,
establece aprobado en false.
"""

    try:
        respuesta = client.models.generate_content(
            model=MODELO_GEMINI,
            contents=instrucciones,
            config={
                "response_mime_type": "application/json"
            }
        )

        texto_respuesta = respuesta.text.strip()

        # Eliminar posibles bloques Markdown.
        texto_respuesta = re.sub(
            r"^```(?:json)?\s*",
            "",
            texto_respuesta,
            flags=re.IGNORECASE
        )

        texto_respuesta = re.sub(
            r"\s*```$",
            "",
            texto_respuesta
        )

        resultado = json.loads(texto_respuesta)

        if not isinstance(resultado, dict):
            raise ValueError("La respuesta JSON no es un objeto.")

        if not isinstance(resultado.get("aprobado"), bool):
            raise ValueError("El campo 'aprobado' no es booleano.")

        if not isinstance(resultado.get("errores"), list):
            raise ValueError("El campo 'errores' no es una lista.")

        if not isinstance(resultado.get("advertencias"), list):
            raise ValueError(
                "El campo 'advertencias' no es una lista."
            )

        print("\nAUDITORÍA DE GEMINI")

        print(
            "Estado:",
            "APROBADO" if resultado["aprobado"] else "RECHAZADO"
        )

        for error in resultado["errores"]:
            print(f"- Error: {error}")

        for advertencia in resultado["advertencias"]:
            print(f"- Advertencia: {advertencia}")

        observaciones = resultado.get("observaciones", "")
        if observaciones:
            print(f"\nObservaciones: {observaciones}")

        return resultado

    except Exception as error:
        print(f"\nError durante la validación de Gemini: {error}")

        return {
            "aprobado": False,
            "errores": [
                "No fue posible completar la auditoría de Gemini."
            ],
            "advertencias": [],
            "observaciones": str(error),
        }


# ============================================================
# GUARDAR CONTENIDO EN MARKDOWN Y PDF
# ============================================================

def guardar_contenido(pregunta, contenido):
    """
    Guarda el contenido aprobado en archivos Markdown y PDF.
    """

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    fecha = datetime.now().strftime("%Y%m%d_%H%M%S")

    nombre_base = f"contenido_fitaccesorios_{fecha}"

    ruta_markdown = REPORTS_DIR / f"{nombre_base}.md"
    ruta_pdf = REPORTS_DIR / f"{nombre_base}.pdf"

    # --------------------------------------------------------
    # MARKDOWN
    # --------------------------------------------------------

    texto_markdown = (
        "# Contenido generado para FitAccesorios\n\n"
        f"**Solicitud:** {pregunta}\n\n"
        f"**Fecha:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        "---\n\n"
        f"{contenido}\n"
    )

    ruta_markdown.write_text(
        texto_markdown,
        encoding="utf-8"
    )

    # --------------------------------------------------------
    # PDF
    # --------------------------------------------------------

    documento = SimpleDocTemplate(
        str(ruta_pdf),
        pagesize=letter,
        rightMargin=50,
        leftMargin=50,
        topMargin=50,
        bottomMargin=50,
    )

    estilos = getSampleStyleSheet()

    estilo_titulo = ParagraphStyle(
        "TituloFit",
        parent=estilos["Title"],
        alignment=TA_CENTER,
        spaceAfter=20,
    )

    estilo_normal = estilos["BodyText"]
    estilo_normal.leading = 15
    estilo_normal.spaceAfter = 8

    elementos = [
        Paragraph(
            "Contenido para FitAccesorios",
            estilo_titulo
        ),
        Paragraph(
            f"<b>Solicitud:</b> {escape(pregunta)}",
            estilo_normal
        ),
        Spacer(1, 15),
    ]

    for linea in contenido.splitlines():

        linea = linea.strip()

        if not linea:
            elementos.append(Spacer(1, 8))
            continue

        if linea.startswith("# "):
            elementos.append(
                Paragraph(
                    escape(linea[2:]),
                    estilos["Heading1"]
                )
            )

        elif linea.startswith("## "):
            elementos.append(
                Paragraph(
                    escape(linea[3:]),
                    estilos["Heading2"]
                )
            )

        elif linea.startswith("### "):
            elementos.append(
                Paragraph(
                    escape(linea[4:]),
                    estilos["Heading3"]
                )
            )

        else:
            linea = escape(linea)

            linea = re.sub(
                r"\*\*(.*?)\*\*",
                r"<b>\1</b>",
                linea
            )

            linea = re.sub(
                r"\*(.*?)\*",
                r"<i>\1</i>",
                linea
            )

            elementos.append(
                Paragraph(linea, estilo_normal)
            )

    documento.build(elementos)

    print("\nARCHIVOS GENERADOS")
    print(f"Markdown: {ruta_markdown}")
    print(f"PDF: {ruta_pdf}")


# ============================================================
# GENERAR CONTENIDO
# ============================================================


def generar_contenido(client, pregunta):
    """
    Genera contenido, lo valida y permite hasta tres
    intentos de autocorrección antes de guardarlo.
    """

    MAX_INTENTOS = 3

    print("\nCargando información comercial de FitAccesorios...")

    informacion = cargar_informacion_comercial()

    if not informacion.strip():
        print("No se encontró información comercial para trabajar.")
        return

    print("Generando estrategia de contenido...")

    instrucciones = f"""
Actúa como estratega senior de marketing digital,
especializado en negocios fitness en Colombia.

Debes crear contenido comercial para FitAccesorios.

Utiliza exclusivamente la información comercial documentada.
No inventes precios, características, beneficios, resultados,
testimonios, credenciales ni condiciones.

Prioriza el servicio de entrenamiento personalizado virtual.
Los accesorios deportivos son una oferta complementaria.

Cuando una información no esté documentada, no la inventes.
Utiliza llamados a la acción claros y naturales.

INFORMACIÓN COMERCIAL:

{informacion}

SOLICITUD DEL USUARIO:

{pregunta}

Entrega contenido organizado, estratégico y listo para revisión.
"""

    try:
        respuesta = client.models.generate_content(
            model=MODELO_GEMINI,
            contents=instrucciones
        )

        contenido = respuesta.text.strip()

        if not contenido:
            print("Gemini no generó contenido.")
            return

    except Exception as error:
        print(f"Error generando contenido: {error}")
        return

    # --------------------------------------------------------
    # CICLO DE VALIDACIÓN Y AUTOCORRECCIÓN
    # --------------------------------------------------------

    for intento in range(1, MAX_INTENTOS + 1):

        print(
            f"\nVALIDACIÓN DEL CONTENIDO "
            f"(Intento {intento}/{MAX_INTENTOS})"
        )

        # ----------------------------------------------------
        # PRIMERA VALIDACIÓN: PYTHON
        # ----------------------------------------------------

        resultado_python = validar_reglas_python(contenido)

        if not resultado_python["aprobado"]:

            errores = "\n".join(
                f"- {error}"
                for error in resultado_python["errores"]
            )

            print("\nPython encontró errores.")

            observaciones = (
                "El validador determinista de Python rechazó "
                "el contenido por los siguientes motivos:\n"
                f"{errores}"
            )

        else:

            # ------------------------------------------------
            # SEGUNDA VALIDACIÓN: GEMINI
            # ------------------------------------------------

            print("\nEjecutando auditoría comercial con Gemini...")

            resultado_gemini = validar_contenido(
                client,
                contenido,
                informacion
            )

            if resultado_gemini["aprobado"]:

                print(
                    "\nContenido aprobado por ambas validaciones."
                )

                guardar_contenido(
                    pregunta,
                    contenido
                )

                return

            errores_gemini = "\n".join(
                f"- {error}"
                for error in resultado_gemini["errores"]
            )

            advertencias_gemini = "\n".join(
                f"- {advertencia}"
                for advertencia in resultado_gemini["advertencias"]
            )

            observaciones = (
                "La auditoría comercial de Gemini rechazó "
                "el contenido.\n"
                f"Errores:\n{errores_gemini}\n"
                f"Advertencias:\n{advertencias_gemini}\n"
                f"Observaciones: "
                f"{resultado_gemini.get('observaciones', '')}"
            )

        # ----------------------------------------------------
        # LÍMITE DE INTENTOS
        # ----------------------------------------------------

        if intento == MAX_INTENTOS:
            print(
                "\nSe alcanzó el límite de intentos de corrección."
            )
            print("Contenido rechazado. No se generarán archivos.")
            return

        # ----------------------------------------------------
        # AUTOCORRECCIÓN CON GEMINI
        # ----------------------------------------------------

        print("\nGemini intentará corregir el contenido...")

        instrucciones_correccion = f"""
Actúa como editor y estratega comercial de FitAccesorios.

Debes corregir el contenido rechazado sin cambiar
la solicitud original del usuario.

INFORMACIÓN COMERCIAL AUTORIZADA:

{informacion}

SOLICITUD ORIGINAL:

{pregunta}

CONTENIDO QUE DEBES CORREGIR:

{contenido}

ERRORES Y OBSERVACIONES DETECTADOS:

{observaciones}

INSTRUCCIONES:

1. Corrige todos los errores identificados.
2. Respeta estrictamente la información comercial.
3. No inventes características, precios ni condiciones.
4. Conserva el objetivo y la estructura del contenido.
5. No elimines información importante de la solicitud.
6. No agregues explicaciones sobre las correcciones.
7. Devuelve únicamente el contenido completo corregido.
"""

        try:
            respuesta_correccion = client.models.generate_content(
                model=MODELO_GEMINI,
                contents=instrucciones_correccion
            )

            contenido_corregido = (
                respuesta_correccion.text.strip()
                if respuesta_correccion.text
                else ""
            )

            if not contenido_corregido:
                print("Gemini no devolvió contenido corregido.")
                print("No se generarán archivos.")
                return

            contenido = contenido_corregido

            print("Contenido corregido. Se repetirá la validación.")

        except Exception as error:
            print(f"Error durante la autocorrección: {error}")
            print("No se generarán archivos.")
            return
