import os
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

# Charger les variables de l'environnement (.env)
load_dotenv()

EMAIL = os.getenv("JIRA_EMAIL")
API_TOKEN = os.getenv("JIRA_API_TOKEN")
JIRA_DOMAIN = os.getenv("JIRA_DOMAIN")
PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY")

if not all([EMAIL, API_TOKEN, JIRA_DOMAIN, PROJECT_KEY]):
    raise ValueError("Une ou plusieurs variables d'environnement sont manquantes.")

auth = HTTPBasicAuth(EMAIL, API_TOKEN)
headers = {
    "Accept": "application/json",
    "Content-Type": "application/json"
}

def create_ticket(summary, description_text, issuetype="Task"):
    url = f"{JIRA_DOMAIN}/rest/api/3/issue"

    description_adf = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": description_text
                    }
                ]
            }
        ]
    }

    payload = {
        "fields": {
            "project": {
                "key": PROJECT_KEY
            },
            "summary": summary,
            "description": description_adf,
            "issuetype": {
                "name": issuetype
            }
        }
    }

    try:
        response = requests.post(url, headers=headers, auth=auth, json=payload)
        response.raise_for_status()
        return response.json()["key"]
    except requests.exceptions.RequestException as e:
        print("Erreur de création :", response.status_code, response.text)
        return None


def get_ticket_status(ticket_key):
    url = f"{JIRA_DOMAIN}/rest/api/3/issue/{ticket_key}"

    response = requests.get(url, headers=headers, auth=auth)

    if response.status_code == 200:
        try:
            data = response.json()
            status = data["fields"]["status"]["name"]
            return status
        except KeyError:
            print("Impossible de lire le statut dans la réponse.")
            return None
    else:
        print("Erreur HTTP :", response.status_code)
        print("Réponse : ", response.text)
        return None

