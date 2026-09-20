import sys
import os
import re
import json
import requests
from playwright.sync_api import sync_playwright

try:
    from google.oauth2 import service_account
    import google.auth.transport.requests
except ImportError:
    service_account = None

try:
    from playwright_stealth import stealth_sync
except ImportError:
    stealth_sync = None

# Variaveis de ambiente (GitHub Secrets)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

GREEN_API_INSTANCE = os.environ.get("GREEN_API_INSTANCE")
GREEN_API_TOKEN = os.environ.get("GREEN_API_TOKEN")
GREEN_API_GROUP_ID = os.environ.get("GREEN_API_GROUP_ID")

GOOGLE_CREDENTIALS_JSON = os.environ.get("GOOGLE_CREDENTIALS_JSON")

# CLOUDFLARE WORKER E BLOGGER OFICIAL
URL_WORKER = "https://orange-star-d066.claudiokennedymorgy.workers.dev"
PAGINA_INICIAL_BLOG = "https://k-404modapk.blogspot.com/"
FOTO_OFICIAL_SITE = "https://k-404modapk.blogspot.com/favicon.ico"

def normalizar_url_blogspot(url):
    """Garante URL canônica limpa sem parâmetros como ?m=1 para aceitação no Google."""
    if not url:
        return ""
    url_limpa = url.split('?')[0].split('#')[0]
    if not url_limpa.endswith('/') and not url_limpa.endswith('.html'):
        url_limpa += '/'
    return url_limpa

def notificar_google_indexing_api(url_para_indexar):
    """Envia a URL canônica para a Google Indexing API e dispara Ping de Sitemap/Atom."""
    url_limpa = normalizar_url_blogspot(url_para_indexar)
    
    # Validação rigorosa: só envia o seu próprio domínio
    if "k-404modapk.blogspot.com" not in url_limpa:
        print(f"⚠️ URL externa ignorada ({url_limpa}). O Google rejeita domínios de terceiros.")
        return

    # 1. PING AUTOMÁTICO DE SITEMAPS (Sitemap XML + Atom Feed)
    sitemaps = [
        f"{PAGINA_INICIAL_BLOG}sitemap.xml",
        f"{PAGINA_INICIAL_BLOG}atom.xml?redirect=false&start-index=1&max-results=500"
    ]
    for sm in sitemaps:
        try:
            requests.get(f"https://www.google.com/ping?sitemap={sm}", timeout=5)
        except Exception:
            pass
    print("📡 Ping de Sitemap/Atom disparado ao Google!")

    # 2. SOLICITAÇÃO DIRETA À GOOGLE INDEXING API
    if not GOOGLE_CREDENTIALS_JSON:
        print("⚠️ GOOGLE_CREDENTIALS_JSON não configurado. Pulando Google Indexing.")
        return

    if not service_account:
        print("⚠️ Módulo 'google-auth' não encontrado no requirements.txt.")
        return

    try:
        info = json.loads(GOOGLE_CREDENTIALS_JSON)
        scopes = ["https://www.googleapis.com/auth/indexing"]
        credentials = service_account.Credentials.from_service_account_info(info, scopes=scopes)
        
        req = google.auth.transport.requests.Request()
        credentials.refresh(req)
        token = credentials.token

        endpoint = "https://indexing.googleapis.com/v1/urlNotifications:publish"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
        payload = {
            "url": url_limpa,
            "type": "URL_UPDATED"
        }

        res = requests.post(endpoint, headers=headers, json=payload, timeout=8)
        if res.status_code == 200:
            print(f"🚀 Google Indexing API: Notificado com sucesso -> {url_limpa}")
        else:
            print(f"❌ Erro na Google Indexing API ({res.status_code}): {res.text}")
    except Exception as e:
        print(f"❌ Falha ao comunicar com Google Indexing API: {e}")

def enviar_notificacao_telegram(nome_jogo, versao_jogo, id_jogo):
    """Envia aviso no Telegram."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Telegram não configurado nos Secrets. Pulando.")
        return

    mensagem = (
        f"🔥 <b>JOGO ATUALIZADO!</b>\n\n"
        f"🎮 <b>Jogo:</b> {nome_jogo}\n"
        f"📦 <b>Versão:</b> {versao_jogo}\n"
        f"🔗 <b>Página:</b> <a href='{PAGINA_INICIAL_BLOG}'>Baixar no Blog</a>\n\n"
        f"⚡ <i>Nova versão salva no servidor!</i>"
    )

    url_api = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "photo": FOTO_OFICIAL_SITE,
        "caption": mensagem,
        "parse_mode": "HTML"
    }

    try:
        res = requests.post(url_api, json=payload, timeout=8)
        if res.status_code != 200:
            url_msg = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            requests.post(url_msg, json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": mensagem,
                "parse_mode": "HTML",
                "disable_web_page_preview": False
            }, timeout=8)
        print(f"📢 Notificação enviada para o Telegram: {nome_jogo} ({versao_jogo})")
    except Exception as e:
        print(f"❌ Erro no Telegram: {e}")

def enviar_notificacao_whatsapp(nome_jogo, versao_jogo, id_jogo):
    """Envia aviso no WhatsApp via GREEN-API."""
    if not GREEN_API_INSTANCE or not GREEN_API_TOKEN or not GREEN_API_GROUP_ID:
        print("⚠️ GREEN-API não configurada nos Secrets. Pulando.")
        return

    chat_id = GREEN_API_GROUP_ID.strip()
    if not chat_id.endswith("@g.us") and not chat_id.endswith("@c.us"):
        chat_id = f"{chat_id}@g.us"

    mensagem = (
        f"🔥 *JOGO ATUALIZADO!*\n\n"
        f"🎮 *Jogo:* {nome_jogo}\n"
        f"📦 *Versão:* {versao_jogo}\n"
        f"🔗 *Página:* {PAGINA_INICIAL_BLOG}\n\n"
        f"⚡ _Nova versão disponível!_"
    )

    url_file = f"https://api.green-api.com/waInstance{GREEN_API_INSTANCE}/sendFileByUrl/{GREEN_API_TOKEN}"
    payload_file = {
        "chatId": chat_id,
        "urlFile": FOTO_OFICIAL_SITE,
        "fileName": "icon.ico",
        "caption": mensagem
    }

    try:
        res = requests.post(url_file, json=payload_file, timeout=8)
        if res.status_code != 200:
            url_msg = f"https://api.green-api.com/waInstance{GREEN_API_INSTANCE}/sendMessage/{GREEN_API_TOKEN}"
            requests.post(url_msg, json={"chatId": chat_id, "message": mensagem}, timeout=8)
        print(f"🟢 Notificação enviada para o WhatsApp: {nome_jogo} ({versao_jogo})")
    except Exception as e:
        print(f"❌ Erro no WhatsApp: {e}")

def buscar_dados_atuais_firebase(id_jogo):
    """Busca dados armazenados no Firebase."""
    firebase_base_url = "https://meublog-apks-default-rtdb.firebaseio.com"
    try:
        res = requests.get(f"{firebase_base_url}/links/{id_jogo}.json", timeout=8)
        if res.status_code == 200 and res.text != 'null':
            return res.json()
    except Exception as e:
        print(f"Erro ao consultar Firebase: {e}")
    return {}

def extrair_id_jogo(url_origem):
    """Gera um ID limpo a partir da URL."""
    url_limpa = url_origem.split(']')[0].rstrip('/')
    partes = url_limpa.split('/')
    partes_filtradas = [
        p for p in partes 
        if p and p not in ['download', 'file'] and not p.isdigit()
    ]
    id_jogo = partes_filtradas[-1] if partes_filtradas else "jogo"
    return id_jogo.replace('.html', '').replace('.apk', '')

def extrair_versao_do_texto_ou_link(texto_ou_url):
    """Extrai número de versão de títulos ou links."""
    if not texto_ou_url:
        return None
    
    match_filename = re.search(r'[vV]?(\d+[\.\-_]\d+(?:[\.\-_]\d+)+)', texto_ou_url)
    if match_filename:
        ver_str = match_filename.group(1).replace('-', '.').replace('_', '.')
        if not ver_str.startswith("202"):
            return ver_str

    match_std = re.search(r'\b(\d+\.\d+(?:\.\d+)*)\b', texto_ou_url)
    if match_std and not match_std.group(1).startswith("202"):
        return match_std.group(1)

    return None

def salvar_no_firebase_se_novo(url_origem, link_novo, dados_jogo):
    id_jogo = extrair_id_jogo(url_origem)
    nome_jogo = dados_jogo.get("nome", id_jogo.replace('-', ' ').title())
    versao_jogo = dados_jogo.get("versao", "v1.0.0")

    dados_atuais = buscar_dados_atuais_firebase(id_jogo)
    link_atual = dados_atuais.get("link_direto") if isinstance(dados_atuais, dict) else None
    versao_atual = dados_atuais.get("versao") if isinstance(dados_atuais, dict) else None

    if link_atual == link_novo and versao_atual == versao_jogo:
        print(f"⏩ Jogo '{id_jogo}' já está atualizado ({versao_jogo}). Nenhuma ação necessária.")
        return id_jogo

    print(f"🔄 Atualização detectada para '{id_jogo}'! Salvando no Firebase...")
    firebase_base_url = "https://meublog-apks-default-rtdb.firebaseio.com"
    payload = {
        "url_original": url_origem,
        "link_direto": link_novo,
        "nome": nome_jogo,
        "versao": versao_jogo,
        "foto": FOTO_OFICIAL_SITE
    }

    try:
        res1 = requests.patch(f"{firebase_base_url}/links/{id_jogo}.json", json=payload, timeout=8)
        requests.patch(f"{firebase_base_url}/jogos/{id_jogo}.json", json=payload, timeout=8)
        
        if res1.status_code == 200:
            print(f"✅ Firebase atualizado: {id_jogo} ({versao_jogo})")
            enviar_notificacao_telegram(nome_jogo, versao_jogo, id_jogo)
            enviar_notificacao_whatsapp(nome_jogo, versao_jogo, id_jogo)
            
            # --- INDEXAÇÃO AUTOMÁTICA NO GOOGLE ---
            notificar_google_indexing_api(PAGINA_INICIAL_BLOG)
            if "blogspot.com" in url_origem or "k-404" in url_origem:
                notificar_google_indexing_api(url_origem)

    except Exception as e:
        print(f"❌ Erro ao salvar no Firebase: {e}")
    
    return id_jogo

def extrair_link_direto(url_alvo):
    print(f"🔍 Extraindo: {url_alvo}")
    id_fallback = extrair_id_jogo(url_alvo).replace('-', ' ').title()

    dados_jogo = {
        "nome": id_fallback,
        "versao": "",
        "foto": FOTO_OFICIAL_SITE
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--disable-gpu',
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

        # OTIMIZAÇÃO DE VELOCIDADE: Bloqueia imagens, fontes e mídias desnecessárias
        page.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "font", "media"] else route.continue_())

        if stealth_sync:
            stealth_sync(page)
        else:
            page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")

        link_final = None

        def interceptar_requisicao(request):
            nonlocal link_final
            url = request.url

            ignorar = ["yandex", "mc.yandex", "google-analytics", "googletagmanager", "facebook", "doubleclick", "cdn-cgi"]
            if any(dom in url for dom in ignorar):
                return

            if not url.startswith("blob:") and "play.google.com" not in url:
                if "dl.modplays.com" in url or ("files" in url and "modyolo" in url) or url.endswith(".apk") or ".apk?" in url:
                    link_final = url

        page.on("request", interceptar_requisicao)

        try:
            page.goto(url_alvo, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2000)

            # Extração rápida de metadados (Título e Versão)
            full_title = ""
            try:
                og_elem = page.locator('meta[property="og:title"]').first
                if og_elem.count() > 0:
                    full_title = og_elem.get_attribute("content") or ""
            except:
                pass

            if not full_title:
                full_title = page.title() or ""

            num_versao = page.evaluate(r'''() => {
                const elements = Array.from(document.querySelectorAll('tr, td, th, div, li, span, p'));
                for (let el of elements) {
                    const txt = (el.innerText || '').trim();
                    if (/^(version|versão)$/i.test(txt) || /^version\s*:/i.test(txt) || /^versão\s*:/i.test(txt)) {
                        const parentText = el.parentElement ? el.parentElement.innerText : '';
                        const match = parentText.match(/\b(\d+\.\d+(?:\.\d+)*)\b/);
                        if (match && match[1] && !match[1].startsWith('202')) {
                            return match[1];
                        }
                    }
                }
                return null;
            }''')

            if not num_versao and full_title:
                num_versao = extrair_versao_do_texto_ou_link(full_title)

            if full_title and len(full_title.strip()) > 3:
                nome_limpo = re.sub(r'(?i)\s*(?:MOD|APK|v?\d+\.\d+.*|\(.*?\)|-|–|Download).*$', '', full_title).strip()
                nome_limpo = re.sub(r'(?i)modyolo\.com|modplays\.com|modyolo|modplays', '', nome_limpo).strip()
                if nome_limpo and len(nome_limpo) > 1 and nome_limpo.lower() != "download":
                    dados_jogo["nome"] = nome_limpo

            if num_versao:
                dados_jogo["versao"] = f"v{num_versao.lstrip('vV')}"

            # Clique otimizado no botão de Download
            for b in page.locator("a, button").all():
                try:
                    texto = (b.inner_text() or "").lower()
                    href = b.get_attribute("href") or ""
                    if ("download" in texto or "download" in href) and "play.google.com" not in href:
                        b.click(force=True, timeout=2000)
                        break
                except:
                    continue

            page.wait_for_timeout(4000)

            if not link_final:
                hrefs = page.eval_on_selector_all("a[href]", "elements => elements.map(e => e.href)")
                for href in hrefs:
                    if "yandex" not in href and "cdn-cgi" not in href and not href.startswith("blob:"):
                        if "dl.modplays.com" in href or ("files" in href and "modyolo" in href) or href.endswith(".apk"):
                            link_final = href
                            break

            if not dados_jogo["versao"] or dados_jogo["versao"] == "v1.0.0":
                ver_do_link = extrair_versao_do_texto_ou_link(link_final or "") or extrair_versao_do_texto_ou_link(url_alvo)
                if ver_do_link:
                    dados_jogo["versao"] = f"v{ver_do_link.lstrip('vV')}"
                else:
                    dados_jogo["versao"] = "v1.0.0"

            print(f"🎯 Extraído -> Jogo: '{dados_jogo['nome']}' | Versão: '{dados_jogo['versao']}'")

        except Exception as e:
            print(f"Erro na extração: {e}")

        browser.close()
        return link_final, dados_jogo

def salvar_url_na_lista(url):
    """Guarda a URL no jogos.txt sem duplicatas."""
    arquivo = "jogos.txt"
    urls_existentes = set()
    
    if os.path.exists(arquivo):
        with open(arquivo, "r", encoding="utf-8") as f:
            urls_existentes = set(line.strip() for line in f if line.strip())

    if url not in urls_existentes:
        with open(arquivo, "a", encoding="utf-8") as f:
            f.write(f"{url}\n")
        print(f"📝 Registrado em {arquivo}.")

def processar_jogo(url_alvo):
    """Processa um jogo por vez."""
    print(f"\n==================================================")
    link, dados_jogo = extrair_link_direto(url_alvo)
    if link:
        id_jogo = salvar_no_firebase_se_novo(url_alvo, link, dados_jogo)
        salvar_url_na_lista(url_alvo)
        link_protegido = f"{URL_WORKER}?id={id_jogo}"
        print(f"LINK_ENCONTRADO:{link_protegido}")
    else:
        print(f"❌ Nenhum link direto encontrado para: {url_alvo}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].startswith("http"):
        url_single = sys.argv[1]
        processar_jogo(url_single)
    else:
        arquivo_jogos = "jogos.txt"
        if os.path.exists(arquivo_jogos):
            with open(arquivo_jogos, "r", encoding="utf-8") as f:
                lista_urls = [linha.strip() for linha in f if linha.strip()]
            
            print(f"🤖 Modo Automático: {len(lista_urls)} jogo(s) na fila...")
            for url in lista_urls:
                processar_jogo(url)
        else:
            print("⚠️ 'jogos.txt' não encontrado ou vazio. Passe uma URL por argumento.")
