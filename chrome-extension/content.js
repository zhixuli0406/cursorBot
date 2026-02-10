/**
 * ClaudeBot Chrome Extension - Content Script
 * 
 * Injected into web pages to provide:
 * - Chat overlay
 * - Selection handling
 * - Result display
 */

// ============================================
// Chat Overlay
// ============================================

let chatOverlay = null;
let chatVisible = false;

function createChatOverlay() {
  if (chatOverlay) return;

  chatOverlay = document.createElement('div');
  chatOverlay.id = 'claudebot-overlay';
  chatOverlay.innerHTML = `
    <div class="claudebot-chat">
      <div class="claudebot-header">
        <span class="claudebot-title">ClaudeBot</span>
        <button class="claudebot-close">&times;</button>
      </div>
      <div class="claudebot-messages"></div>
      <div class="claudebot-input-area">
        <input type="text" class="claudebot-input" placeholder="Ask anything..." />
        <button class="claudebot-send">Send</button>
      </div>
    </div>
  `;

  document.body.appendChild(chatOverlay);

  // Event handlers
  const closeBtn = chatOverlay.querySelector('.claudebot-close');
  const input = chatOverlay.querySelector('.claudebot-input');
  const sendBtn = chatOverlay.querySelector('.claudebot-send');

  closeBtn.addEventListener('click', toggleChat);
  
  sendBtn.addEventListener('click', () => sendMessage(input));
  
  input.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage(input);
  });
}

function toggleChat() {
  if (!chatOverlay) createChatOverlay();
  
  chatVisible = !chatVisible;
  chatOverlay.style.display = chatVisible ? 'block' : 'none';
  
  if (chatVisible) {
    chatOverlay.querySelector('.claudebot-input').focus();
  }
}

async function sendMessage(input) {
  const message = input.value.trim();
  if (!message) return;

  const messagesDiv = chatOverlay.querySelector('.claudebot-messages');
  
  // Add user message
  addMessage(messagesDiv, message, 'user');
  input.value = '';

  // Add loading
  const loadingId = addMessage(messagesDiv, 'Thinking...', 'loading');

  try {
    // Send to background script
    const response = await chrome.runtime.sendMessage({
      action: 'chat',
      message,
    });

    // Remove loading
    document.getElementById(loadingId)?.remove();

    if (response.success) {
      addMessage(messagesDiv, response.response, 'assistant');
    } else {
      addMessage(messagesDiv, `Error: ${response.error}`, 'error');
    }
  } catch (error) {
    document.getElementById(loadingId)?.remove();
    addMessage(messagesDiv, `Error: ${error.message}`, 'error');
  }
}

function addMessage(container, text, type) {
  const id = `msg-${Date.now()}`;
  const div = document.createElement('div');
  div.id = id;
  div.className = `claudebot-message claudebot-${type}`;
  div.textContent = text;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
  return id;
}

// ============================================
// Result Display
// ============================================

let resultOverlay = null;

function showResult(result) {
  hideResult();

  resultOverlay = document.createElement('div');
  resultOverlay.id = 'claudebot-result';
  resultOverlay.innerHTML = `
    <div class="claudebot-result-content">
      <div class="claudebot-result-header">
        <span>ClaudeBot Result</span>
        <button class="claudebot-result-close">&times;</button>
      </div>
      <div class="claudebot-result-body">${escapeHtml(result)}</div>
      <div class="claudebot-result-actions">
        <button class="claudebot-copy">Copy</button>
      </div>
    </div>
  `;

  document.body.appendChild(resultOverlay);

  // Event handlers
  resultOverlay.querySelector('.claudebot-result-close').addEventListener('click', hideResult);
  resultOverlay.querySelector('.claudebot-copy').addEventListener('click', () => {
    navigator.clipboard.writeText(result);
    showToast('Copied to clipboard');
  });

  // Click outside to close
  resultOverlay.addEventListener('click', (e) => {
    if (e.target === resultOverlay) hideResult();
  });
}

function hideResult() {
  if (resultOverlay) {
    resultOverlay.remove();
    resultOverlay = null;
  }
}

function showLoading(message) {
  hideResult();

  resultOverlay = document.createElement('div');
  resultOverlay.id = 'claudebot-result';
  resultOverlay.innerHTML = `
    <div class="claudebot-result-content claudebot-loading">
      <div class="claudebot-spinner"></div>
      <div class="claudebot-loading-text">${escapeHtml(message)}</div>
    </div>
  `;

  document.body.appendChild(resultOverlay);
}

function showError(error) {
  showResult(`Error: ${error}`);
  const body = resultOverlay?.querySelector('.claudebot-result-body');
  if (body) body.classList.add('claudebot-error-text');
}

// ============================================
// Toast Notifications
// ============================================

function showToast(message) {
  const toast = document.createElement('div');
  toast.className = 'claudebot-toast';
  toast.textContent = message;
  document.body.appendChild(toast);

  setTimeout(() => {
    toast.classList.add('claudebot-toast-show');
  }, 10);

  setTimeout(() => {
    toast.classList.remove('claudebot-toast-show');
    setTimeout(() => toast.remove(), 300);
  }, 2000);
}

// ============================================
// Page Content Extraction
// ============================================

function getPageContent() {
  // Get main content (try common selectors)
  const selectors = [
    'article',
    'main',
    '[role="main"]',
    '.content',
    '.post-content',
    '#content',
  ];

  for (const selector of selectors) {
    const el = document.querySelector(selector);
    if (el) return el.innerText;
  }

  // Fallback to body
  return document.body.innerText;
}

// ============================================
// Utilities
// ============================================

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// ============================================
// Message Handling
// ============================================

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  switch (request.action) {
    case 'toggleChat':
      toggleChat();
      break;
    case 'showResult':
      showResult(request.result);
      break;
    case 'showLoading':
      showLoading(request.message);
      break;
    case 'showError':
      showError(request.error);
      break;
    case 'getPageContent':
      sendResponse({ content: getPageContent() });
      break;
  }
});

console.log('ClaudeBot content script loaded');
