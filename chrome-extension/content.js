/**
 * CursorBot Chrome Extension - Content Script
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
  chatOverlay.id = 'cursorbot-overlay';
  chatOverlay.innerHTML = `
    <div class="cursorbot-chat">
      <div class="cursorbot-header">
        <span class="cursorbot-title">CursorBot</span>
        <button class="cursorbot-close">&times;</button>
      </div>
      <div class="cursorbot-messages"></div>
      <div class="cursorbot-input-area">
        <input type="text" class="cursorbot-input" placeholder="Ask anything..." />
        <button class="cursorbot-send">Send</button>
      </div>
    </div>
  `;

  document.body.appendChild(chatOverlay);

  // Event handlers
  const closeBtn = chatOverlay.querySelector('.cursorbot-close');
  const input = chatOverlay.querySelector('.cursorbot-input');
  const sendBtn = chatOverlay.querySelector('.cursorbot-send');

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
    chatOverlay.querySelector('.cursorbot-input').focus();
  }
}

async function sendMessage(input) {
  const message = input.value.trim();
  if (!message) return;

  const messagesDiv = chatOverlay.querySelector('.cursorbot-messages');
  
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
  div.className = `cursorbot-message cursorbot-${type}`;
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
  resultOverlay.id = 'cursorbot-result';
  resultOverlay.innerHTML = `
    <div class="cursorbot-result-content">
      <div class="cursorbot-result-header">
        <span>CursorBot Result</span>
        <button class="cursorbot-result-close">&times;</button>
      </div>
      <div class="cursorbot-result-body">${escapeHtml(result)}</div>
      <div class="cursorbot-result-actions">
        <button class="cursorbot-copy">Copy</button>
      </div>
    </div>
  `;

  document.body.appendChild(resultOverlay);

  // Event handlers
  resultOverlay.querySelector('.cursorbot-result-close').addEventListener('click', hideResult);
  resultOverlay.querySelector('.cursorbot-copy').addEventListener('click', () => {
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
  resultOverlay.id = 'cursorbot-result';
  resultOverlay.innerHTML = `
    <div class="cursorbot-result-content cursorbot-loading">
      <div class="cursorbot-spinner"></div>
      <div class="cursorbot-loading-text">${escapeHtml(message)}</div>
    </div>
  `;

  document.body.appendChild(resultOverlay);
}

function showError(error) {
  showResult(`Error: ${error}`);
  const body = resultOverlay?.querySelector('.cursorbot-result-body');
  if (body) body.classList.add('cursorbot-error-text');
}

// ============================================
// Toast Notifications
// ============================================

function showToast(message) {
  const toast = document.createElement('div');
  toast.className = 'cursorbot-toast';
  toast.textContent = message;
  document.body.appendChild(toast);

  setTimeout(() => {
    toast.classList.add('cursorbot-toast-show');
  }, 10);

  setTimeout(() => {
    toast.classList.remove('cursorbot-toast-show');
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

console.log('CursorBot content script loaded');
