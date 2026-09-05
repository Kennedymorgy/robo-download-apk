import os
import time
import requests

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHAT_ID")
DISCUSSION_GROUP_ID = os.environ.get("DISCUSSION_GROUP_ID")
ADMIN_USER_ID_STR = os.environ.get("ADMIN_USER_ID")

ADMIN_USER_ID = int(ADMIN_USER_ID_STR) if ADMIN_USER_ID_STR else 0

TEXTO_ABERTA = (
    "🔥 <b>LISTA DE PEDIDOS ABERTA! (0/10)</b>\n"
    "🔥 <b>GAME REQUESTS OPEN! (0/10)</b>\n\n"
    "🎮 Comente o jogo que você quer abaixo (Apenas os 10 primeiros! 1 por pessoa)\n"
    "🎮 Comment your game below (Only the FIRST 10 requests! 1 per person)\n\n"
    "• Assim que bater 10 pedidos, a lista fecha.\n"
    "• As soon as we reach 10 requests, it closes."
)

def criar_texto_fechada(total):
    return (
        f"🚫 <b>LISTA DE PEDIDOS ENCERRADA! ({total}/10)</b>\n"
        f"🚫 <b>GAME REQUESTS CLOSED! ({total}/10)</b>\n\n"
        "Já atingimos o limite de 10 pedidos para hoje! Os jogos selecionados serão postados em breve.\n"
        "We have reached today's 10-request limit! The selected games will be posted soon.\n\n"
        "🔒 Comentários fechados para esta lista.\n"
        "🔒 Comments closed for this list."
    )

def enviar_telegram(endpoint, payload):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/{endpoint}"
    try:
        res = requests.post(url, json=payload)
        return res.json()
    except Exception as e:
        print(f"❌ Erro na requisição: {e}")
        return {"ok": False}

def main():
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHANNEL_ID or not DISCUSSION_GROUP_ID or not ADMIN_USER_ID:
        print("❌ ERRO: Faltam variáveis nos Secrets.")
        return

    print("🤖 Verificando comandos no canal K404...")
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates?timeout=10"
    resposta = requests.get(url).json()

    if not resposta.get("ok"):
        print("❌ Erro ao buscar atualizações do Telegram.")
        return

    sessao_aberta = False
    message_id_canal = None
    usuarios_que_pediram = set()

    # 1. Procura se você mandou /pedidos_bot recentemente no canal
    for update in resposta.get("result", []):
        msg = update.get("channel_post") or update.get("message")
        if not msg:
            continue

        chat_id = str(msg.get("chat", {}).get("id"))
        texto_msg = msg.get("text", "")

        if chat_id == str(TELEGRAM_CHANNEL_ID) and texto_msg.strip() == "/pedidos_bot":
            print("🚀 Comando /pedidos_bot encontrado no canal! Abrindo lista...")
            
            # Apaga o seu comando do canal
            enviar_telegram("deleteMessage", {
                "chat_id": TELEGRAM_CHANNEL_ID,
                "message_id": msg.get("message_id")
            })

            # Envia a mensagem de lista aberta
            res = enviar_telegram("sendMessage", {
                "chat_id": TELEGRAM_CHANNEL_ID,
                "text": TEXTO_ABERTA,
                "parse_mode": "HTML"
            })

            if res.get("ok"):
                message_id_canal = res["result"]["message_id"]
                sessao_aberta = True
                print(f"✅ Lista aberta com sucesso! ID: {message_id_canal}")
            break

    if not sessao_aberta:
        print("ℹ️ Nenhum comando /pedidos_bot novo encontrado no canal. Finalizando script.")
        return

    # 2. Se abriu a lista, fica monitorando os comentários por alguns minutos até fechar os 10
    print("👀 Monitorando o grupo de comentários...")
    inicio = time.time()
    
    # Roda por até 10 minutos recolhendo os pedidos do grupo
    while (time.time() - inicio) < 600:
        time.sleep(5)
        url_updates = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates?timeout=5"
        resp_grupo = requests.get(url_updates).json()

        for update in resp_grupo.get("result", []):
            msg = update.get("message")
            if not msg:
                continue

            chat_id = str(msg.get("chat", {}).get("id"))
            user = msg.get("from", {})
            user_id = user.get("id")

            # Se a mensagem veio do grupo de comentários
            if chat_id == str(DISCUSSION_GROUP_ID):
                if user_id and user_id != ADMIN_USER_ID and user_id not in usuarios_que_pediram:
                    usuarios_que_pediram.add(user_id)
                    total = len(usuarios_que_pediram)
                    print(f"📥 Pedido contado! Total: {total}/10")

                    if total >= 10:
                        print("🔒 10 pedidos atingidos! Fechando lista...")
                        enviar_telegram("editMessageText", {
                            "chat_id": TELEGRAM_CHANNEL_ID,
                            "message_id": message_id_canal,
                            "text": criar_texto_fechada(total),
                            "parse_mode": "HTML"
                        })
                        print("✅ Lista fechada com sucesso. Script finalizado.")
                        return

    print("⏰ Tempo limite de monitoramento esgotado.")

if __name__ == "__main__":
    main()
