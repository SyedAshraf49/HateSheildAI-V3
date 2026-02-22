// Load theme and settings on page load
document.addEventListener('DOMContentLoaded', () => {
  loadTheme();
  initializeCharCounter();
  loadSettings();
});

function loadTheme() {
  const settings = getSettings();
  const isDark = settings.darkMode !== false; // Default to dark
  
  applyThemeToPage(isDark);
}

function applyThemeToPage(isDark) {
  const themeBtn = document.getElementById('themeToggle');
  
  if (isDark) {
    document.documentElement.classList.remove('light-theme');
    document.body.classList.remove('light-theme');
    if (themeBtn) themeBtn.textContent = '🌙';
  } else {
    document.documentElement.classList.add('light-theme');
    document.body.classList.add('light-theme');
    if (themeBtn) themeBtn.textContent = '☀️';
  }
}

function toggleTheme() {
  const isCurrentlyLight = document.documentElement.classList.contains('light-theme');
  const newIsDark = isCurrentlyLight; // Toggle to opposite
  
  applyThemeToPage(newIsDark);
  
  // Save to settings
  const settings = getSettings();
  settings.darkMode = newIsDark;
  localStorage.setItem('hs_settings', JSON.stringify(settings));
  
  // Show feedback if function exists
  if (typeof showFeedback === 'function') {
    showFeedback(newIsDark ? '🌙 Dark mode enabled' : '☀️ Light mode enabled');
  }
}

function getSettings() {
  const saved = localStorage.getItem('hs_settings');
  if (saved) {
    try {
      return JSON.parse(saved);
    } catch (e) {
      console.error('Failed to parse settings:', e);
      return getDefaultSettings();
    }
  }
  return getDefaultSettings();
}

function getDefaultSettings() {
  return {
    darkMode: true,
    animations: true,
    autoAnalyze: false,
    confidenceThreshold: 50,
    showEmotions: true,
    backendUrl: 'http://127.0.0.1:5000',
    requestTimeout: 10,
    saveHistory: true,
    historyLimit: 5,
    showSuccess: true,
    soundEffects: false
  };
}

function loadSettings() {
  const settings = getSettings();
  
  // Apply animations setting
  if (!settings.animations) {
    const style = document.createElement('style');
    style.id = 'disable-animations';
    style.textContent = '* { animation: none !important; transition: none !important; }';
    document.head.appendChild(style);
  } else {
    // Remove disable style if it exists
    const disableStyle = document.getElementById('disable-animations');
    if (disableStyle) {
      disableStyle.remove();
    }
  }
}

function initializeCharCounter() {
  const input = document.getElementById('inputText');
  if (input) {
    input.addEventListener('input', () => {
      const counter = document.getElementById('charcount');
      if (counter) {
        const len = input.value.length;
        const max = parseInt(input.getAttribute('maxlength') || '5000');
        counter.innerText = `${len} / ${max} chars`;
        
        // Add warning classes
        counter.classList.remove('char-limit-warning', 'char-limit-error');
        
        if (len >= max) {
          counter.classList.add('char-limit-error');
        } else if (len > max * 0.9) {
          counter.classList.add('char-limit-warning');
        }
      }
    });
  }
}

function setExampleText(txt) {
  const el = document.getElementById('inputText');
  if (el) {
    el.value = txt;
    // Trigger input event to update char count
    el.dispatchEvent(new Event('input'));
  }
}

function copyRewrite() {
  const txt = document.getElementById('rewrittenText')?.innerText || '';
  if (!txt) {
    if (typeof showFeedback === 'function') {
      showFeedback('⚠️ No text to copy', 'warning');
    }
    return;
  }
  
  navigator.clipboard.writeText(txt).then(() => {
    if (typeof showFeedback === 'function') {
      showFeedback('✅ Copied to clipboard!');
    } else {
      alert('Copied to clipboard!');
    }
  }).catch(err => {
    console.error('Copy failed:', err);
    alert('Failed to copy to clipboard');
  });
}

function saveSettings() {
  const mode = document.getElementById('runMode')?.value || 'local';
  localStorage.setItem('hs_runMode', mode);
  
  if (typeof showFeedback === 'function') {
    showFeedback('✅ Settings saved!');
  } else {
    alert('Settings saved (mode: ' + mode + ')');
  }
}

// Utility functions
function formatNumber(num) {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + 'M';
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K';
  }
  return num.toString();
}

function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

// Add light theme CSS
const lightThemeStyles = `
  .light-theme {
    --bg1: linear-gradient(180deg, #f0f4f8, #e2e8f0);
    --glass-bg: rgba(255,255,255,0.8);
    --glass-border: rgba(0,0,0,0.1);
    --muted: rgba(0,0,0,0.6);
    --accent: #3b82f6;
    --accent2: #8b5cf6;
  }
  
  .light-theme body {
    color: #1e293b;
    background: var(--bg1);
  }
  
  .light-theme .glass-nav {
    background: linear-gradient(180deg,rgba(255,255,255,0.9),rgba(255,255,255,0.8));
    border-bottom: 1px solid rgba(0,0,0,0.1);
  }
  
  .light-theme .glass-card {
    background: rgba(255,255,255,0.9);
    border: 1px solid rgba(0,0,0,0.1);
  }
  
  .light-theme textarea {
    background: rgba(255,255,255,0.95);
    color: #1e293b;
    border: 1px solid rgba(0,0,0,0.1);
  }
  
  .light-theme .nav-link {
    color: rgba(0,0,0,0.7);
  }
  
  .light-theme .nav-link.active,
  .light-theme .nav-link:hover {
    background: rgba(0,0,0,0.05);
    color: #1e293b;
  }
  
  .light-theme .icon-btn {
    background: rgba(255,255,255,0.8);
    border: 1px solid rgba(0,0,0,0.1);
    color: rgba(0,0,0,0.7);
  }
  
  .light-theme .icon-btn:hover {
    background: rgba(255,255,255,1);
  }
  
  .light-theme .outline-btn {
    border: 1px solid rgba(0,0,0,0.2);
    color: rgba(0,0,0,0.7);
  }
  
  .light-theme .outline-btn:hover {
    background: rgba(0,0,0,0.05);
    color: #1e293b;
  }
  
  .light-theme .chip {
    background: rgba(0,0,0,0.05);
    color: rgba(0,0,0,0.7);
  }
  
  .light-theme .chip:hover {
    background: rgba(0,0,0,0.1);
    color: #1e293b;
  }
  
  .light-theme .result-block {
    background: linear-gradient(180deg,rgba(0,0,0,0.02),rgba(0,0,0,0.01));
    border: 1px solid rgba(0,0,0,0.05);
  }
  
  .light-theme .rewritten {
    background: rgba(0,0,0,0.05);
  }
  
  .light-theme .emotion-bar {
    background: rgba(0,0,0,0.05);
  }
  
  .light-theme .emotion-progress {
    background: rgba(0,0,0,0.1);
  }
  
  .light-theme .input-field,
  .light-theme .select-field {
    background: rgba(255,255,255,0.95);
    color: #1e293b;
    border: 1px solid rgba(0,0,0,0.2);
  }
  
  .light-theme code {
    background: rgba(0,0,0,0.1);
  }
`;

// Inject light theme styles
const styleElement = document.createElement('style');
styleElement.textContent = lightThemeStyles;
document.head.appendChild(styleElement);

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    getSettings,
    loadTheme,
    toggleTheme,
    setExampleText,
    copyRewrite,
    saveSettings,
    formatNumber,
    debounce
  };
}