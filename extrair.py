import sys
import os
import requests
from playwright.sync_api import sync_playwright

def extrair_link_direto(url_alvo):
    print(f"Iniciando extração para: {url_alvo}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
        )
        page = context.new_page()
        
        link_final = None

        # Intercepta as requisições de rede para capturar o APK assim que ele é chamado
        def interceptar_resposta(response):
            nonlocal link_final
            url = response.url
            if ("dl.modplays.com" in url or "files.modyolo.com" in url or (".apk" in url and "play.google.com" not in url)):
                link_final = url

        page.on("response", interceptar_resposta)

        try:
            page.goto(url_alvo, wait_until="domcontentloaded", timeout=60000)
            
            # ESPERA O TIMER DO SITE (10 a 15 segundos)
            print("Aguardando o timer da página carregar o botão real...")
            page.wait_for_timeout(12000)

            # Busca por links gerados após o timer
            hrefs = page.eval_on_selector_all("a[href]", "elements => elements.map(e => e.href)")
            for href in hrefs:
                if ("dl.modplays.com" in href or "files.modyolo.com" in href or href.endswith(".apk")) and "play.google.com" not in href:
                    link_final = href
                    break

            # Se não pegou link direto no href, tenta clicar no botão azul de download
            if not link_final:
                print("Tentando clicar no botão de download após o timer...")
                btn = page.query_selector("a[href*='download'], a.download-button, a.btn-download, .download-btn, a[aria-label*='Download']")
                if btn:
                    btn.click(force=True, timeout=5000)
                    page.wait_for_timeout(5000)

        except Exception as e:
            print(f"Erro na navegação: {e}")

        browser.close()
        return link_final

def salvar_no_firebase(url_origem, link_direto):
    partes = url_origem.rstrip('/').split('/')
    id_jogo = partes[-2] if len(partes) >= 2 else "jogo"
    id_jogo = id_jogo.replace('.html', '').replace('.a', '')
    
    firebase_base_url = "https://meublog-apks-default-rtdb.firebaseio.com"
    payload = {
        "url_original": url_origem,
        "link_direto": link_direto
    }
    
    try:
        res1 = requests.patch(f"{firebase_base_url}/links/{id_jogo}.json", json=payload)
        res2 = requests.patch(f"{firebase_base_url}/jogos/{id_jogo}.json", json=payload)
        if res1.status_code == 200:
            print(f"Link salvo no Firebase com sucesso para: {id_jogo}")
    except Exception as e:
        print(f"Erro no Firebase: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].startswith("http"):
        url_single = sys.argv[1]
        link = extrair_link_direto(url_single)
        if link:
            salvar_no_firebase(url_single, link)
            print(f"LINK_ENCONTRADO:{link}")
        else:
            print("Nenhum link direto encontrado.")
