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

        # Intercepta as requisições de rede
        def interceptar_resposta(response):
            nonlocal link_final
            url = response.url
            if ("dl.modplays.com" in url or "files.modyolo.com" in url or (".apk" in url and "play.google.com" not in url)):
                link_final = url

        page.on("response", interceptar_resposta)

        try:
            page.goto(url_alvo, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(2000)

            # 1. Clica no primeiro botão de download visível para ativar o timer/geração
            print("Procurando e clicando no botão para iniciar...")
            botoes_iniciais = page.locator("a, button, div.download-btn, .btn-download").all()
            for b in botoes_iniciais:
                try:
                    texto = b.inner_text().lower()
                    href = b.get_attribute("href") or ""
                    if ("download" in texto or "download" in href) and "play.google.com" not in href:
                        b.click(force=True, timeout=3000)
                        print("Botão inicial clicado!")
                        break
                except:
                    continue

            # 2. Aguarda 16 segundos para o timer/gerador de link finalizar
            print("Aguardando 16 segundos pelo timer/gerador do Modplays...")
            page.wait_for_timeout(16000)

            # 3. Varredura nos links da página pós-timer
            hrefs = page.eval_on_selector_all("a[href]", "elements => elements.map(e => e.href)")
            for href in hrefs:
                if ("dl.modplays.com" in href or "files.modyolo.com" in href or href.endswith(".apk")) and "play.google.com" not in href:
                    link_final = href
                    break

            # 4. Se ainda não pegou, tenta clicar no botão final que foi liberado após o timer
            if not link_final:
                print("Tentando clicar no botão liberado após o timer...")
                botoes_finais = page.locator("a, button").all()
                for b in botoes_finais:
                    try:
                        href = b.get_attribute("href") or ""
                        if ("dl.modplays.com" in href or "files.modyolo.com" in href or ".apk" in href) and "play.google.com" not in href:
                            b.click(force=True, timeout=3000)
                            page.wait_for_timeout(3000)
                            if link_final:
                                break
                    except:
                        continue

            # Diagnóstico de segurança (se mesmo assim falhar, mostra os links para ajuste)
            if not link_final:
                print("\n--- LINKS ENCONTRADOS NA PÁGINA PARA DIAGNÓSTICO ---")
                for h in hrefs[:15]:
                    print(f"-> {h}")

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
