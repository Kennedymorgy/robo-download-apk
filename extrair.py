import asyncio
import os
import sys
from playwright.async_api import async_playwright

async def obter_link_direto(url_alvo):
    print(f"Iniciando busca para a URL: {url_alvo}")
    async with async_playwright() as p:
        # Abre o navegador invisível simulando um celular Android
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Linux; Android 13; SM-A256E) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
        )
        page = await context.new_page()

        try:
            # Acesse a página do jogo
            await page.goto(url_alvo, wait_until="domcontentloaded", timeout=60000)
            
            # Espera 6 segundos para o timer interno do Modyolo rodar
            print("Aguardando geração do link interno...")
            await page.wait_for_timeout(6000)
            
            # Procura por links contendo .apk ou servidores conhecidos
            links = await page.query_selector_all('a[href]')
            for link in links:
                href = await link.get_attribute('href')
                if href and ('.apk' in href or 'files.modyolo.com' in href or 'download.liteapks.dev' in href):
                    print(f"LINK_ENCONTRADO:{href}")
                    await browser.close()
                    return href

            print("Nenhum link direto foi localizado.")
            await browser.close()
            return None

        except Exception as e:
            print(f"Erro ao acessar página: {e}")
            await browser.close()
            return None

if __name__ == "__main__":
    target_url = sys.argv[1] if len(sys.argv) > 1 else "https://modyolo.com/download/baseball-9-21102/1"
    asyncio.run(obter_link_direto(target_url))
