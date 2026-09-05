import os
import time
import requests

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "SEU_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID", "@k404_modapk")
DISCUSSION_GROUP_ID = os.environ.get("DISCUSSION_GROUP_ID", "-100XXXXXXXXXX") # ID do grupo de comentários
ADMIN_USER_ID = int(os.environ.get("ADMIN_USER_ID", "123456789")) # Seu ID do Telegram para segurança

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
    res = requests.post(url, json=payload)
    return res.json()

def main():
    print("🤖 Bot de controle de pedidos K404 rodando e aguardando comando /pedidos_bot...")
    offset = 0
    
    # Estado da sessão de pedidos
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

                # Verifica se há mensagens
                msg = update.get("message") or update.get("channel_post")
                if not msg:
                    continue

                chat_id = msg["chat"]["id"]
                user_id = msg.get("from", {}).get("id")
                texto_msg = msg.get("text", "")

                # 1. ADMIN ABRE A LISTA COM /pedidos_bot
                if texto_msg.strip() == "/pedidos_bot" and user_id == ADMIN_USER_ID and not sessao_ativa:
                    print("🚀 Comando recebido! Abrindo lista no canal...")
                    res = enviar_telegram("sendMessage", {
                        "chat_id": TELEGRAM_CHANNEL_ID,
                        "text": TEXTO_ABERTA,
                        "parse_mode": "HTML"
                    })
                    
                    if res.get("ok"):
                        message_id_canal = res["result"]["message_id"]
                        sessao_ativa = True
                        usuarios_que_pediram.clear()
                        print(f"✅ Lista aberta com sucesso! ID da mensagem: {message_id_canal}")
                    else:
                        print(f"❌ Erro ao abrir lista: {res}")

                # 2. CONTROLE DOS COMENTÁRIOS NO GRUPO ENQUANTO A LISTA ESTIVER ABERTA
                elif sessao_ativa and str(chat_id) == str(DISCUSSION_GROUP_ID):
                    # Ignora mensagens do próprio bot ou do admin se quiser, mas conta os membros
                    if user_id == ADMIN_USER_ID:
                        continue

                    # Regra: 1 pedido por usuário
                    if user_id not in usuarios_que_pediram:
                        usuarios_que_pediram.add(user_id)
                        total_atual = len(usuarios_que_pediram)
                        print(f"📥 Pedido recebido! Total: {total_atual}/10")

                        # Atualiza o contador na mensagem do canal em tempo real (opcional) ou verifica o limite
                        if total_atual >= 10:
                            print("🔒 Limite de 10 atingido! Fechando lista automaticamente...")
                            enviar_telegram("editMessageText", {
                                "chat_id": TELEGRAM_CHANNEL_ID,
                                "message_id": message_id_canal,
                                "text": criar_texto_fechada(total_atual),
                                "parse_mode": "HTML"
                            })
                            sessao_ativa = False
                            print("✅ Lista encerrada e fechada com sucesso via código.")

        except Exception as e:
            print(f"❌ Erro no loop do bot: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
