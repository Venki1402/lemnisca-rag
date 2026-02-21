document.addEventListener('DOMContentLoaded', () => {
    const chatBox = document.getElementById('chat-box');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const API_URL = 'http://127.0.0.1:8000/chat';

    // Remove the initial pre-rendered message to handle rendering via JS logic
    chatBox.innerHTML = '';
    addMessage("Hello! I'm the Clearpath Support Assistant. How can I help you today?", 'bot');

    function createTypeIndicator() {
        const id = 'typing-' + Date.now();
        const msgDiv = document.createElement('div');
        msgDiv.className = `message bot`;
        msgDiv.id = id;

        msgDiv.innerHTML = `
            <div class="message-text typing-indicator">
                <span></span><span></span><span></span>
            </div>
        `;
        chatBox.appendChild(msgDiv);
        chatBox.scrollTop = chatBox.scrollHeight;
        return id;
    }

    function removeTypeIndicator(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    }

    function addMessage(text, sender, debugInfo = null) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${sender}`;

        // Escape HTML
        const safeText = document.createElement('div');
        safeText.innerText = text;

        let htmlContent = `<div class="message-text">${safeText.innerHTML}</div>`;

        // Add debug panel if available and it's a bot message
        if (sender === 'bot' && debugInfo) {
            let warningHtml = '';
            if (!debugInfo.is_safe || debugInfo.evaluator_flags.length > 0) {
                // Formatting warning
                warningHtml = `
                    <div class="warning-banner">
                        ⚠️ Low confidence — please verify with support.
                    </div>
                `;
            }

            let flagsList = '';
            if (debugInfo.evaluator_flags.length > 0) {
                flagsList = `<div><span class="label">Flags:</span> ${debugInfo.evaluator_flags.join('<br>')}</div>`;
            }

            htmlContent += `
                ${warningHtml}
                <div class="debug-panel">
                    <div class="debug-heading">Develper Debug Info</div>
                    <div><span class="label">Model:</span> <span style="font-family: monospace">${debugInfo.model_used}</span></div>
                    <div><span class="label">Tokens [In/Out]:</span> ${debugInfo.tokens_input} / ${debugInfo.tokens_output}</div>
                    ${flagsList}
                </div>
            `;
        }

        msgDiv.innerHTML = htmlContent;
        chatBox.appendChild(msgDiv);
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    async function handleSend() {
        const text = userInput.value.trim();
        if (!text) return;

        // User message
        addMessage(text, 'user');
        userInput.value = '';

        // Show typing
        const indicatorId = createTypeIndicator();

        try {
            const response = await fetch(API_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ query: text })
            });

            const data = await response.json();
            removeTypeIndicator(indicatorId);

            if (response.ok) {
                addMessage(data.response, 'bot', {
                    model_used: data.model_used,
                    tokens_input: data.tokens_input,
                    tokens_output: data.tokens_output,
                    evaluator_flags: data.evaluator_flags,
                    is_safe: data.is_safe
                });
            } else {
                addMessage("Oops! Something went wrong communicating with the server: " + (data.detail || "Server error"), 'bot');
            }
        } catch (error) {
            removeTypeIndicator(indicatorId);
            addMessage("Oops! Could not connect to the backend server. Make sure it's running.", 'bot');
            console.error("Chat error:", error);
        }
    }

    sendBtn.addEventListener('click', handleSend);
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleSend();
    });
});
