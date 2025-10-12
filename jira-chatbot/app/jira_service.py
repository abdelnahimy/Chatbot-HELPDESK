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
def list_all_tickets(max_results=50):
    """
    Récupère la liste de tous les tickets du projet
    
    Args:
        max_results (int): Nombre maximum de tickets à récupérer (défaut: 50)
    
    Returns:
        list: Liste des tickets avec leurs informations
    """
    # ✅ NOUVEAU: Utiliser le nouvel endpoint /search/jql
    url = f"{JIRA_DOMAIN}/rest/api/3/search/jql"
    
    # Requête JQL pour filtrer les tickets du projet
    jql_query = f'project = {PROJECT_KEY} ORDER BY created DESC'
    
    # ✅ CHANGEMENT: Les paramètres sont maintenant dans le body (POST)
    payload = {
        "jql": jql_query,
        "maxResults": max_results,
        "fields": ["summary", "description", "status", "created", "priority", "issuetype"]
    }
    
    try:
        # ✅ CHANGEMENT: Utiliser POST au lieu de GET
        response = requests.post(url, headers=headers, auth=auth, json=payload)
        response.raise_for_status()
        
        data = response.json()
        issues = data.get("issues", [])
        
        tickets = []
        for issue in issues:
            fields = issue.get("fields", {})
            
            # Extraire le texte de la description (format ADF)
            description_text = ""
            description = fields.get("description")
            if description and isinstance(description, dict):
                content = description.get("content", [])
                for block in content:
                    if block.get("type") == "paragraph":
                        for item in block.get("content", []):
                            if item.get("type") == "text":
                                description_text += item.get("text", "")
            
            # Construire l'objet ticket
            ticket = {
                "ticket_key": issue.get("key"),
                "title": fields.get("summary", "Sans titre"),
                "description": description_text or "Aucune description",
                "status": fields.get("status", {}).get("name", "Unknown"),
                "created_at": fields.get("created", ""),
                "priority": fields.get("priority", {}).get("name", "Medium") if fields.get("priority") else "Medium",
                "issuetype": fields.get("issuetype", {}).get("name", "Task")
            }
            
            tickets.append(ticket)
        
        print(f"✅ {len(tickets)} tickets récupérés avec succès")
        return tickets
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur lors de la récupération des tickets: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Status Code: {e.response.status_code}")
            print(f"Response: {e.response.text}")
        return []

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

