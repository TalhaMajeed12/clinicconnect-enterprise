(() => {
    'use strict';

    const toggle = document.getElementById('clinical-chat-toggle');
    const panel = document.getElementById('clinical-chat-panel');
    const close = document.getElementById('clinical-chat-close');
    const form = document.getElementById('clinical-chat-form');
    const input = document.getElementById('clinical-chat-input');
    const messages = document.getElementById('clinical-chat-messages');
    if (!toggle || !panel || !form || !input || !messages) return;

    const addMessage = (text, kind, emergency = false) => {
        const item = document.createElement('div');
        item.className = `clinical-chat-message ${kind}${emergency ? ' emergency' : ''}`;
        item.textContent = text;
        messages.appendChild(item);
        messages.scrollTop = messages.scrollHeight;
    };

    const openPanel = () => {
        panel.hidden = false;
        toggle.setAttribute('aria-expanded', 'true');
        input.focus();
        if (!messages.children.length) {
            addMessage(panel.dataset.welcome, 'assistant');
        }
    };

    const closePanel = () => {
        panel.hidden = true;
        toggle.setAttribute('aria-expanded', 'false');
        toggle.focus();
    };

    const sendMessage = async (question) => {
        const message = question.trim();
        if (!message) return;
        addMessage(message, 'user');
        input.value = '';
        input.disabled = true;

        try {
            const response = await fetch('/chatbot/message', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken,
                },
                body: JSON.stringify({message}),
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Request failed');
            addMessage(`${data.message}\n\n${data.disclaimer}`, 'assistant', data.emergency);
        } catch (error) {
            addMessage(panel.dataset.error, 'assistant', true);
        } finally {
            input.disabled = false;
            input.focus();
        }
    };

    toggle.addEventListener('click', openPanel);
    close.addEventListener('click', closePanel);
    form.addEventListener('submit', (event) => {
        event.preventDefault();
        sendMessage(input.value);
    });
    document.querySelectorAll('[data-chat-question]').forEach((button) => {
        button.addEventListener('click', () => sendMessage(button.dataset.chatQuestion));
    });
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && !panel.hidden) closePanel();
    });
})();
