
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from pypdf import PdfReader

from tools.task_router import clasificar_tarea
from tools.task_executor import ejecutar_tarea


# Configuración
load_dotenv()

BASE_DIR = Path(__file__).parent
KNOWLEDGE_DIR = BASE_DIR / "knowledge"

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("No se encontró la API key.")

client = genai.Client(api_key=api_key)


def load_knowledge():
    """Lee los documentos de conocimiento de FitAccesorios."""

    documents = []

    for file_path in sorted(KNOWLEDGE_DIR.iterdir()):

        if file_path.suffix == ".md":
            content = file_path.read_text(encoding="utf-8")

            documents.append(
                f"\nDOCUMENTO: {file_path.name}\n{content}"
            )

        elif file_path.suffix == ".pdf":
            reader = PdfReader(file_path)

            pages = [
                page.extract_text() or ""
                for page in reader.pages
            ]

            content = "\n".join(pages)

            documents.append(
                f"\nDOCUMENTO: {file_path.name}\n{content}"
            )

    return "\n".join(documents)


def main():

    knowledge = load_knowledge()

    if not knowledge.strip():
        raise ValueError("No se encontró información empresarial.")

    # Cargar instrucciones estratégicas
    instructions_path = (
        BASE_DIR / "config" / "agent_instructions.txt"
    )

    instructions = instructions_path.read_text(
        encoding="utf-8"
    )

    system_instruction = f"""
{instructions}

REGLAS ESTRATÉGICAS OBLIGATORIAS:

1. El mercado prioritario de FitAccesorios es Colombia.
2. No priorices España, México u otros países.
3. No inventes servicios, precios, certificaciones,
   resultados, clientes ni características empresariales.
4. Si un dato no está documentado, indica que no tienes
   información suficiente para confirmarlo.
5. Prioriza comercialmente la captación de clientes
   para entrenamiento personalizado virtual.
6. La venta de accesorios fitness es la segunda
   línea comercial.

BASE DE CONOCIMIENTO DE FITACCESORIOS:

{knowledge}
"""

    chat = client.chats.create(
        model="gemini-3.5-flash-lite",
        config={
            "system_instruction": system_instruction
        }
    )

    print("\nFITACCESORIOS AI AGENT")
    print("-" * 40)
    print("Base de conocimiento cargada.")
    print("Memoria conversacional activada.")
    print("Clasificador de tareas activado.")
    print("\nEscribe 'salir' para terminar.")

    while True:

        question = input("\nTú: ").strip()

        if question.lower() == "salir":
            print("Agente finalizado.")
            break

        if not question:
            continue

        try:
            # Identificar el tipo de tarea
            tarea = clasificar_tarea(client, question)

            print(f"\nTarea identificada: {tarea}")

            # Ejecutar tareas especializadas
            if tarea != "general":

                ejecutar_tarea(
                    client,
                    tarea,
                    question
                )

            # Consultas generales con memoria conversacional
            else:
                response = chat.send_message(question)

                print("\nFITACCESORIOS AGENT:")
                print(response.text)

        except Exception as error:
            print(f"\nError al procesar la solicitud: {error}")


if __name__ == "__main__":
    main()
