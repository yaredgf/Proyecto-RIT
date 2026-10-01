 # pip install requests


import requests

from bs4 import BeautifulSoup

# 1. Define la URL del sitio web que quieres descargar
url = "https://ejemplo.com"

# 2. Realiza la petición GET a la página
response = requests.get(url)

# 3. Verifica que la petición fue exitosa (código 200)
if response.status_code == 200:
    # 4. Abre un archivo local en modo escritura de texto con codificación utf-8
    with open("pagina.html", "w", encoding="utf-8") as archivo:
        archivo.write(response.text)
    print("¡Archivo HTML descargado con éxito!")
else:
    print(f"Error al acceder a la página: {response.status_code}")







html_doc = "<html><body><p class='old'>Hola</p></body></html>"
soup = BeautifulSoup(html_doc, 'html.parser')

# Modificar el texto y un atributo
parrafo = soup.find('p')
parrafo.string = 'Hola Mundo'
parrafo['class'] = 'new'

print(soup.prettify())
