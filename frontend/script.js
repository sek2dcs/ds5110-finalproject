// --- GAME STATE ---
let characters = [
  { name: "Arthur the Butler", emoji: "🤵", status: "alive", persona: "You are intensely loyal and protective." },
  { name: "Beatrice the Widow", emoji: "😭", status: "alive", persona: "You are grieving but secretly relieved." },
  { name: "Charles the Doctor", emoji: "🩺", status: "alive", persona: "You are cold, analytical, and in debt." },
  { name: "Diana the Heiress", emoji: "💎", status: "alive", persona: "You are arrogant and dismissive." },
  { name: "George the Chef", emoji: "👨‍🍳", status: "alive", persona: "You are hot-tempered and fiercely defensive of your kitchen." }
];

let gameNotes = { general: "", suspects: {} };
let currentlySelectedSuspect = null;
let currentDay = 1;

// Win/Loss & Speaking Logic Trackers
let gameRoles = { killer: null, detective: null };
let isGameOver = false;
let availableSpeakers = [];
let lastSpeakerName = null;

// --- SETUP SCREEN LOGIC ---
function renderSetupCast() {
  const body = document.getElementById('setupCastBody');
  body.innerHTML = '';
  
  characters.forEach((char, index) => {
    body.innerHTML += `
      <div style="margin-bottom: 15px; padding-bottom: 15px; border-bottom: 1px solid rgba(255,255,255,0.1);">
        <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
          <label style="font-size: 0.8rem; opacity: 0.7;">Suspect ${index + 1}</label>
          <button class="secondary-btn" style="border-color: #cc0000; color: #cc0000;" onclick="removeCharacter(${index})">Remove</button>
        </div>
        <div style="display: flex; gap: 10px; margin-bottom: 10px;">
          <input type="text" class="setup-input" style="width: 60px; text-align: center;" value="${char.emoji}" onchange="updateChar(${index}, 'emoji', this.value)">
          <input type="text" class="setup-input" style="flex-grow: 1;" value="${char.name}" onchange="updateChar(${index}, 'name', this.value)">
        </div>
        <textarea class="setup-input" style="height: 50px; resize: none;" onchange="updateChar(${index}, 'persona', this.value)">${char.persona}</textarea>
      </div>
    `;
  });
}

function updateChar(index, field, value) { characters[index][field] = value; }

function addCharacter() {
  characters.push({ name: "New Suspect", emoji: "👤", status: "alive", persona: "A mysterious newcomer." });
  renderSetupCast();
}

function removeCharacter(index) {
  characters.splice(index, 1);
  renderSetupCast();
}

function changeTheme() {
  const theme = document.getElementById('themeSelector').value;
  document.body.className = `theme-${theme}`;
}

// --- GAME INITIALIZATION ---
function startGame() {
  if (characters.length < 3) { alert("You need at least 3 suspects to run a simulation."); return; }
  
  // Assign Hidden Roles randomly
  let shuffled = [...characters].sort(() => 0.5 - Math.random());
  gameRoles.killer = shuffled[0].name;
  gameRoles.detective = shuffled[1].name;
  
  characters.forEach(char => gameNotes.suspects[char.name] = "");
  
  document.getElementById('setup-screen').style.display = 'none';
  document.getElementById('game-screen').style.display = 'block';
  changeTheme();
  updateGameUI();
}

function updateGameUI() {
  if (isGameOver) return;
  document.getElementById('day-counter').innerText = `Day ${currentDay}: The manor is sealed.`;
  
  const rosterDiv = document.getElementById('roster');
  const suspectGrid = document.getElementById('suspect-grid');
  const statusList = document.getElementById('status-list');

  rosterDiv.innerHTML = ''; suspectGrid.innerHTML = ''; statusList.innerHTML = '';

  characters.forEach((char, index) => {
    rosterDiv.innerHTML += `
      <div class="character-card ${char.status === 'dead' ? 'dead' : ''}">
        <div class="char-emoji">${char.emoji}</div>
        <div class="char-name">${char.name}</div>
      </div>`;

    statusList.innerHTML += `<li>${char.emoji} <b>${char.name}</b>: <span style="color: ${char.status === 'alive' ? '#43a047' : '#cc0000'}">${char.status.toUpperCase()}</span></li>`;

    suspectGrid.innerHTML += `
      <div class="mini-card ${char.status === 'dead' ? 'dead' : ''}" id="mini-card-${index}" onclick="selectSuspect('${char.name}', ${index})">
        <div style="font-size: 1.5rem;">${char.emoji}</div>
        <div style="font-size: 0.85rem; font-weight: bold;">${char.name}</div>
      </div>`;
  });
}

// --- NIGHT PROGRESSION & ACCUSATIONS ---
function openWhisperModal() { 
  if (isGameOver) return;
  document.getElementById('whisperModal').style.display = 'flex'; 
}

function closeWhisperModal() { document.getElementById('whisperModal').style.display = 'none'; }

async function submitWhisper() {
  const text = document.getElementById('god-whisper-text').value;
  if(!text) return;
  
  closeWhisperModal();
  const chatbox = document.getElementById('chatbox');
  
  // 1. Post the Whisper to the UI
  chatbox.innerHTML += `<div class="whisper-bubble">Divine Whisper to Detective: "${text}"</div>`;
  chatbox.scrollTop = chatbox.scrollHeight;

  // Temporarily disable buttons while AI thinks
  document.getElementById('speak-btn').disabled = true;
  document.getElementById('whisper-btn').disabled = true;

  // 2. Ask the AI Detective who they accuse based on the whisper
  let aliveNames = characters.filter(c => c.status === 'alive').map(c => c.name);
  let detectiveChar = characters.find(c => c.name === gameRoles.detective);

  chatbox.innerHTML += `<div class="chat-bubble" id="pondering-bubble"><em>The Detective is pondering your whisper and preparing an accusation...</em></div>`;
  chatbox.scrollTop = chatbox.scrollHeight;

  try {
    const response = await fetch("http://localhost:8000/generate-response", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: "qwen/qwen3.6-plus",
        sys_prompt: `You are ${detectiveChar.name}, the hidden detective in a murder mystery. You just heard a divine whisper in your mind: "${text}". Based on this whisper and your own intuition, you must make a formal accusation. Choose exactly ONE name from this list of alive suspects: ${aliveNames.join(", ")}. You MUST output ONLY the exact name. Do not include any punctuation, explanations, or extra words. Under no circumstances should you explicitly identify yourself as the detective.`,
        user_prompt: "Who do you formally accuse?"
      })
    });

    const data = await response.json();
    let aiAccusedName = data.response.trim();

    // Fallback just in case the AI hallucinates a name not on the list
    if (!aliveNames.includes(aiAccusedName)) {
        aiAccusedName = aliveNames[Math.floor(Math.random() * aliveNames.length)];
    }

    // Remove the pondering text
    document.getElementById('pondering-bubble').remove(); 
    
    // Announce the AI's decision
    chatbox.innerHTML += `<div class="sys-bubble" style="background: rgba(255,255,255,0.1); border-color: white; color: white;"><b>The Detective formally accuses ${aiAccusedName}!</b></div>`;
    
    // 3. Evaluate the AI's choice
    evaluateAccusation(aiAccusedName);

  } catch (error) {
    chatbox.innerHTML += `<span class="sys-bubble">Backend unreachable. Cannot process accusation. Ensure Python server is running.</span>`;
    document.getElementById('speak-btn').disabled = false;
    document.getElementById('whisper-btn').disabled = false;
  }
  
  document.getElementById('god-whisper-text').value = '';
}

function evaluateAccusation(accusedName) {
  const chatbox = document.getElementById('chatbox');
  
  // Win Condition
  if (accusedName === gameRoles.killer) {
    chatbox.innerHTML += `<div class="sys-bubble" style="border-color: #43a047; color: #43a047; background: rgba(67, 160, 71, 0.15);"><b>SIMULATION WON!</b><br>The Detective successfully exposed ${accusedName} as the killer!</div>`;
    endGame();
    return;
  }

  // Loss/Continue Condition: If wrong, the Killer strikes
  let potentialVictims = characters.filter(c => c.status === 'alive' && c.name !== gameRoles.killer);
  
  if (potentialVictims.length > 0) {
    let victim = potentialVictims[Math.floor(Math.random() * potentialVictims.length)];
    victim.status = 'dead';
    currentDay++;
    
    setTimeout(() => {
      if (victim.name === gameRoles.detective) {
        chatbox.innerHTML += `<div class="sys-bubble">NIGHT FALLS...<br>Morning arrives. The killer has struck again.<br><br><b>SIMULATION LOST!</b><br>The hidden Detective, ${victim.name}, was murdered by ${gameRoles.killer}!</div>`;
        endGame();
      } else {
        chatbox.innerHTML += `<div class="sys-bubble">NIGHT FALLS...<br>Morning arrives (Day ${currentDay}). The accusation was wrong. The killer remains free.<br><br>${victim.name} has been found dead.</div>`;
        updateGameUI();
        // Re-enable buttons for the next day
        document.getElementById('speak-btn').disabled = false;
        document.getElementById('whisper-btn').disabled = false;
      }
      chatbox.scrollTop = chatbox.scrollHeight;
    }, 2500);
  }
}

function endGame() {
  isGameOver = true;
  document.getElementById('speak-btn').disabled = true;
  document.getElementById('whisper-btn').disabled = true;
  document.getElementById('speak-btn').style.opacity = 0.5;
  document.getElementById('whisper-btn').style.opacity = 0.5;
  updateGameUI();
}

// --- BACKEND AI LOGIC ---
async function triggerNextSpeaker() {
  if (isGameOver) return;
  
  let aliveChars = characters.filter(c => c.status === 'alive');
  if(aliveChars.length === 0) return;
  
  // Clean dead characters out of the speaker bag
  availableSpeakers = availableSpeakers.filter(name => characters.find(c => c.name === name && c.status === 'alive'));

  // If the bag is empty, refill it with everyone who is alive
  if (availableSpeakers.length === 0) {
    availableSpeakers = aliveChars.map(c => c.name);
    // Prevent the last person to speak from immediately speaking again in the new round
    if (availableSpeakers.length > 1 && lastSpeakerName) {
      availableSpeakers = availableSpeakers.filter(name => name !== lastSpeakerName);
    }
  }

  // Draw a random character from the bag
  const randomIndex = Math.floor(Math.random() * availableSpeakers.length);
  const chosenName = availableSpeakers.splice(randomIndex, 1)[0];
  const char = characters.find(c => c.name === chosenName);
  
  lastSpeakerName = char.name;

  const chatbox = document.getElementById('chatbox');
  const bubble = document.createElement('div');
  bubble.className = 'chat-bubble';
  bubble.innerHTML = `<em>${char.name} is speaking...</em>`;
  chatbox.appendChild(bubble);
  chatbox.scrollTop = chatbox.scrollHeight;

  // Inject hidden roles into the AI prompt
  let hiddenRolePrompt = "";
  if (char.name === gameRoles.killer) {
    hiddenRolePrompt = "You are secretly the KILLER. Hide your guilt, but exhibit subtle suspicious behavior.";
  } else if (char.name === gameRoles.detective) {
    hiddenRolePrompt = "You are secretly the DETECTIVE investigating the murders. Remember to ask probing questions.";
  } else {
    hiddenRolePrompt = "You are an INNOCENT suspect.";
  }

  try {
    const response = await fetch("http://localhost:8000/generate-response", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: "qwen/qwen3.6-plus",
        sys_prompt: `You are ${char.name}. ${char.persona} ${hiddenRolePrompt} You are a character in a murder mystery. Provide ONLY the spoken dialogue. Do not include stage directions, actions, descriptions of your behavior, or narrative prose. Speak in exactly one sentence. Under no circumstances should you explicitly identify yourself as the detective.`,
        user_prompt: "What is your next line?"
      })
    });

    const data = await response.json();
    bubble.innerHTML = `<div class="chat-header">${char.name} ${char.emoji}</div><div class="chat-text">${data.response}</div>`;
    chatbox.scrollTop = chatbox.scrollHeight;
  } catch (error) {
    bubble.innerHTML = `<span class="sys-bubble">Backend unreachable. Ensure your Python server is running.</span>`;
  }
}

// --- NOTEBOOK TABS LOGIC ---
function openNotebook() { 
  document.getElementById('notebookOverlay').style.display = 'flex'; 
  document.getElementById('general-notes').value = gameNotes.general;
  document.getElementById('general-notes').oninput = e => gameNotes.general = e.target.value;
}
function closeNotebook() { document.getElementById('notebookOverlay').style.display = 'none'; }

function switchTab(tabName) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  event.target.classList.add('active');
  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
  document.getElementById(`tab-${tabName}`).classList.add('active');
}

function selectSuspect(name, index) {
  currentlySelectedSuspect = name;
  document.querySelectorAll('.mini-card').forEach(c => c.classList.remove('active'));
  document.getElementById(`mini-card-${index}`).classList.add('active');
  
  const textarea = document.getElementById('suspect-notes');
  document.getElementById('selected-suspect-name').innerText = `Notes on: ${name}`;
  textarea.disabled = false;
  textarea.value = gameNotes.suspects[name];
  textarea.oninput = e => gameNotes.suspects[name] = e.target.value;
  textarea.focus();
}

window.onload = renderSetupCast;
