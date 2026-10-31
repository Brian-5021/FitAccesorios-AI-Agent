
import requests
from bs4 import BeautifulSoup


def leer_pagina(url):
    try:
        encabezados = {
            "User-Agent": "Mozilla/5.0 (compatible; FitAccesoriosAgent/1.0)"
        }

        respuesta = requests.get(
            url,
            headers=encabezados,
            timeout=15
        )

        respuesta.raise_for_status()

        soup = BeautifulSoup(respuesta.text, "html.parser")

        # Eliminar elementos que no aportan información comercial
        for elemento in soup([
            "script",
            "style",
            "nav",
            "footer",
            "header",
            "noscript"
        ]):
            elemento.decompose()

        titulo = soup.title.get_text(strip=True) if soup.title else "Sin título"

        contenido = soup.get_text(separator=" ", strip=True)

        return {
            "url": url,
            "titulo": titulo,
            "contenido": contenido[:12000]
        }

    except requests.RequestException as error:
        return {
            "url": url,
            "error": str(error)
        }


if __name__ == "__main__":
    url = input("Introduce la URL que quieres analizar: ")

    resultado = leer_pagina(url)

    print("\nRESULTADO DE LA EXTRACCIÓN\n")
    print(resultado)
