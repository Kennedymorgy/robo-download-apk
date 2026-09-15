import os
import json
import requests
import xml.etree.ElementTree as ET

try:
    from google.oauth2 import service_account
    import google.auth.transport.requests
except ImportError:
    service_account = None

# CREDENCIAIS E LINKS
GOOGLE_CREDENTIALS_JSON = os.environ.get("GOOGLE_CREDENTIALS_JSON")
SITEMAP_BLOGGER = "https://k-404modapk.blogspot.com/sitemap.xml"
PAGINA_INICIAL = "https://k-404modapk.blogspot.com/?m=1"

def obter_urls_do_sitemap():
    """Lê todas as URLs publicadas no seu sitemap do Blogger."""
    print(f"🌐 Lendo Sitemap: {SITEMAP_BLOGGER}")
    urls = [PAGINA_INICIAL]
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(SITEMAP_BLOGGER, headers=headers, timeout=15)
        if res.status_code == 200:
            tree = ET.fromstring(res.content)
            ns = {'g': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            for loc in tree.findall('.//g:loc', ns):
                link = loc.text.strip()
                if link and link not in urls:
                    urls.append(link)
            print(f"✅ Total de {len(urls)} URLs encontradas no Sitemap.")
        else:
            print(f"⚠️ Falha ao ler Sitemap ({res.status_code})")
    except Exception as e:
        print(f"❌ Erro ao processar Sitemap: {e}")
    return urls

def enviar_para_google_indexing(url):
    """Envia solicitação direta de indexação para a API do Google."""
    if not GOOGLE_CREDENTIALS_JSON or not service_account:
        print("⚠️ Secret GOOGLE_CREDENTIALS_JSON não encontrada ou biblioteca ausente.")
        return

    try:
        info = json.loads(GOOGLE_CREDENTIALS_JSON)
        scopes = ["https://www.googleapis.com/auth/indexing"]
        credentials = service_account.Credentials.from_service_account_info(info, scopes=scopes)
        
        req = google.auth.transport.requests.Request()
        credentials.refresh(req)

        endpoint = "https://indexing.googleapis.com/v1/urlNotifications:publish"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {credentials.token}"
        }
        payload = {
            "url": url,
            "type": "URL_UPDATED"
        }

        res = requests.post(endpoint, headers=headers, json=payload)
        if res.status_code == 200:
            print(f"🚀 Indexado no Google: {url}")
        else:
            print(f"❌ Erro ({res.status_code}) na URL {url}: {res.text}")
    except Exception as e:
        print(f"❌ Erro na API do Google: {e}")

if __name__ == "__main__":
    print("🤖 Iniciando Robô Solo de Indexação (Google + Sitemap)...")
    urls_para_indexar = obter_urls_do_sitemap()
    
    for url in urls_para_indexar:
        enviar_para_google_indexing(url)
        
    print("✨ Trabalho concluído com sucesso!")
