
import os
from dotenv import load_dotenv
from google import genai

from tools.task_router import clasificar_tarea


load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

pruebas = [
    "Identifica mis cinco principales competidores en Colombia.",
    "Dame cinco publicaciones para Instagram que atraigan clientes.",
    "Analiza el SEO de mi página web.",
    "Cómo puedo conseguir más clientes para entrenamiento virtual?",
    "Identifica empresas que puedan comprar mis accesorios fitness.",
    "Qué es FitAccesorios?"
]

for pregunta in pruebas:

    tarea = clasificar_tarea(client, pregunta)

    print("\nSolicitud:", pregunta)
    print("Categoría:", tarea)
