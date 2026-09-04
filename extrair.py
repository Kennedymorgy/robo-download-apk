import sys
import os
import re
import requests
from playwright.sync_api import sync_playwright

try:
    from playwright_stealth import stealth_sync
except ImportError:
    stealth_sync = None

# Pega as chaves salvas nos Secrets do GitHub
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# SEU BLOG OFICIAL (PÁGINA INICIAL)
PAGINA_INICIAL_BLOG = "https://k-404modapk.blogspot.com/?m=1"

# LOGO REDONDA / FAVICON DO SEU SITE (SÓ VAI USAR ESSA FOTO)
FOTO_OFICIAL_SITE = "https://k-404modapk.blogspot.com/favicon.ico"

def enviar_notificacao_telegram(nome_jogo, versao_jogo, id_jogo):
    """Envia mensagem no Telegram com a foto oficial do site apontando para a página inicial."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Telegram não configurado nos Secrets. Pulando notificação.")
        return

    # Mensagem 100% profissional e sem menções a extração
    mensagem = (
        f"🔥 <b>JOGO ATUALIZADO!</b>\n\n"
        f"🎮 <b>Jogo:</b> {nome_jogo}\n"
        f"📦 <b>Versão:</b> {versao_jogo}\n"
        f"🔗 <b>Página:</b> <a href='{PAGINA_INICIAL_BLOG}'>Baixar no Blog</a>\n\n"
        f"⚡ <i>Nova versão disponível! Clique no link acima para fazer o download com segurança.</i>"
    )

    # Envio para o Telegram utilizando SEMPRE a foto oficial do seu blog
    url_api = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "photo": FOTO_OFICIAL_SITE,
        "caption": mensagem,
        "parse_mode": "HTML"
    }

    try:
        res = requests.post(url_api, json=payload)
        # Se por algum motivo o envio por foto falhar, envia como mensagem de texto
        if res.status_code != 200:
            print(f"⚠️ Erro ao enviar foto ({res.text}). Tentando envio de mensagem...")
            url_api_msg = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            payload_msg = {
                "chat_id": TELEGRAM_CHAT_ID,
                "text": mensagem,
                "parse_mode": "HTML",
                "disable_web_page_preview": False
            }
            res = requests.post(url_api_msg, json=payload_msg)

        if res.status_code == 200:
            print(f"📢 Notificação enviada para o Telegram sobre: {nome_jogo} (Versão: {versao_jogo})")
        else:
            print(f"❌ Erro ao enviar Telegram: {res.text}")
    except Exception as e:
        print(f"❌ Erro na API do Telegram: {e}")

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

def salvar_no_firebase_se_novo(url_origem, link_novo, dados_jogo):
    partes = url_origem.rstrip('/').split('/')
    id_jogo = partes[-2] if len(partes) >= 2 else "jogo"
    id_jogo = id_jogo.replace('.html', '').replace('.a', '')

    nome_jogo = dados_jogo.get("nome", id_jogo.replace('-', ' ').title())
    versao_jogo = dados_jogo.get("versao", "Última Versão")
    foto_url = FOTO_OFICIAL_SITE  # Sempre salva a foto do seu blog

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
        "link_direto": link_novo,
        "nome": nome_jogo,
        "versao": versao_jogo,
        "foto": foto_url
    }

    try:
        res1 = requests.patch(f"{firebase_base_url}/links/{id_jogo}.json", json=payload)
        res2 = requests.patch(f"{firebase_base_url}/jogos/{id_jogo}.json", json=payload)
        if res1.status_code == 200:
            print(f"✅ Link atualizado com sucesso no Firebase para: {id_jogo}")
            # Dispara a notificação automática no Telegram!
            enviar_notificacao_telegram(nome_jogo, versao_jogo, id_jogo)
    except Exception as e:
        print(f"❌ Erro ao salvar no Firebase: {e}")

def extrair_link_direto(url_alvo):
    print(f"Iniciando extração para: {url_alvo}")

    dados_jogo = {
        "nome": "Jogo Desconhecido",
        "versao": "Última Versão",
        "foto": FOTO_OFICIAL_SITE
    }

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

            # --- EXTRAÇÃO DE NOME E VERSÃO DO JOGO ---
            try:
                # Pega o título principal (H1) da página
                h1_elem = page.locator("h1").first
                full_title = h1_elem.inner_text().strip() if h1_elem.count() > 0 else page.title()

                # Extrai versão usando expressão regular (ex: v0.4.7.7)
                match_v = re.search(r'v?(\d+\.\d+[\.\d+]*)', full_title)
                if match_v:
                    dados_jogo["versao"] = f"v{match_v.group(1)}"

                # Limpa o título para deixar apenas o Nome do jogo
                nome_limpo = full_title.split(" MOD")[0].split(" (")[0].split(" v")[0].strip()
                if nome_limpo:
                    dados_jogo["nome"] = nome_limpo

            except Exception as err_meta:
                print(f"⚠️ Erro ao extrair metadados da página: {err_meta}")

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
        return link_final, dados_jogo

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].startswith("http"):
        url_single = sys.argv[1]
        link, dados_jogo = extrair_link_direto(url_single)
        if link:
            salvar_no_firebase_se_novo(url_single, link, dados_jogo)
            print(f"LINK_ENCONTRADO:{link}")
        else:
            print("Nenhum link direto encontrado.")
