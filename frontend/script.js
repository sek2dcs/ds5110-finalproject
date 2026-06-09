// --- GAME STATE ---
let characters = [
  { name: "Arthur the Butler", emoji: "🤵", status: "alive", persona: "You are intensely loyal and protective.", model: "qwen/qwen3.6-plus" },
  { name: "Beatrice the Widow", emoji: "😭", status: "alive", persona: "You are grieving but secretly relieved.", model: "minimax/minimax-m2.7" },
  { name: "Charles the Doctor", emoji: "🩺", status: "alive", persona: "You are cold, highly analytical, and keep to yourself.", model: "moonshotai/kimi-k2.5" },
  { name: "Diana the Heiress", emoji: "💎", status: "alive", persona: "You are arrogant and dismissive.", model: "openai/gpt-oss-120b:free" },
  { name: "George the Chef", emoji: "👨‍🍳", status: "alive", persona: "You are hot-tempered and fiercely defensive of your kitchen.", model: "z-ai/glm-5" }
];

let gameNotes = { general: "", suspects: {} };
let currentlySelectedSuspect = null;
let currentDay = 1;
let lastVictim = null; // NEW: Tracks the most recent death for the AI's prompt
let gameRoles = { killer: null, detective: null };
let isGameOver = false;
let availableSpeakers = [];
let lastSpeakerName = null;

// --- SETUP & INTRO LOGIC ---
function renderSetupCast() {
  const body = document.getElementById('setupCastBody');
  body.innerHTML = '';
  characters.forEach((char, index) => {
    body.innerHTML += `
      <div style="margin-bottom: 15px; padding-bottom: 15px; border-bottom: 1px solid rgba(255,255,255,0.1);">
        <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
          <label style="font-size: 0.8rem; opacity: 0.7;">Suspect ${index + 1} (${char.model.split('/')[1] || char.model})</label>
          <button class="secondary-btn" style="border-color: #cc0000; color: #cc0000;" onclick="removeCharacter(${index})">Remove</button>
        </div>
        <div style="display: flex; gap: 10px; margin-bottom: 10px;">
          <input type="text" class="setup-input" style="width: 60px; text-align: center;" value="${char.emoji}" onchange="updateChar(${index}, 'emoji', this.value)">
          <input type="text" class="setup-input" style="flex-grow: 1;" value="${char.name}" onchange="updateChar(${index}, 'name', this.value)">
        </div>
        <textarea class="setup-input" style="height: 50px; resize: none;" onchange="updateChar(${index}, 'persona', this.value)">${char.persona}</textarea>
      </div>`;
  });
}

function updateChar(index, field, value) { characters[index][field] = value; }
function addCharacter() { characters.push({ name: "New Suspect", emoji: "👤", status: "alive", persona: "A mysterious newcomer.", model: "qwen/qwen3.6-plus" }); renderSetupCast(); }
function removeCharacter(index) { characters.splice(index, 1); renderSetupCast(); }
function changeTheme() { document.body.className = `theme-${document.getElementById('themeSelector').value}`; }

async function initializeGame() {
  if (characters.length < 3) { alert("You need at least 3 suspects."); return; }
  
  let shuffled = [...characters].sort(() => 0.5 - Math.random());
  gameRoles.killer = shuffled[0].name;
  gameRoles.detective = shuffled[1].name;
  lastVictim = null; // Reset for new game
  characters.forEach(char => gameNotes.suspects[char.name] = "");
  
  document.getElementById('setup-screen').style.display = 'none';
  document.getElementById('introModal').style.display = 'flex';
  changeTheme();

  const textElement = document.getElementById('intro-story-text');
  const btn = document.getElementById('enter-manor-btn');
  let aliveNames = characters.map(c => c.name).join(", ");
  
  textElement.innerHTML = "";
  
  await streamText({
    model: "qwen/qwen3.6-plus",
    max_tokens: 200,
    sys_prompt: "You are the dramatic narrator. Write a thrilling 3-sentence prologue establishing that a tragedy has occurred in the manor, trapping these suspects inside: " + aliveNames,
    user_prompt: "Begin the prologue."
  }, textElement);
  
  btn.style.display = "block";
}

function startDayOne() {
  document.getElementById('introModal').style.display = 'none';
  document.getElementById('game-screen').style.display = 'block';
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
    rosterDiv.innerHTML += `<div class="character-card ${char.status === 'dead' ? 'dead' : ''}"><div class="char-emoji">${char.emoji}</div><div class="char-name">${char.name}</div></div>`;
    statusList.innerHTML += `<li>${char.emoji} <b>${char.name}</b>: <span style="color: ${char.status === 'alive' ? '#43a047' : '#cc0000'}">${char.status.toUpperCase()}</span></li>`;
    suspectGrid.innerHTML += `<div class="mini-card ${char.status === 'dead' ? 'dead' : ''}" id="mini-card-${index}" onclick="selectSuspect('${char.name}', ${index})"><div style="font-size: 1.5rem;">${char.emoji}</div><div style="font-size: 0.85rem; font-weight: bold;">${char.name}</div></div>`;
  });
}

// --- MASTER STREAMING PIPELINE ---
async function streamText(payload, htmlElementContainer, useFallback = false) {
    let success = false;
    let fallbackModel = "qwen/qwen3.6-plus";

    try {
        const response = await fetch("http://localhost:8000/generate-response-stream", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (!response.ok) throw new Error("Stream rejected");

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullText = "";

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            success = true; 

            const chunk = decoder.decode(value, { stream: true });
            fullText += chunk;

            let display = fullText;
            display = display.replace(/<think>[\s\S]*?<\/think>/g, '');
            display = display.replace(/<think>[\s\S]*$/, ''); 

            htmlElementContainer.innerHTML = display;
        }

        if (fullText.trim() === "") throw new Error("Empty response");

    } catch (e) {
        if (!useFallback) {
            htmlElementContainer.innerHTML = "*(Remains silent. The ethereal connection faltered...)*";
        } else {
            console.log(`Model failed. Executing fallback to ${fallbackModel}...`);
            htmlElementContainer.innerHTML = "<em>(Reconnecting...)</em> ";
            payload.model = fallbackModel;
            await streamText(payload, htmlElementContainer, false); 
        }
    }
}

// --- INTERROGATION LOGIC ---
async function triggerNextSpeaker() {
  if (isGameOver) return;
  document.getElementById('speak-btn').disabled = true;
  
  let aliveChars = characters.filter(c => c.status === 'alive');
  if(aliveChars.length === 0) return;
  
  availableSpeakers = availableSpeakers.filter(name => characters.find(c => c.name === name && c.status === 'alive'));
  if (availableSpeakers.length === 0) {
    availableSpeakers = aliveChars.map(c => c.name);
    if (availableSpeakers.length > 1 && lastSpeakerName) {
      availableSpeakers = availableSpeakers.filter(name => name !== lastSpeakerName);
    }
  }

  const randomIndex = Math.floor(Math.random() * availableSpeakers.length);
  const chosenName = availableSpeakers.splice(randomIndex, 1)[0];
  const char = characters.find(c => c.name === chosenName);
  lastSpeakerName = char.name;

  // NEW DAY FILTER: Only read messages from the CURRENT day
  let chatLogs = [];
  document.querySelectorAll(`.chat-bubble[data-day="${currentDay}"]`).forEach(bubble => {
     let header = bubble.querySelector('.chat-header');
     let text = bubble.querySelector('.chat-text');
     if (header && text) chatLogs.push(`${header.innerText.replace(/[\uD800-\uDBFF][\uDC00-\uDFFF]/g, '').trim()}: ${text.innerText}`);
  });
  
  let roomContext = chatLogs.slice(-5).join("\n");
  if (!roomContext) roomContext = "(The room is tense. A new day has dawned. Someone needs to speak first.)";

  // Create the new bubble and assign it the current day tag
  const chatbox = document.getElementById('chatbox');
  const bubble = document.createElement('div');
  bubble.className = 'chat-bubble';
  bubble.setAttribute('data-day', currentDay);
  
  const header = document.createElement('div');
  header.className = 'chat-header';
  header.innerHTML = `${char.name} ${char.emoji}`;
  
  const textContainer = document.createElement('div');
  textContainer.className = 'chat-text';
  textContainer.innerHTML = "<em>...</em>";

  bubble.appendChild(header);
  bubble.appendChild(textContainer);
  chatbox.appendChild(bubble);
  
  let scrollInterval = setInterval(() => { chatbox.scrollTop = chatbox.scrollHeight; }, 100);

  let hiddenRolePrompt = "";
  if (char.name === gameRoles.killer) {
    hiddenRolePrompt = "You are secretly the guilty culprit. Hide your secret, but act slightly defensive.";
  } else if (char.name === gameRoles.detective) {
    hiddenRolePrompt = "You are secretly the hidden investigator. Remember to ask probing questions.";
  } else {
    hiddenRolePrompt = "You are playing an innocent bystander.";
  }

  // NEW DAY INJECTION: Tell the AI who just died
  let dayContext = lastVictim 
    ? `It is now Day ${currentDay}. Last night, ${lastVictim} was eliminated from the game. You are all reacting to this recent death and arguing about who did it.` 
    : `It is Day 1. The manor was just sealed. You are all trapped in the drawing room arguing about who committed the first crime.`;

  const generatedSysPrompt = `You are ${char.name}. ${char.persona} ${hiddenRolePrompt} ${dayContext} Output exactly two things. First: Write a stage direction in brackets (e.g. [Glaring at Beatrice]). Second: Provide your spoken dialogue in exactly one short sentence. React directly to what the other characters just said. Under no circumstances should you explicitly identify yourself as the investigator.`;

  const generatedUserPrompt = `Recent conversation in the room:\n${roomContext}\n\nBased on this, what is your next action and line?`;

  await streamText({
      model: char.model,
      max_tokens: 300,
      sys_prompt: generatedSysPrompt,
      user_prompt: generatedUserPrompt
  }, textContainer, true);

  clearInterval(scrollInterval);
  document.getElementById('speak-btn').disabled = false;
}

// --- WHISPER & SUMMARY LOGIC ---
async function openWhisperModal() { 
  if (isGameOver) return;
  document.getElementById('whisperModal').style.display = 'flex'; 
  document.getElementById('summary-section').style.display = 'none';
  document.getElementById('whisper-input-section').style.display = 'none';
  document.getElementById('whisper-loading').style.display = 'block';

  // NEW DAY FILTER: Summarize ONLY the current day's logs
  let chatLogs = [];
  document.querySelectorAll(`.chat-bubble[data-day="${currentDay}"]`).forEach(bubble => {
     let header = bubble.querySelector('.chat-header');
     let text = bubble.querySelector('.chat-text');
     if (header && text) chatLogs.push(`${header.innerText}: ${text.innerText}`);
  });
  
  let recentLogs = chatLogs.slice(-4).join("\n");
  if (!recentLogs) recentLogs = "The suspects have been entirely silent today.";

  try {
    const response = await fetch("http://localhost:8000/generate-response", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: "qwen/qwen3.6-plus", 
        max_tokens: 60, 
        sys_prompt: "You are a narrator. Summarize the provided dialogue in exactly ONE short, dramatic sentence.",
        user_prompt: "Dialogue:\n" + recentLogs
      })
    });
    const data = await response.json();
    let summaryText = data.response ? data.response.replace(/<think>[\s\S]*?<\/think>/g, '').trim() : "The events remain clouded.";
    document.getElementById('summary-section').innerHTML = `<b>Day ${currentDay} Summary:</b><br>${summaryText}`;
  } catch (e) {
    document.getElementById('summary-section').innerHTML = "<b>Day Summary:</b><br>The events remain clouded in mystery.";
  }

  document.getElementById('whisper-loading').style.display = 'none';
  document.getElementById('summary-section').style.display = 'block';
  document.getElementById('whisper-input-section').style.display = 'block';
}

function closeWhisperModal() { document.getElementById('whisperModal').style.display = 'none'; }

async function submitWhisper() {
  const text = document.getElementById('god-whisper-text').value;
  if(!text) return;
  
  closeWhisperModal();
  const chatbox = document.getElementById('chatbox');
  chatbox.innerHTML += `<div class="whisper-bubble">Divine Whisper to Investigator: "${text}"</div>`;
  chatbox.scrollTop = chatbox.scrollHeight;

  document.getElementById('speak-btn').disabled = true;
  document.getElementById('whisper-btn').disabled = true;

  let aliveNames = characters.filter(c => c.status === 'alive').map(c => c.name);
  let detectiveChar = characters.find(c => c.name === gameRoles.detective);

  const bubble = document.createElement('div');
  bubble.className = 'sys-bubble';
  bubble.style.background = 'rgba(255,255,255,0.1)';
  bubble.style.borderColor = 'white';
  bubble.style.color = 'white';
  bubble.innerHTML = `<em>The Investigator is pondering...</em>`;
  chatbox.appendChild(bubble);

  try {
    const response = await fetch("http://localhost:8000/generate-response", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: "moonshotai/kimi-k2.5", 
        max_tokens: 30, 
        sys_prompt: `You are ${detectiveChar.name}, the hidden investigator. You heard a hint: "${text}". Choose exactly ONE name from this list to accuse: ${aliveNames.join(", ")}. Output ONLY the exact name. No punctuation.`,
        user_prompt: "Who do you formally accuse?"
      })
    });

    const data = await response.json();
    let aiAccusedName = data.response ? data.response.replace(/<think>[\s\S]*?<\/think>/g, '').replace(/[^a-zA-Z ]/g, "").trim() : "";

    if (!aliveNames.includes(aiAccusedName)) {
        const fallbackResponse = await fetch("http://localhost:8000/generate-response", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              model: "qwen/qwen3.6-plus", 
              max_tokens: 15, 
              sys_prompt: `You are the investigator. You heard a hint: "${text}". Choose exactly ONE name from this list: ${aliveNames.join(", ")}. Output ONLY the name.`,
              user_prompt: "Who do you formally accuse?"
            })
        });
        const fallbackData = await fallbackResponse.json();
        aiAccusedName = fallbackData.response ? fallbackData.response.replace(/[^a-zA-Z ]/g, "").trim() : aliveNames[Math.floor(Math.random() * aliveNames.length)];
    }

    if (!aliveNames.includes(aiAccusedName)) aiAccusedName = aliveNames[0];

    bubble.innerHTML = `<b>The Investigator formally accuses ${aiAccusedName}!</b>`;
    evaluateAccusation(aiAccusedName);

  } catch (error) {
    bubble.innerHTML = `Backend unreachable. Cannot process accusation.`;
    document.getElementById('speak-btn').disabled = false;
    document.getElementById('whisper-btn').disabled = false;
  }
  document.getElementById('god-whisper-text').value = '';
}

function evaluateAccusation(accusedName) {
  const chatbox = document.getElementById('chatbox');
  
  if (accusedName === gameRoles.killer) {
    chatbox.innerHTML += `<div class="sys-bubble" style="border-color: #43a047; color: #43a047; background: rgba(67, 160, 71, 0.15);"><b>SIMULATION WON!</b><br>The Investigator successfully exposed ${accusedName} as the culprit!</div>`;
    endGame();
    generateEpilogue(true, accusedName, null);
    return;
  }

  let potentialVictims = characters.filter(c => c.status === 'alive' && c.name !== gameRoles.killer);
  
  if (potentialVictims.length > 0) {
    let victim = potentialVictims[Math.floor(Math.random() * potentialVictims.length)];
    
    setTimeout(() => {
      victim.status = 'dead';
      lastVictim = victim.name; // NEW: Save the victim's name for tomorrow's AI prompt
      currentDay++;

      if (victim.name === gameRoles.detective) {
        chatbox.innerHTML += `<div class="sys-bubble">NIGHT FALLS...<br>Morning arrives. The culprit has struck again.<br><br><b>SIMULATION LOST!</b><br>The hidden investigator, ${victim.name}, was eliminated by ${gameRoles.killer}!</div>`;
        endGame();
        generateEpilogue(false, accusedName, victim.name);
      } else {
        chatbox.innerHTML += `<div class="sys-bubble">NIGHT FALLS...<br>Morning arrives (Day ${currentDay}). The accusation was wrong. The culprit remains free.<br><br>${victim.name} has been eliminated.</div>`;
        updateGameUI();
        document.getElementById('speak-btn').disabled = false;
        document.getElementById('whisper-btn').disabled = false;
      }
      chatbox.scrollTop = chatbox.scrollHeight;
    }, 2500);
  }
}

async function generateEpilogue(won, accusedName, victimName) {
  const chatbox = document.getElementById('chatbox');
  
  const bubble = document.createElement('div');
  bubble.className = 'whisper-bubble';
  bubble.style.textAlign = 'left';
  bubble.style.fontStyle = 'italic';
  bubble.innerHTML = "<b>The Final Truth:</b><br><br>";
  
  const textContainer = document.createElement('span');
  bubble.appendChild(textContainer);
  chatbox.appendChild(bubble);

  let scrollInterval = setInterval(() => { chatbox.scrollTop = chatbox.scrollHeight; }, 100);

  let prompt = won 
    ? `The game is over. The investigator caught the guilty culprit, ${gameRoles.killer}. Write a dramatic 2-sentence epilogue revealing exactly WHY ${gameRoles.killer} committed the crime, and how they reacted to being caught.`
    : `The culprit won. The culprit, ${gameRoles.killer}, successfully eliminated the hidden investigator, ${victimName}, and escaped. Write a dramatic 2-sentence epilogue revealing exactly WHY ${gameRoles.killer} committed the crime, and how they vanished into the night.`;

  await streamText({
      model: "qwen/qwen3.6-plus",
      max_tokens: 150, 
      sys_prompt: "You are the dramatic narrator of a mystery play. Respond directly with the story. Do not explain yourself.",
      user_prompt: prompt
  }, textContainer, true);

  clearInterval(scrollInterval);
}

function endGame() {
  isGameOver = true;
  document.getElementById('speak-btn').disabled = true;
  document.getElementById('whisper-btn').disabled = true;
  document.getElementById('speak-btn').style.opacity = 0.5;
  document.getElementById('whisper-btn').style.opacity = 0.5;
  updateGameUI();
}

// --- NOTEBOOK LOGIC ---
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
  
  const char = characters.find(c => c.name === name);
  const textarea = document.getElementById('suspect-notes');
  document.getElementById('selected-suspect-name').innerText = `Notes on: ${name}`;
  document.getElementById('selected-suspect-persona').innerText = `"${char.persona}"`;
  
  textarea.disabled = false;
  textarea.value = gameNotes.suspects[name];
  textarea.oninput = e => gameNotes.suspects[name] = e.target.value;
  textarea.focus();
}

window.onload = renderSetupCast;
