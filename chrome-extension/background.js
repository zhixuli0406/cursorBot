/**
 * CursorBot Chrome Extension - Background Service Worker
 * 
 * Handles:
 * - Communication with CursorBot server
 * - Context menu integration
 * - Keyboard shortcuts
 * - Notifications
 */

// Default configuration
const DEFAULT_CONFIG = {
  serverUrl: 'http://localhost:8000',
  apiKey: '',
  model: 'gpt-4o-mini',
  autoCapture: true,
  notifications: true,
};

// Load configuration
async function getConfig() {
  const result = await chrome.storage.sync.get(DEFAULT_CONFIG);
  return result;
}

// Save configuration
async function saveConfig(config) {
  await chrome.storage.sync.set(config);
}

// ============================================
// Context Menu
// ============================================

// Create context menu on install
chrome.runtime.onInstalled.addListener(() => {
  // Main menu
  chrome.contextMenus.create({
    id: 'cursorbot-main',
    title: 'CursorBot',
    contexts: ['selection', 'page'],
  });

  // Ask about selection
  chrome.contextMenus.create({
    id: 'cursorbot-ask',
    parentId: 'cursorbot-main',
    title: 'Ask about this',
    contexts: ['selection'],
  });

  // Explain selection
  chrome.contextMenus.create({
    id: 'cursorbot-explain',
    parentId: 'cursorbot-main',
    title: 'Explain this',
    contexts: ['selection'],
  });

  // Translate selection
  chrome.contextMenus.create({
    id: 'cursorbot-translate',
    parentId: 'cursorbot-main',
    title: 'Translate this',
    contexts: ['selection'],
  });

  // Summarize page
  chrome.contextMenus.create({
    id: 'cursorbot-summarize',
    parentId: 'cursorbot-main',
    title: 'Summarize page',
    contexts: ['page'],
  });

  // Separator
  chrome.contextMenus.create({
    id: 'cursorbot-separator',
    parentId: 'cursorbot-main',
    type: 'separator',
    contexts: ['selection', 'page'],
  });

  // Settings
  chrome.contextMenus.create({
    id: 'cursorbot-settings',
    parentId: 'cursorbot-main',
    title: 'Settings',
    contexts: ['selection', 'page'],
  });

  console.log('CursorBot context menu created');
});

// Handle context menu clicks
chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  const config = await getConfig();

  switch (info.menuItemId) {
    case 'cursorbot-ask':
      await sendToServer(config, 'ask', info.selectionText, tab);
      break;
    case 'cursorbot-explain':
      await sendToServer(config, 'explain', info.selectionText, tab);
      break;
    case 'cursorbot-translate':
      await sendToServer(config, 'translate', info.selectionText, tab);
      break;
    case 'cursorbot-summarize':
      // Get page content via content script
      chrome.tabs.sendMessage(tab.id, { action: 'getPageContent' }, async (response) => {
        if (response?.content) {
          await sendToServer(config, 'summarize', response.content, tab);
        }
      });
      break;
    case 'cursorbot-settings':
      chrome.runtime.openOptionsPage();
      break;
  }
});

// ============================================
// API Communication
// ============================================

async function sendToServer(config, action, content, tab) {
  if (!config.serverUrl) {
    showNotification('Error', 'Server URL not configured');
    return;
  }

  try {
    // Show loading
    chrome.tabs.sendMessage(tab.id, {
      action: 'showLoading',
      message: `Processing ${action}...`,
    });

    // Prepare prompt based on action
    let prompt;
    switch (action) {
      case 'ask':
        prompt = `Answer this question about the following text:\n\n${content}`;
        break;
      case 'explain':
        prompt = `Explain the following text in simple terms:\n\n${content}`;
        break;
      case 'translate':
        prompt = `Translate the following text to English (or Chinese if it's already in English):\n\n${content}`;
        break;
      case 'summarize':
        prompt = `Summarize the following webpage content:\n\n${content.substring(0, 5000)}`;
        break;
      default:
        prompt = content;
    }

    // Send to CursorBot server
    const response = await fetch(`${config.serverUrl}/api/agent`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${config.apiKey}`,
      },
      body: JSON.stringify({
        message: prompt,
        model: config.model,
      }),
    });

    if (!response.ok) {
      throw new Error(`Server error: ${response.status}`);
    }

    const data = await response.json();

    // Show result
    chrome.tabs.sendMessage(tab.id, {
      action: 'showResult',
      result: data.response || data.message || 'No response',
    });

    // Show notification
    if (config.notifications) {
      showNotification('CursorBot', `${action} completed`);
    }

  } catch (error) {
    console.error('CursorBot error:', error);
    chrome.tabs.sendMessage(tab.id, {
      action: 'showError',
      error: error.message,
    });
    showNotification('Error', error.message);
  }
}

// ============================================
// Quick Chat
// ============================================

async function quickChat(message) {
  const config = await getConfig();

  try {
    const response = await fetch(`${config.serverUrl}/api/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${config.apiKey}`,
      },
      body: JSON.stringify({
        message,
        model: config.model,
      }),
    });

    if (!response.ok) {
      throw new Error(`Server error: ${response.status}`);
    }

    const data = await response.json();
    return data.response || data.message;

  } catch (error) {
    console.error('Chat error:', error);
    throw error;
  }
}

// ============================================
// Message Handling
// ============================================

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'chat') {
    quickChat(request.message)
      .then(response => sendResponse({ success: true, response }))
      .catch(error => sendResponse({ success: false, error: error.message }));
    return true; // Keep channel open for async response
  }

  if (request.action === 'getConfig') {
    getConfig().then(config => sendResponse(config));
    return true;
  }

  if (request.action === 'saveConfig') {
    saveConfig(request.config).then(() => sendResponse({ success: true }));
    return true;
  }
});

// ============================================
// Notifications
// ============================================

function showNotification(title, message) {
  chrome.notifications.create({
    type: 'basic',
    iconUrl: 'icons/icon128.png',
    title,
    message,
  });
}

// ============================================
// Keyboard Shortcuts
// ============================================

chrome.commands.onCommand.addListener(async (command) => {
  if (command === 'toggle-chat') {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    chrome.tabs.sendMessage(tab.id, { action: 'toggleChat' });
  }
});

console.log('CursorBot background service worker loaded');
