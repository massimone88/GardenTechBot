import re
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os
import smtplib
from email.message import EmailMessage

# Configurazione (queste variabili verranno lette dai segreti di GitHub)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GEMINI_KEY = os.getenv("GEMINI_KEY")
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD") # Usa una "App Password"
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", 465))
README_PATH = "README.md"

# Configura Gemini
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-flash-latest')


def create_eml_content(links_data):
    today = datetime.now().strftime("%d/%m/%Y")

    # Costruiamo il contenuto HTML per ogni link
    html_items = ""
    for item in links_data:
        html_items += f"""
        <div style="margin-bottom: 15px;">
            <a href="{item['url']}" style="font-size: 18px; color: #007bff; text-decoration: none; font-weight: bold;">{item['title']}</a>
            <p style="margin: 5px 0; font-style: italic; color: #555;">{item['summary']}</p>
        </div>
        """

    # Leggiamo il template e sostituiamo i placeholder
    with open("template.html", "r", encoding="utf-8") as f:
        template = f.read()

    email_body = template.replace("{{date}}", today).replace("{{content}}", html_items)

    # Creazione dell'oggetto EmailMessage (struttura .eml)
    msg = EmailMessage()
    msg['Subject'] = f"Digital Garden Newsletter - {today}"
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER
    msg.set_content("Abilita l'HTML per vedere questa newsletter.")  # Fallback testo semplice
    msg.add_alternative(email_body, subtype='html')

    return msg


def send_email(msg):
    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as smtp:
            smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
            smtp.send_message(msg)
        print("Email inviata con successo!")
    except Exception as e:
        print(f"Errore invio email: {e}")


# Modifica la funzione update_readme per ritornare i dati
def process_data(links):
    if not links: return []
    data = []
    for link in links:
        title = get_page_title(link)
        summary = get_summary(link, title)
        data.append({'url': link, 'title': title, 'summary': summary})
    return data

def get_summary(url, title):
    """Chiede a Gemini di riassumere il contenuto del link."""
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(m.name)

    try:
        prompt = f"Riassumi in una sola frase professionale in italiano il contenuto di questo link: {url}. Il titolo della pagina è {title}. Non essere logorroico. Minimo 100 caratteri. Sotto questa soglia, la preview sembra povera e non dà valore aggiunto al titolo. Massimo: 200-250 caratteri."
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return "Riassunto non disponibile."

def get_page_title(url):
    """Scarica la pagina e cerca il titolo. Se fallisce, ritorna l'URL."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'} # Simula un browser per evitare blocchi
        response = requests.get(url, timeout=5, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        title = soup.title.string.strip()
        # Rimuove eventuali ritorni a capo nel titolo
        return " ".join(title.split())
    except Exception as e:
        print(f"Errore nel recupero titolo per {url}: {e}")
        return url

def get_telegram_updates():
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    response = requests.get(url).json()
    links = set()  # Usiamo un set per garantire l'univocità a livello di esecuzione
    last_update_id = 0

    if response["ok"] and response["result"]:
        for result in response["result"]:
            last_update_id = result["update_id"]
            message = result.get("message", {})
            text = message.get("text", "")

            # Controllo sicurezza: processa solo i messaggi inviati dal tuo ID
            if str(message.get("chat", {}).get("id")) == CHAT_ID:
                # Regex per estrarre tutti i link che iniziano con http o https
                found_links = re.findall(r'(https?://[^\s]+)', text)
                for link in found_links:
                    links.add(link)

        # Conferma a Telegram che abbiamo processato questi messaggi
        requests.get(f"{url}?offset={last_update_id + 1}")

    return list(links)

def update_readme(data):
    if not len(data):
        return False

    today = datetime.now().strftime("%d/%m/%Y")
    with open(README_PATH, "a", encoding="utf-8") as f:
        f.write(f"\n### Risorse salvate il {today}\n")
        for d in data:  # set() evita duplicati nello stesso giorno
            f.write(f"* [{d['title']}]({d['url']})\n")
    return True


if __name__ == "__main__":
    new_links = get_telegram_updates()
    new_links = ['https://share.google/Gmw6cXBCq6Ub7xTkb','https://github.com/EmulatorJS/EmulatorJS','https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals']

    if new_links:
        data = process_data(new_links)
        update_readme(data)
        msg = create_eml_content(data)
        send_email(msg)
    if update_readme(new_links):
        print("README aggiornato con nuovi link da Telegram!")
    else:
        print("Nessun nuovo link trovato.")