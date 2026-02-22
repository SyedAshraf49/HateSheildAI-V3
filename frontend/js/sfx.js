(function () {
  let audioCtx = null;

  function getSettings() {
    try {
      return JSON.parse(localStorage.getItem('hs_settings') || '{}');
    } catch (e) {
      return {};
    }
  }

  function isEnabled() {
    const settings = getSettings();
    return settings.soundEffects === true;
  }

  function ensureContext() {
    if (!audioCtx) {
      const Ctx = window.AudioContext || window.webkitAudioContext;
      if (!Ctx) return null;
      audioCtx = new Ctx();
    }
    if (audioCtx.state === 'suspended') {
      audioCtx.resume();
    }
    return audioCtx;
  }

  function playTone(freq, durationMs, gainValue) {
    if (!isEnabled()) return;
    const ctx = ensureContext();
    if (!ctx) return;

    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'sine';
    osc.frequency.value = freq;

    gain.gain.value = gainValue;
    osc.connect(gain);
    gain.connect(ctx.destination);

    const durationSec = durationMs / 1000;
    const endTime = ctx.currentTime + durationSec;
    gain.gain.exponentialRampToValueAtTime(0.0001, endTime);

    osc.start();
    osc.stop(endTime);
  }

  function playSfx(type) {
    if (!isEnabled()) return;

    switch (type) {
      case 'success':
        playTone(523.25, 90, 0.08);
        setTimeout(() => playTone(659.25, 110, 0.08), 90);
        break;
      case 'error':
        playTone(220, 120, 0.1);
        setTimeout(() => playTone(196, 140, 0.1), 110);
        break;
      case 'warning':
        playTone(330, 120, 0.08);
        break;
      case 'toggle':
        playTone(392, 80, 0.06);
        break;
      case 'click':
      default:
        playTone(440, 60, 0.05);
        break;
    }
  }

  window.playSfx = playSfx;
})();
