from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Iterable


BASE_DIR = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = BASE_DIR / "knowledge"
REPORTS_DIR = BASE_DIR / "reports"
MEMORY_DIR = BASE_DIR / "memory"


def cargar_base_conocimiento() -> str:
    partes = []
    for ruta in sorted(KNOWLEDGE_DIR.glob("*")):
        if ruta.suffix.lower() == ".md":
            partes.append(f"\n\nDOCUMENTO: {ruta.name}\n{ruta.read_text(encoding='utf-8')}")
        elif ruta.suffix.lower() == ".pdf":
            try:
                from pypdf import PdfReader
                texto = "\n".join(p.extract_text() or "" for p in PdfReader(str(ruta)).pages)
                partes.append(f"\n\nDOCUMENTO: {ruta.name}\n{texto}")
            except Exception as exc:
                partes.append(f"\n\nDOCUMENTO: {ruta.name}\n[No se pudo extraer: {exc}]")
    return "\n".join(partes)


def _normalizar_monto(valor: str) -> str:
    return re.sub(r"\D", "", valor or "")


def _montos(texto: str) -> set[str]:
    encontrados = re.findall(r"(?:COP\s*)?\$\s*([\d.]+(?:,\d+)?)|\bCOP\s*([\d.]+(?:,\d+)?)", texto or "", re.I)
    salida = set()
    for grupo in encontrados:
        bruto = next((x for x in grupo if x), "")
        limpio = _normalizar_monto(bruto)
        if len(limpio) >= 4:
            salida.add(limpio)
    return salida


def validar_afirmaciones_comerciales(texto: str, conocimiento: str | None = None) -> dict:
    """Valida afirmaciones comerciales contra la base documental; no certifica verdad externa."""
    original = texto or ""
    t = original.lower()
    k = (conocimiento if conocimiento is not None else cargar_base_conocimiento()).lower()
    bloqueos: list[str] = []
    advertencias: list[str] = []

    # Un precio publicado debe existir literalmente en la base documental (MD/PDF).
    montos_k = _montos(k)
    for monto in sorted(_montos(original)):
        if monto not in montos_k:
            bloqueos.append(f"Precio o monto comercial ${monto} no encontrado en la base de conocimiento; requiere verificación.")

    # El Plan Inicio tiene un alcance expresamente limitado.
    patrones_inicio = [
        (r"plan\s+inicio\s+fitness.{0,220}(?:plataforma\s+online|plataforma\s+en\s+línea)", "Se atribuye plataforma online al Plan Inicio Fitness, que no la incluye."),
        (r"(?:plataforma\s+online|plataforma\s+en\s+línea).{0,220}plan\s+inicio\s+fitness", "Se atribuye plataforma online al Plan Inicio Fitness, que no la incluye."),
        (r"plan\s+inicio\s+fitness.{0,220}(?:seguimiento\s+semanal|ajustes\s+progresivos|corrección\s+de\s+técnica|plan\s+nutricional)", "Se atribuye al Plan Inicio una característica que no está incluida en ese plan."),
        (r"(?:seguimiento\s+semanal|ajustes\s+progresivos|corrección\s+de\s+técnica|plan\s+nutricional).{0,220}plan\s+inicio\s+fitness", "Se atribuye al Plan Inicio una característica que no está incluida en ese plan."),
    ]
    # Evaluar por párrafo evita relacionar menciones independientes en distintas secciones.
    for parrafo in re.split(r"\n\s*\n", t):
        for patron, mensaje in patrones_inicio:
            if re.search(patron, parrafo, re.S): bloqueos.append(mensaje)

    # Generalizaciones de alcance entre planes.
    if re.search(r"(?:todos\s+(?:los\s+)?planes|cualquier\s+plan|los\s+tres\s+planes)[^.\n]{0,180}(?:plataforma\s+online|seguimiento\s+semanal|ajustes\s+progresivos|corrección\s+de\s+técnica)", t):
        bloqueos.append("Se generaliza a todos los planes una característica que solo corresponde a planes específicos.")

    # Condiciones de pago, tiempos y garantías no definidos.
    reglas = [
        (r"\b(?:nequi|transferencia\s+bancaria|pse|tarjeta\s+de\s+crédito)\b", "Se afirma disponibilidad de un método de pago sin respaldo en la documentación comercial."),
        (r"\b(?:en\s+menos\s+de\s+\d+\s*minutos|respuesta\s+en\s+\d+\s*minutos|\d+\s*minutos\s+de\s+respuesta)\b", "Se promete un tiempo de respuesta específico no documentado."),
        (r"\b(?:respuesta\s+inmediata|atención\s+las\s+24\s+horas|disponible\s+las\s+24\s+horas|soporte\s+24/7|videollamadas?\s+(?:ilimitadas|sin\s+límite))\b", "Se promete disponibilidad o frecuencia no establecida para el servicio."),
        (r"\bgarantizamos?\b", "Se utiliza lenguaje de garantía comercial; no hay una garantía de servicio documentada."),
        (r"\b\d{1,2}\s*%\s*(?:de\s*)?descuento\b", "Se anuncia un porcentaje de descuento no documentado; solo consta un descuento exclusivo sin porcentaje."),
        (r"\b(?:nutricionista|nutrición)\s+(?:certificado|certificada|titulado|titulada)\b", "Se atribuyen credenciales específicas no verificadas en la base documental."),
    ]
    for patron, mensaje in reglas:
        if re.search(patron, t): bloqueos.append(mensaje)

    # No convertir un precio de duración mínima en suscripción recurrente.
    if re.search(r"89[.,]?900.{0,35}(?:al\s+mes|mensual(?:mente)?|por\s+mes)|(?:al\s+mes|mensual(?:mente)?|por\s+mes).{0,35}89[.,]?900", t):
        bloqueos.append("El precio de Inicio Fitness se presenta como mensual recurrente; la documentación indica duración desde un mes, no renovación mensual automática.")

    # Una hipótesis puede plantearse, pero no presentarse como benchmark o resultado probado.
    for m in re.finditer(r"\b(\d{1,3})\s*%\b", t):
        contexto = t[max(0,m.start()-100):m.end()+100]
        if not re.search(r"hipótesis|hipotesis|supuesto|a\s+validar|meta\s+de\s+prueba", contexto):
            if int(m.group(1)) >= 50:
                advertencias.append(f"Porcentaje ({m.group(1)}%) sin fuente o línea base explícita; presentarlo como hipótesis o eliminarlo.")

    return {
        "aprobado": not bloqueos,
        "bloqueos": sorted(set(bloqueos)),
        "advertencias": sorted(set(advertencias)),
        "alcance": "Comprobación determinista contra la base documental. No certifica veracidad de fuentes externas ni sustituye revisión humana."
    }

def extraer_urls(texto: str) -> list[str]:
    urls = re.findall(r"https?://[^\s)\]>\"']+", texto or "", flags=re.IGNORECASE)
    return list(dict.fromkeys(u.rstrip(".,;") for u in urls))


def auditar_informe_externo(ruta: str | Path, registro_fuentes: str | Path | None = None) -> dict:
    """Audita trazabilidad y comprueba que los montos publicados aparezcan en extractos."""
    path = Path(ruta)
    contenido = path.read_text(encoding="utf-8", errors="replace")
    urls = extraer_urls(contenido)
    advertencias, bloqueos = [], []
    if not urls:
        bloqueos.append("El informe no contiene URLs que permitan rastrear las afirmaciones externas.")
    if not re.search(r"(fecha de consulta|consultado el|capturado el|fecha de captura)", contenido, re.I):
        advertencias.append("No se registra fecha de consulta/captura dentro del informe.")
    if registro_fuentes:
        try:
            fuentes = json.loads(Path(registro_fuentes).read_text(encoding="utf-8"))
            extractos = "\n".join(str(x.get("extracto", "")) for x in fuentes if isinstance(x, dict))
            montos_evidencia = _montos(extractos)
            for monto in sorted(_montos(contenido)):
                if monto not in montos_evidencia:
                    bloqueos.append(f"El monto ${monto} aparece en la investigación, pero no está en los extractos de evidencia capturados.")
            for fuente in fuentes:
                if not fuente.get("url") or not fuente.get("titulo") or not fuente.get("extracto") or not fuente.get("fecha_consulta"):
                    advertencias.append("El registro contiene al menos una fuente con metadatos o extracto incompleto.")
                    break
        except Exception as exc:
            bloqueos.append(f"No se pudo contrastar la investigación con el registro de fuentes: {exc}")
    else:
        advertencias.append("No se proporcionó el registro JSON de fuentes para contrastar precios y afirmaciones.")
    return {
        "archivo": path.name, "urls_encontradas": urls, "cantidad_urls": len(urls),
        "bloqueos": bloqueos, "advertencias": advertencias,
        "estado": "requiere_revision" if bloqueos or advertencias else "trazabilidad_contrastada"
    }

def guardar_memoria(registro: dict) -> Path:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    ruta = MEMORY_DIR / "execution_history.jsonl"
    entrada = {"timestamp": datetime.now().isoformat(timespec="seconds"), **registro}
    with ruta.open("a", encoding="utf-8") as archivo:
        archivo.write(json.dumps(entrada, ensure_ascii=False) + "\n")
    return ruta


def leer_memoria(limite: int = 5) -> list[dict]:
    ruta = MEMORY_DIR / "execution_history.jsonl"
    if not ruta.exists():
        return []
    registros = []
    for linea in ruta.read_text(encoding="utf-8").splitlines()[-limite:]:
        try:
            registros.append(json.loads(linea))
        except json.JSONDecodeError:
            continue
    return registros


def auditar_registro_fuentes(ruta: str | Path) -> dict:
    path = Path(ruta)
    try:
        fuentes = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"archivo": path.name, "estado": "invalido", "advertencias": [f"No se pudo leer el registro: {exc}"]}
    advertencias = []
    if not isinstance(fuentes, list) or not fuentes:
        return {"archivo": path.name, "estado": "vacio", "advertencias": ["El registro no contiene fuentes."]}
    for indice, fuente in enumerate(fuentes, 1):
        if not fuente.get("url") or not fuente.get("titulo"):
            advertencias.append(f"Fuente {indice}: falta URL o título.")
        if not fuente.get("fecha_consulta"):
            advertencias.append(f"Fuente {indice}: falta fecha de consulta.")
        if not fuente.get("extracto"):
            advertencias.append(f"Fuente {indice}: falta extracto de evidencia.")
    return {
        "archivo": path.name,
        "cantidad_fuentes": len(fuentes),
        "estado": "trazabilidad_basica" if not advertencias else "trazabilidad_parcial",
        "advertencias": advertencias,
    }
