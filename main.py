import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from pypdf import PdfReader

from tools.task_router import clasificar_tarea
from tools.task_executor import ejecutar_tarea
from tools.autonomous_agent import ejecutar_objetivo_autonomo

load_dotenv()

BASE_DIR = Path(__file__).parent
KNOWLEDGE_DIR = BASE_DIR / "knowledge"
MODELO = "gemini-3.5-flash-lite"

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("No se encontró GEMINI_API_KEY en el archivo .env.")

client = genai.Client(api_key=api_key)


def load_knowledge():
    documents = []
    for file_path in sorted(KNOWLEDGE_DIR.iterdir()):
        if file_path.suffix.lower() == ".md":
            content = file_path.read_text(encoding="utf-8")
        elif file_path.suffix.lower() == ".pdf":
            reader = PdfReader(file_path)
            content = "\n".join(page.extract_text() or "" for page in reader.pages)
        else:
            continue
        documents.append(f"\nDOCUMENTO: {file_path.name}\n{content}")
    return "\n".join(documents)


def main():
    knowledge = load_knowledge()
    if not knowledge.strip():
        raise ValueError("No se encontró información empresarial.")

    instructions_path = BASE_DIR / "config" / "agent_instructions.txt"
    instructions = instructions_path.read_text(encoding="utf-8")

    system_instruction = f"""
{instructions}

REGLAS ESTRATÉGICAS OBLIGATORIAS:
1. El mercado prioritario es Colombia.
2. La prioridad comercial es captar clientes para entrenamiento personalizado virtual.
3. La venta de accesorios fitness es secundaria.
4. No inventes precios, servicios, resultados, credenciales ni condiciones.
5. Diferencia hechos documentados, datos externos, hipótesis y recomendaciones.
6. Si falta información, indícalo explícitamente.

BASE DE CONOCIMIENTO:
{knowledge}
"""
    chat = client.chats.create(
        model=MODELO,
        config={"system_instruction": system_instruction}
    )

    print("\nFITACCESORIOS AI AGENT v2.2")
    print("-" * 44)
    print("Base de conocimiento cargada.")
    print("Modo autónomo disponible: escribe /auto seguido de tu objetivo.")
    print("Modo normal disponible: escribe una consulta o tarea.")
    print("Escribe 'salir' para terminar.")

    while True:
        question = input("\nTú: ").strip()
        if question.lower() == "salir":
            print("Agente finalizado.")
            break
        if not question:
            continue

        try:
            if question.lower().startswith("/auto "):
                objetivo = question[6:].strip()
                if objetivo:
                    ejecutar_objetivo_autonomo(client, objetivo)
                else:
                    print("Escribe un objetivo después de /auto.")
                continue

            tarea = clasificar_tarea(client, question)
            print(f"\nTarea identificada: {tarea}")

            if tarea != "general":
                resultado = ejecutar_tarea(client, tarea, question)
                if resultado:
                    print(resultado)
            else:
                response = chat.send_message(question)
                print("\nFITACCESORIOS AGENT:")
                print(response.text or "No se obtuvo respuesta.")

        except Exception as error:
            print(f"\nError al procesar la solicitud: {error}")


if __name__ == "__main__":
    main()
