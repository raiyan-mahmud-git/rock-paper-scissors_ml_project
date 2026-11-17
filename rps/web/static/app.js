// Rock Paper Scissors AI Arena Frontend Controller

const EMOJIS = {
  rock: '🪨',
  paper: '📄',
  scissors: '✂️',
  lizard: '🦎',
  spock: '🖖',
};

// State
let sessionId = localStorage.getItem('rps_session_id') || null;
let currentMode = 'classic';
let currentDiff = 'hard';
let isSoundEnabled = true;
let isPlaying = false;

// Web Audio API Sound Synthesizer (Zero external audio files needed!)
class SoundEffects {
  constructor() {
    this.ctx = null;
  }

  init() {
    if (!this.ctx) {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (AudioCtx) this.ctx = new AudioCtx();
    }
  }

  playTone(freq, type, duration, delay = 0) {
    if (!isSoundEnabled) return;
    this.init();
    if (!this.ctx) return;

    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();

    osc.type = type;
    osc.frequency.setValueAtTime(freq, this.ctx.currentTime + delay);

    gain.gain.setValueAtTime(0.15, this.ctx.currentTime + delay);
    gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + delay + duration);

    osc.connect(gain);
    gain.connect(this.ctx.destination);

    osc.start(this.ctx.currentTime + delay);
    osc.stop(this.ctx.currentTime + delay + duration);
  }

  click() {
    this.playTone(600, 'sine', 0.05);
  }

  throw() {
    this.playTone(300, 'triangle', 0.1);
  }

  win() {
    this.playTone(523.25, 'triangle', 0.12, 0);      // C5
    this.playTone(659.25, 'triangle', 0.12, 0.1);    // E5
    this.playTone(783.99, 'triangle', 0.25, 0.2);    // G5
  }

  loss() {
    this.playTone(350, 'sawtooth', 0.15, 0);
    this.playTone(260, 'sawtooth', 0.25, 0.12);
  }

  tie() {
    this.playTone(440, 'sine', 0.1, 0);
    this.playTone(440, 'sine', 0.15, 0.12);
  }
}

const sounds = new SoundEffects();

// DOM elements
const playerHandCard = document.getElementById('playerHandCard');
const playerHandEmoji = document.getElementById('playerHandEmoji');
const playerChoiceLabel = document.getElementById('playerChoiceLabel');

const aiHandCard = document.getElementById('aiHandCard');
const aiHandEmoji = document.getElementById('aiHandEmoji');
const aiChoiceLabel = document.getElementById('aiChoiceLabel');

const outcomeBadge = document.getElementById('outcomeBadge');
const commentaryText = document.getElementById('commentaryText');
const aiIntelText = document.getElementById('aiIntelText');

const statWins = document.getElementById('statWins');
const statTies = document.getElementById('statTies');
const statLosses = document.getElementById('statLosses');
const currentStreak = document.getElementById('currentStreak');
const bestStreak = document.getElementById('bestStreak');
const winRate = document.getElementById('winRate');

const habitBars = document.getElementById('habitBars');
const historyList = document.getElementById('historyList');

const modeSelector = document.getElementById('modeSelector');
const diffSelector = document.getElementById('diffSelector');
const soundToggle = document.getElementById('soundToggle');
const soundIcon = document.getElementById('soundIcon');
const resetBtn = document.getElementById('resetBtn');
const rulesBtn = document.getElementById('rulesBtn');
const closeRulesBtn = document.getElementById('closeRulesBtn');
const rulesModal = document.getElementById('rulesModal');

// Setup Move Buttons
document.querySelectorAll('.move-btn').forEach((btn) => {
  btn.addEventListener('click', () => {
    const move = btn.dataset.move;
    playMove(move);
  });
});

// Setup Mode Toggle (Classic vs Extended)
modeSelector.querySelectorAll('.pill-btn').forEach((btn) => {
  btn.addEventListener('click', () => {
    modeSelector.querySelectorAll('.pill-btn').forEach((b) => b.classList.remove('active'));
    btn.classList.add('active');
    currentMode = btn.dataset.mode;

    // Show/hide lizard and spock
    const extendedBtns = document.querySelectorAll('.extended-move');
    extendedBtns.forEach((b) => {
      if (currentMode === 'extended') {
        b.classList.remove('hidden');
      } else {
        b.classList.add('hidden');
      }
    });

    sounds.click();
    resetArenaUI();
  });
});

// Setup Difficulty Toggle
diffSelector.querySelectorAll('.pill-btn').forEach((btn) => {
  btn.addEventListener('click', () => {
    diffSelector.querySelectorAll('.pill-btn').forEach((b) => b.classList.remove('active'));
    btn.classList.add('active');
    currentDiff = btn.dataset.diff;
    sounds.click();

    if (currentDiff === 'hard') {
      aiIntelText.innerText = 'Markov Order-2 AI Active';
    } else if (currentDiff === 'medium') {
      aiIntelText.innerText = 'Frequency Decay AI Active';
    } else {
      aiIntelText.innerText = 'Uniform Random AI Active';
    }
  });
});

// Setup Sound Toggle
soundToggle.addEventListener('click', () => {
  isSoundEnabled = !isSoundEnabled;
  soundIcon.innerText = isSoundEnabled ? '🔊' : '🔇';
});

// Setup Rules Modal
rulesBtn.addEventListener('click', () => {
  rulesModal.classList.remove('hidden');
});
closeRulesBtn.addEventListener('click', () => {
  rulesModal.classList.add('hidden');
});
rulesModal.addEventListener('click', (e) => {
  if (e.target === rulesModal) rulesModal.classList.add('hidden');
});

// Setup Reset
resetBtn.addEventListener('click', async () => {
  if (!confirm('Reset your scores and AI session?')) return;
  sounds.click();
  try {
    const res = await fetch('/api/reset', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        difficulty: currentDiff,
        ruleset: currentMode,
      }),
    });
    const data = await res.json();
    sessionId = data.session_id;
    localStorage.setItem('rps_session_id', sessionId);
    updateStats(data.stats);
    historyList.innerHTML = '<div class="empty-history">Scores reset. Make your first throw!</div>';
    resetArenaUI();
  } catch (err) {
    console.error('Reset failed:', err);
  }
});

// Keyboard shortcuts (R, P, S, L, K)
window.addEventListener('keydown', (e) => {
  if (isPlaying) return;
  const key = e.key.toLowerCase();
  const keyMap = {
    r: 'rock',
    p: 'paper',
    s: 'scissors',
    l: currentMode === 'extended' ? 'lizard' : null,
    k: currentMode === 'extended' ? 'spock' : null,
  };
  if (keyMap[key]) {
    playMove(keyMap[key]);
  }
});

function resetArenaUI() {
  playerHandCard.className = 'fighter-card';
  aiHandCard.className = 'fighter-card';
  playerHandEmoji.innerText = '❔';
  aiHandEmoji.innerText = '🤖';
  playerChoiceLabel.innerText = 'Ready...';
  aiChoiceLabel.innerText = 'Predicting...';
  outcomeBadge.className = 'outcome-badge';
  outcomeBadge.innerText = 'CHOOSE YOUR MOVE';
  commentaryText.innerText = 'Select a move below to play.';
}

// Main Play Function
async function playMove(playerMove) {
  if (isPlaying) return;
  isPlaying = true;

  sounds.throw();

  // Animation: shake hands
  playerHandCard.className = 'fighter-card';
  aiHandCard.className = 'fighter-card';
  playerHandEmoji.innerText = '✊';
  aiHandEmoji.innerText = '✊';
  playerChoiceLabel.innerText = 'Throwing...';
  aiChoiceLabel.innerText = 'Throwing...';
  outcomeBadge.className = 'outcome-badge';
  outcomeBadge.innerText = '3... 2... 1...';

  try {
    const response = await fetch('/api/play', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        move: playerMove,
        difficulty: currentDiff,
        ruleset: currentMode,
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    sessionId = data.session_id;
    localStorage.setItem('rps_session_id', sessionId);

    // Brief delay for dramatic suspense
    await new Promise((r) => setTimeout(r, 400));

    // Reveal choices
    playerHandEmoji.innerText = EMOJIS[data.player_move] || '❓';
    playerChoiceLabel.innerText = data.player_move;

    aiHandEmoji.innerText = EMOJIS[data.computer_move] || '❓';
    aiChoiceLabel.innerText = data.computer_move;

    // Apply outcome classes & sounds
    outcomeBadge.className = `outcome-badge ${data.outcome}`;
    if (data.outcome === 'win') {
      outcomeBadge.innerText = 'YOU WIN!';
      playerHandCard.classList.add('active-win');
      aiHandCard.classList.add('active-loss');
      sounds.win();
    } else if (data.outcome === 'lose') {
      outcomeBadge.innerText = 'AI WINS!';
      playerHandCard.classList.add('active-loss');
      aiHandCard.classList.add('active-win');
      sounds.loss();
    } else {
      outcomeBadge.innerText = 'DRAW / TIE!';
      playerHandCard.classList.add('active-tie');
      aiHandCard.classList.add('active-tie');
      sounds.tie();
    }

    commentaryText.innerText = data.commentary;
    if (data.ai_status) {
      aiIntelText.innerText = data.ai_status;
    }

    // Update scoreboard & analytics
    updateStats(data.stats);
    addHistoryItem(data);
  } catch (err) {
    console.error('Play error:', err);
    outcomeBadge.innerText = 'Error';
    commentaryText.innerText = 'Could not contact server. Please retry.';
  } finally {
    isPlaying = false;
  }
}

function updateStats(stats) {
  statWins.innerText = stats.rounds_won;
  statLosses.innerText = stats.rounds_lost;
  statTies.innerText = stats.rounds_tied;
  currentStreak.innerText = stats.current_streak;
  bestStreak.innerText = stats.best_streak;
  winRate.innerText = `${stats.win_rate}%`;

  // Update Move habits breakdown
  renderHabits(stats.move_counts, stats.rounds_played);
}

function renderHabits(counts, total) {
  habitBars.innerHTML = '';
  const moves = currentMode === 'extended' 
    ? ['rock', 'paper', 'scissors', 'lizard', 'spock'] 
    : ['rock', 'paper', 'scissors'];

  moves.forEach((m) => {
    const count = counts[m] || 0;
    const pct = total > 0 ? Math.round((count / total) * 100) : 0;

    const row = document.createElement('div');
    row.className = 'habit-row';
    row.innerHTML = `
      <span class="habit-label">${EMOJIS[m]} ${m}</span>
      <div class="habit-track">
        <div class="habit-fill" style="width: ${pct}%"></div>
      </div>
      <span class="habit-count">${count}</span>
    `;
    habitBars.appendChild(row);
  });
}

function addHistoryItem(data) {
  const empty = historyList.querySelector('.empty-history');
  if (empty) empty.remove();

  const item = document.createElement('div');
  item.className = 'history-item';
  const playerEmoji = EMOJIS[data.player_move] || '';
  const aiEmoji = EMOJIS[data.computer_move] || '';

  const outcomeClass = data.outcome === 'win' ? 'win' : data.outcome === 'lose' ? 'loss' : 'tie';
  const outcomeText = data.outcome.toUpperCase();

  item.innerHTML = `
    <div class="history-meta">
      <span class="history-badge ${outcomeClass}">${outcomeText}</span>
      <span>Round ${data.stats.rounds_played}: You played ${playerEmoji} vs AI ${aiEmoji}</span>
    </div>
    <span style="color: var(--text-muted); font-size: 0.8rem;">${data.commentary}</span>
  `;

  historyList.insertBefore(item, historyList.firstChild);
}

// Initial habits render
renderHabits({}, 0);
