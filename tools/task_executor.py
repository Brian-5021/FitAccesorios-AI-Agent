from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from .research import investigar
from .content import generar_contenido
from .seo import analizar_seo
from .conversion import analizar_conversion
from .prospeccion import prospectar_empresas

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"

ACCIONES = {
    "investigacion": investigar,
    "contenido": generar_contenido,
    "seo": analizar_seo,
    "conversion": analizar_conversion,
    "prospeccion": prospectar_empresas,
}


def ejecutar_tarea(client, tarea, pregunta):
    if tarea not in ACCIONES:
        raise ValueError(f"Tarea no permitida o desconocida: {tarea}")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    existentes = {p.resolve() for p in REPORTS_DIR.glob("*") if p.is_file()}
    salida = StringIO()
    error = None

    try:
        with redirect_stdout(salida):
            if tarea == "investigacion":
                ACCIONES[tarea](pregunta)
            else:
                ACCIONES[tarea](client, pregunta)
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"

    nuevos = sorted(
        str(p.resolve()) for p in REPORTS_DIR.glob("*")
        if p.is_file() and p.resolve() not in existentes
    )
    texto = salida.getvalue().strip()
    marcadores_error = ("no se pudo completar", "no fue posible", "error durante", "no se encontraron resultados")
    salida_fallida = any(m in texto.lower() for m in marcadores_error)

    if error:
        estado = "fallida"
    elif nuevos and not salida_fallida:
        estado = "completada"
    else:
        estado = "fallida"

    return {
        "tarea": tarea,
        "salida": texto,
        "informes": nuevos,
        "estado": estado,
        "error": error,
    }
