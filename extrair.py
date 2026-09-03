import sys
import os
import requests
from playwright.sync_api import sync_playwright
try:
    from playwright_stealth import stealth_sync
except ImportError:
    stealth_sync = None

def extrair_link_direto(url_alvo):
    print(f"Iniciando extração para: {url_alvo}")
    
    with sync_playwright() as p:
        # Lança Chromium com argumentos para evitar detecção do Cloudflare
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
            locale="pt-BR"
        )
        
        page = context.new_page()
        
        # Aplica stealth se disponível
        if stealth_sync:
            stealth_sync(page)
        else:
            # Script manual anti-bot básico
            page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")

        link_final = None

        def interceptar_resposta(response):
            nonlocal link_final
            url = response.url
            if ("dl.modplays.com" in url or "files.modyolo.com" in url or (".apk" in url and "play.google.com" not in url)):
                link_final = url

        page.on("response", interceptar_resposta)

        try:
            # Carrega a página
            page.goto(url_alvo, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(4000)

            # Verifica se caiu no Cloudflare e espera passar
            if "cloudflare" in page.content().lower() or "just a moment" in page.title().lower():
                print("Detectado Cloudflare Challenge, aguardando resolução...")
                page.wait_for_timeout(8000)

            # 1. Clique inicial no botão de download para ativar o timer
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

            # 2. Espera o timer (15 segundos)
            print("Aguardando 15s pelo timer do Modplays...")
            page.wait_for_timeout(15000)

            # 3. Busca o link direto pós-timer
            hrefs = page.eval_on_selector_all("a[href]", "elements => elements.map(e => e.href)")
            for href in hrefs:
                if ("dl.modplays.com" in href or "files.modyolo.com" in href or href.endswith(".apk")) and "play.google.com" not in href:
                    link_final = href
                    break

            # 4. Tenta clicar no botão gerado após o timer
            if not link_final:
                print("Tentando clicar no botão gerado pós-timer...")
                for b in page.locator("a[href]").all():
                    try:
                        href = b.get_attribute("href") or ""
                        if ("dl.modplays.com" in href or "files.modyolo.com" in href or ".apk" in href) and "play.google.com" not in href:
                            link_final = href
                            break
                    except:
                        continue

            if not link_final:
                print("\n--- LINKS ENCONTRADOS PÓS-CLOUDFLARE ---")
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
