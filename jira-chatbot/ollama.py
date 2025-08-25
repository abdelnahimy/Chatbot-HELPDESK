import requests
import json
import os
import subprocess
import time
from typing import Optional

class ImprovedOllamaChatbot:
    def __init__(self, model_name="phi3:mini"):
        """
        Chatbot Ollama amélioré basé sur main.py
        
        Modèles recommandés :
        - "llama3.1:8b" - Meilleure précision pour la détection d'intent
        - "mistral:7b" - Bon équilibre
        - "phi3:mini" - Plus rapide mais moins précis
        """
        self.model_name = model_name
        self.ollama_url = "http://localhost:11434"
        
        # Charger les données d'intention (identique à main.py)
        self.load_intent_data()
        
        # Liste des intents "non problèmes" (identique à main.py)
        self.NON_PROBLEM_INTENTS = {
            "greet", "goodbye", "thanks", "help", "compliment", "frustrated_user", "system_status"
        }
        
        # Vérifier et initialiser Ollama
        self.setup_ollama()
    
    def load_intent_data(self):
        """Charger les fichiers de données d'intention (identique à main.py)"""
        try:
            if not os.path.exists("data"):
                os.makedirs("data")
            
            # Créer tags.json avec plus de tags pour améliorer la précision
            if not os.path.exists("data/tags.json"):
                default_tags = [
                    "greet", "goodbye", "thanks", "help", "login_problem", 
                    "password_reset", "software_issue", "hardware_problem",
                    "network_issue", "email_problem", "printer_issue",
                    "system_status", "compliment", "frustrated_user",
                    "account_locked", "vpn_issue", "file_access", "installation_help"
                ]
                with open("data/tags.json", "w", encoding="utf-8") as f:
                    json.dump(default_tags, f, ensure_ascii=False, indent=2)
                print("✅ Fichier data/tags.json créé")
            
            # Créer intents.json avec plus d'exemples pour améliorer la précision
            if not os.path.exists("data/intents.json"):
                default_intents = {
                    "intents": [
                        {
                            "tag": "greet",
                            "patterns": ["Bonjour", "Salut", "Hello", "Bonsoir", "Coucou", "Hey"]
                        },
                        {
                            "tag": "goodbye", 
                            "patterns": ["Au revoir", "Bye", "À bientôt", "Salut", "Ciao"]
                        },
                        {
                            "tag": "thanks",
                            "patterns": ["Merci", "Merci beaucoup", "Thanks", "Je vous remercie"]
                        },
                        {
                            "tag": "login_problem", 
                            "patterns": [
                                "Je n'arrive pas à me connecter", 
                                "Problème de connexion", 
                                "Login ne marche pas",
                                "Impossible de me connecter",
                                "Erreur de connexion"
                            ]
                        },
                        {
                            "tag": "password_reset",
                            "patterns": [
                                "Mot de passe oublié", 
                                "Reset password", 
                                "Changer mot de passe",
                                "J'ai oublié mon mot de passe",
                                "Réinitialiser mot de passe"
                            ]
                        },
                        {
                            "tag": "email_problem",
                            "patterns": [
                                "Problème email",
                                "Email ne marche pas", 
                                "Impossible d'envoyer email",
                                "Outlook ne fonctionne pas"
                            ]
                        }
                    ]
                }
                with open("data/intents.json", "w", encoding="utf-8") as f:
                    json.dump(default_intents, f, ensure_ascii=False, indent=2)
                print("✅ Fichier data/intents.json créé")
            
            # Charger les données
            with open("data/tags.json", "r", encoding="utf-8") as f:
                self.intents_tags = json.load(f)

            with open("data/intents.json", "r", encoding="utf-8") as f:
                self.intents_data = json.load(f)
                
        except Exception as e:
            print(f"❌ Erreur lors du chargement des données: {e}")
            # Données de fallback
            self.intents_tags = ["greet", "help", "login_problem"]
            self.intents_data = {"intents": []}
    
    def check_ollama_installed(self):
        """Vérifier si Ollama est installé"""
        try:
            result = subprocess.run(["ollama", "--version"], 
                                 capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except:
            return False
    
    def check_ollama_running(self):
        """Vérifier si le serveur Ollama est en cours d'exécution"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def start_ollama_service(self):
        """Démarrer le service Ollama"""
        try:
            print("🚀 Démarrage du service Ollama...")
            subprocess.Popen(["ollama", "serve"], 
                           creationflags=subprocess.CREATE_NO_WINDOW)
            
            # Attendre que le service démarre
            for i in range(15):  # Augmenté à 15 tentatives
                if self.check_ollama_running():
                    print("✅ Service Ollama démarré avec succès")
                    return True
                print(f"⏳ Attente du démarrage... ({i+1}/15)")
                time.sleep(2)
            
            return False
        except Exception as e:
            print(f"❌ Erreur lors du démarrage d'Ollama: {e}")
            return False
    
    def check_model_exists(self):
        """Vérifier si le modèle est téléchargé"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags")
            if response.status_code == 200:
                models = response.json().get('models', [])
                return any(model['name'].startswith(self.model_name) for model in models)
        except:
            pass
        return False
    
    def download_model(self):
        """Télécharger le modèle"""
        print(f"📥 Téléchargement du modèle {self.model_name}...")
        try:
            result = subprocess.run(["ollama", "pull", self.model_name], 
                                 capture_output=False, text=True)
            return result.returncode == 0
        except Exception as e:
            print(f"❌ Erreur lors du téléchargement: {e}")
            return False
    
    def setup_ollama(self):
        """Configuration complète d'Ollama"""
        print("=== Configuration d'Ollama ===")
        
        if not self.check_ollama_installed():
            print("❌ Ollama n'est pas installé!")
            print("📋 Installez Ollama depuis https://ollama.ai")
            return False
        
        if not self.check_ollama_running():
            if not self.start_ollama_service():
                print("❌ Impossible de démarrer Ollama")
                return False
        
        if not self.check_model_exists():
            print(f"📦 Téléchargement du modèle {self.model_name}...")
            if not self.download_model():
                print("❌ Échec du téléchargement")
                return False
        
        print("🎉 Configuration terminée!\n")
        return True
    
    def call_ollama(self, prompt: str, max_tokens: int = 100) -> Optional[str]:
        """
        Appeler l'API Ollama avec des paramètres optimisés pour la précision
        """
        try:
            response = requests.post(f"{self.ollama_url}/api/generate", 
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": 0.3,  # Augmenté légèrement pour plus de naturel
                        "top_p": 0.9,        
                        "top_k": 40,         
                        "repeat_penalty": 1.1,
                        "stop": ["\n\n", "```", "json"]  # Arrêter sur JSON ou double saut de ligne
                    }
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()["response"].strip()
                
                # Nettoyer la réponse de tout format indésirable
                # Enlever les balises JSON, markdown, etc.
                result = result.replace("```json", "").replace("```", "")
                result = result.replace("```python", "").replace("```text", "")
                
                # Prendre la première phrase cohérente
                lines = result.split('\n')
                clean_result = []
                
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('{') and not line.startswith('['):
                        clean_result.append(line)
                    elif clean_result:  # Si on a déjà du contenu, arrêter
                        break
                
                return ' '.join(clean_result) if clean_result else result.split('\n')[0].strip()
            else:
                print(f"❌ Erreur API Ollama: {response.status_code}")
        except Exception as e:
            print(f"❌ Erreur Ollama: {e}")
        
        return None
    
    def detect_intent(self, user_message: str) -> str:
        """
        Détection d'intent améliorée (identique à main.py)
        """
        # Prompt plus strict et précis
        prompt = f"""Tu es un assistant support en français.
Voici la liste des intentions possibles : {self.intents_tags}.
Détecte l'intention de l'utilisateur dans ce message :
"{user_message}"

IMPORTANT : Réponds uniquement par UN SEUL mot qui correspond exactement à une intention de la liste.
Ne donne pas d'explication, pas de phrase complète, juste le mot-clé d'intention."""
        
        result = self.call_ollama(prompt, max_tokens=5)
        
        # Nettoyer et valider le résultat
        if result:
            result = result.strip().lower().replace('"', '').replace("'", "")
            # Extraire juste le premier mot
            result = result.split()[0] if result.split() else result
        
        # Validation du résultat
        if result and result in [tag.lower() for tag in self.intents_tags]:
            return result
        
        # Si l'intent n'est pas reconnu, essayer une approche par mots-clés
        message_lower = user_message.lower()
        
        # Mapping de mots-clés vers intents
        keyword_mapping = {
            "bonjour|salut|hello|bonsoir|coucou": "greet",
            "au revoir|bye|ciao": "goodbye", 
            "merci|thanks": "thanks",
            "connexion|connecter|login|log in": "login_problem",
            "mot de passe|password|mdp": "password_reset",
            "email|mail|outlook|courrier": "email_problem",
            "imprimante|printer|imprimer": "printer_issue",
            "réseau|network|internet|wifi": "network_issue",
            "aide|help|aidez": "help"
        }
        
        for keywords, intent in keyword_mapping.items():
            if any(keyword in message_lower for keyword in keywords.split('|')):
                return intent
                
        return "help"  # Intent par défaut
    
    def ask_user_yes_no(self, question: str) -> str:
        """Demander oui/non à l'utilisateur (identique à main.py)"""
        while True:
            answer = input(question + " (oui/non) ").strip().lower()
            if answer in {"oui", "non"}:
                return answer
            print("Merci de répondre par 'oui' ou 'non'.")
    
    def generate_solution(self, user_message: str, intent: str) -> str:
        """
        Génération de solution améliorée (identique à main.py)
        """
        intent_obj = next((i for i in self.intents_data['intents'] if i['tag'] == intent), None)
        
        if intent_obj:
            prompt = f"""Tu es un assistant support technique en français pour OCP.
L'utilisateur a le problème suivant : "{intent}".
Exemples similaires : {intent_obj['patterns']}.
Message de l'utilisateur : "{user_message}"

Donne une réponse courte et professionnelle en français (maximum 2 phrases).
Ne commence pas par "Voici" ou "```". Réponds directement comme un humain."""
        else:
            prompt = f"""Tu es un assistant support technique en français pour OCP.
Message de l'utilisateur : "{user_message}"

Donne une réponse courte et professionnelle en français (maximum 2 phrases).
Ne commence pas par "Voici" ou "```". Réponds directement comme un humain."""
        
        result = self.call_ollama(prompt, max_tokens=80)
        return result if result else "Désolé, je n'ai pas de solution disponible pour cette demande."
    
    def ask_solution_or_ticket(self) -> str:
        """Demander choix solution/ticket (identique à main.py)"""
        while True:
            choice = input("Voulez-vous une solution ou créer un ticket ? (solution/ticket) ").strip().lower()
            if choice in ["solution", "ticket"]:
                return choice
            print("Merci de répondre par 'solution' ou 'ticket'.")
    
    def generate_ticket_details(self, user_message: str) -> tuple[str, str]:
        """
        Génération de détails de ticket améliorée (identique à main.py)
        """
        # Générer le titre
        prompt_title = f"""Crée un titre court (maximum 8 mots) pour un ticket d'assistance basé sur :
"{user_message}"

Réponds seulement par le titre, sans guillemets ni explications."""
        
        title = self.call_ollama(prompt_title, max_tokens=15)
        
        # Générer la description
        prompt_desc = f"""Crée une description technique claire pour un ticket d'assistance :
Message utilisateur : "{user_message}"

Écris une description professionnelle en 2-3 phrases maximum, sans format spécial."""
        
        description = self.call_ollama(prompt_desc, max_tokens=60)
        
        return (
            title or "Problème technique", 
            description or user_message
        )
    
    def create_ticket(self, title: str, description: str):
        """Créer un ticket (identique à main.py)"""
        print(f"\nTicket créé avec succès !\nTitre : {title}\nDescription : {description}\n")
    
    def run_chat(self):
        """
        Boucle principale du chatbot (identique à main.py)
        """
        print("Chatbot Helpdesk - Dites 'quit' pour arrêter.\n")

        while True:
            try:
                user_input = input("Vous: ").strip()
                if user_input.lower() == "quit":
                    print("Au revoir !")
                    break

                intent = self.detect_intent(user_input)
                print(f"Intent détectée : {intent}")

                if intent in self.NON_PROBLEM_INTENTS:
                    # Pour les intents non-problèmes, réponse directe
                    response = self.generate_solution(user_input, intent)
                    print(f"Bot: {response}\n")
                else:
                    # Pour les intents problèmes, proposer solution ou ticket
                    choice = self.ask_solution_or_ticket()

                    if choice == "solution":
                        solution = self.generate_solution(user_input, intent)
                        print(f"Bot (solution): {solution}\n")
                    else:
                        title, description = self.generate_ticket_details(user_input)
                        self.create_ticket(title, description)
                        
            except KeyboardInterrupt:
                print("\n\n👋 Au revoir!")
                break
            except Exception as e:
                print(f"\n❌ Erreur: {e}")
                continue

if __name__ == "__main__":
    print("=== CHATBOT HELPDESK OCP - VERSION AMÉLIORÉE ===\n")
    
    MODEL_NAME = "phi3:mini"
    
    try:
        chatbot = ImprovedOllamaChatbot(model_name=MODEL_NAME)
        chatbot.run_chat()
    except KeyboardInterrupt:
        print("\n\nApplication fermée.")
    except Exception as e:
        print(f"\n❌ Erreur fatale: {e}")
        input("\nAppuyez sur Entrée pour quitter...")