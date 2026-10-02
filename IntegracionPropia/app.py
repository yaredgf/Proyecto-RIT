# pip install requests
# pip install beautifulsoup4

import requests

from bs4 import BeautifulSoup 


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
baneos = ["mailto.","youtube.com","x.com","facebook.com","instagram.com","twitter.com","linkedin.com",".pdf","www.reddit"]
whitelist = ["https://www.microsoft.com/en-us/security/blog.",
             "https://www.cisa.gov/news-events",
             "https://ubuntu.com/security/notices",
             "https://lists.debian.org/debian-security-announce",
             "https://blog.talosintelligence.com/",
             "https://unit42.paloaltonetworks.com/",
             "https://securelist.com/",
             "https://cwe.mitre.org/data/definitions/",
             "https://capec.mitre.org/data/definitions/"]


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
    print("Descargando "+url)
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
                
                return soup.get_text(), links, True
    except:
        print("Error en "+url)
    
    return "", [], False


def Crawlear(maximo):
    guardarEnlaces = True
    while (len(enlacesPorBuscar) > 0):
        enlace = enlacesPorBuscar.pop()
        enlacesBuscados.append(enlace)
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
    enlacesPorBuscar.append(urlsBase[0])
    Crawlear(1000)
    


IniciarCrawler()