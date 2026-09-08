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

def extrair_versao_do_texto_ou_link(texto_ou_url):
    """Extrai padrões numéricos de versão (ex: 3.8.0, 4.2.1, 1.23.4) de strings ou URLs de download."""
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
    foto_url = FOTO_OFICIAL_SITE

    dados_atuais = buscar_dados_atuais_firebase(id_jogo)
    link_atual = dados_atuais.get("link_direto") if isinstance(dados_atuais, dict) else None
    versao_atual = dados_atuais.get("versao") if isinstance(dados_atuais, dict) else None

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
            print(f"✅ Link e versão atualizados no Firebase para: {id_jogo} ({versao_jogo})")
            enviar_notificacao_telegram(nome_jogo, versao_jogo, id_jogo)
            enviar_notificacao_whatsapp(nome_jogo, versao_jogo, id_jogo)
    except Exception as e:
        print(f"❌ Erro ao salvar no Firebase: {e}")
    
    return id_jogo

def extrair_link_direto(url_alvo):
    print(f"Iniciando extração para: {url_alvo}")

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

            ignorar_dominios = [
                "yandex", "mc.yandex", "google-analytics", "googletagmanager", 
                "facebook", "doubleclick", "cdn-cgi", "challenge-platform"
            ]
            if any(dom in url for dom in ignorar_dominios):
                return

            if not url.startswith("blob:") and "play.google.com" not in url:
                if "dl.modplays.com" in url:
                    link_final = url
                elif "files" in url and "modyolo" in url:
                    link_final = url
                elif url.endswith(".apk") or ".apk?" in url:
                    link_final = url

        page.on("request", interceptar_requisicao)

        try:
            page.goto(url_alvo, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(4000)

            if "cloudflare" in page.content().lower() or "just a moment" in page.title().lower():
                print("Detectado Cloudflare Challenge, aguardando resolução...")
                page.wait_for_timeout(8000)

            # --- EXTRAÇÃO DE NOME E VERSÃO ---
            try:
                full_title = ""
                try:
                    og_elem = page.locator('meta[property="og:title"]').first
                    if og_elem.count() > 0:
                        full_title = og_elem.get_attribute("content") or ""
                except:
                    pass

                if not full_title:
                    full_title = page.title() or ""

                # 1. TENTA VIA JS NO DOM
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

                # 2. SE NÃO ACHOU, EXTRAI DO TÍTULO COMPLETO
                if not num_versao and full_title:
                    num_versao = extrair_versao_do_texto_ou_link(full_title)

                # 3. EXTRAÇÃO E LIMPEZA DO NOME
                if full_title and len(full_title.strip()) > 3:
                    nome_limpo = re.sub(r'(?i)\s*(?:MOD|APK|v?\d+\.\d+.*|\(.*?\)|-|–|Download).*$', '', full_title).strip()
                    nome_limpo = re.sub(r'(?i)modyolo\.com|modplays\.com|modyolo|modplays', '', nome_limpo).strip()
                    if nome_limpo and len(nome_limpo) > 1 and nome_limpo.lower() != "download":
                        dados_jogo["nome"] = nome_limpo

                if num_versao:
                    dados_jogo["versao"] = f"v{num_versao.lstrip('vV')}"

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

            print("Aguardando carregamento da página de download...")
            page.wait_for_timeout(10000)

            if "download" in page.url and "modyolo.com" in page.url and not link_final:
                print("Detectada página intermediária do Modyolo, clicando no link direto final...")
                for b in page.locator("a[href]").all():
                    try:
                        href = b.get_attribute("href") or ""
                        if ("files" in href and "modyolo" in href) or href.endswith(".apk") or "dl.modplays.com" in href:
                            link_final = href
                            break
                        elif "download" in (b.inner_text() or "").lower() and "yandex" not in href:
                            b.click(force=True, timeout=3000)
                            page.wait_for_timeout(5000)
                            break
                    except:
                        continue

            if not link_final:
                hrefs = page.eval_on_selector_all("a[href]", "elements => elements.map(e => e.href)")
                for href in hrefs:
                    if "yandex" not in href and "cdn-cgi" not in href and not href.startswith("blob:"):
                        if "dl.modplays.com" in href or ("files" in href and "modyolo" in href) or href.endswith(".apk"):
                            link_final = href
                            break

            # 4. EXTRAÇÃO DE SEGURANÇA PARA A VERSÃO
            if not dados_jogo["versao"] or dados_jogo["versao"] == "v1.0.0":
                ver_do_link = extrair_versao_do_texto_ou_link(link_final or "")
                if ver_do_link:
                    dados_jogo["versao"] = f"v{ver_do_link.lstrip('vV')}"
                else:
                    ver_da_url = extrair_versao_do_texto_ou_link(url_alvo)
                    if ver_da_url:
                        dados_jogo["versao"] = f"v{ver_da_url.lstrip('vV')}"
                    else:
                        dados_jogo["versao"] = "v1.0.0"

            print(f"🎯 Metadados Extraídos -> Jogo: '{dados_jogo['nome']}' | Versão: '{dados_jogo['versao']}'")

        except Exception as e:
            print(f"Erro na navegação: {e}")

        browser.close()
        return link_final, dados_jogo

def salvar_url_na_lista(url):
    """Guarda a URL no arquivo jogos.txt para o robô monitorar sozinho depois."""
    arquivo = "jogos.txt"
    urls_existentes = set()
    
    if os.path.exists(arquivo):
        with open(arquivo, "r", encoding="utf-8") as f:
            urls_existentes = set(line.strip() for line in f if line.strip())

    if url not in urls_existentes:
        with open(arquivo, "a", encoding="utf-8") as f:
            f.write(f"{url}\n")
        print(f"📝 URL salva em {arquivo} para monitoramento automático.")

def processar_jogo(url_alvo):
    """Executa a verificação e atualização de um único jogo."""
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
            
            print(f"🤖 Rodando em modo automático. {len(lista_urls)} jogo(s) para verificar...")
            for url in lista_urls:
                processar_jogo(url)
        else:
            print("⚠️ Nenhuma URL cadastrada no 'jogos.txt'. Adicione uma URL manualmente primeiro.")
