import requests

from config import BOT_TOKEN, CHAT_ID


def send_message(message):

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }

    try:

        response = requests.post(
            url,
            data=payload,
            timeout=10
        )

        if response.status_code == 200:
            print("Telegram Message Sent")

        else:
            print("Telegram Error :", response.text)

    except Exception as e:

        print("Telegram Exception :", e)
