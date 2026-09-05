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

def criar_texto_andamento(total):
    return (
        f"🔥 <b>LISTA DE PEDIDOS ABERTA! ({total}/10)</b>\n"
        f"🔥 <b>GAME REQUESTS OPEN! ({total}/10)</b>\n\n"
        "🎮 Comente o jogo que você quer abaixo (Apenas os 10 primeiros! 1 por pessoa)\n"
        "🎮 Comment your game below (Only the FIRST 10 requests! 1 per person)\n\n"
        f"⏳ Pedidos recebidos / Requests received: <b>{total}/10</b>"
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

    print("🚀 Abrindo a lista de pedidos no canal...")
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
    
    print("👀 Monitorando comentários no grupo vinculado...")
    usuarios_que_pediram = set()
    inicio = time.time()
    offset = None
    
    # Roda por até 20 minutos monitorando
    while (time.time() - inicio) < 1200:
        time.sleep(4)
        
        url_updates = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates?timeout=3"
        if offset:
            url_updates += f"&offset={offset}"
            
        try:
            resp_grupo = requests.get(url_updates).json()
        except:
            continue

        if not resp_grupo.get("ok"):
            continue

        for update in resp_grupo.get("result", []):
            update_id = update.get("update_id")
            offset = update_id + 1

            msg = update.get("message")
            if not msg:
                continue

            chat_id = str(msg.get("chat", {}).get("id"))
            user = msg.get("from", {})
            user_id = user.get("id")
            message_thread_id = msg.get("message_thread_id")

            # Verifica se a mensagem pertence ao grupo de discussão E está conectada ao tópico da postagem do canal
            if chat_id == str(DISCUSSION_GROUP_ID):
                # Se o grupo usa tópicos por postagem, message_thread_id costuma bater com o message_id do canal ou o bot aceita do grupo geral
                if user_id and user_id != ADMIN_USER_ID and user_id not in usuarios_que_pediram:
                    usuarios_que_pediram.add(user_id)
                    total = len(usuarios_que_pediram)
                    print(f"📥 Pedido de @{user.get('username', user_id)} contado! Total: {total}/10")

                    # Atualiza o contador na mensagem do canal em tempo real!
                    enviar_telegram("editMessageText", {
                        "chat_id": TELEGRAM_CHANNEL_ID,
                        "message_id": message_id_canal,
                        "text": criar_texto_andamento(total),
                        "parse_mode": "HTML"
                    })

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

    print("⏰ Tempo limite esgotado.")

if __name__ == "__main__":
    main()
