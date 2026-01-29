import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os


# Configurazione (queste variabili verranno lette dai segreti di GitHub)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
README_PATH = "README.md"


def get_page_title(url):
    try:
        response = requests.get(url, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        return soup.title.string.strip() if soup.title else url
    except:
        return url

def get_telegram_updates():
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    response = requests.get(url).json()
    links = []
    if response["ok"]:
        for result in response["result"]:
            # Filtra solo i messaggi che contengono "http"
            message = result.get("message", {})
            text = message.get("text", "")
            if "http" in text and str(message.get("chat", {}).get("id")) == CHAT_ID:
                links.append(text)
    return links

def update_readme(links):
    if not links:
        return False

    today = datetime.now().strftime("%d/%m/%Y")
    with open(README_PATH, "a", encoding="utf-8") as f:
        f.write(f"\n### Risorse salvate il {today}\n")
        for link in set(links):  # set() evita duplicati nello stesso giorno
            title = get_page_title(link)
            f.write(f"* [{title}]({link})\n")
    return True


if __name__ == "__main__":
    new_links = get_telegram_updates()
    if update_readme(new_links):
        print("README aggiornato con nuovi link da Telegram!")
    else:
        print("Nessun nuovo link trovato.")