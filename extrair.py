import sys
import os
import requests
from playwright.sync_api import sync_playwright

def extrair_link(url_alvo):
    print(f"Iniciando busca para a URL: {url_alvo}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        link_final = None

        # Intercepta requisições de rede APENAS para arquivos .apk ou servidores diretos
        def interceptar_resposta(response):
            nonlocal link_final
            url = response.url
            # Ignora Play Store e foca estritamente no arquivo APK
            if ("files.modyolo.com" in url or ".apk" in url) and "play.google.com" not in url:
                link_final = url

        page.on("response", interceptar_resposta)

        try:
            page.goto(url_alvo, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(3000)

            # Varre os links da página procurando a URL do APK direto
            links = page.query_selector_all("a[href]")
            for l in links:
                href = l.get_attribute("href") or ""
                # Filtro rígido: precisa ser servidor do Modyolo ou terminar em .apk, e NÃO ser Play Store
                if ("files.modyolo.com" in href or href.endswith(".apk")) and "play.google.com" not in href:
                    link_final = href
                    break

            # Se não achou na primeira varredura, procura o botão "Download" final e clica
            if not link_final:
                botoes = page.query_selector_all("a, button")
                for botao in botoes:
                    href = botao.get_attribute("href") or ""
                    texto = botao.inner_text().lower()
                    
                    if "play.google.com" in href:
                        continue
                        
                    if "download" in texto or "files.modyolo.com" in href:
                        try:
                            botao.click(timeout=3000)
                            page.wait_for_timeout(4000)
                        except:
                            pass
                    if link_final:
                        break

        except Exception as e:
            print(f"Erro ao navegar na pagina: {e}")

        browser.close()
        
        if link_final:
            print(f"LINK_ENCONTRADO:{link_final}")
            salvar_no_firebase(url_alvo, link_final)
        else:
            print("Nenhum link direto encontrado.")

def salvar_no_firebase(url_origem, link_direto):
    partes = url_origem.rstrip('/').split('/')
    id_jogo = partes[-2] if len(partes) >= 2 else "jogo"
    
    firebase_endpoint = f"https://meublog-apks-default-rtdb.firebaseio.com/links/{id_jogo}.json"
    
    dados = {
        "url_original": url_origem,
        "link_direto": link_direto
    }
    
    try:
        response = requests.patch(firebase_endpoint, json=dados)
        if response.status_code == 200:
            print("Link salvo no Firebase com sucesso!")
        else:
            print(f"Erro no Firebase: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Erro na conexao com Firebase: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = "https://modyolo.com/download/baseball-9-21102/1"
        
    extrair_link(url)
