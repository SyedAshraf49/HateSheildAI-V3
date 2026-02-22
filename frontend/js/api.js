// Get backend URL from settings
function getBackendUrl() {
  const settings = localStorage.getItem('hs_settings');
  if (settings) {
    const parsed = JSON.parse(settings);
    return parsed.backendUrl || 'http://127.0.0.1:5000';
  }
  return 'http://127.0.0.1:5000';
}

// Enhanced analyze function with better UX
async function analyzeComment() {
  const textEl = document.getElementById('inputText');
  const resultBox = document.getElementById('analysisResult');
  const badge = document.getElementById('resultBadge');
  const meta = document.getElementById('resultMeta');
  const rewritten = document.getElementById('rewrittenText');
  const analyzeBtn = document.getElementById('analyzeBtn');

  const text = textEl.value.trim();
  if (!text) { 
    showFeedback('⚠️ Please enter text to analyze', 'warning');
    textEl.focus();
    return; 
  }

  // Check minimum length
  if (text.length < 3) {
    showFeedback('⚠️ Text is too short. Please enter at least 3 characters.', 'warning');
    return;
  }

  analyzeBtn.disabled = true;
  analyzeBtn.innerHTML = '<span class="loading-spinner"></span> Analyzing...';

  try {
    const backendUrl = getBackendUrl();
    const resp = await fetch(backendUrl + '/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
    });
    
    if (!resp.ok) {
      throw new Error('Backend returned error: ' + resp.status);
    }
    
    const data = await resp.json();

    // Handle errors from backend
    if (data.error) {
      throw new Error(data.error);
    }

    // Update badge with classification class
    const classification = (data.classification || 'safe').toLowerCase();
    badge.innerText = classification.toUpperCase().replace('_', ' ');
    badge.className = `classification-badge badge badge-${classification}`;
    
    meta.innerText = `Confidence: ${data.confidence}% • Processed in ${data.processing_time_ms || 0}ms`;
    rewritten.innerText = data.rewritten_text || text;
    
    // Update emotions if available
    if (data.emotions && shouldShowEmotions()) {
      updateEmotions(data.emotions);
    }
    
    resultBox.classList.remove('visually-hidden');
    
    // Save to history if enabled
    if (shouldSaveHistory()) {
      saveToHistory(text, classification, data.confidence);
    }
    
    // Smooth scroll to results
    setTimeout(() => {
      resultBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }, 100);
    
    showFeedback('✅ Analysis complete!');
    
  } catch (e) {
    console.error('Analysis error:', e);
    showFeedback('❌ Failed to analyze. Make sure backend is running at ' + getBackendUrl(), 'error');
  } finally {
    analyzeBtn.disabled = false;
    analyzeBtn.innerHTML = '🛡️ Analyze & Shield';
  }
}

function updateEmotions(emotions) {
  const emotionTypes = ['anger', 'joy', 'sadness', 'fear', 'disgust'];
  emotionTypes.forEach(emotion => {
    const value = emotions[emotion] || 0;
    const fill = document.getElementById(`${emotion}-fill`);
    const valueEl = document.getElementById(`${emotion}-value`);
    
    if (fill && valueEl) {
      // Smooth animation
      setTimeout(() => {
        fill.style.width = value + '%';
        valueEl.textContent = value + '%';
      }, 100);
    }
  });
}

function clearText() {
  const el = document.getElementById('inputText');
  if (el) {
    el.value = '';
    updateCharCount();
    el.focus();
  }
  const resultBox = document.getElementById('analysisResult');
  if (resultBox) {
    resultBox.classList.add('visually-hidden');
  }
  showFeedback('🗑️ Text cleared');
}

function setExampleText(txt) {
  const el = document.getElementById('inputText');
  if (el) {
    el.value = txt;
    updateCharCount();
    el.focus();
  }
}

function copyRewrite() {
  const txt = document.getElementById('rewrittenText')?.innerText || '';
  if (!txt) {
    showFeedback('⚠️ No text to copy', 'warning');
    return;
  }
  
  navigator.clipboard.writeText(txt).then(() => {
    showFeedback('✅ Copied to clipboard!');
  }).catch(err => {
    console.error('Copy failed:', err);
    showFeedback('❌ Failed to copy', 'error');
  });
}

function useRewrite() {
  const txt = document.getElementById('rewrittenText')?.innerText || '';
  if (!txt) {
    showFeedback('⚠️ No rewritten text available', 'warning');
    return;
  }
  
  const el = document.getElementById('inputText');
  if (el) {
    el.value = txt;
    updateCharCount();
    showFeedback('✅ Text replaced with safe version!');
    
    // Hide results after using rewrite
    const resultBox = document.getElementById('analysisResult');
    if (resultBox) {
      setTimeout(() => {
        resultBox.classList.add('visually-hidden');
      }, 1000);
    }
  }
}

function showFeedback(message, type = 'success') {
  const existing = document.querySelector('.copy-feedback');
  if (existing) existing.remove();
  
  const feedback = document.createElement('div');
  feedback.className = 'copy-feedback';
  feedback.textContent = message;
  
  if (type === 'warning') {
    feedback.style.background = '#fbbf24';
    feedback.style.color = '#052033';
  } else if (type === 'error') {
    feedback.style.background = '#f87171';
    feedback.style.color = '#fff';
  }
  
  document.body.appendChild(feedback);
  
  setTimeout(() => {
    feedback.style.opacity = '0';
    feedback.style.transform = 'translateY(10px)';
    feedback.style.transition = 'all 0.3s ease-out';
    setTimeout(() => feedback.remove(), 300);
  }, 2500);
}

function updateCharCount() {
  const input = document.getElementById('inputText');
  const counter = document.getElementById('charcount');
  if (!input || !counter) return;
  
  const len = input.value.length;
  const max = 5000;
  counter.textContent = `${len} / ${max} chars`;
  
  if (len > max * 0.9) {
    counter.className = 'charcount char-limit-warning';
  } else if (len >= max) {
    counter.className = 'charcount char-limit-error';
  } else {
    counter.className = 'charcount';
  }
}

function saveToHistory(text, classification, confidence) {
  const settings = getSettings();
  const limit = settings.historyLimit || 5;
  
  let history = JSON.parse(localStorage.getItem('hs_history') || '[]');
  history.unshift({
    text: text.substring(0, 100),
    fullText: text,
    classification,
    confidence,
    timestamp: Date.now()
  });
  
  // Keep only the configured limit
  history = history.slice(0, limit);
  localStorage.setItem('hs_history', JSON.stringify(history));
  loadHistory();
}

function loadHistory() {
  const history = JSON.parse(localStorage.getItem('hs_history') || '[]');
  const container = document.getElementById('historyList');
  
  if (!container) return;
  
  if (history.length === 0) {
    container.innerHTML = '<p class="muted" style="font-size: 13px; text-align: center;">No analyses yet</p>';
    return;
  }
  
  container.innerHTML = history.map((item, index) => {
    const date = new Date(item.timestamp);
    const timeAgo = getTimeAgo(date);
    return `
      <div class="history-item" onclick="loadFromHistory(${index})">
        <div class="history-item-text">${escapeHtml(item.text)}${item.text.length >= 100 ? '...' : ''}</div>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 4px;">
          <span class="history-item-badge">${item.classification.toUpperCase()}</span>
          <span style="font-size: 11px; color: var(--muted);">${timeAgo}</span>
        </div>
      </div>
    `;
  }).join('');
}

function loadFromHistory(index) {
  const history = JSON.parse(localStorage.getItem('hs_history') || '[]');
  if (history[index]) {
    const item = history[index];
    setExampleText(item.fullText || item.text);
    showFeedback('📝 Loaded from history');
  }
}

function clearHistory() {
  if (confirm('Clear all analysis history?')) {
    localStorage.removeItem('hs_history');
    loadHistory();
    showFeedback('🗑️ History cleared');
  }
}

function getTimeAgo(date) {
  const seconds = Math.floor((new Date() - date) / 1000);
  
  if (seconds < 60) return 'just now';
  if (seconds < 3600) return Math.floor(seconds / 60) + 'm ago';
  if (seconds < 86400) return Math.floor(seconds / 3600) + 'h ago';
  if (seconds < 604800) return Math.floor(seconds / 86400) + 'd ago';
  return date.toLocaleDateString();
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function shouldSaveHistory() {
  const settings = getSettings();
  return settings.saveHistory !== false;
}

function shouldShowEmotions() {
  const settings = getSettings();
  return settings.showEmotions !== false;
}

function getSettings() {
  const saved = localStorage.getItem('hs_settings');
  return saved ? JSON.parse(saved) : {};
}

// Auto-analyze on typing (if enabled)
let autoAnalyzeTimeout = null;
function setupAutoAnalyze() {
  const settings = getSettings();
  if (!settings.autoAnalyze) return;
  
  const input = document.getElementById('inputText');
  if (!input) return;
  
  input.addEventListener('input', () => {
    clearTimeout(autoAnalyzeTimeout);
    autoAnalyzeTimeout = setTimeout(() => {
      if (input.value.trim().length > 10) {
        analyzeComment();
      }
    }, 2000); // Wait 2 seconds after typing stops
  });
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
  const input = document.getElementById('inputText');
  if (input) {
    input.addEventListener('input', updateCharCount);
    
    // Ctrl+Enter to analyze
    input.addEventListener('keydown', (e) => {
      if (e.ctrlKey && e.key === 'Enter') {
        analyzeComment();
      }
    });
  }
  
  loadHistory();
  updateCharCount();
  setupAutoAnalyze();
});