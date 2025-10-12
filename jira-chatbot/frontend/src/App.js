import React, { useState, useEffect, useRef, useMemo } from 'react';
import { MessageCircle, Home, Ticket, Send, User, Bot, Clock, CheckCircle, AlertCircle, Loader } from 'lucide-react';

// API Configuration
const API_BASE_URL = 'http://localhost:8000';

// API Service class
class APIService {
  static async post(endpoint, data) {
    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('API Error:', error);
      throw error;
    }
  }

  static async get(endpoint) {
    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('API Error:', error);
      throw error;
    }
  }

  static async sendMessage(message, conversationId = null) {
    return this.post('/chat', {
      message: message,
      conversation_id: conversationId
    });
  }

  static async createTicket(message) {
    return this.post('/tickets/auto-create', {
      message: message
    });
  }

  static async getTicketStatus(ticketKey) {
    return this.get(`/tickets/${ticketKey}`);
  }

  static async healthCheck() {
    return this.get('/health');
  }

  static async getTickets(maxResults = 50) {
  return this.get(`/tickets?max_results=${maxResults}`);
}
}

// Mock data fallback (in case API is not available)
const mockTickets = [
  { id: 'SUP-001', title: 'Problème de connexion', status: 'Open', createdAt: '2025-01-20', description: 'Impossible de se connecter au système' },
  { id: 'SUP-002', title: 'Reset mot de passe', status: 'In Progress', createdAt: '2025-01-19', description: 'Demande de réinitialisation de mot de passe' },
  { id: 'SUP-003', title: 'Problème imprimante', status: 'Resolved', createdAt: '2025-01-18', description: 'Imprimante ne répond pas' },
];

// Local Chatbot service (fallback when API is not available)
class ChatbotService {
  constructor() {
    this.NON_PROBLEM_INTENTS = new Set([
      'greet', 'goodbye', 'thanks', 'help', 'compliment', 'frustrated_user', 
      'system_status', 'get_ticket_status'
    ]);
    
    this.intentPatterns = {
      greet: ['bonjour', 'salut', 'hello', 'bonsoir', 'coucou', 'hi'],
      goodbye: ['au revoir', 'bye', 'ciao', 'goodbye', 'à bientôt'],
      thanks: ['merci', 'thanks', 'thank you', 'je vous remercie'],
      get_ticket_status: ['statut', 'status', 'état', 'suivi', 'avancement', 'sup-'],
      login_problem: ['connexion', 'connecter', 'login', 'log in'],
      password_reset: ['mot de passe', 'password', 'mdp', 'reset'],
      email_problem: ['email', 'mail', 'outlook', 'courrier', 'messagerie'],
      printer_issue: ['imprimante', 'printer', 'imprimer', 'impression'],
      network_issue: ['réseau', 'network', 'internet', 'wifi'],
      help: ['aide', 'help', 'aidez', 'support']
    };

    this.responses = {
      greet: [
        "Bonjour ! Je suis votre assistant support OCP. Comment puis-je vous aider aujourd'hui ?",
        "Salut ! En quoi puis-je vous assister ?",
        "Hello ! Je suis là pour vous aider avec vos questions techniques."
      ],
      goodbye: [
        "Au revoir ! N'hésitez pas à revenir si vous avez d'autres questions.",
        "À bientôt ! Passez une excellente journée."
      ],
      thanks: [
        "De rien ! C'est un plaisir de vous aider.",
        "Je vous en prie ! N'hésitez pas si vous avez d'autres questions."
      ],
      help: [
        "Je peux vous aider avec : problèmes de connexion, mots de passe, emails, réseau, imprimantes, logiciels. Vous pouvez aussi vérifier le statut de vos tickets.",
        "Mes spécialités : support technique, gestion des comptes, résolution de problèmes IT, suivi de tickets. Que puis-je faire pour vous ?"
      ]
    };

    this.solutions = {
      login_problem: "Vérifiez votre nom d'utilisateur et mot de passe. Si le problème persiste, essayez de vider le cache de votre navigateur ou contactez l'administrateur système.",
      password_reset: "Vous pouvez réinitialiser votre mot de passe en cliquant sur 'Mot de passe oublié' sur la page de connexion, ou contacter le support pour une réinitialisation manuelle.",
      email_problem: "Vérifiez votre connexion internet et les paramètres de votre client email. Redémarrez Outlook si nécessaire. Pour les problèmes persistants, contactez le support IT.",
      printer_issue: "Vérifiez que l'imprimante est allumée et connectée au réseau. Redémarrez l'imprimante et votre ordinateur. Assurez-vous que les pilotes sont à jour.",
      network_issue: "Vérifiez votre connexion Wi-Fi ou Ethernet. Redémarrez votre routeur si nécessaire. Contactez l'administrateur réseau si le problème persiste."
    };
  }

  detectIntent(message) {
    const messageLower = message.toLowerCase();
    
    // Check for ticket status request
    if (this.extractTicketKey(message)) return 'get_ticket_status';
    
    // Check patterns
    for (const [intent, patterns] of Object.entries(this.intentPatterns)) {
      if (patterns.some(pattern => messageLower.includes(pattern))) {
        return intent;
      }
    }
    
    return 'help';
  }

  extractTicketKey(message) {
    const ticketPattern = /\b([A-Z]{2,10}-\d+)\b/i;
    const match = message.match(ticketPattern);
    return match ? match[1].toUpperCase() : null;
  }

  generateResponse(message, intent) {
    if (this.NON_PROBLEM_INTENTS.has(intent)) {
      const responses = this.responses[intent] || this.responses.help;
      return responses[Math.floor(Math.random() * responses.length)];
    }
    
    if (intent === 'get_ticket_status') {
      const ticketKey = this.extractTicketKey(message);
      if (ticketKey) {
        return `Recherche du statut du ticket ${ticketKey}...`;
      }
      return "Pour vérifier le statut de votre ticket, j'ai besoin de la clé du ticket (ex: SUP-123).";
    }
    
    const solution = this.solutions[intent];
    if (solution) {
      return solution;
    }
    
    return "Je vais vous aider avec ce problème. Pouvez-vous me donner plus de détails ?";
  }

  generateTicketTitle(message) {
    const intent = this.detectIntent(message);
    const titles = {
      login_problem: 'Problème de connexion utilisateur',
      password_reset: 'Demande de réinitialisation mot de passe',
      email_problem: 'Dysfonctionnement messagerie',
      printer_issue: 'Problème d\'imprimante',
      network_issue: 'Problème de réseau'
    };
    
    return titles[intent] || 'Demande d\'assistance technique';
  }
}

const App = () => {
  const [currentPage, setCurrentPage] = useState('home');
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [tickets, setTickets] = useState(mockTickets);
  const [isLoading, setIsLoading] = useState(false);
  const [apiAvailable, setApiAvailable] = useState(false);
  const [selectedTicket, setSelectedTicket] = useState(null);
  const [showTicketModal, setShowTicketModal] = useState(false);
  const [conversationContext, setConversationContext] = useState({
    active: false,
    type: null,
    intent: null,
    originalMessage: null,
    conversationId: null
  });
  
  // ✅ Utilisation d'useMemo pour éviter la re-création à chaque rendu
  const chatbotService = useMemo(() => new ChatbotService(), []);
  
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Check API availability on mount
  useEffect(() => {
    checkApiAvailability();
  }, []);

  useEffect(() => {
    const loadTicketsFromJira = async () => {
      if (apiAvailable) {
        try {
          console.log('🔄 Chargement des tickets depuis Jira...');
          const response = await APIService.getTickets(50);
          
          if (response.tickets && response.tickets.length > 0) {
            const formattedTickets = response.tickets.map(ticket => ({
              id: ticket.ticket_key,
              title: ticket.title,
              status: ticket.status,
              createdAt: ticket.created_at.split('T')[0],
              description: ticket.description
            }));
            
            setTickets(formattedTickets);
            console.log(`✅ ${formattedTickets.length} tickets chargés depuis Jira`);
          } else {
            console.log('⚠️ Aucun ticket trouvé dans Jira');
          }
        } catch (error) {
          console.error('❌ Erreur lors du chargement des tickets:', error);
          console.log('⚠️ Utilisation des tickets mockés');
        }
      }
    };
    
    loadTicketsFromJira();
  }, [apiAvailable]);

  useEffect(() => {
    if (currentPage === 'chat') {
      setTimeout(() => inputRef.current?.focus(), 0);
    }
  }, [currentPage]);

  useEffect(() => {
    if (currentPage === 'chat' && !isLoading) {
      setTimeout(() => inputRef.current?.focus(), 0);
    }
  }, [isLoading, currentPage]);

  const checkApiAvailability = async () => {
    try {
      await APIService.healthCheck();
      setApiAvailable(true);
      console.log('✅ API Backend available');
    } catch (error) {
      setApiAvailable(false);
      console.log('⚠️ API Backend not available, using fallback');
    }
  };
  
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // ✅ Utilisation d'useCallback pour éviter les re-créations
  const handleSendMessage = React.useCallback(async () => {
    if (!inputMessage.trim() || isLoading) return;

    const userMessage = {
      id: Date.now(),
      text: inputMessage,
      sender: 'user',
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);
    const currentMessage = inputMessage; // ✅ Capturer la valeur avant de la réinitialiser
    setInputMessage(''); // ✅ Réinitialiser immédiatement
    setTimeout(() => inputRef.current?.focus(), 0);

    try {
      let botResponse;
      let needsAction = false;
      let intent = 'help';

      if (apiAvailable) {
        // Use API backend
        const response = await APIService.sendMessage(
          currentMessage, 
          conversationContext.conversationId
        );
        
        botResponse = response.response;
        intent = response.intent;
        needsAction = response.needs_action;
        
        // Update conversation context with API response
        if (needsAction) {
          setConversationContext({
            active: true,
            type: null,
            intent: intent,
            originalMessage: currentMessage,
            conversationId: response.conversation_id
          });
        }
      } else {
        // Use local fallback
        intent = chatbotService.detectIntent(currentMessage);
        
        if (intent === 'get_ticket_status') {
          const ticketKey = chatbotService.extractTicketKey(currentMessage);
          if (ticketKey) {
            const ticket = tickets.find(t => t.id === ticketKey);
            if (ticket) {
              botResponse = `✅ Ticket ${ticketKey} trouvé!\n📊 Statut: ${ticket.status}\n📋 Titre: ${ticket.title}`;
            } else {
              botResponse = `❌ Ticket ${ticketKey} introuvable. Vérifiez la clé du ticket.`;
            }
          } else {
            botResponse = "Pour vérifier le statut de votre ticket, j'ai besoin de la clé du ticket (ex: SUP-123).";
          }
        } else {
          botResponse = chatbotService.generateResponse(currentMessage, intent);
          needsAction = !chatbotService.NON_PROBLEM_INTENTS.has(intent) && intent !== 'get_ticket_status';
        }
        
        if (needsAction) {
          setConversationContext({
            active: true,
            type: null,
            intent: intent,
            originalMessage: currentMessage,
            conversationId: null
          });
        }
      }

      const botMessage = {
        id: Date.now() + 1,
        text: botResponse,
        sender: 'bot',
        timestamp: new Date(),
        intent: intent,
        needsAction: needsAction
      };

      setMessages(prev => [...prev, botMessage]);
      
    } catch (error) {
      console.error('Error sending message:', error);
      
      // Fallback response
      const errorMessage = {
        id: Date.now() + 1,
        text: "❌ Désolé, je rencontre un problème technique. Pouvez-vous réessayer ?",
        sender: 'bot',
        timestamp: new Date(),
        intent: 'error',
        needsAction: false
      };
      
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  }, [inputMessage, isLoading, apiAvailable, conversationContext.conversationId, chatbotService, tickets]);

  // ✅ Gestionnaire d'événement pour Enter optimisé
  const handleKeyPress = React.useCallback((e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  }, [handleSendMessage]);

  // No auto-resize needed for input element

  const handleCreateTicket = async () => {
    if (!conversationContext.originalMessage) return;

    try {
      setIsLoading(true);
      
      let newTicket;
      
      if (apiAvailable) {
        // Use API to create ticket
        const response = await APIService.createTicket(conversationContext.originalMessage);
        
        newTicket = {
          id: response.ticket_key,
          title: response.title,
          status: response.status,
          createdAt: response.created_at.split('T')[0], // Format date
          description: response.description
        };
      } else {
        // Local ticket creation (fallback)
        const title = chatbotService.generateTicketTitle(conversationContext.originalMessage);
        
        newTicket = {
          id: `SUP-${String(tickets.length + 1).padStart(3, '0')}`,
          title: title,
          status: 'Open',
          createdAt: new Date().toISOString().split('T')[0],
          description: conversationContext.originalMessage
        };
      }
      
      // Add to local tickets list
      setTickets(prev => [newTicket, ...prev]);
      
      // Show confirmation message
      const confirmMessage = {
        id: Date.now(),
        text: `✅ Ticket créé avec succès!\n🎫 Numéro: ${newTicket.id}\n📋 Titre: ${newTicket.title}`,
        sender: 'bot',
        timestamp: new Date()
      };
      
      setMessages(prev => [...prev, confirmMessage]);
      
      // Reset conversation context
      setConversationContext({ 
        active: false, 
        type: null, 
        intent: null, 
        originalMessage: null,
        conversationId: null 
      });
      
    } catch (error) {
      console.error('Error creating ticket:', error);
      
      const errorMessage = {
        id: Date.now(),
        text: "❌ Erreur lors de la création du ticket. Veuillez réessayer.",
        sender: 'bot',
        timestamp: new Date()
      };
      
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const StatusBadge = ({ status }) => {
    const statusConfig = {
      'Open': { color: 'bg-blue-100 text-blue-800', icon: AlertCircle },
      'In Progress': { color: 'bg-yellow-100 text-yellow-800', icon: Clock },
      'Resolved': { color: 'bg-green-100 text-green-800', icon: CheckCircle },
      'Closed': { color: 'bg-gray-100 text-gray-800', icon: CheckCircle }
    };
    
    const config = statusConfig[status] || statusConfig['Open'];
    const IconComponent = config.icon;
    
    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.color}`}>
        <IconComponent className="w-3 h-3 mr-1" />
        {status}
      </span>
    );
  };

  const HomePage = () => (
    <div className="min-h-screen bg-primary-50">
      <div className="container mx-auto px-4 py-16">
        <div className="text-center mb-12">
          <div className="mb-8">
            <div className="inline-flex items-center justify-center w-20 h-20 bg-primary-600 rounded-full mb-6">
              <MessageCircle className="w-10 h-10 text-white" />
            </div>
          </div>
          <h1 className="text-5xl font-bold text-gray-900 mb-6">
            Assistant Support <span className="text-primary-600">OCP</span>
          </h1>
          <p className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto">
            Votre assistant intelligent pour résoudre tous vos problèmes techniques rapidement et efficacement
          </p>
          <button 
            onClick={() => setCurrentPage('chat')}
            className="bg-primary-600 text-white px-8 py-4 rounded-full font-semibold text-lg hover:bg-primary-700 transform hover:scale-105 transition-all duration-200 shadow-lg hover:shadow-xl"
          >
            Démarrer une conversation
          </button>
        </div>

        <div className="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto">
          <div className="bg-white p-8 rounded-2xl shadow-lg hover:shadow-xl transition-all duration-300 border border-gray-100">
            <div className="w-12 h-12 bg-primary-600 rounded-lg flex items-center justify-center mb-6">
              <MessageCircle className="w-6 h-6 text-white" />
            </div>
            <h3 className="text-xl font-semibold text-gray-900 mb-4">Chat Intelligent</h3>
            <p className="text-gray-600">
              Discutez avec notre assistant IA pour obtenir des solutions instantanées à vos problèmes techniques
            </p>
          </div>

          <div className="bg-white p-8 rounded-2xl shadow-lg hover:shadow-xl transition-all duration-300 border border-gray-100">
            <div className="w-12 h-12 bg-primary-600 rounded-lg flex items-center justify-center mb-6">
              <Ticket className="w-6 h-6 text-white" />
            </div>
            <h3 className="text-xl font-semibold text-gray-900 mb-4">Gestion de Tickets</h3>
            <p className="text-gray-600">
              Créez et suivez vos tickets de support en temps réel avec notre système intégré
            </p>
          </div>

          <div className="bg-white p-8 rounded-2xl shadow-lg hover:shadow-xl transition-all duration-300 border border-gray-100">
            <div className="w-12 h-12 bg-primary-600 rounded-lg flex items-center justify-center mb-6">
              <CheckCircle className="w-6 h-6 text-white" />
            </div>
            <h3 className="text-xl font-semibold text-gray-900 mb-4">Support 24/7</h3>
            <p className="text-gray-600">
              Une assistance disponible à tout moment pour résoudre vos problèmes rapidement
            </p>
          </div>
        </div>

        <div className="mt-16 bg-white rounded-3xl shadow-xl p-8 max-w-4xl mx-auto border border-gray-100">
          <h2 className="text-3xl font-bold text-gray-900 text-center mb-8">Types de problèmes supportés</h2>
          <div className="grid md:grid-cols-2 gap-6">
            <div className="flex items-start space-x-4">
              <div className="w-8 h-8 bg-orange-100 rounded-lg flex items-center justify-center flex-shrink-0">
                <span className="text-accent-orange font-semibold">🔐</span>
              </div>
              <div>
                <h4 className="font-semibold text-gray-900">Authentification</h4>
                <p className="text-gray-600 text-sm">Problèmes de connexion, mots de passe oubliés</p>
              </div>
            </div>
            <div className="flex items-start space-x-4">
              <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center flex-shrink-0">
                <span className="text-accent-blue font-semibold">📧</span>
              </div>
              <div>
                <h4 className="font-semibold text-gray-900">Messagerie</h4>
                <p className="text-gray-600 text-sm">Outlook, configuration email, synchronisation</p>
              </div>
            </div>
            <div className="flex items-start space-x-4">
              <div className="w-8 h-8 bg-purple-100 rounded-lg flex items-center justify-center flex-shrink-0">
                <span className="text-accent-purple font-semibold">🖨️</span>
              </div>
              <div>
                <h4 className="font-semibold text-gray-900">Impression</h4>
                <p className="text-gray-600 text-sm">Problèmes d'imprimantes, pilotes, connexion</p>
              </div>
            </div>
            <div className="flex items-start space-x-4">
              <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center flex-shrink-0">
                <span className="text-accent-blue font-semibold">🌐</span>
              </div>
              <div>
                <h4 className="font-semibold text-gray-900">Réseau</h4>
                <p className="text-gray-600 text-sm">WiFi, VPN, connectivité internet</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  const ChatPage = () => (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white/80 backdrop-blur shadow-sm border-b p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-primary-600 rounded-full flex items-center justify-center">
              <Bot className="w-6 h-6 text-white" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Assistant Support OCP</h2>
              <p className="text-sm text-gray-500">
                {apiAvailable ? "🟢 Connecté • IA Disponible" : "🟡 Mode Local • Fonctionnalités Limitées"}
              </p>
            </div>
          </div>
          <div className="text-xs text-gray-400">
            {apiAvailable ? "Backend API" : "Mode Fallback"}
          </div>
        </div>
      </div>

      <div className="container mx-auto max-w-3xl xl:max-w-4xl px-4 py-4">
        <div className="h-[calc(100vh-12rem)] overflow-y-auto space-y-4 pr-1">
        {messages.length === 0 && (
          <div className="text-center py-12">
            <div className="w-16 h-16 bg-primary-600 rounded-full flex items-center justify-center mx-auto mb-4">
              <MessageCircle className="w-8 h-8 text-white" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Bienvenue dans le chat support</h3>
            <p className="text-gray-600">Décrivez votre problème et je vous aiderai à le résoudre</p>
          </div>
        )}

        {messages.map((message) => (
          <div key={message.id} className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[85%] md:max-w-[80%] lg:max-w-[75%] ${
              message.sender === 'user' 
                ? 'bg-primary-600 text-white' 
                : 'bg-white text-gray-900 shadow-sm border'
            } rounded-2xl px-4 py-3`}>
              <div className="flex items-start space-x-2">
                {message.sender === 'bot' && (
                  <Bot className="w-5 h-5 text-primary-600 flex-shrink-0 mt-0.5" />
                )}
                <div className="flex-1">
                  <p className="whitespace-pre-line">{message.text}</p>
                  <p className={`text-xs mt-1 ${message.sender === 'user' ? 'text-primary-100' : 'text-gray-500'}`}>
                    {message.timestamp.toLocaleTimeString()}
                  </p>
                </div>
                {message.sender === 'user' && (
                  <User className="w-5 h-5 text-primary-100 flex-shrink-0 mt-0.5" />
                )}
              </div>
              
              {message.needsAction && (
                <div className="mt-3 pt-3 border-t border-gray-100">
                  <p className="text-sm text-gray-600 mb-2">Voulez-vous :</p>
                  <div className="space-y-2">
                    <button 
                      onClick={handleCreateTicket}
                      disabled={isLoading}
                      className="w-full bg-primary-600 text-white px-3 py-2 rounded-lg text-sm hover:bg-primary-700 disabled:opacity-50 transition-colors"
                    >
                      {isLoading ? "Création..." : "Créer un ticket"}
                    </button>
                    <button 
                      className="w-full bg-gray-100 text-gray-700 px-3 py-2 rounded-lg text-sm hover:bg-gray-200 transition-colors"
                      onClick={() => setConversationContext(prev => ({ ...prev, active: false }))}
                    >
                      Continuer la conversation
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-white rounded-2xl px-4 py-3 shadow-sm border">
              <div className="flex items-center space-x-2">
                <Bot className="w-5 h-5 text-primary-600" />
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
                </div>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
        </div>
      </div>

      <div className="sticky bottom-0 bg-white/90 backdrop-blur border-t">
        <div className="container mx-auto max-w-3xl xl:max-w-4xl px-4 py-4">
          <div className="flex items-end space-x-3">
            <input
              ref={inputRef}
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyDown={handleKeyPress}
              placeholder="Décrivez votre problème... (Entrée pour envoyer)"
              className="flex-1 border border-gray-300 rounded-xl px-4 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white shadow-sm chat-input"
              autoFocus
              onBlur={() => setTimeout(() => inputRef.current?.focus(), 0)}
              type="text"
              autoComplete="off"
              autoCorrect="off"
              spellCheck={false}
            />
            <button
              onClick={handleSendMessage}
              disabled={isLoading || !inputMessage.trim()}
              className="bg-primary-600 text-white p-2 rounded-xl hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm"
              onMouseDown={(e) => e.preventDefault()}
            >
              {isLoading ? <Loader className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
            </button>
          </div>
        </div>
      </div>
    </div>
  );

// ✅ MODAL SANS BOUTONS D'ACTIONS
  const TicketDetailsModal = ({ ticket, onClose }) => {
    if (!ticket) return null;

    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
        <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-hidden">
          {/* Header */}
          <div className="bg-primary-600 text-white p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-2xl font-bold">Détails du Ticket</h2>
              <button
                onClick={onClose}
                className="text-white hover:bg-white/20 rounded-lg p-2 transition-colors"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="flex items-center space-x-3">
              <span className="text-lg font-semibold">#{ticket.id}</span>
              <StatusBadge status={ticket.status} />
            </div>
          </div>

          {/* Body */}
          <div className="p-6 overflow-y-auto max-h-[calc(90vh-200px)]">
            {/* Titre */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-500 mb-2">Titre</label>
              <h3 className="text-xl font-semibold text-gray-900">{ticket.title}</h3>
            </div>

            {/* Description */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-500 mb-2">Description</label>
              <div className="bg-gray-50 rounded-lg p-4 text-gray-700">
                {ticket.description}
              </div>
            </div>

            {/* Informations */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-500 mb-1">Statut</label>
                <StatusBadge status={ticket.status} />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-500 mb-1">Date de création</label>
                <div className="flex items-center text-gray-700">
                  <Clock className="w-4 h-4 mr-2" />
                  {new Date(ticket.createdAt).toLocaleDateString('fr-FR', {
                    day: 'numeric',
                    month: 'long',
                    year: 'numeric'
                  })}
                </div>
              </div>

              {ticket.priority && (
                <div>
                  <label className="block text-sm font-medium text-gray-500 mb-1">Priorité</label>
                  <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
                    ticket.priority === 'High' ? 'bg-red-100 text-red-800' :
                    ticket.priority === 'Medium' ? 'bg-yellow-100 text-yellow-800' :
                    'bg-green-100 text-green-800'
                  }`}>
                    {ticket.priority}
                  </span>
                </div>
              )}

              {ticket.issuetype && (
                <div>
                  <label className="block text-sm font-medium text-gray-500 mb-1">Type</label>
                  <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800">
                    {ticket.issuetype}
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Footer */}
          <div className="bg-gray-50 px-6 py-4 flex justify-end">
            <button
              onClick={onClose}
              className="bg-primary-600 text-white px-6 py-2 rounded-lg hover:bg-primary-700 transition-colors font-medium"
            >
              Fermer
            </button>
          </div>
        </div>
      </div>
    );
  };

  const TicketsPage = () => {
    // ✅ AJOUTER CETTE FONCTION
     const handleViewDetails = (ticket) => {
      setSelectedTicket(ticket);
      setShowTicketModal(true);
    };

    // ✅ AJOUTER CETTE FONCTION (OPTIONNEL: pour refresh)
    const refreshTickets = async () => {
      if (apiAvailable) {
        try {
          setIsLoading(true);
          const response = await APIService.getTickets(50);
          
          if (response.tickets && response.tickets.length > 0) {
            const formattedTickets = response.tickets.map(ticket => ({
              id: ticket.ticket_key,
              title: ticket.title,
              status: ticket.status,
              createdAt: ticket.created_at.split('T')[0],
              description: ticket.description,
              priority: ticket.priority,
              issuetype: ticket.issuetype
            }));
            
            setTickets(formattedTickets);
          }
        } catch (error) {
          console.error('Erreur refresh:', error);
        } finally {
          setIsLoading(false);
        }
      }
    };

    return (
      <>
        {/* ✅ AJOUTER LE MODAL */}
        {showTicketModal && (
          <TicketDetailsModal
            ticket={selectedTicket}
            onClose={() => {
              setShowTicketModal(false);
              setSelectedTicket(null);
            }}
          />
        )}

        <div className="min-h-screen bg-gray-50 py-8">
          <div className="container mx-auto px-4">
            {/* ✅ MODIFIER LE HEADER POUR AJOUTER LE BOUTON REFRESH */}
            <div className="mb-8 flex items-center justify-between">
              <div>
                <h1 className="text-3xl font-bold text-gray-900 mb-2">Mes Tickets</h1>
                <p className="text-gray-600">Gérez et suivez tous vos tickets de support</p>
              </div>
              
              {apiAvailable && (
                <button
                  onClick={refreshTickets}
                  disabled={isLoading}
                  className="bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center space-x-2"
                >
                  {isLoading ? (
                    <>
                      <Loader className="w-4 h-4 animate-spin" />
                      <span>Chargement...</span>
                    </>
                  ) : (
                    <>
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                      </svg>
                      <span>Actualiser</span>
                    </>
                  )}
                </button>
              )}
            </div>

            <div className="grid gap-4 md:gap-6">
              {tickets.map((ticket) => (
                <div key={ticket.id} className="bg-white rounded-xl shadow-sm border border-gray-200 hover:shadow-md transition-all duration-200">
                  <div className="p-6">
                    <div className="flex items-start justify-between mb-4">
                      <div>
                        <div className="flex items-center space-x-3 mb-2">
                          <h3 className="text-lg font-semibold text-gray-900">#{ticket.id}</h3>
                          <StatusBadge status={ticket.status} />
                        </div>
                        <h4 className="text-xl font-medium text-gray-800 mb-2">{ticket.title}</h4>
                        <p className="text-gray-600">{ticket.description}</p>
                      </div>
                    </div>
                    
                    <div className="flex items-center justify-between pt-4 border-t border-gray-100">
                      <div className="flex items-center text-sm text-gray-500">
                        <Clock className="w-4 h-4 mr-1" />
                        Créé le {new Date(ticket.createdAt).toLocaleDateString('fr-FR')}
                      </div>
                      {/* ✅ MODIFIER CE BOUTON */}
                      <button
                        onClick={() => handleViewDetails(ticket)}
                        className="text-primary-600 hover:text-primary-700 font-medium text-sm flex items-center space-x-1"
                      >
                        <span>Voir détails</span>
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {tickets.length === 0 && (
              <div className="text-center py-12">
                <Ticket className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Aucun ticket trouvé</h3>
                <p className="text-gray-600 mb-4">Vous n'avez pas encore créé de tickets</p>
                <button 
                  onClick={() => setCurrentPage('chat')}
                  className="bg-primary-600 text-white px-6 py-2 rounded-lg hover:bg-primary-700 transition-colors"
                >
                  Démarrer une conversation
                </button>
              </div>
            )}
          </div>
        </div>
      </>
    );
  };

  const Navigation = () => (
    <nav className="bg-white shadow-sm border-b">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
              <MessageCircle className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-bold text-gray-900">Chatbot HELPDESK</span>
          </div>
          
          <div className="flex space-x-1">
            <button
              onClick={() => setCurrentPage('home')}
              className={`px-4 py-2 rounded-lg transition-colors ${
                currentPage === 'home' 
                  ? 'bg-primary-100 text-primary-700' 
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
              }`}
            >
              <Home className="w-4 h-4 inline mr-2" />
              Accueil
            </button>
            <button
              onClick={() => setCurrentPage('chat')}
              className={`px-4 py-2 rounded-lg transition-colors ${
                currentPage === 'chat' 
                  ? 'bg-primary-100 text-primary-700' 
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
              }`}
            >
              <MessageCircle className="w-4 h-4 inline mr-2" />
              Chat
            </button>
            <button
              onClick={() => setCurrentPage('tickets')}
              className={`px-4 py-2 rounded-lg transition-colors ${
                currentPage === 'tickets' 
                  ? 'bg-primary-100 text-primary-700' 
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
              }`}
            >
              <Ticket className="w-4 h-4 inline mr-2" />
              Mes Tickets
              {tickets.length > 0 && (
                <span className="ml-1 bg-primary-600 text-white text-xs px-1.5 py-0.5 rounded-full">
                  {tickets.length}
                </span>
              )}
            </button>
          </div>
        </div>
      </div>
    </nav>
  );

  return (
    <div className="min-h-screen bg-primary-50">
      <Navigation />
      {currentPage === 'home' && <HomePage />}
      {currentPage === 'chat' && <ChatPage />}
      {currentPage === 'tickets' && <TicketsPage />}
    </div>
  );
};

export default App;