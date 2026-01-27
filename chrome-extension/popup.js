/**
 * CursorBot Chrome Extension - Popup Script
 */

// Load configuration and update UI
async function init() {
  const config = await chrome.runtime.sendMessage({ action: 'getConfig' });
  
  // Update status indicator
  const status = document.getElementById('status');
  if (config.serverUrl) {
    status.classList.remove('offline');
  } else {
    status.classList.add('offline');
  }
  
  // Update model badge
  document.getElementById('model').textContent = config.model || 'gpt-4o-mini';
  
  // Load recent queries
  loadRecentQueries();
}

// Load recent queries from storage
async function loadRecentQueries() {
  const result = await chrome.storage.local.get({ recentQueries: [] });
  const list = document.getElementById('recent-list');
  
  if (result.recentQueries.length === 0) {
    list.innerHTML = '<div class="recent-item">No recent queries</div>';
    return;
  }
  
  list.innerHTML = result.recentQueries
    .slice(0, 5)
    .map(q => `<div class="recent-item" data-query="${escapeHtml(q)}">${escapeHtml(q)}</div>`)
    .join('');
  
  // Add click handlers
  list.querySelectorAll('.recent-item').forEach(item => {
    item.addEventListener('click', () => {
      document.getElementById('input').value = item.dataset.query;
    });
  });
}

// Save query to recent
async function saveQuery(query) {
  const result = await chrome.storage.local.get({ recentQueries: [] });
  const queries = [query, ...result.recentQueries.filter(q => q !== query)].slice(0, 10);
  await chrome.storage.local.set({ recentQueries: queries });
  loadRecentQueries();
}

// Send message
async function sendMessage() {
  const input = document.getElementById('input');
  const message = input.value.trim();
  
  if (!message) return;
  
  // Save to recent
  saveQuery(message);
  
  // Send to background
  try {
    const response = await chrome.runtime.sendMessage({
      action: 'chat',
      message,
    });
    
    if (response.success) {
      // Show in current tab
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      chrome.tabs.sendMessage(tab.id, {
        action: 'showResult',
        result: response.response,
      });
      window.close();
    } else {
      alert('Error: ' + response.error);
    }
  } catch (error) {
    alert('Error: ' + error.message);
  }
}

// Quick actions
async function quickAction(action) {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  
  if (action === 'chat') {
    chrome.tabs.sendMessage(tab.id, { action: 'toggleChat' });
    window.close();
    return;
  }
  
  // Get selected text or page content
  const response = await chrome.tabs.sendMessage(tab.id, { action: 'getPageContent' });
  const content = response?.content || '';
  
  if (!content) {
    alert('No content found on page');
    return;
  }
  
  // Send to background for processing
  const config = await chrome.runtime.sendMessage({ action: 'getConfig' });
  
  let prompt;
  switch (action) {
    case 'summarize':
      prompt = `Summarize this page:\n\n${content.substring(0, 5000)}`;
      break;
    case 'translate':
      prompt = `Translate this to English (or Chinese if already English):\n\n${content.substring(0, 3000)}`;
      break;
    case 'explain':
      prompt = `Explain this in simple terms:\n\n${content.substring(0, 3000)}`;
      break;
  }
  
  if (prompt) {
    saveQuery(prompt.substring(0, 50) + '...');
    
    chrome.tabs.sendMessage(tab.id, {
      action: 'showLoading',
      message: `Processing ${action}...`,
    });
    
    const result = await chrome.runtime.sendMessage({
      action: 'chat',
      message: prompt,
    });
    
    chrome.tabs.sendMessage(tab.id, {
      action: result.success ? 'showResult' : 'showError',
      result: result.response,
      error: result.error,
    });
    
    window.close();
  }
}

// Utility
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// Event listeners
document.addEventListener('DOMContentLoaded', init);

document.getElementById('send').addEventListener('click', sendMessage);

document.getElementById('input').addEventListener('keypress', (e) => {
  if (e.key === 'Enter') sendMessage();
});

document.getElementById('btn-chat').addEventListener('click', () => quickAction('chat'));
document.getElementById('btn-summarize').addEventListener('click', () => quickAction('summarize'));
document.getElementById('btn-translate').addEventListener('click', () => quickAction('translate'));
document.getElementById('btn-explain').addEventListener('click', () => quickAction('explain'));

document.getElementById('settings').addEventListener('click', (e) => {
  e.preventDefault();
  chrome.runtime.openOptionsPage();
});
