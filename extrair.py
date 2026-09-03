import sys
import os
import requests
from playwright.sync_api import sync_playwright

def extrair_link(url_alvo):
    print(f"Iniciando busca para a URL: {url_alvo}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Configura o navegador como um celular Android real
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
        )
        page = context.new_page()
        
        link_final = None

        # Escuta os downloads disparados pelo navegador
        def tratar_download(download):
            nonlocal link_final
            link_final = download.url

        page.on("download", tratar_download)

        # Escuta requisições de rede
        def interceptar_resposta(response):
            nonlocal link_final
            url = response.url
            if ("files.modyolo.com" in url or ".apk" in url) and "play.google.com" not in url:
                link_final = url

        page.on("response", interceptar_resposta)

        try:
            page.goto(url_alvo, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(5000)

            # Clica no botão primário do Modyolo (ex: "Download (170MB)" ou similar)
            botoes = page.query_selector_all("a, button, div.download-button, .btn-download")
            for b in botoes:
                texto = b.inner_text().lower()
                href = b.get_attribute("href") or ""
                
                if "download" in texto or "files.modyolo.com" in href or ".apk" in href:
                    if "play.google.com" in href:
                        continue
                    try:
                        b.click(force=True, timeout=5000)
                        page.wait_for_timeout(5000)
                    except:
                        pass
                    if link_final:
                        break

            # Varredura secundária caso o link apareça no DOM após o clique
            if not link_final:
                links = page.query_selector_all("a[href]")
                for l in links:
                    href = l.get_attribute("href") or ""
                    if ("files.modyolo.com" in href or href.endswith(".apk")) and "play.google.com" not in href:
                        link_final = href
                        break

        except Exception as e:
            print(f"Erro na navegação: {e}")

        browser.close()
        
        if link_final:
            print(f"LINK_ENCONTRADO:{link_final}")
            salvar_no_firebase(url_alvo, link_final)
        else:
            print("Nenhum link direto encontrado.")

def salvar_no_firebase(url_origem, link_direto):
    partes = url_origem.rstrip('/').split('/')
    id_jogo = partes[-2] if len(partes) >= 2 else "jogo"
    
    firebase_endpoint = f"https://meublog-apks-default-rtdb.firebaseio.com/links/{id_jogo}.json"
    
    dados = {
        "url_original": url_origem,
        "link_direto": link_direto
    }
    
    try:
        response = requests.patch(firebase_endpoint, json=dados)
        if response.status_code == 200:
            print("Link salvo no Firebase com sucesso!")
        else:
            print(f"Erro no Firebase: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Erro na conexao com Firebase: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = "https://modyolo.com/download/baseball-9-21102/1"
        
    extrair_link(url)
