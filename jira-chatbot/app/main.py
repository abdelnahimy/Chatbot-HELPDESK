from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import uvicorn
import json
import os
import requests
import re
import random
from datetime import datetime

# Import your existing chatbot logic
try:
    from jira_service import create_ticket as jira_create_ticket, get_ticket_status, list_all_tickets
    JIRA_AVAILABLE = True
    print("✅ Service JIRA importé avec succès")
except ImportError as e:
    JIRA_AVAILABLE = False
    print(f"⚠️ Service JIRA non disponible: {e}")

app = FastAPI(title="OCP Helpdesk Chatbot API", version="1.0.0")

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for API
class ChatMessage(BaseModel):
    message: str
    conversation_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    intent: str
    needs_action: bool
    conversation_id: Optional[str] = None
    ticket_key: Optional[str] = None

class TicketCreate(BaseModel):
    title: str
    description: str
    priority: Optional[str] = "Medium"
    ticket_type: Optional[str] = "Task"

class TicketResponse(BaseModel):
    ticket_key: str
    title: str
    description: str
    status: str
    created_at: str

class TicketStatusRequest(BaseModel):
    ticket_key: str

# Adapted chatbot class for API use
class APIImprovedOllamaChatbot:
    def __init__(self, model_name="llama3.1:8b"):
        self.model_name = model_name
        self.ollama_url = "http://localhost:11434"
        
        # Load intent data
        self.load_intent_data()
        
        # Non-problem intents
        self.NON_PROBLEM_INTENTS = {
            "greet", "goodbye", "thanks", "help", "compliment", "frustrated_user", 
            "system_status", "get_ticket_status"
        }
        
        # In-memory storage for conversation contexts (use Redis in production)
        self.conversation_contexts = {}
        
        # Setup Ollama
        self.setup_ollama()
    
    def load_intent_data(self):
        """Load intent data with fallback"""
        try:
            if not os.path.exists("data"):
                os.makedirs("data")
            
            # Create default files if they don't exist
            self._create_default_intent_files()
            
            # Load the data
            with open("../data/tags.json", "r", encoding="utf-8") as f:
                self.intents_tags = json.load(f)

            with open("../data/intents.json", "r", encoding="utf-8") as f:
                self.intents_data = json.load(f)
                
        except Exception as e:
            print(f"❌ Erreur lors du chargement des données: {e}")
            # Fallback data
            self.intents_tags = ["greet", "help", "login_problem", "get_ticket_status"]
            self.intents_data = {"intents": []}
    
    def _create_default_intent_files(self):
        """Create default intent files if they don't exist"""
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
    
    def setup_ollama(self):
        """Simple setup check for API use"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if response.status_code == 200:
                print("✅ Ollama service accessible")
                return True
        except:
            print("⚠️ Ollama service not accessible - using fallback responses")
            return False
        return False
    
    def call_ollama(self, prompt: str, max_tokens: int = 100) -> Optional[str]:
        """Call Ollama API with fallback"""
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
                # Clean response
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
        """Extract ticket key from message"""
        ticket_pattern = r'\b([A-Z]{2,10}-\d+)\b'
        matches = re.findall(ticket_pattern, message.upper())
        
        if matches:
            return matches[0]
        return None
    
    def detect_intent(self, user_message: str) -> str:
        """Intent detection with keyword mapping fallback"""
        message_lower = user_message.lower()
        
        # Check for ticket status request
        status_keywords = ["statut", "status", "état", "suivi", "avancement", "où en est"]
        ticket_keywords = ["ticket", "sup-", "demande", "incident"]
        
        if (any(keyword in message_lower for keyword in status_keywords) and 
            any(keyword in message_lower for keyword in ticket_keywords)):
            return "get_ticket_status"
        
        if self.extract_ticket_key_from_message(user_message):
            return "get_ticket_status"
        
        # Try Ollama first
        prompt = f"""Tu es un assistant support en français.
Voici la liste des intentions possibles : {self.intents_tags}.
Détecte l'intention de l'utilisateur dans ce message :
"{user_message}"

IMPORTANT : Réponds uniquement par UN SEUL mot qui correspond exactement à une intention de la liste.
Ne donne pas d'explication, pas de phrase complète, juste le mot-clé d'intention."""
        
        result = self.call_ollama(prompt, max_tokens=5)
        
        if result:
            result = result.strip().lower().replace('"', '').replace("'", "")
            result = result.split()[0] if result.split() else result
            
            if result in [tag.lower() for tag in self.intents_tags]:
                return result
        
        # Fallback keyword mapping
        keyword_mapping = {
            "bonjour|salut|hello|bonsoir|coucou|hi": "greet",
            "au revoir|bye|ciao|goodbye": "goodbye", 
            "merci|thanks|thank you": "thanks",
            "statut|status|état|suivi|avancement": "get_ticket_status",
            "connexion|connecter|login|log in": "login_problem",
            "mot de passe|password|mdp|reset": "password_reset",
            "email|mail|outlook|courrier|messagerie": "email_problem",
            "imprimante|printer|imprimer|impression": "printer_issue",
            "réseau|network|internet|wifi": "network_issue",
            "logiciel|software|application|programme": "software_issue",
            "matériel|hardware|ordinateur|pc": "hardware_problem",
            "aide|help|aidez|support": "help"
        }
        
        for keywords, intent in keyword_mapping.items():
            if any(keyword in message_lower for keyword in keywords.split('|')):
                return intent
                
        return "help"
    
    def generate_response_for_intent(self, user_message: str, intent: str) -> str:
        """Generate response for non-problem intents"""
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
    
    def generate_solution(self, user_message: str, intent: str) -> str:
        """Generate solution for technical problems"""
        # Predefined solutions for common problems
        solutions = {
            "login_problem": "Vérifiez votre nom d'utilisateur et mot de passe. Si le problème persiste, essayez de vider le cache de votre navigateur ou contactez l'administrateur système.",
            "password_reset": "Vous pouvez réinitialiser votre mot de passe en cliquant sur 'Mot de passe oublié' sur la page de connexion, ou contacter le support pour une réinitialisation manuelle.",
            "email_problem": "Vérifiez votre connexion internet et les paramètres de votre client email. Redémarrez Outlook si nécessaire. Pour les problèmes persistants, contactez le support IT.",
            "printer_issue": "Vérifiez que l'imprimante est allumée et connectée au réseau. Redémarrez l'imprimante et votre ordinateur. Assurez-vous que les pilotes sont à jour.",
            "network_issue": "Vérifiez votre connexion Wi-Fi ou Ethernet. Redémarrez votre routeur si nécessaire. Contactez l'administrateur réseau si le problème persiste.",
            "software_issue": "Redémarrez l'application et votre ordinateur. Vérifiez les mises à jour disponibles. Si le problème persiste, contactez le support technique.",
            "hardware_problem": "Vérifiez toutes les connexions physiques. Redémarrez votre équipement. Si le problème persiste, contactez le support technique pour une intervention."
        }
        
        if intent in solutions:
            return solutions[intent]
        
        # Try Ollama for custom solution
        intent_obj = next((i for i in self.intents_data['intents'] if i['tag'] == intent), None)
        
        if intent_obj:
            prompt = f"""Tu es un assistant support technique en français pour OCP.
L'utilisateur a le problème suivant : "{intent}".
Exemples similaires : {intent_obj['patterns']}.
Message de l'utilisateur : "{user_message}"

Donne une solution pratique et professionnelle en français (maximum 3 phrases).
Ne commence pas par "Voici" ou "```". Réponds directement comme un humain."""
        else:
            prompt = f"""Tu es un assistant support technique en français pour OCP.
Message de l'utilisateur : "{user_message}"

Donne une solution pratique et professionnelle en français (maximum 3 sentences).
Ne commence pas par "Voici" ou "```". Réponds directement comme un humain."""
        
        result = self.call_ollama(prompt, max_tokens=120)
        return result if result else "Je vais vous aider avec ce problème. Pouvez-vous me donner plus de détails pour que je puisse vous proposer une solution personnalisée ?"
    
    def generate_ticket_details(self, user_message: str) -> tuple[str, str]:
        """Generate ticket title and description"""
        intent = self.detect_intent(user_message)
        
        # Predefined titles for common problems
        titles = {
            "login_problem": "Problème de connexion utilisateur",
            "password_reset": "Demande de réinitialisation mot de passe",
            "email_problem": "Dysfonctionnement messagerie",
            "printer_issue": "Problème d'imprimante",
            "network_issue": "Problème de réseau",
            "software_issue": "Problème logiciel",
            "hardware_problem": "Problème matériel"
        }
        
        title = titles.get(intent, "Demande d'assistance technique")
        
        # Try to generate a better title with Ollama
        prompt_title = f"""Crée un titre court (maximum 8 mots) pour un ticket d'assistance basé sur :
"{user_message}"

Réponds seulement par le titre, sans guillemets ni explications."""
        
        ollama_title = self.call_ollama(prompt_title, max_tokens=15)
        if ollama_title:
            title = ollama_title
        
        # Generate description
        description = f"Demande d'assistance: {user_message}\n\nCréé automatiquement via le chatbot OCP."
        
        return title, description

# Initialize chatbot instance
chatbot = APIImprovedOllamaChatbot()

# API Endpoints
@app.get("/")
async def root():
    return {"message": "OCP Helpdesk Chatbot API", "status": "running"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "jira_available": JIRA_AVAILABLE,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(chat_request: ChatMessage):
    """Main chat endpoint"""
    try:
        user_message = chat_request.message.strip()
        
        if not user_message:
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        # Detect intent
        intent = chatbot.detect_intent(user_message)
        
        # Handle ticket status requests
        if intent == "get_ticket_status":
            ticket_key = chatbot.extract_ticket_key_from_message(user_message)
            if ticket_key:
                if JIRA_AVAILABLE:
                    try:
                        status = get_ticket_status(ticket_key)
                        if status:
                            response_text = f"✅ Ticket {ticket_key} trouvé!\n📊 Statut: {status}"
                        else:
                            response_text = f"❌ Ticket {ticket_key} introuvable dans le système JIRA."
                    except Exception as e:
                        response_text = f"❌ Erreur lors de la vérification du statut: {str(e)}"
                else:
                    response_text = "⚠️ Service JIRA non disponible pour vérifier le statut"
            else:
                response_text = "Pour vérifier le statut de votre ticket, j'ai besoin de la clé du ticket (format: SUP-123)."
            
            return ChatResponse(
                response=response_text,
                intent=intent,
                needs_action=False,
                conversation_id=chat_request.conversation_id,
                ticket_key=ticket_key
            )
        
        # Handle non-problem intents
        if intent in chatbot.NON_PROBLEM_INTENTS:
            response_text = chatbot.generate_response_for_intent(user_message, intent)
            needs_action = False
        else:
            # Generate solution for technical problems
            response_text = chatbot.generate_solution(user_message, intent)
            needs_action = True
        
        return ChatResponse(
            response=response_text,
            intent=intent,
            needs_action=needs_action,
            conversation_id=chat_request.conversation_id
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/tickets", response_model=TicketResponse)
async def create_ticket_endpoint(ticket_request: TicketCreate):
    """Create a new ticket"""
    try:
        title = ticket_request.title
        description = ticket_request.description
        
        if JIRA_AVAILABLE:
            try:
                ticket_key = jira_create_ticket(
                    title, 
                    description, 
                    ticket_request.ticket_type
                )
                
                if ticket_key:
                    # Get status
                    status = get_ticket_status(ticket_key) or "Open"
                    
                    return TicketResponse(
                        ticket_key=ticket_key,
                        title=title,
                        description=description,
                        status=status,
                        created_at=datetime.now().isoformat()
                    )
                else:
                    raise HTTPException(status_code=500, detail="Failed to create JIRA ticket")
                    
            except Exception as e:
                print(f"JIRA Error: {e}")
                # Fallback to local ticket creation
                pass
        
        # Local ticket creation (fallback)
        import uuid
        ticket_key = f"SUP-{str(uuid.uuid4())[:8].upper()}"
        
        return TicketResponse(
            ticket_key=ticket_key,
            title=title,
            description=description,
            status="Open",
            created_at=datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating ticket: {str(e)}")

@app.post("/tickets/auto-create")
async def auto_create_ticket(chat_request: ChatMessage):
    """Auto-create ticket from chat message"""
    try:
        user_message = chat_request.message.strip()
        
        if not user_message:
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        # Generate ticket details
        title, description = chatbot.generate_ticket_details(user_message)
        
        # Create the ticket
        ticket_request = TicketCreate(
            title=title,
            description=description,
            ticket_type="Task"
        )
        
        return await create_ticket_endpoint(ticket_request)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error auto-creating ticket: {str(e)}")

@app.get("/tickets/{ticket_key}")
async def get_ticket_status_endpoint(ticket_key: str):
    """Get ticket status"""
    try:
        if JIRA_AVAILABLE:
            try:
                status = get_ticket_status(ticket_key)
                if status:
                    return {
                        "ticket_key": ticket_key,
                        "status": status,
                        "found": True
                    }
                else:
                    return {
                        "ticket_key": ticket_key,
                        "status": None,
                        "found": False,
                        "message": "Ticket not found in JIRA"
                    }
            except Exception as e:
                return {
                    "ticket_key": ticket_key,
                    "status": None,
                    "found": False,
                    "error": str(e)
                }
        else:
            return {
                "ticket_key": ticket_key,
                "status": None,
                "found": False,
                "message": "JIRA service not available"
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking ticket status: {str(e)}")

@app.get("/tickets")
async def list_tickets_endpoint(max_results: int = 50):
    """Liste tous les tickets du projet"""
    try:
        if JIRA_AVAILABLE:
            try:
                tickets = list_all_tickets(max_results)
                return {
                    "tickets": tickets,
                    "count": len(tickets),
                    "source": "jira",
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                print(f"❌ Erreur JIRA lors du listing: {e}")
                return {
                    "tickets": [],
                    "count": 0,
                    "source": "fallback",
                    "error": str(e)
                }
        else:
            return {
                "tickets": [],
                "count": 0,
                "source": "fallback",
                "message": "JIRA service not available"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing tickets: {str(e)}")
    
if __name__ == "__main__":
    print("🚀 Démarrage de l'API Chatbot OCP...")
    print(f"📋 JIRA disponible: {JIRA_AVAILABLE}")
    print("🌐 API disponible sur: http://localhost:8000")
    print("📖 Documentation: http://localhost:8000/docs")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)