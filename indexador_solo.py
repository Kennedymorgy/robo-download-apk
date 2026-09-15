import os
import json
import requests
import xml.etree.ElementTree as ET

from google.oauth2 import service_account
from googleapiclient.discovery import build

GOOGLE_CREDENTIALS_JSON = os.environ.get("GOOGLE_CREDENTIALS_JSON")
SITEMAP_BLOGGER = "https://k-404modapk.blogspot.com/sitemap.xml"
PAGINA_INICIAL = "https://k-404modapk.blogspot.com/"

def obter_urls_do_sitemap():
    """Busca todas as URLs publicadas no Sitemap XML do Blogger."""
    print(f"🌐 Lendo Sitemap do Blog: {SITEMAP_BLOGGER}")
    urls = [PAGINA_INICIAL]
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(SITEMAP_BLOGGER, headers=headers, timeout=15)
        if res.status_code == 200:
            tree = ET.fromstring(res.content)
            ns = {'g': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            for loc in tree.findall('.//g:loc', ns):
                link = loc.text.strip()
                if link:
                    link_limpo = link.split('?')[0]
                    if link_limpo not in urls:
                        urls.append(link_limpo)
            print(f"✅ Total de {len(urls)} URLs encontradas para indexar.")
        else:
            print(f"⚠️ Erro ao acessar Sitemap ({res.status_code})")
    except Exception as e:
        print(f"❌ Falha ao processar Sitemap XML: {e}")
    return urls

def inicializar_servico_indexing():
    """Autentica e cria o serviço oficial da Google Indexing API."""
    if not GOOGLE_CREDENTIALS_JSON:
        print("⚠️ Secret GOOGLE_CREDENTIALS_JSON não encontrada.")
        return None

    try:
        info = json.loads(GOOGLE_CREDENTIALS_JSON)
        scopes = ["https://www.googleapis.com/auth/indexing"]
        credentials = service_account.Credentials.from_service_account_info(info, scopes=scopes)
        
        service = build('indexing', 'v3', credentials=credentials)
        return service
    except Exception as e:
        print(f"❌ Erro ao autenticar com a API do Google: {e}")
        return None

def notificar_google_indexing(service, url):
    """Envia solicitação de indexação utilizando a biblioteca oficial."""
    try:
        body = {
            "url": url,
            "type": "URL_UPDATED"
        }
        response = service.urlNotifications().publish(body=body).execute()
        print(f"🚀 [OK] Indexação enviada -> {url}")
    except Exception as e:
        print(f"❌ Erro ao indexar {url}: {e}")

if __name__ == "__main__":
    print("🤖 Iniciando Robô Solo de Indexação Automática...")
    
    servico_indexing = inicializar_servico_indexing()
    if servico_indexing:
        lista_urls = obter_urls_do_sitemap()
        for url_jogo in lista_urls:
            notificar_google_indexing(servico_indexing, url_jogo)
        print("✨ Processo concluído com sucesso!")
    else:
        print("❌ Falha de autenticação na API do Google.")
