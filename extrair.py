import sys
import os
import time
import requests
from playwright.sync_api import sync_playwright

try:
    from playwright_stealth import stealth_sync
except ImportError:
    stealth_sync = None

def extrair_link_direto(url_alvo):
    print(f"Iniciando extração para: {url_alvo}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-infobars',
                '--window-size=375,812',
            ]
        )
        
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Linux; Android 13; SM-G998B) AppleWebKit/537.36 (KHTML, Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            viewport={"width": 375, "height": 812},
            is_mobile=True,
            has_touch=True,
            locale="pt-BR",
            accept_downloads=True
        )
        
        page = context.new_page()
        
        if stealth_sync:
            stealth_sync(page)
        else:
            page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")

        link_final = None

        # Intercepta requisições HTTP reais (ignorando blobs e chamadas do cloudflare)
        def interceptar_requisicao(request):
            nonlocal link_final
            url = request.url
            if not url.startswith("blob:") and ("dl.modplays.com" in url or "files.modyolo.com" in url or ".apk" in url):
                if "play.google.com" not in url and "cloudflare" not in url:
                    link_final = url

        page.on("request", interceptar_requisicao)

        try:
            page.goto(url_alvo, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(4000)

            if "cloudflare" in page.content().lower() or "just a moment" in page.title().lower():
                print("Detectado Cloudflare Challenge, aguardando resolução...")
                page.wait_for_timeout(8000)

            print("Procurando botão inicial de download...")
            botoes = page.locator("a, button").all()
            for b in botoes:
                try:
                    texto = (b.inner_text() or "").lower()
                    href = b.get_attribute("href") or ""
                    if ("download" in texto or "download" in href) and "play.google.com" not in href:
                        b.click(force=True, timeout=3000)
                        print("Botão acionado com sucesso!")
                        break
                except:
                    continue

            print("Aguardando 15s pelo timer do Modplays...")
            page.wait_for_timeout(15000)

            # Procura links <a href="..."> diretamente na página ignorando o protocolo blob
            hrefs = page.eval_on_selector_all("a[href]", "elements => elements.map(e => e.href)")
            for href in hrefs:
                if not href.startswith("blob:") and ("dl.modplays.com" in href or "files.modyolo.com" in href or href.endswith(".apk")):
                    if "play.google.com" not in href:
                        link_final = href
                        break

            # Se ainda não encontrou o link direto, tenta capturar o evento de download do navegador
            if not link_final:
                print("Tentando clicar no botão final para disparar o download...")
                for b in page.locator("a[href], button").all():
                    try:
                        href = b.get_attribute("href") or ""
                        if ("dl.modplays.com" in href or "files.modyolo.com" in href or ".apk" in href) and not href.startswith("blob:"):
                            link_final = href
                            break
                        elif "download" in (b.inner_text() or "").lower():
                            with page.expect_download(timeout=5000) as download_info:
                                b.click(force=True)
                            download = download_info.value
                            link_final = download.url
                            break
                    except:
                        continue

            if not link_final:
                print("\n--- LINKS ENCONTRADOS PÓS-TIMER ---")
                for h in hrefs[:15]:
                    if not h.startswith("blob:"):
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
