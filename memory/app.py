import os
from pathlib import Path
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv
from google import genai
from pypdf import PdfReader

from tools.task_executor import ejecutar_tarea
from tools.task_router import clasificar_tarea

BASE_DIR = Path(__file__).resolve().parent
REPORTS_DIR = BASE_DIR / "reports"
KNOWLEDGE_DIR = BASE_DIR / "knowledge"
load_dotenv(BASE_DIR / ".env")

st.set_page_config(page_title="FitAccesorios AI", page_icon="💪", layout="wide")

def login():
    expected = os.getenv("APP_PASSWORD", "")
    if not expected:
        st.error("Falta configurar APP_PASSWORD en las variables de entorno del servidor.")
        st.stop()
    if st.session_state.get("authenticated"):
        return
    st.title("💪 FitAccesorios AI")
    st.caption("Acceso privado para el equipo")
    with st.form("login"):
        password = st.text_input("Contraseña de acceso", type="password")
        submitted = st.form_submit_button("Ingresar", use_container_width=True)
    if submitted:
        import hmac
        if hmac.compare_digest(password, expected):
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Contraseña incorrecta.")
    st.stop()

login()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    st.error("El servidor no tiene configurada GEMINI_API_KEY.")
    st.stop()

@st.cache_resource
def get_client(key):
    return genai.Client(api_key=key)

client = get_client(api_key)

def cargar_conocimiento():
    partes = []
    for path in sorted(KNOWLEDGE_DIR.iterdir()):
        try:
            if path.suffix.lower() == ".md":
                contenido = path.read_text(encoding="utf-8")
            elif path.suffix.lower() == ".pdf":
                contenido = "\n".join(p.extract_text() or "" for p in PdfReader(path).pages)
            else:
                continue
            partes.append(f"\nDOCUMENTO: {path.name}\n{contenido}")
        except Exception:
            continue
    return "\n".join(partes)

st.title("💪 FitAccesorios AI")
st.caption("Asistente de marketing, investigación y ventas")
with st.sidebar:
    st.success("Sesión iniciada")
    if st.button("Cerrar sesión", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()
    st.divider()
    st.caption("Los resultados generados deben revisarse antes de publicarse.")

tab_task, tab_chat, tab_reports = st.tabs(["🚀 Ejecutar tarea", "💬 Consultar al agente", "📁 Informes"])

with tab_task:
    st.subheader("¿Qué necesitas que haga?")
    labels = {
        "Investigación de mercado": "investigacion",
        "Crear contenido para redes": "contenido",
        "Estrategia de ventas y conversión": "conversion",
        "SEO": "seo",
        "Prospección comercial": "prospeccion",
    }
    selected = st.selectbox("Tipo de tarea", list(labels.keys()))
    request = st.text_area(
        "Describe el resultado que necesitas",
        height=150,
        placeholder="Ejemplo: Diseña una estrategia de bajo costo para captar clientes de entrenamiento personalizado virtual en Colombia."
    )
    if st.button("Ejecutar tarea", type="primary", use_container_width=True, disabled=not request.strip()):
        with st.spinner("El agente está trabajando. Esto puede tardar unos minutos..."):
            try:
                result = ejecutar_tarea(client, labels[selected], request.strip())
                st.session_state.last_result = result
            except Exception as exc:
                st.error(f"No se pudo ejecutar la tarea: {exc}")
                st.stop()
        result = st.session_state.last_result
        if result.get("estado") == "completada":
            st.success("Tarea completada.")
        else:
            st.warning("La tarea no pudo completarse correctamente. Revisa el detalle.")
        if result.get("salida"):
            st.text_area("Resultado de ejecución", result["salida"], height=300)
        if result.get("error"):
            st.error(result["error"])
        for file in result.get("informes", []):
            p = Path(file)
            if p.exists():
                st.write(f"Informe: **{p.name}**")
                st.download_button(
                    f"Descargar {p.name}",
                    data=p.read_bytes(),
                    file_name=p.name,
                    mime="application/pdf" if p.suffix.lower()==".pdf" else "text/markdown",
                    key=f"download_{p.name}"
                )

with tab_chat:
    st.subheader("Consulta general")
    st.caption("Haz preguntas sobre FitAccesorios y sus servicios.")
    question = st.text_area("Escribe tu consulta", height=120, key="chat_question")
    if st.button("Enviar consulta", key="send_chat", disabled=not question.strip()):
        with st.spinner("Consultando Gemini..."):
            try:
                knowledge = cargar_conocimiento()
                prompt = f"""Eres el asistente de FitAccesorios. Responde en español colombiano.
No inventes precios, condiciones, características, resultados, credenciales ni políticas.
Distingue lo documentado de las recomendaciones. Si no sabes algo, dilo.
BASE DOCUMENTAL:
{knowledge}
CONSULTA:
{question}"""
                response = client.models.generate_content(
                    model="gemini-3.5-flash-lite",
                    contents=prompt
                )
                st.session_state.chat_answer = response.text or "No se obtuvo respuesta."
            except Exception as exc:
                st.error(f"Error al consultar Gemini: {exc}")
    if st.session_state.get("chat_answer"):
        st.markdown(st.session_state.chat_answer)

with tab_reports:
    st.subheader("Informes generados")
    REPORTS_DIR.mkdir(exist_ok=True)
    reports = sorted(
        [p for p in REPORTS_DIR.iterdir() if p.is_file() and p.suffix.lower() in {".md", ".pdf", ".json"}],
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    if not reports:
        st.info("Todavía no hay informes.")
    for p in reports[:50]:
        c1, c2 = st.columns([4, 1])
        c1.write(f"📄 {p.name}")
        c2.download_button("Descargar", p.read_bytes(), file_name=p.name, key=f"r_{p.name}")
