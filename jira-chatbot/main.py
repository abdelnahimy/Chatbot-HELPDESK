import requests
import json

API_KEY = "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"
MODEL = "mistralai/mistral-small-3.2-24b-instruct:free"

# Charger les tags et intents
with open("data/tags.json", "r", encoding="utf-8") as f:
    intents_tags = json.load(f)

with open("data/intents.json", "r", encoding="utf-8") as f:
    intents_data = json.load(f)

# Liste des intents "non problèmes" : pas besoin de confirmation ni choix solution/ticket
NON_PROBLEM_INTENTS = {
    "greet", "goodbye", "thanks", "help", "compliment", "frustrated_user", "system_status"
}

def call_openrouter_api(prompt, max_tokens=100):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.5
    }
    response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
    
    try:
        response_json = response.json()
    except json.JSONDecodeError:
        print("Erreur : Réponse invalide.")
        return None
    
    if 'choices' in response_json:
        return response_json['choices'][0]['message']['content'].strip()
    else:
        print("Erreur API : Impossible d'obtenir une réponse.")
        return None


def detect_intent(user_message):
    prompt = f"""
Tu es un assistant support en français.
Voici la liste des intentions possibles : {intents_tags}.
Détecte l’intention de l’utilisateur dans ce message :
\"{user_message}\"
Répond uniquement par le tag d’intention.
"""
    return call_openrouter_api(prompt, max_tokens=10)

def ask_user_yes_no(question):
    while True:
        answer = input(question + " (oui/non) ").strip().lower()
        if answer in {"oui", "non"}:
            return answer
        print("Merci de répondre par 'oui' ou 'non'.")

def generate_solution(user_message, intent):
    intent_obj = next((i for i in intents_data['intents'] if i['tag'] == intent), None)
    if intent_obj:
        prompt = f"""
Tu es un assistant support en français.
L'utilisateur a l'intention suivante : "{intent}".
Voici des exemples de cette intention : {intent_obj['patterns']}.
Propose une solution courte et claire pour cette demande :
\"{user_message}\"
"""
        return call_openrouter_api(prompt)
    else:
        return "Désolé, je n'ai pas de solution disponible pour cette demande."

def ask_solution_or_ticket():
    while True:
        choice = input("Voulez-vous une solution ou créer un ticket ? (solution/ticket) ").strip().lower()
        if choice in ["solution", "ticket"]:
            return choice
        print("Merci de répondre par 'solution' ou 'ticket'.")

def generate_ticket_details(user_message):
    prompt_title = f"""
Tu es un assistant support. Génère un titre court et clair (moins de 10 mots) pour un ticket d'après ce message utilisateur :
\"{user_message}\"
Répond uniquement par le titre.
"""
    title = call_openrouter_api(prompt_title, max_tokens=15)

    prompt_desc = f"""
Tu es un assistant support. Génère une description détaillée pour un ticket d'après ce message utilisateur :
\"{user_message}\"
Répond uniquement par la description.
"""
    description = call_openrouter_api(prompt_desc, max_tokens=100)

    return title, description

def create_ticket(title, description):
    # TODO: Appeler ton API Jira pour créer le ticket
    print(f"\nTicket créé avec succès !\nTitre : {title}\nDescription : {description}\n")

if __name__ == "__main__":
    print("Chatbot Helpdesk - Dites 'quit' pour arrêter.\n")

    while True:
        user_input = input("Vous: ").strip()
        if user_input.lower() == "quit":
            print("Au revoir !")
            break

        intent = detect_intent(user_input)
        print(f"Intent détectée : {intent}")

        if intent in NON_PROBLEM_INTENTS:
            # Pour les intents non-problèmes, réponse directe sans confirmation ni choix
            response = generate_solution(user_input, intent)
            print(f"Bot: {response}\n")
        else:
            # Pour les intents problèmes, directement proposer solution ou ticket sans confirmation d'intent
            choice = ask_solution_or_ticket()

            if choice == "solution":
                solution = generate_solution(user_input, intent)
                print(f"Bot (solution): {solution}\n")
            else:
                title, description = generate_ticket_details(user_input)
                create_ticket(title, description)
