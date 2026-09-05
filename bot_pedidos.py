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
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHANNEL_ID:
        print("❌ ERRO: Faltam variáveis nos Secrets do GitHub.")
        return

    print("🚀 Abrindo a lista de pedidos no canal automaticamente...")
    
    res = enviar_telegram("sendMessage", {
        "chat_id": TELEGRAM_CHANNEL_ID,
        "text": TEXTO_ABERTA,
        "parse_mode": "HTML"
    })

    if not res.get("ok"):
        print(f"❌ Erro ao enviar mensagem no canal: {res}")
        return

    message_id_canal = res["result"]["message_id"]
    print(f"✅ Lista aberta com sucesso! ID da mensagem: {message_id_canal}")
    
    print("👀 Monitorando o grupo de comentários em busca dos 10 pedidos...")
    usuarios_que_pediram = set()
    inicio = time.time()
    
    # Vamos deixar monitorando por 15 minutos (900 segundos)
    while (time.time() - inicio) < 900:
        time.sleep(5)
        url_updates = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates?offset=-1"
        try:
            resp_grupo = requests.get(url_updates).json()
        except:
            continue

        for update in resp_grupo.get("result", []):
            msg = update.get("message")
            if not msg:
                continue

            chat_id = str(msg.get("chat", {}).get("id"))
            user = msg.get("from", {})
            user_id = user.get("id")

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
                        print("✅ Lista fechada com sucesso.")
                        return

    print("⏰ Tempo limite de 15 minutos esgotado.")

if __name__ == "__main__":
    main()
