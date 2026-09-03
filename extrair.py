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

        def interceptar_resposta(response):
            nonlocal link_final
            url = response.url
            # Captura Modyolo, Modplays e links diretos de APK
            if (".apk" in url or "files.modyolo.com" in url or "dl.modplays.com" in url) and "play.google.com" not in url:
                link_final = url

        page.on("response", interceptar_resposta)

        try:
            page.goto(url_alvo, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(3000)

            # Procura e clica em botões de download (Modyolo / Modplays)
            botoes = page.query_selector_all("a, button, .download-btn, .btn-download")
            for b in botoes:
                href = b.get_attribute("href") or ""
                texto = b.inner_text().lower()
                
                if "play.google.com" in href:
                    continue
                    
                if "download" in texto or "download" in href or ".apk" in href or "modplays" in href:
                    try:
                        b.click(force=True, timeout=5000)
                        page.wait_for_timeout(3000)
                    except:
                        pass
                if link_final:
                    break

            # Varredura no DOM caso o clique não tenha disparado requisição
            if not link_final:
                links = page.query_selector_all("a[href]")
                for l in links:
                    href = l.get_attribute("href") or ""
                    if (".apk" in href or "files.modyolo.com" in href or "dl.modplays.com" in href) and "play.google.com" not in href:
                        link_final = href
                        break

        except Exception as e:
            print(f"Erro na extração: {e}")

        browser.close()
        return link_final

def processar_todos_os_jogos():
    firebase_base_url = "https://meublog-apks-default-rtdb.firebaseio.com"
    
    try:
        res = requests.get(f"{firebase_base_url}/jogos.json")
        if res.status_code != 200 or not res.json():
            print("Nenhum jogo encontrado no banco para atualizar.")
            return
            
        jogos = res.json()
        
        for id_jogo, dados in jogos.items():
            url_origem = dados.get("url_original")
            if not url_origem:
                continue
                
            print(f"\n--- Processando: {id_jogo} ---")
            novo_link = extrair_link_direto(url_origem)
            
            if novo_link:
                payload = {
                    "url_original": url_origem,
                    "link_direto": novo_link
                }
                requests.patch(f"{firebase_base_url}/links/{id_jogo}.json", json=payload)
                requests.patch(f"{firebase_base_url}/jogos/{id_jogo}.json", json=payload)
                print(f"✓ Link atualizado para {id_jogo}!")
            else:
                print(f"✗ Não foi possível extrair o link para {id_jogo}.")

    except Exception as e:
        print(f"Erro geral no processamento: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].startswith("http"):
        url_single = sys.argv[1]
        link = extrair_link_direto(url_single)
        if link:
            partes = url_single.rstrip('/').split('/')
            id_jogo = partes[-2] if len(partes) >= 2 else "jogo"
            id_jogo = id_jogo.replace('.html', '').replace('.a', '')
            
            firebase_base_url = "https://meublog-apks-default-rtdb.firebaseio.com"
            payload = {"url_original": url_single, "link_direto": link}
            requests.patch(f"{firebase_base_url}/links/{id_jogo}.json", json=payload)
            requests.patch(f"{firebase_base_url}/jogos/{id_jogo}.json", json=payload)
            print(f"LINK_ENCONTRADO:{link}")
    else:
        processar_todos_os_jogos()
