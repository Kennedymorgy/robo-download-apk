import os
import json
import requests
import xml.etree.ElementTree as ET

try:
    from google.oauth2 import service_account
    import google.auth.transport.requests
except ImportError:
    service_account = None

# CREDENCIAIS E MAPA DO SITE
GOOGLE_CREDENTIALS_JSON = os.environ.get("GOOGLE_CREDENTIALS_JSON")
SITEMAP_BLOGGER = "https://k-404modapk.blogspot.com/sitemap.xml"
PAGINA_INICIAL = "https://k-404modapk.blogspot.com/?m=1"

def obter_urls_do_sitemap():
    """Busca todas as URLs publicadas no Sitemap XML do Blogger."""
    print(f"🌐 Lendo Sitemap do Blog: {SITEMAP_BLOGGER}")
    urls = [PAGINA_INICIAL]
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(SITEMAP_BLOGGER, headers=headers, timeout=15)
        if res.status_code == 200:
            tree = ET.fromstring(res.content)
            # Namespace padrão do Blogger / Sitemaps
            ns = {'g': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            for loc in tree.findall('.//g:loc', ns):
                link = loc.text.strip()
                if link and link not in urls:
                    urls.append(link)
            print(f"✅ Total de {len(urls)} URLs encontradas para indexar.")
        else:
            print(f"⚠️ Erro ao acessar Sitemap ({res.status_code})")
    except Exception as e:
        print(f"❌ Falha ao processar Sitemap XML: {e}")
    return urls

def notificar_google_indexing(url):
    """Envia a URL para a Google Indexing API usando a Conta de Serviço (e-mail autenticado)."""
    if not GOOGLE_CREDENTIALS_JSON:
        print("⚠️ Secret GOOGLE_CREDENTIALS_JSON não encontrada.")
        return

    if not service_account:
        print("⚠️ Módulo 'google-auth' não encontrado.")
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
            print(f"🚀 [OK] Indexação enviada -> {url}")
        else:
            print(f"❌ Erro ({res.status_code}) ao indexar {url}: {res.text}")
    except Exception as e:
        print(f"❌ Erro crítico no envio para o Google: {e}")

if __name__ == "__main__":
    print("🤖 Iniciando Robô Solo de Indexação Automática...")
    lista_urls = obter_urls_do_sitemap()
    
    for url_jogo in lista_urls:
        notificar_google_indexing(url_jogo)
        
    print("✨ Processo concluído com sucesso!")
