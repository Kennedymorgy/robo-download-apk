import os
import time
import requests

# Puxa as chaves dos Secrets do GitHub
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
        print(f"❌ Erro na requisição do Telegram: {e}")
        return {"ok": False}

def main():
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHANNEL_ID or not DISCUSSION_GROUP_ID or not ADMIN_USER_ID:
        print("❌ ERRO: Faltam variáveis nos Secrets do GitHub.")
        return

    print("🤖 Bot de pedidos do Canal K404 iniciado e escutando...")
    offset = 0
    sessao_ativa = False
    message_id_canal = None
    usuarios_que_pediram = set()

    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates?offset={offset}&timeout=30"
            resposta = requests.get(url).json()

            if not resposta.get("ok"):
                time.sleep(5)
                continue

            for update in resposta.get("result", []):
                offset = update["update_id"] + 1

                # Verifica se veio mensagem do canal ou do grupo
                msg = update.get("message") or update.get("channel_post") or update.get("edited_channel_post")
                if not msg:
                    continue

                chat_id = str(msg.get("chat", {}).get("id"))
                user = msg.get("from", {})
                user_id = user.get("id") if user else None
                texto_msg = msg.get("text", "")

                # Se a mensagem veio do canal principal
                if chat_id == str(TELEGRAM_CHANNEL_ID):
                    if texto_msg.strip() == "/pedidos_bot" and not sessao_ativa:
                        print("🚀 Comando /pedidos_bot detectado no canal! Abrindo lista...")
                        
                        # Tenta apagar o comando que você mandou no canal para ficar limpo (opcional)
                        msg_id_comando = msg.get("message_id")
                        if msg_id_comando:
                            enviar_telegram("deleteMessage", {
                                "chat_id": TELEGRAM_CHANNEL_ID,
                                "message_id": msg_id_comando
                            })

                        # Envia a mensagem de lista aberta
                        res = enviar_telegram("sendMessage", {
                            "chat_id": TELEGRAM_CHANNEL_ID,
                            "text": TEXTO_ABERTA,
                            "parse_mode": "HTML"
                        })
                        
                        if res.get("ok"):
                            message_id_canal = res["result"]["message_id"]
                            sessao_ativa = True
                            usuarios_que_pediram.clear()
                            print(f"✅ Lista aberta com sucesso no canal! ID da mensagem: {message_id_canal}")
                        else:
                            print(f"❌ Erro ao enviar mensagem para o canal: {res}")

                # Se a lista estiver aberta e a mensagem vier do GRUPO DE COMENTÁRIOS vinculado
                elif sessao_ativa and chat_id == str(DISCUSSION_GROUP_ID):
                    # Ignora se o admin mandar mensagem no grupo
                    if user_id and user_id == ADMIN_USER_ID:
                        continue

                    if user_id and user_id not in usuarios_que_pediram:
                        usuarios_que_pediram.add(user_id)
                        total_atual = len(usuarios_que_pediram)
                        print(f"📥 Pedido de usuário registrado! Total: {total_atual}/10")

                        if total_atual >= 10:
                            print("🔒 Limite de 10 atingido! Fechando lista no canal...")
                            enviar_telegram("editMessageText", {
                                "chat_id": TELEGRAM_CHANNEL_ID,
                                "message_id": message_id_canal,
                                "text": criar_texto_fechada(total_atual),
                                "parse_mode": "HTML"
                            })
                            sessao_ativa = False
                            print("✅ Lista encerrada com sucesso.")

        except Exception as e:
            print(f"❌ Erro no loop: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
