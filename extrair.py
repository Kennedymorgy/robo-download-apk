import sys
import os
import requests
from playwright.sync_api import sync_playwright

try:
    from playwright_stealth import stealth_sync
except ImportError:
    stealth_sync = None

def buscar_link_atual_firebase(id_jogo):
    """Consulta o Firebase para ver qual link já está salvo."""
    firebase_base_url = "https://meublog-apks-default-rtdb.firebaseio.com"
    try:
        res = requests.get(f"{firebase_base_url}/links/{id_jogo}/link_direto.json")
        if res.status_code == 200 and res.text != 'null':
            return res.json()
    except Exception as e:
        print(f"Erro ao consultar Firebase: {e}")
    return None

def salvar_no_firebase_se_novo(url_origem, link_novo):
    partes = url_origem.rstrip('/').split('/')
    id_jogo = partes[-2] if len(partes) >= 2 else "jogo"
    id_jogo = id_jogo.replace('.html', '').replace('.a', '')

    # 1. Verifica se o link salvo no Firebase já é o mesmo
    link_atual = buscar_link_atual_firebase(id_jogo)
    if link_atual == link_novo:
        print(f"⏩ O link para '{id_jogo}' continua o mesmo. Nenhuma alteração feita no Firebase.")
        return

    # 2. Se for um link novo ou diferente, faz a atualização
    print(f"🔄 Link novo detectado para '{id_jogo}'! Atualizando no Firebase...")
    firebase_base_url = "https://meublog-apks-default-rtdb.firebaseio.com"
    payload = {
        "url_original": url_origem,
        "link_direto": link_novo
    }

    try:
        res1 = requests.patch(f"{firebase_base_url}/links/{id_jogo}.json", json=payload)
        res2 = requests.patch(f"{firebase_base_url}/jogos/{id_jogo}.json", json=payload)
        if res1.status_code == 200:
            print(f"✅ Link atualizado com sucesso no Firebase para: {id_jogo}")
    except Exception as e:
        print(f"❌ Erro ao salvar no Firebase: {e}")

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

        def interceptar_requisicao(request):
            nonlocal link_final
            url = request.url
            if "cdn-cgi" not in url and "challenge-platform" not in url and not url.startswith("blob:"):
                if ("dl.modplays.com" in url or "files.modyolo.com" in url or ".apk" in url):
                    if "play.google.com" not in url:
                        if url.endswith(".apk") or "download" in url or "file" in url:
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

            print("Aguardando 16s pelo timer do Modplays...")
            page.wait_for_timeout(16000)

            if not link_final:
                hrefs = page.eval_on_selector_all("a[href]", "elements => elements.map(e => e.href)")
                for href in hrefs:
                    if "cdn-cgi" not in href and not href.startswith("blob:"):
                        if ("dl.modplays.com" in href or "files.modyolo.com" in href or href.endswith(".apk")):
                            if "play.google.com" not in href:
                                link_final = href
                                break

            if not link_final:
                print("Tentando disparar download no evento do botão...")
                for b in page.locator("a[href], button").all():
                    try:
                        href = b.get_attribute("href") or ""
                        if "cdn-cgi" not in href and ("dl.modplays.com" in href or href.endswith(".apk")):
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

        except Exception as e:
            print(f"Erro na navegação: {e}")

        browser.close()
        return link_final

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].startswith("http"):
        url_single = sys.argv[1]
        link = extrair_link_direto(url_single)
        if link:
            salvar_no_firebase_se_novo(url_single, link)
            print(f"LINK_ENCONTRADO:{link}")
        else:
            print("Nenhum link direto encontrado.")
