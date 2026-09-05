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

GREEN_API_INSTANCE = os.environ.get("GREEN_API_INSTANCE")
GREEN_API_TOKEN = os.environ.get("GREEN_API_TOKEN")
GREEN_API_GROUP_ID = os.environ.get("GREEN_API_GROUP_ID")

# URL DA SUA CLOUDFLARE WORKER
URL_WORKER = "https://orange-star-d066.claudiokennedymorgy.workers.dev"

# SEU BLOG OFICIAL
PAGINA_INICIAL_BLOG = "https://k-404modapk.blogspot.com/?m=1"
FOTO_OFICIAL_SITE = "https://k-404modapk.blogspot.com/favicon.ico"

def enviar_notificacao_telegram(nome_jogo, versao_jogo, id_jogo):
    """Envia mensagem no Telegram com a foto oficial do site."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Telegram não configurado nos Secrets. Pulando notificação.")
        return

    mensagem = (
        f"🔥 <b>JOGO ATUALIZADO!</b>\n\n"
        f"🎮 <b>Jogo:</b> {nome_jogo}\n"
        f"📦 <b>Versão:</b> {versao_jogo}\n"
        f"🔗 <b>Página:</b> <a href='{PAGINA_INICIAL_BLOG}'>Baixar no Blog</a>\n\n"
        f"⚡ <i>Nova versão disponível no servidor! Atualize os dados no Blogger se necessário.</i>"
    )

    url_api = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "photo": FOTO_OFICIAL_SITE,
        "caption": mensagem,
        "parse_mode": "HTML"
    }

    try:
        res = requests.post(url_api, json=payload)
        if res.status_code != 200:
            url_api_msg = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            payload_msg = {
                "chat_id": TELEGRAM_CHAT_ID,
                "text": mensagem,
                "parse_mode": "HTML",
                "disable_web_page_preview": False
            }
            res = requests.post(url_api_msg, json=payload_msg)

        if res.status_code == 200:
            print(f"📢 Notificação enviada para o Telegram: {nome_jogo} ({versao_jogo})")
        else:
            print(f"❌ Erro ao enviar Telegram: {res.text}")
    except Exception as e:
        print(f"❌ Erro na API do Telegram: {e}")

def enviar_notificacao_whatsapp(nome_jogo, versao_jogo, id_jogo):
    """Envia mensagem no WhatsApp via GREEN-API com Foto + Legenda."""
    if not GREEN_API_INSTANCE or not GREEN_API_TOKEN or not GREEN_API_GROUP_ID:
        print("⚠️ GREEN-API não configurada nos Secrets. Pulando WhatsApp.")
        return

    chat_id = GREEN_API_GROUP_ID.strip()
    if not chat_id.endswith("@g.us") and not chat_id.endswith("@c.us"):
        chat_id = f"{chat_id}@g.us"

    mensagem = (
        f"🔥 *JOGO ATUALIZADO!*\n\n"
        f"🎮 *Jogo:* {nome_jogo}\n"
        f"📦 *Versão:* {versao_jogo}\n"
        f"🔗 *Página:* {PAGINA_INICIAL_BLOG}\n\n"
        f"⚡ _Nova versão disponível no servidor! Atualize os dados no Blogger se necessário._"
    )

    url_file = f"https://api.green-api.com/waInstance{GREEN_API_INSTANCE}/sendFileByUrl/{GREEN_API_TOKEN}"
    payload_file = {
        "chatId": chat_id,
        "urlFile": FOTO_OFICIAL_SITE,
        "fileName": "icon.ico",
        "caption": mensagem
    }

    try:
        print(f"🔄 Enviando WhatsApp (Foto + Legenda) para: {chat_id}")
        res = requests.post(url_file, json=payload_file)

        if res.status_code != 200:
            print("⚠️ Falha no envio de arquivo. Tentando enviar como texto simples...")
            url_msg = f"https://api.green-api.com/waInstance{GREEN_API_INSTANCE}/sendMessage/{GREEN_API_TOKEN}"
            payload_msg = {
                "chatId": chat_id,
                "message": mensagem
            }
            res = requests.post(url_msg, json=payload_msg)

        if res.status_code == 200:
            print(f"🟢 Notificação enviada com sucesso para o WhatsApp: {nome_jogo} ({versao_jogo})")
        else:
            print(f"❌ Falha ao enviar WhatsApp. Verifique as credenciais no GitHub.")
    except Exception as e:
        print(f"❌ Erro crítico na API do WhatsApp: {e}")

def buscar_dados_atuais_firebase(id_jogo):
    """Consulta os dados atuais salvos no Firebase."""
    firebase_base_url = "https://meublog-apks-default-rtdb.firebaseio.com"
    try:
        res = requests.get(f"{firebase_base_url}/links/{id_jogo}.json")
        if res.status_code == 200 and res.text != 'null':
            return res.json()
    except Exception as e:
        print(f"Erro ao consultar Firebase: {e}")
    return {}

def extrair_id_jogo(url_origem):
    """Extrai o ID correto do jogo ignorando sufixos como /download/, /0/, /1/, .html, etc."""
    url_limpa = url_origem.split(']')[0].rstrip('/')
    partes = url_limpa.split('/')
    
    partes_filtradas = [
        p for p in partes 
        if p and p not in ['download', 'file'] and not p.isdigit()
    ]
    
    if partes_filtradas:
        id_jogo = partes_filtradas[-1]
    else:
        id_jogo = "jogo"
        
    id_jogo = id_jogo.replace('.html', '').replace('.apk', '')
    return id_jogo

def salvar_no_firebase_se_novo(url_origem, link_novo, dados_jogo):
    id_jogo = extrair_id_jogo(url_origem)

    nome_jogo = dados_jogo.get("nome", id_jogo.replace('-', ' ').title())
    versao_jogo = dados_jogo.get("versao", "Última Versão")
    foto_url = FOTO_OFICIAL_SITE

    dados_atuais = buscar_dados_atuais_firebase(id_jogo)
    link_atual = dados_atuais.get("link_direto") if isinstance(dados_atuais, dict) else None
    versao_atual = dados_atuais.get("versao") if isinstance(dados_atuais, dict) else None

    # Compara se o link ou a versão mudaram
    if link_atual == link_novo and versao_atual == versao_jogo:
        print(f"⏩ O jogo '{id_jogo}' continua com o mesmo link ({versao_jogo}). Nenhuma notificação enviada.")
        return id_jogo

    print(f"🔄 Nova versão/link detectado para '{id_jogo}'! Atualizando no Firebase...")
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
            print(f"✅ Link e versão atualizados no Firebase para: {id_jogo}")
            enviar_notificacao_telegram(nome_jogo, versao_jogo, id_jogo)
            enviar_notificacao_whatsapp(nome_jogo, versao_jogo, id_jogo)
    except Exception as e:
        print(f"❌ Erro ao salvar no Firebase: {e}")
    
    return id_jogo

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

            try:
                h1_elem = page.locator("h1").first
                full_title = h1_elem.inner_text().strip() if h1_elem.count() > 0 else page.title()

                match_v = re.search(r'v?(\d+\.\d+[\.\d+]*)', full_title)
                if match_v:
                    dados_jogo["versao"] = f"v{match_v.group(1)}"

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
            id_jogo = salvar_no_firebase_se_novo(url_single, link, dados_jogo)
            link_protegido = f"{URL_WORKER}?id={id_jogo}"
            print(f"LINK_ENCONTRADO:{link_protegido}")
        else:
            print("Nenhum link direto encontrado.")
