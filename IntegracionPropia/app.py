# pip install requests
# pip install beautifulsoup4

import requests

from bs4 import BeautifulSoup 
import threading
import time
import json
from concurrent.futures import ThreadPoolExecutor

maximo = 100000
configuracion = [{}]
enlacesBuscados = []
enlacesPorBuscar = []
urlsBase = ["https://www.cisa.gov/news-events/cybersecurity-advisories",
            "https://www.microsoft.com/en-us/security/blog/topic/threat-intelligence/",
            "https://ubuntu.com/security/notices",
            "https://www.debian.org/security/",
            "https://blog.talosintelligence.com/",
            "https://unit42.paloaltonetworks.com/",
            "https://securelist.com/",
            "https://cwe.mitre.org/data/definitions/79.html",
            "https://capec.mitre.org/data/definitions/100.html"
         ]
baneos = ["mailto:","youtube.com","x.com","facebook.com","instagram.com","twitter.com","linkedin.com","www.reddit",
          ".pdf", ".zip", ".gz", ".tar", ".exe", ".msi",
              ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp",
              ".mp4", ".mp3", ".css", ".js", ".xml", ".json"]
whitelist = ["https://www.microsoft.com/en-us/security/blog.",
             "https://www.cisa.gov/news-events",
             "https://ubuntu.com/security/notices",
             "https://lists.debian.org/debian-security-announce",
             "https://blog.talosintelligence.com/",
             "https://unit42.paloaltonetworks.com/",
             "https://securelist.com/",
             "https://cwe.mitre.org/data/definitions/",
             "https://capec.mitre.org/data/definitions/"]

def ObtenerConfiguracion():
    with open("settingsCrawler.json", "r", encoding="utf-8") as archivo:
        configuracion[0] = json.load(archivo)

def ObtenerListas():
    with open("IntegracionPropia/enlacesBuscados.json", "r", encoding="utf-8") as archivo:
        enlacesBuscados.extend(json.load(archivo)["enlacesBuscados"])

def GuardarListas():
    with open("IntegracionPropia/producto.json", "w", encoding="utf-8") as archivo:
        json.dump({"enlacesBuscados": enlacesBuscados}, archivo, indent=4, ensure_ascii=False)




def AgregarEnlaces(enlaces):
    for a in enlaces:
        estaWhiteList=False
        noBaneado=True
        if a in enlacesBuscados:
            continue
        if a in enlacesPorBuscar:
            continue

        for sitio in whitelist:
            if a.find(sitio) != -1:
                estaWhiteList = True
                break

        if estaWhiteList:
            for sitio in baneos:
                if a.find(sitio) != -1:
                    noBaneado = False
                    break
        
            if noBaneado:
                enlacesPorBuscar.append(a)

def DescargarPagina(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
        
                titulo = "-".join(url.split("//")[1].split("/")).split("?")[0]
        
                path="IntegracionPropia/Pruebas/"+titulo+".html"
                pathtxt="IntegracionPropia/Texto/"+titulo+".txt"
        
                with open(path, "w", encoding="utf-8") as archivo:
                    archivo.write(response.text)

                with open(pathtxt, "w", encoding="utf-8") as archivo:
                    archivo.write(soup.get_text())

                enlaces = soup.find_all('a')
                links = [] # Estos son los que se van a devolver
                for a in enlaces:
                    if type(a.get('href')) != str:
                        continue
                    
                    if a.get('href').find("http") != -1:
                        links.append(a.get('href'))

                    if a.get('href')[0] == "/":
                        base = url.split("/")
                        links.append(base[0]+"//"+base[2]+a.get('href'))

                print("Se descargo "+url)
                return soup.get_text(), links, True
    except:
        print("Error en "+url)
    
    return "", [], False


def Crawlear(idHilo):
    guardarEnlaces = True
    while (len(enlacesPorBuscar) > 0):
        enlace = enlacesPorBuscar.pop()
        enlacesBuscados.append(enlace)
        print("Hilo "+str(idHilo)+" prueba: "+enlace)
        texto, enlaces, siDescarga = DescargarPagina(enlace)
        if not siDescarga:
            continue

        if not guardarEnlaces:
            continue

        if len(enlacesBuscados) < maximo:
            AgregarEnlaces(enlaces)
        else:
            guardarEnlaces = False


def IniciarCrawler ():
    ObtenerConfiguracion()
    ObtenerListas()
    enlacesPorBuscar.extend(urlsBase)

    numHilos = configuracion[0]["descarga"]["concurrencia_total"]
    hilos = []
    '''
    with ThreadPoolExecutor(max_workers=numHilos) as executor:
        # executor.map ejecuta la función pasando cada elemento de la lista a un hilo
        resultados = executor.map(Crawlear, range(numHilos))
    '''
    # 1. Crea e inicia los N hilos
    for i in range(numHilos):
        hilo = threading.Thread(target=Crawlear, args=(i,))
        hilos.append(hilo)
        hilo.start()

    # 2. Esperar a que TODOS los hilos terminen antes de continuar
    for hilo in hilos:
        hilo.join()


    GuardarListas()
    print("Listoooo!")
    


IniciarCrawler()