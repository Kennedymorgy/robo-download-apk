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

        # Intercepta as requisições de rede para capturar o APK no momento em que é disparado
        def interceptar_resposta(response):
            nonlocal link_final
            url = response.url
            if (".apk" in url or "files.modyolo.com" in url or "dl.modplays.com" in url) and "play.google.com" not in url:
                link_final = url

        page.on("response", interceptar_resposta)

        try:
            page.goto(url_alvo, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(3000)

            # Tenta encontrar e clicar no botão principal de download
            botoes = page.locator("a, button, .download-btn, .btn-download").all()
            for b in botoes:
                try:
                    href = b.get_attribute("href") or ""
                    texto = b.inner_text().lower()
                    
                    if "play.google.com" in href:
                        continue
                        
                    if "download" in texto or "download" in href or ".apk" in href or "modplays" in href:
                        b.click(force=True, timeout=3000)
                        page.wait_for_timeout(3000)
                        if link_final:
                            break
                except:
                    continue

            # Se o clique não disparou evento, faz a varredura estática dos links
            if not link_final:
                hrefs = page.eval_on_selector_all("a[href]", "elements => elements.map(e => e.href)")
                for href in hrefs:
                    if (".apk" in href or "files.modyolo.com" in href or "dl.modplays.com" in href) and "play.google.com" not in href:
                        link_final = href
                        break

        except Exception as e:
            print(f"Erro na extração: {e}")

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
            print(f"Link salvo no Firebase com sucesso para a chave: {id_jogo}!")
    except Exception as e:
        print(f"Erro ao conectar ao Firebase: {e}")

def processar_todos_os_jogos():
    firebase_base_url = "https://meublog-apks-default-rtdb.firebaseio.com"
    try:
        res = requests.get(f"{firebase_base_url}/jogos.json")
        if res.status_code != 200 or not res.json():
            print("Nenhum jogo cadastrado no Firebase para atualizar.")
            return
            
        jogos = res.json()
        for id_jogo, dados in jogos.items():
            url_origem = dados.get("url_original")
            if not url_origem:
                continue
                
            print(f"\n--- Processando: {id_jogo} ---")
            novo_link = extrair_link_direto(url_origem)
            if novo_link:
                salvar_no_firebase(url_origem, novo_link)
            else:
                print(f"✗ Não foi possível extrair o link para {id_jogo}.")

    except Exception as e:
        print(f"Erro geral: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].startswith("http"):
        url_single = sys.argv[1]
        link = extrair_link_direto(url_single)
        if link:
            salvar_no_firebase(url_single, link)
            print(f"LINK_ENCONTRADO:{link}")
        else:
            print("Nenhum link direto encontrado.")
    else:
        processar_todos_os_jogos()
