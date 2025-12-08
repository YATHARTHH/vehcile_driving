class VehicleChatbot {
    constructor() {
        this.isOpen = false;
        this.messageQueue = [];
        this.isTyping = false;
        this.conversationId = this.generateConversationId();
        this.init();
    }
    
    generateConversationId() {
        return 'conv_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    init() {
        this.createChatbotHTML();
        this.bindEvents();
        this.addWelcomeMessage();
    }

    createChatbotHTML() {
        const chatbotHTML = `
            <div class="chatbot-container">
                <button class="chatbot-toggle" id="chatbotToggle">
                    <i class="fas fa-comments"></i>
                </button>
                <div class="chatbot-window" id="chatbotWindow">
                    <div class="chatbot-header">
                        <h3><i class="fas fa-robot"></i> Vehicle Assistant</h3>
                        <button class="chatbot-close" id="chatbotClose">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                    <div class="chatbot-messages" id="chatbotMessages">
                        <div class="typing-indicator" id="typingIndicator">
                            <div class="typing-dot"></div>
                            <div class="typing-dot"></div>
                            <div class="typing-dot"></div>
                        </div>
                    </div>
                    <div class="chatbot-input">
                        <input type="text" id="chatbotInput" placeholder="Ask me about your driving..." maxlength="200">
                        <button class="chatbot-send" id="chatbotSend">
                            <i class="fas fa-paper-plane"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', chatbotHTML);
    }

    bindEvents() {
        const toggle = document.getElementById('chatbotToggle');
        const close = document.getElementById('chatbotClose');
        const input = document.getElementById('chatbotInput');
        const send = document.getElementById('chatbotSend');

        toggle.addEventListener('click', () => this.toggleChatbot());
        close.addEventListener('click', () => this.closeChatbot());
        send.addEventListener('click', () => this.sendMessage());
        
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.sendMessage();
            }
        });
    }

    toggleChatbot() {
        const window = document.getElementById('chatbotWindow');
        const toggle = document.getElementById('chatbotToggle');
        
        if (this.isOpen) {
            this.closeChatbot();
        } else {
            window.classList.add('active');
            toggle.innerHTML = '<i class="fas fa-times"></i>';
            this.isOpen = true;
            document.getElementById('chatbotInput').focus();
        }
    }

    closeChatbot() {
        const window = document.getElementById('chatbotWindow');
        const toggle = document.getElementById('chatbotToggle');
        
        window.classList.remove('active');
        toggle.innerHTML = '<i class="fas fa-comments"></i>';
        this.isOpen = false;
    }

    addWelcomeMessage() {
        const welcomeMsg = "Hello! I'm your vehicle assistant. I can help you with driving tips, fuel efficiency advice, and explain your trip data. What would you like to know?";
        this.addMessage(welcomeMsg, 'bot');
        this.addQuickActions();
    }
    
    addQuickActions() {
        const messagesContainer = document.getElementById('chatbotMessages');
        const quickActionsDiv = document.createElement('div');
        quickActionsDiv.className = 'quick-actions';
        quickActionsDiv.innerHTML = `
            <div class="quick-actions-title">Quick Actions:</div>
            <div class="quick-action-buttons">
                <button class="quick-action-btn" data-action="analyze">📊 Analyze My Trips</button>
                <button class="quick-action-btn" data-action="fuel">⛽ Fuel Tips</button>
                <button class="quick-action-btn" data-action="safety">🛡️ Safety Advice</button>
                <button class="quick-action-btn" data-action="maintenance">🔧 Maintenance</button>
            </div>
        `;
        
        // Add click handlers for quick actions
        quickActionsDiv.addEventListener('click', (e) => {
            if (e.target.classList.contains('quick-action-btn')) {
                const action = e.target.dataset.action;
                this.handleQuickAction(action);
            }
        });
        
        messagesContainer.appendChild(quickActionsDiv);
    }
    
    handleQuickAction(action) {
        const actionMessages = {
            'analyze': 'Analyze my recent trips and give me insights',
            'fuel': 'How can I improve my fuel efficiency?',
            'safety': 'Give me safety tips for driving',
            'maintenance': 'What maintenance should I be aware of?'
        };
        
        const message = actionMessages[action];
        if (message) {
            document.getElementById('chatbotInput').value = message;
            this.sendMessage();
        }
    }

    addMessage(text, sender, options = {}) {
        const messagesContainer = document.getElementById('chatbotMessages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        
        // Handle markdown-like formatting
        const formattedText = this.formatMessage(text);
        messageDiv.innerHTML = formattedText;
        
        // Add message status for user messages
        if (sender === 'user') {
            const statusDiv = document.createElement('div');
            statusDiv.className = 'message-status';
            statusDiv.innerHTML = '<i class="fas fa-check"></i>';
            messageDiv.appendChild(statusDiv);
        }
        
        // Add timestamp
        const timestamp = document.createElement('div');
        timestamp.className = 'message-time';
        timestamp.textContent = new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        messageDiv.appendChild(timestamp);
        
        // Add animation
        messageDiv.style.opacity = '0';
        messageDiv.style.transform = 'translateY(10px)';
        messagesContainer.appendChild(messageDiv);
        
        // Animate in
        requestAnimationFrame(() => {
            messageDiv.style.transition = 'all 0.3s ease';
            messageDiv.style.opacity = '1';
            messageDiv.style.transform = 'translateY(0)';
        });
        
        this.scrollToBottom();
    }
    
    formatMessage(text) {
        // Convert bullet points
        text = text.replace(/•/g, '<span class="bullet">•</span>');
        
        // Convert emojis and icons to spans for better styling
        text = text.replace(/(📊|⛽|🛡️|🔧|🚗|💡|⚠️|✅|🎯|📈|📉|🌟|👍|🔴)/g, '<span class="emoji">$1</span>');
        
        // Convert **bold** text
        text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        
        // Convert line breaks
        text = text.replace(/\n/g, '<br>');
        
        return text;
    }
    
    scrollToBottom() {
        const messagesContainer = document.getElementById('chatbotMessages');
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    showTyping() {
        const indicator = document.getElementById('typingIndicator');
        indicator.style.display = 'flex';
        indicator.style.opacity = '0';
        
        // Animate typing indicator
        requestAnimationFrame(() => {
            indicator.style.transition = 'opacity 0.3s ease';
            indicator.style.opacity = '1';
        });
        
        this.scrollToBottom();
    }

    hideTyping() {
        const indicator = document.getElementById('typingIndicator');
        indicator.style.opacity = '0';
        
        setTimeout(() => {
            indicator.style.display = 'none';
        }, 300);
    }

    async sendMessage() {
        const input = document.getElementById('chatbotInput');
        const send = document.getElementById('chatbotSend');
        const message = input.value.trim();

        if (!message || this.isTyping) return;

        // Add user message
        this.addMessage(message, 'user');
        input.value = '';
        send.disabled = true;
        this.isTyping = true;

        // Show typing indicator
        this.showTyping();

        try {
            const response = await fetch('/chatbot', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    message: message,
                    conversation_id: this.conversationId
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            
            // Realistic typing delay based on response length
            const typingDelay = Math.min(Math.max(data.response.length * 20, 800), 3000);
            
            setTimeout(() => {
                this.hideTyping();
                this.addMessage(data.response, 'bot');
                this.isTyping = false;
                send.disabled = false;
                input.focus();
                
                // Add follow-up suggestions if available
                if (data.suggestions) {
                    this.addSuggestions(data.suggestions);
                }
            }, typingDelay);

        } catch (error) {
            console.error('Chatbot error:', error);
            this.hideTyping();
            this.addMessage('Sorry, I encountered an error. Please check your connection and try again.', 'bot');
            this.isTyping = false;
            send.disabled = false;
            input.focus();
        }
    }
    
    addSuggestions(suggestions) {
        const messagesContainer = document.getElementById('chatbotMessages');
        const suggestionsDiv = document.createElement('div');
        suggestionsDiv.className = 'message-suggestions';
        
        const title = document.createElement('div');
        title.className = 'suggestions-title';
        title.textContent = 'You might also ask:';
        suggestionsDiv.appendChild(title);
        
        suggestions.forEach(suggestion => {
            const btn = document.createElement('button');
            btn.className = 'suggestion-btn';
            btn.textContent = suggestion;
            btn.onclick = () => {
                document.getElementById('chatbotInput').value = suggestion;
                this.sendMessage();
                suggestionsDiv.remove();
            };
            suggestionsDiv.appendChild(btn);
        });
        
        messagesContainer.appendChild(suggestionsDiv);
        this.scrollToBottom();
    }
}

// Initialize chatbot when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.vehicleChatbot = new VehicleChatbot();
    
    // Add keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        // Ctrl/Cmd + K to open chatbot
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            if (!window.vehicleChatbot.isOpen) {
                window.vehicleChatbot.toggleChatbot();
            }
        }
        
        // Escape to close chatbot
        if (e.key === 'Escape' && window.vehicleChatbot.isOpen) {
            window.vehicleChatbot.closeChatbot();
        }
    });
    
    // Add notification for keyboard shortcut
    const shortcutHint = document.createElement('div');
    shortcutHint.className = 'keyboard-shortcut-hint';
    shortcutHint.innerHTML = 'Press <kbd>Ctrl</kbd> + <kbd>K</kbd> to open assistant';
    shortcutHint.style.cssText = `
        position: fixed;
        bottom: 90px;
        right: 20px;
        background: rgba(0,0,0,0.8);
        color: white;
        padding: 8px 12px;
        border-radius: 6px;
        font-size: 12px;
        opacity: 0;
        transition: opacity 0.3s;
        pointer-events: none;
        z-index: 999;
    `;
    document.body.appendChild(shortcutHint);
    
    // Show hint briefly on page load
    setTimeout(() => {
        shortcutHint.style.opacity = '1';
        setTimeout(() => {
            shortcutHint.style.opacity = '0';
        }, 3000);
    }, 2000);
});