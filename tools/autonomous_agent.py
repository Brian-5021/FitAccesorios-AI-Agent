from datetime import datetime
from pathlib import Path
import json

from .ai_utils import MODELO_GEMINI
from .task_planner import planificar_objetivo
from .task_executor import ejecutar_tarea
from .evidence import (
    cargar_base_conocimiento,
    validar_afirmaciones_comerciales,
    auditar_informe_externo,
    auditar_registro_fuentes,
    guardar_memoria,
    leer_memoria,
)

BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = BASE_DIR / "reports"
MAX_PASOS = 4
MAX_REINTENTOS = 1


def _leer_informes(resultados):
    informes = []
    for resultado in resultados:
        for nombre in resultado.get("informes", []):
            ruta = Path(nombre)
            if ruta.suffix.lower() == ".md" and ruta.exists():
                try:
                    contenido = ruta.read_text(encoding="utf-8", errors="replace")
                    informes.append({"tarea": resultado["tarea"], "ruta": str(ruta), "contenido": contenido[:16000]})
                except OSError:
                    continue
    return informes


def _ultimos_resultados_por_tarea(resultados):
    ultimos = {}
    for resultado in resultados:
        ultimos[resultado["tarea"]] = resultado
    return list(ultimos.values())


def _validacion_determinista(resultados):
    resultados_actuales = _ultimos_resultados_por_tarea(resultados)
    conocimiento = cargar_base_conocimiento()
    informes = _leer_informes(resultados_actuales)
    bloqueos, advertencias, auditorias = [], [], []

    for informe in informes:
        validacion = validar_afirmaciones_comerciales(informe["contenido"], conocimiento)
        for item in validacion["bloqueos"]:
            bloqueos.append(f"{informe['tarea']} ({Path(informe['ruta']).name}): {item}")
        for item in validacion["advertencias"]:
            advertencias.append(f"{informe['tarea']} ({Path(informe['ruta']).name}): {item}")
        if informe["tarea"] == "investigacion":
            registro_json = None
            for resultado in resultados_actuales:
                if resultado["tarea"] == "investigacion":
                    registro_json = next((n for n in resultado.get("informes", []) if str(n).lower().endswith(".json") and "fuentes_investigacion_" in str(n)), None)
                    break
            auditoria = auditar_informe_externo(informe["ruta"], registro_json)
            auditorias.append(auditoria)
            bloqueos.extend(f"Investigación: {item}" for item in auditoria.get("bloqueos", []))
            advertencias.extend(f"Investigación: {item}" for item in auditoria.get("advertencias", []))

    for resultado in resultados_actuales:
        for nombre in resultado.get("informes", []):
            if str(nombre).lower().endswith(".json") and "fuentes_investigacion_" in str(nombre):
                registro = auditar_registro_fuentes(nombre)
                auditorias.append(registro)
                advertencias.extend(f"Registro de fuentes: {x}" for x in registro.get("advertencias", []))
                if registro.get("estado") in {"invalido", "vacio"}:
                    bloqueos.append("El registro de fuentes de investigación es inválido o está vacío.")

    fallidas = [r["tarea"] for r in resultados_actuales if r["estado"] != "completada"]
    if fallidas:
        bloqueos.append("Herramientas fallidas o sin informe: " + ", ".join(fallidas))

    return {
        "aprobado": not bloqueos,
        "bloqueos": sorted(set(bloqueos)),
        "advertencias": sorted(set(advertencias)),
        "auditorias_fuentes": auditorias,
        "informes_leidos": len(informes),
    }


def _revision_ia(client, objetivo, resultados, determinista):
    resumen = []
    for item in resultados:
        resumen.append({
            "herramienta": item["tarea"],
            "estado": item["estado"],
            "salida": item.get("salida", "")[:5000],
            "informes": item.get("informes", []),
            "error": item.get("error"),
        })

    prompt = f"""
Eres un revisor independiente de calidad para FitAccesorios.
No debes aprobar por cortesía ni asumir que las afirmaciones son ciertas.

OBJETIVO:
{objetivo}

RESULTADOS DE HERRAMIENTAS:
{json.dumps(resumen, ensure_ascii=False, indent=2)}

VALIDACIÓN DETERMINISTA DE PYTHON:
{json.dumps(determinista, ensure_ascii=False, indent=2)}

Devuelve exclusivamente JSON:
{{
 "status": "aprobado" o "requiere_revision",
 "coverage": "alta" o "media" o "baja",
 "issues": ["observación concreta"],
 "reason": "explicación breve"
}}

REGLAS:
- Si la validación determinista tiene bloqueos, status debe ser requiere_revision.
- Si una herramienta falló, no apruebes.
- No afirmes que verificaste fuentes externas si no hay evidencia.
- Distingue hechos documentados, hipótesis, recomendaciones y datos externos.
- Si faltan fechas, URLs o evidencia para precios de competidores, indícalo.
- No uses la conclusión de otro modelo como prueba de verdad.
"""
    respuesta = client.models.generate_content(model=MODELO_GEMINI, contents=prompt)
    texto = (respuesta.text or "").strip()
    inicio, fin = texto.find("{"), texto.rfind("}")
    if inicio < 0 or fin <= inicio:
        return {"status": "requiere_revision", "coverage": "baja",
                "issues": ["El revisor no devolvió JSON válido."],
                "reason": "No se pudo interpretar la revisión independiente."}
    try:
        revision = json.loads(texto[inicio:fin + 1])
    except json.JSONDecodeError:
        return {"status": "requiere_revision", "coverage": "baja",
                "issues": ["JSON de revisión inválido."],
                "reason": "No se pudo interpretar la revisión independiente."}

    if not determinista["aprobado"]:
        revision["status"] = "requiere_revision"
    if any(r["estado"] != "completada" for r in resultados):
        revision["status"] = "requiere_revision"
    return revision


def _guardar_resumen(objetivo, plan, resultados, determinista, revision, reintentos):
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
    ruta = REPORTS_DIR / f"agente_autonomo_{fecha}.md"
    lineas = [
        "# Ejecución autónoma FitAccesorios v2.3",
        "", f"Fecha: {datetime.now():%Y-%m-%d %H:%M:%S}",
        "", "## Objetivo", "", objetivo,
        "", "## Plan",
    ]
    for i, paso in enumerate(plan["steps"], 1):
        lineas.append(f"{i}. **{paso['tool']}** — {paso['task']}")
    lineas += ["", "## Resultados"]
    for item in resultados:
        lineas += [f"### {item['tarea']} — {item['estado']}", "", item.get("salida") or "Sin salida capturada.", ""]
        if item.get("error"):
            lineas.append(f"Error: {item['error']}")
        lineas.append("Informes:")
        lineas.extend([f"- `{p}`" for p in item.get("informes", [])] or ["- Ninguno detectado."])
        lineas.append("")
    lineas += [
        "## Validación determinista",
        "",
        f"- Aprobado: {determinista['aprobado']}",
        f"- Informes inspeccionados: {determinista['informes_leidos']}",
        "",
        "### Bloqueos",
    ]
    lineas += [f"- {x}" for x in determinista["bloqueos"]] or ["- Ninguno detectado."]
    lineas += ["", "### Advertencias"]
    lineas += [f"- {x}" for x in determinista["advertencias"]] or ["- Ninguna."]
    lineas += ["", "## Revisión de IA", "",
               f"- Estado: {revision.get('status', 'requiere_revision')}",
               f"- Cobertura estimada: {revision.get('coverage', 'baja')}",
               f"- Motivo: {revision.get('reason', '')}",
               "", "### Observaciones"]
    lineas += [f"- {x}" for x in revision.get("issues", [])] or ["- Sin observaciones."]
    lineas += ["", f"Reintentos de corrección ejecutados: {reintentos}",
               "", "> La aprobación indica que pasaron las reglas implementadas; no certifica la veracidad de datos externos. Verificar fuentes y condiciones comerciales antes de publicar."]
    ruta.write_text("\n".join(lineas), encoding="utf-8")
    return ruta


def ejecutar_objetivo_autonomo(client, objetivo):
    historial = leer_memoria(3)
    print("\nPLANIFICANDO OBJETIVO...")
    plan = planificar_objetivo(client, objetivo)

    print(f"\nOBJETIVO: {plan.get('objective', objetivo)}")
    print("\nPLAN DE EJECUCIÓN:")
    for i, paso in enumerate(plan["steps"][:MAX_PASOS], 1):
        print(f"{i}. {paso['tool']}: {paso['task']}")

    if historial:
        print(f"\nMemoria: {len(historial)} ejecuciones anteriores disponibles.")

    confirmacion = input("\n¿Ejecutar este plan? (s/n): ").strip().lower()
    if confirmacion not in {"s", "si", "sí"}:
        print("Ejecución cancelada.")
        return

    resultados = []
    pasos = plan["steps"][:MAX_PASOS]
    for i, paso in enumerate(pasos, 1):
        print(f"\n[{i}/{len(pasos)}] Ejecutando: {paso['tool']}")
        resultado = ejecutar_tarea(client, paso["tool"], paso["task"])
        resultados.append(resultado)
        print(f"Estado: {resultado['estado']}")
        for informe in resultado.get("informes", []):
            print(f"Informe: {informe}")

    determinista = _validacion_determinista(resultados)
    reintentos = 0

    # Un único reintento dirigido cuando hay bloqueos o una herramienta fallida.
    if (not determinista["aprobado"] or any(r["estado"] != "completada" for r in resultados)) and MAX_REINTENTOS:
        tareas_afectadas = set()
        for r in resultados:
            if r["estado"] != "completada":
                tareas_afectadas.add(r["tarea"])
        for bloqueo in determinista["bloqueos"]:
            for paso in pasos:
                if paso["tool"] in bloqueo:
                    tareas_afectadas.add(paso["tool"])
        if tareas_afectadas:
            reintentos = 1
            print("\nSe detectaron problemas. Ejecutando un reintento dirigido...")
            nuevos = []
            for paso in pasos:
                if paso["tool"] in tareas_afectadas:
                    instruccion = (
                        paso["task"] + "\n\nINSTRUCCIÓN DE CORRECCIÓN: "
                        "Revisa el resultado anterior y evita afirmaciones comerciales "
                        "no respaldadas. Distingue hechos, hipótesis y recomendaciones. "
                        "No presentes como mensual recurrente el precio de Inicio Fitness; "
                        "no atribuyas plataforma, seguimiento semanal ni ajustes al plan Inicio; "
                        "no inventes credenciales, descuentos, kits ni precios. "
                        "Incluye URLs junto a datos externos y señala datos no comprobados."
                    )
                    nuevo = ejecutar_tarea(client, paso["tool"], instruccion)
                    nuevos.append(nuevo)
            resultados.extend(nuevos)
            determinista = _validacion_determinista(resultados)

    print("\nVALIDANDO RESULTADOS...")
    try:
        revision = _revision_ia(client, objetivo, _ultimos_resultados_por_tarea(resultados), determinista)
    except Exception as exc:
        revision = {"status": "requiere_revision", "coverage": "baja",
                    "issues": [f"No se pudo ejecutar la revisión IA: {exc}"],
                    "reason": "La revisión falló; se requiere control humano."}

    ruta = _guardar_resumen(objetivo, plan, resultados, determinista, revision, reintentos)
    guardar_memoria({
        "objetivo": objetivo,
        "status": revision.get("status", "requiere_revision"),
        "coverage": revision.get("coverage", "baja"),
        "issues": revision.get("issues", []),
        "report": str(ruta),
    })

    print("\nRESULTADO DE CALIDAD")
    print(f"Estado: {revision.get('status', 'requiere_revision')}")
    print(f"Cobertura: {revision.get('coverage', 'baja')}")
    print(f"Bloqueos deterministas: {len(determinista['bloqueos'])}")
    print(f"Advertencias: {len(determinista['advertencias'])}")
    print(f"Reintentos: {reintentos}")
    print(f"\nInforme consolidado: {ruta}")
    print("\nLa revisión automática reduce riesgos, pero no sustituye la verificación humana.")
