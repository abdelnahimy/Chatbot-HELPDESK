import requests
from bs4 import BeautifulSoup
import json

# URL à scraper
url = "https://micropro.com/blog/the-most-frequently-asked-questions-our-it-support-helpdesk-is-asked-answered/"

# En-têtes pour simuler un navigateur
headers = {
    "User-Agent": "Mozilla/5.0"
}

# Requête HTTP
response = requests.get(url, headers=headers)
soup = BeautifulSoup(response.content, "html.parser")

faq_data = []

# Extrait tous les titres de questions (éléments h2)
questions = soup.find_all("h2")

for q in questions:
    question_text = q.get_text(strip=True)
    answer_parts = []
    # Récupère les paragraphes suivants jusqu'au prochain h2
    for sibling in q.find_next_siblings():
        if sibling.name == "h2":
            break
        if sibling.name in ["p", "ul", "ol"]:
            answer_parts.append(sibling.get_text(" ", strip=True))
    if answer_parts:
        answer_text = " ".join(answer_parts)
        faq_data.append({
            "question": question_text,
            "answer": answer_text
        })

# Sauvegarde dans un fichier JSON
with open("faq_scraped.json", "w", encoding="utf-8") as f:
    json.dump(faq_data, f, ensure_ascii=False, indent=2)

print(f"  {len(faq_data)} questions extraites avec succès.")
