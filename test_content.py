
from unittest.mock import patch

from tools.content import generar_contenido


contenido_inicial = """
Plan Inicio Fitness.
Resultados garantizados.
Precio: $89.900 COP al mes.
"""

contenido_corregido = """
Plan Inicio Fitness.
Precio: $89.900 COP.
Rutina inicial básica, guía simple de alimentación
y soporte limitado por WhatsApp.
"""

auditoria_aprobada = {
    "aprobado": True,
    "errores": [],
    "advertencias": [],
    "observaciones": "Contenido correcto."
}


class RespuestaSimulada:
    def __init__(self, texto):
        self.text = texto


class GeminiSimulado:
    def __init__(self):
        self.models = self
        self.llamadas = 0

    def generate_content(self, **kwargs):
        self.llamadas += 1

        if self.llamadas == 1:
            return RespuestaSimulada(contenido_inicial)

        return RespuestaSimulada(contenido_corregido)


client_simulado = GeminiSimulado()


with patch(
    "tools.content.validar_contenido",
    return_value=auditoria_aprobada
) as auditoria, patch(
    "tools.content.guardar_contenido"
) as guardado:

    generar_contenido(
        client_simulado,
        "Crea una publicación para el Plan Inicio Fitness."
    )

    print("\nRESULTADOS DE LA PRUEBA")
    print("Llamadas simuladas a Gemini:", client_simulado.llamadas)
    print("Auditorías de Gemini:", auditoria.call_count)
    print("¿Se guardó el contenido?:", guardado.called)

    if (
        client_simulado.llamadas == 2
        and auditoria.call_count == 1
        and guardado.called
    ):
        print("\nPRUEBA SUPERADA")
    else:
        print("\nPRUEBA NO SUPERADA")
