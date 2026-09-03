import sys
import os
import requests
from playwright.sync_api import sync_playwright

def extrair_link(url_alvo):
    print(f"Iniciando busca para a URL: {url_alvo}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Acessa a URL do jogo
        page.goto(url_alvo, wait_until="networkidle")
        
        print("Aguardando geração do link interno...")
        page.wait_for_timeout(5000) # espera 5 segundos
        
        link_final = None
        
        # Procura por links de download direto (Modyolo / LiteAPKs)
        links = page.query_selector_all("a")
        for link in links:
            href = link.get_attribute("href")
            if href and ("files.modyolo.com" in href or "download" in href and ".apk" in href):
                link_final = href
                break
                
        browser.close()
        
        if link_final:
            print(f"LINK_ENCONTRADO:{link_final}")
            salvar_no_firebase(url_alvo, link_final)
        else:
            print("Nenhum link direto encontrado.")

def salvar_no_firebase(url_origem, link_direto):
    firebase_url = "https://meublog-apks-default-rtdb.firebaseio.com/links.json"
    
    # Limpa a URL de origem para usar como chave simples
    id_jogo = url_origem.split("/")[-2] if "/" in url_origem else "jogo"
    
    dados = {
        "url_original": url_origem,
        "link_direto": link_direto
    }
    
    try:
        response = requests.patch(f"https://meublog-apks-default-rtdb.firebaseio.com/links/{id_jogo}.json", json=dados)
        if response.status_code == 200:
            print("Link salvo no Firebase com sucesso!")
        else:
            print(f"Erro ao salvar no Firebase: {response.status_code}")
    except Exception as e:
        print(f"Erro na conexão com Firebase: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = "https://modyolo.com/download/baseball-9-21102/1"
        
    extrair_link(url)
