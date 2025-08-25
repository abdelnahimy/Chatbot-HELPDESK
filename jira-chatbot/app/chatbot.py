import requests
import json
import os
import subprocess
import time
import re
import random
from typing import Optional

# Import the JIRA service functions
try:
    from jira_service import create_ticket as jira_create_ticket, get_ticket_status
    JIRA_AVAILABLE = True
    print("✅ Service JIRA importé avec succès")
except ImportError as e:
    JIRA_AVAILABLE = False
    print(f"⚠️ Service JIRA non disponible: {e}")

class ImprovedOllamaChatbot:
    def __init__(self, model_name="llama3.1:8b"):
        """
        Chatbot Ollama amélioré utilisant jira_service.py
        
        Modèles recommandés :
        - "llama3.1:8b" - Meilleure précision pour la détection d'intent
        - "mistral:7b" - Bon équilibre
        - "phi3:mini" - Plus rapide mais moins précis
        """
        self.model_name = model_name
        self.ollama_url = "http://localhost:11434"
        
        # Charger les données d'intention
        self.load_intent_data()
        
        # Liste des intents "non problèmes"
        self.NON_PROBLEM_INTENTS = {
            "greet", "goodbye", "thanks", "help", "compliment", "frustrated_user", 
            "system_status", "get_ticket_status"
        }
        
        # Gestion du contexte de conversation
        self.conversation_context = {
            "active": False,
            "type": None,  # "solution", "ticket" ou "status_request"
            "intent": None,
            "original_message": None,
            "details_collected": []
        }
        
        # Vérifier et initialiser Ollama
        self.setup_ollama()
    
    def load_intent_data(self):
        """Charger les fichiers de données d'intention"""
        try:
            if not os.path.exists("data"):
                os.makedirs("data")
            
            # Créer tags.json avec tous les intents
            if not os.path.exists("../data/tags.json"):
                default_tags = [
                    "greet", "goodbye", "thanks", "help", "login_problem", 
                    "password_reset", "software_issue", "hardware_problem",
                    "network_issue", "email_problem", "printer_issue",
                    "system_status", "compliment", "frustrated_user",
                    "account_locked", "vpn_issue", "file_access", "installation_help",
                    "get_ticket_status"
                ]
                with open("data/tags.json", "w", encoding="utf-8") as f:
                    json.dump(default_tags, f, ensure_ascii=False, indent=2)
                print("✅ Fichier data/tags.json créé")
            
            # Créer intents.json avec des patterns détaillés
            if not os.path.exists("../data/intents.json"):
                default_intents = {
                    "intents": [
                        {
                            "tag": "greet",
                            "patterns": ["Bonjour", "Salut", "Hello", "Bonsoir", "Coucou", "Hey", "Hi"]
                        },
                        {
                            "tag": "goodbye", 
                            "patterns": ["Au revoir", "Bye", "À bientôt", "Salut", "Ciao", "Goodbye"]
                        },
                        {
                            "tag": "thanks",
                            "patterns": ["Merci", "Merci beaucoup", "Thanks", "Je vous remercie", "Thank you"]
                        },
                        {
                            "tag": "get_ticket_status",
                            "patterns": [
                                "statut de mon ticket", "status du ticket", "où en est mon ticket",
                                "ticket status", "vérifier ticket", "état du ticket",
                                "suivi de ticket", "avancement ticket", "status SUP-", "statut SUP-"
                            ]
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
                        },
                        {
                            "tag": "printer_issue",
                            "patterns": [
                                "Problème imprimante",
                                "Imprimante ne marche pas",
                                "Impossible d'imprimer"
                            ]
                        },
                        {
                            "tag": "network_issue",
                            "patterns": [
                                "Problème réseau",
                                "Pas d'internet",
                                "WiFi ne marche pas",
                                "Connexion lente"
                            ]
                        }
                    ]
                }
                with open("data/intents.json", "w", encoding="utf-8") as f:
                    json.dump(default_intents, f, ensure_ascii=False, indent=2)
                print("✅ Fichier data/intents.json créé")
            
            # Charger les données
            with open("../data/tags.json", "r", encoding="utf-8") as f:
                self.intents_tags = json.load(f)

            with open("../data/intents.json", "r", encoding="utf-8") as f:
                self.intents_data = json.load(f)
                
        except Exception as e:
            print(f"❌ Erreur lors du chargement des données: {e}")
            # Données de fallback
            self.intents_tags = ["greet", "help", "login_problem", "get_ticket_status"]
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
                           creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            
            # Attendre que le service démarre
            for i in range(15):
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
        """Appeler l'API Ollama avec des paramètres optimisés"""
        try:
            response = requests.post(f"{self.ollama_url}/api/generate", 
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": 0.3,
                        "top_p": 0.9,        
                        "top_k": 40,         
                        "repeat_penalty": 1.1,
                        "stop": ["\n\n", "```", "json"]
                    }
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()["response"].strip()
                
                # Nettoyer la réponse
                result = result.replace("```json", "").replace("```", "")
                result = result.replace("```python", "").replace("```text", "")
                
                lines = result.split('\n')
                clean_result = []
                
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('{') and not line.startswith('['):
                        clean_result.append(line)
                    elif clean_result:
                        break
                
                return ' '.join(clean_result) if clean_result else result.split('\n')[0].strip()
            else:
                print(f"❌ Erreur API Ollama: {response.status_code}")
        except Exception as e:
            print(f"❌ Erreur Ollama: {e}")
        
        return None
    
    def extract_ticket_key_from_message(self, message: str) -> Optional[str]:
        """Extraire la clé de ticket du message (format SUP-123, TICKET-456, etc.)"""
        ticket_pattern = r'\b([A-Z]{2,10}-\d+)\b'
        matches = re.findall(ticket_pattern, message.upper())
        
        if matches:
            return matches[0]
        return None
    
    def validate_and_format_ticket_key(self, ticket_key: str) -> Optional[str]:
        """Valider et formater la clé de ticket"""
        if not ticket_key:
            return None
        
        clean_key = ticket_key.strip().upper()
        ticket_pattern = r'^[A-Z]{2,10}-\d+$'
        
        if re.match(ticket_pattern, clean_key):
            return clean_key
        
        return None
    
    def detect_intent(self, user_message: str) -> str:
        """Détection d'intent améliorée"""
        # Vérifier d'abord si c'est une demande de statut avec des mots-clés spécifiques
        message_lower = user_message.lower()
        status_keywords = ["statut", "status", "état", "suivi", "avancement", "où en est"]
        ticket_keywords = ["ticket", "sup-", "demande", "incident"]
        
        # Si le message contient des mots-clés de statut ET de ticket
        if (any(keyword in message_lower for keyword in status_keywords) and 
            any(keyword in message_lower for keyword in ticket_keywords)):
            return "get_ticket_status"
        
        # Si le message contient une référence directe à un ticket (SUP-123)
        if self.extract_ticket_key_from_message(user_message):
            return "get_ticket_status"
        
        # Prompt pour l'IA
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
            result = result.split()[0] if result.split() else result
        
        # Validation du résultat
        if result and result in [tag.lower() for tag in self.intents_tags]:
            return result
        
        # Mapping de mots-clés vers intents
        keyword_mapping = {
            "bonjour|salut|hello|bonsoir|coucou|hi": "greet",
            "au revoir|bye|ciao|goodbye": "goodbye", 
            "merci|thanks|thank you": "thanks",
            "statut|status|état|suivi|avancement|où en est": "get_ticket_status",
            "connexion|connecter|login|log in": "login_problem",
            "mot de passe|password|mdp|reset": "password_reset",
            "email|mail|outlook|courrier|messagerie": "email_problem",
            "imprimante|printer|imprimer|impression": "printer_issue",
            "réseau|network|internet|wifi|connexion internet": "network_issue",
            "logiciel|software|application|programme": "software_issue",
            "matériel|hardware|ordinateur|pc": "hardware_problem",
            "compte|account|utilisateur|user": "account_locked",
            "vpn|réseau privé": "vpn_issue",
            "fichier|dossier|accès|partage": "file_access",
            "installation|installer|setup": "installation_help",
            "aide|help|aidez|support": "help"
        }
        
        for keywords, intent in keyword_mapping.items():
            if any(keyword in message_lower for keyword in keywords.split('|')):
                return intent
                
        return "help"
    
    def handle_ticket_status_request(self, user_message: str):
        """Gérer les demandes de statut de ticket"""
        ticket_key = self.extract_ticket_key_from_message(user_message)
        
        if ticket_key:
            print(f"🔍 Vérification du statut du ticket {ticket_key}...")
            self.check_ticket_status(ticket_key)
        else:
            print("Bot: Pour vérifier le statut de votre ticket, j'ai besoin de la clé du ticket.")
            print("La clé du ticket ressemble à : SUP-123, TICKET-456, etc.")
            
            ticket_key_input = input("Vous: Clé du ticket : ").strip()
            ticket_key = self.extract_ticket_key_from_message(ticket_key_input)
            
            if ticket_key:
                print(f"🔍 Vérification du statut du ticket {ticket_key}...")
                self.check_ticket_status(ticket_key)
            else:
                print("❌ Format de clé de ticket non reconnu. Veuillez utiliser le format : SUP-123, TICKET-456, etc.")
    
    def generate_response_for_intent(self, user_message: str, intent: str) -> str:
        """Générer une réponse spécifique selon l'intent pour les NON_PROBLEM_INTENTS"""
        responses = {
            "greet": [
                "Bonjour ! Je suis votre assistant support OCP. Comment puis-je vous aider aujourd'hui ?",
                "Salut ! En quoi puis-je vous assister ?",
                "Hello ! Je suis là pour vous aider avec vos questions techniques."
            ],
            "goodbye": [
                "Au revoir ! N'hésitez pas à revenir si vous avez d'autres questions.",
                "À bientôt ! Passez une excellente journée.",
                "Goodbye ! Je reste à votre disposition pour toute assistance future."
            ],
            "thanks": [
                "De rien ! C'est un plaisir de vous aider.",
                "Je vous en prie ! N'hésitez pas si vous avez d'autres questions.",
                "Avec plaisir ! Je suis là pour ça."
            ],
            "help": [
                "Je peux vous aider avec : problèmes de connexion, mots de passe, emails, réseau, imprimantes, logiciels, matériel. Vous pouvez aussi vérifier le statut de vos tickets.",
                "Mes spécialités : support technique, gestion des comptes, résolution de problèmes IT, suivi de tickets. Que puis-je faire pour vous ?",
                "Je suis votre assistant support. Décrivez-moi votre problème ou demandez le statut d'un ticket avec sa clé (ex: SUP-123)."
            ],
            "compliment": [
                "Merci ! Je fais de mon mieux pour vous aider efficacement.",
                "C'est gentil ! Mon objectif est de résoudre vos problèmes rapidement.",
                "Merci beaucoup ! Je suis là pour vous accompagner."
            ],
            "frustrated_user": [
                "Je comprends votre frustration. Laissez-moi vous aider à résoudre ce problème étape par étape.",
                "Je sais que c'est frustrant. Travaillons ensemble pour trouver une solution.",
                "Prenons le temps de bien identifier le problème pour le résoudre efficacement."
            ],
            "system_status": [
                "Les systèmes OCP fonctionnent normalement. Y a-t-il un service spécifique qui vous pose problème ?",
                "État des systèmes : Opérationnels. Si vous rencontrez des difficultés, décrivez-moi le problème.",
                "Tous les services sont en ligne. Quel problème rencontrez-vous exactement ?"
            ]
        }
        
        return random.choice(responses.get(intent, responses["help"]))
    
    def generate_solution(self, user_message: str, intent: str, context_details: list = None) -> str:
        """Génération de solution améliorée avec contexte"""
        intent_obj = next((i for i in self.intents_data['intents'] if i['tag'] == intent), None)
        
        context_text = ""
        if context_details:
            context_text = f"\nDétails supplémentaires fournis : {' '.join(context_details)}"
        
        if intent_obj:
            prompt = f"""Tu es un assistant support technique en français pour OCP.
L'utilisateur a le problème suivant : "{intent}".
Exemples similaires : {intent_obj['patterns']}.
Message de l'utilisateur : "{user_message}"{context_text}

Donne une solution pratique et professionnelle en français (maximum 3 phrases).
Ne commence pas par "Voici" ou "```". Réponds directement comme un humain."""
        else:
            prompt = f"""Tu es un assistant support technique en français pour OCP.
Message de l'utilisateur : "{user_message}"{context_text}

Donne une solution pratique et professionnelle en français (maximum 3 phrases).
Ne commence pas par "Voici" ou "```". Réponds directement comme un humain."""
        
        result = self.call_ollama(prompt, max_tokens=120)
        return result if result else "Désolé, je n'ai pas de solution disponible pour cette demande."
    
    def ask_solution_or_ticket(self) -> str:
        """Demander choix solution/ticket"""
        while True:
            choice = input("Voulez-vous une solution ou créer un ticket ? (solution/ticket) ").strip().lower()
            if choice in ["solution", "ticket"]:
                return choice
            print("Merci de répondre par 'solution' ou 'ticket'.")
    
    def generate_ticket_details(self, user_message: str, context_details: list = None) -> tuple[str, str]:
        """Génération de détails de ticket améliorée avec contexte"""
        full_context = user_message
        if context_details:
            full_context += ". Détails supplémentaires : " + " ".join(context_details)
        
        # Générer le titre
        prompt_title = f"""Crée un titre court (maximum 8 mots) pour un ticket d'assistance basé sur :
"{full_context}"

Réponds seulement par le titre, sans guillemets ni explications."""
        
        title = self.call_ollama(prompt_title, max_tokens=15)
        
        # Générer la description
        prompt_desc = f"""Crée une description technique claire pour un ticket d'assistance :
Message utilisateur : "{user_message}"
Contexte complet : "{full_context}"

Écris une description professionnelle complète en 3-4 phrases maximum, sans format spécial."""
        
        description = self.call_ollama(prompt_desc, max_tokens=100)
        
        return (
            title or "Problème technique", 
            description or full_context
        )
    
    def create_ticket(self, title: str, description: str):
        """Créer un ticket en utilisant jira_service.py"""
        if JIRA_AVAILABLE:
            try:
                print("🎫 Création du ticket dans JIRA...")
                ticket_key = jira_create_ticket(title, description, "Task")
                
                if ticket_key:
                    print(f"✅ Ticket JIRA créé avec succès !")
                    print(f"🔑 Clé du ticket: {ticket_key}")
                    print(f"📋 Titre: {title}")
                    print(f"📝 Description: {description}")
                    
                    status = get_ticket_status(ticket_key)
                    if status:
                        print(f"📊 Statut: {status}")
                    
                    print()
                else:
                    print("❌ Échec de création dans JIRA. Création locale...")
                    self._create_local_ticket(title, description)
                    
            except Exception as e:
                print(f"❌ Erreur lors de l'utilisation du service JIRA: {e}")
                print("Création locale du ticket...")
                self._create_local_ticket(title, description)
        else:
            print("⚠️ Service JIRA non disponible. Création locale...")
            self._create_local_ticket(title, description)
    
    def _create_local_ticket(self, title: str, description: str):
        """Créer un ticket localement (fallback)"""
        print(f"\n✅ Ticket créé localement !")
        print(f"📋 Titre: {title}")
        print(f"📝 Description: {description}\n")
    
    def reset_conversation_context(self):
        """Réinitialiser le contexte de conversation"""
        self.conversation_context = {
            "active": False,
            "type": None,
            "intent": None,
            "original_message": None,
            "details_collected": []
        }
    
    def is_providing_details(self, user_input: str) -> bool:
        """Déterminer si l'utilisateur fournit des détails supplémentaires"""
        detail_indicators = [
            "pendant", "lors", "quand", "j'ai", "c'est", "il y a",
            "le problème", "ça", "cela", "maintenant", "après",
            "avant", "depuis", "durant"
        ]
        
        user_lower = user_input.lower()
        
        if any(indicator in user_lower for indicator in detail_indicators):
            return True
        
        major_intent_keywords = [
            "bonjour", "salut", "au revoir", "merci", "aide", "help", "statut", "status"
        ]
        
        if not any(keyword in user_lower for keyword in major_intent_keywords):
            return True
            
        return False
    
    def check_ticket_status(self, ticket_key: str):
        """Vérifier le statut d'un ticket JIRA avec gestion d'erreurs améliorée"""
        if JIRA_AVAILABLE:
            try:
                print(f"⏳ Recherche du ticket {ticket_key} dans JIRA...")
                status = get_ticket_status(ticket_key)
                
                if status:
                    print(f"✅ Ticket trouvé !")
                    print(f"🎫 Ticket: {ticket_key}")
                    print(f"📊 Statut: {status}")
                    
                    # Informations supplémentaires selon le statut
                    status_info = {
                        "Open": "🟢 Votre ticket est ouvert et en attente de traitement.",
                        "In Progress": "🔄 Votre ticket est en cours de traitement par notre équipe.",
                        "Resolved": "✅ Votre ticket a été résolu. Vérifiez si le problème persiste.",
                        "Closed": "🔒 Votre ticket est fermé. Le problème a été résolu.",
                        "Pending": "⏸️ Votre ticket est en attente d'informations supplémentaires.",
                        "Reopened": "🔄 Votre ticket a été rouvert pour investigation."
                    }
                    
                    info = status_info.get(status, "ℹ️ Statut du ticket mis à jour.")
                    print(f"💬 {info}")
                    
                    # Proposer des actions selon le statut
                    if status in ["Resolved", "Closed"]:
                        response = input("\n❓ Le problème est-il toujours présent ? (oui/non) ").strip().lower()
                        if response == "oui":
                            print("🎫 Je vais créer un nouveau ticket pour ce problème persistant.")
                            title = f"Problème persistant - Référence: {ticket_key}"
                            description = f"Le problème du ticket {ticket_key} persiste malgré la résolution."
                            self.create_ticket(title, description)
                    
                else:
                    print(f"❌ Ticket {ticket_key} introuvable dans le système JIRA.")
                    print("🔍 Vérifiez que la clé du ticket est correcte.")
                    print("💡 Format attendu : SUP-123, INC-456, TASK-789, etc.")
                    
            except Exception as e:
                print(f"❌ Erreur lors de la vérification du statut: {e}")
                print("🔧 Problème de connexion au système JIRA.")
        else:
            print("⚠️ Service JIRA non disponible pour vérifier le statut")
            print("🔧 Le système de tickets n'est pas accessible actuellement.")
    
    def show_help_menu(self):
        """Afficher le menu d'aide complet"""
        help_text = """
🤖 === GUIDE D'UTILISATION DU CHATBOT SUPPORT OCP ===

📋 FONCTIONNALITÉS PRINCIPALES :
  • Résolution de problèmes techniques
  • Création de tickets d'assistance
  • Vérification du statut des tickets
  • Support pour divers problèmes IT

🎯 TYPES DE PROBLÈMES SUPPORTÉS :
  • 🔐 Problèmes de connexion et authentification
  • 🔑 Réinitialisation de mots de passe  
  • 📧 Problèmes d'email et messagerie
  • 🖨️ Dysfonctionnements d'imprimante
  • 🌐 Problèmes réseau et internet
  • 💻 Problèmes logiciels et applications
  • 🔧 Problèmes matériels
  • 🔒 Comptes bloqués et accès
  • 📁 Accès aux fichiers et partages

💬 COMMENT UTILISER :
  1. Décrivez simplement votre problème
  2. Choisissez : solution immédiate ou création de ticket
  3. Suivez les instructions du chatbot

🎫 VÉRIFICATION DE TICKETS :
  • "statut de mon ticket SUP-123"
  • "status du ticket INC-456"
  • "où en est mon ticket TASK-789"

⚡ COMMANDES SPÉCIALES :
  • 'quit' - Quitter le chatbot
  • 'reset' - Réinitialiser la conversation
  • 'status SUP-123' - Vérifier un ticket
  • 'help menu' - Afficher cette aide

💡 CONSEILS :
  • Soyez précis dans la description de votre problème
  • Notez la clé de votre ticket (ex: SUP-123)
  • N'hésitez pas à donner des détails supplémentaires

🆘 SUPPORT URGENT :
  Pour les urgences, contactez directement :
  📞 Support technique : +212-xxx-xxx-xxx
  📧 Email : support@ocp.ma
        """
        print(help_text)
    
    def run_chat(self):
        """Boucle principale du chatbot avec gestion de contexte améliorée"""
        print("=== CHATBOT HELPDESK OCP - AVEC SERVICE JIRA ===")
        if JIRA_AVAILABLE:
            print("✅ Service JIRA disponible")
        else:
            print("⚠️ Service JIRA non disponible - tickets créés localement")
        
        print("\nCommandes spéciales:")
        print("- 'quit' : Quitter le chatbot")
        print("- 'reset' : Réinitialiser la conversation")
        print("- 'status TICKET-123' : Vérifier le statut d'un ticket")
        print("- 'help menu' : Afficher le guide complet d'utilisation")
        print()

        while True:
            try:
                user_input = input("Vous: ").strip()
                
                if user_input.lower() == "quit":
                    print("Au revoir !")
                    break
                
                # Commande pour réinitialiser le contexte
                if user_input.lower() == "reset":
                    self.reset_conversation_context()
                    print("🔄 Conversation réinitialisée.\n")
                    continue
                
                # Commande pour vérifier le statut d'un ticket (format: status TICKET-123)
                if user_input.lower().startswith("status "):
                    ticket_key = user_input.split(" ", 1)[1].strip()
                    self.check_ticket_status(ticket_key)
                    continue

                # Gestion du contexte de conversation active
                if self.conversation_context["active"]:
                    if self.is_providing_details(user_input):
                        self.conversation_context["details_collected"].append(user_input)
                        
                        if self.conversation_context["type"] == "solution":
                            solution = self.generate_solution(
                                self.conversation_context["original_message"],
                                self.conversation_context["intent"],
                                self.conversation_context["details_collected"]
                            )
                            print(f"Bot (solution complète): {solution}")
                            
                            while True:
                                response = input("Cette solution répond-elle à votre problème ? (oui/non/ticket) ").strip().lower()
                                if response == "oui":
                                    print("Parfait ! N'hésitez pas si vous avez d'autres questions.\n")
                                    self.reset_conversation_context()
                                    break
                                elif response == "non":
                                    print("Voulez-vous fournir plus de détails ou créer un ticket ?")
                                    choice = input("(détails/ticket) ").strip().lower()
                                    if choice == "ticket":
                                        title, description = self.generate_ticket_details(
                                            self.conversation_context["original_message"],
                                            self.conversation_context["details_collected"]
                                        )
                                        self.create_ticket(title, description)
                                        self.reset_conversation_context()
                                        break
                                    else:
                                        print("Merci de fournir plus de détails :")
                                        break
                                elif response == "ticket":
                                    title, description = self.generate_ticket_details(
                                        self.conversation_context["original_message"],
                                        self.conversation_context["details_collected"]
                                    )
                                    self.create_ticket(title, description)
                                    self.reset_conversation_context()
                                    break
                                else:
                                    print("Merci de répondre par 'oui', 'non' ou 'ticket'.")
                            
                        elif self.conversation_context["type"] == "ticket":
                            title, description = self.generate_ticket_details(
                                self.conversation_context["original_message"],
                                self.conversation_context["details_collected"]
                            )
                            self.create_ticket(title, description)
                            self.reset_conversation_context()
                        
                        continue
                    else:
                        self.reset_conversation_context()

                # Traitement normal
                intent = self.detect_intent(user_input)
                print(f"Intent détectée : {intent}")

                # Si c'est une demande de statut
                if intent == "get_ticket_status":
                    self.handle_ticket_status_request(user_input)
                    continue

                # Gestion spéciale pour l'aide
                if intent == "help":
                    if "menu" in user_input.lower() or "guide" in user_input.lower():
                        self.show_help_menu()
                    else:
                        response = self.generate_response_for_intent(user_input, intent)
                        print(f"Bot: {response}")
                    continue

                if intent in self.NON_PROBLEM_INTENTS:
                    response = self.generate_response_for_intent(user_input, intent)
                    print(f"Bot: {response}\n")
                    self.reset_conversation_context()
                else:
                    choice = self.ask_solution_or_ticket()

                    self.conversation_context = {
                        "active": True,
                        "type": choice,
                        "intent": intent,
                        "original_message": user_input,
                        "details_collected": []
                    }

                    if choice == "solution":
                        solution = self.generate_solution(user_input, intent)
                        print(f"Bot (solution): {solution}")
                        
                        need_details_indicators = [
                            "plus de détails", "me fournir", "pouvez-vous", "contexte",
                            "quand", "comment", "pourquoi"
                        ]
                        
                        if any(indicator in solution.lower() for indicator in need_details_indicators):
                            print("💡 Pour vous aider davantage, merci de fournir plus de détails.")
                        else:
                            while True:
                                response = input("Cette solution répond-elle à votre problème ? (oui/non) ").strip().lower()
                                if response == "oui":
                                    print("Parfait ! N'hésitez pas si vous avez d'autres questions.\n")
                                    self.reset_conversation_context()
                                    break
                                elif response == "non":
                                    print("Merci de fournir plus de détails sur votre problème :")
                                    break
                                else:
                                    print("Merci de répondre par 'oui' ou 'non'.")
                        
                    else:  # choice == "ticket"
                        print("Merci de fournir tous les détails nécessaires pour créer le ticket :")
                        
            except KeyboardInterrupt:
                print("\n\n👋 Au revoir!")
                break
            except Exception as e:
                print(f"\n❌ Erreur: {e}")
                self.reset_conversation_context()
                continue

if __name__ == "__main__":
    print("=== CHATBOT HELPDESK OCP - VERSION CONSOLIDÉE ===\n")
    
    MODEL_NAME = "llama3.1:8b"
    
    try:
        chatbot = ImprovedOllamaChatbot(model_name=MODEL_NAME)
        chatbot.run_chat()
    except KeyboardInterrupt:
        print("\n\nApplication fermée.")
    except Exception as e:
        print(f"\n❌ Erreur fatale: {e}")
        input("\nAppuyez sur Entrée pour quitter...")