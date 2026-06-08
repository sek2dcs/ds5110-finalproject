import streamlit as st
import ollama
import random
import time

# --- CONFIGURATION ---
MODEL = 'llama3:8b'

ALL_CHARACTERS = [
    "Arthur the Butler", "Beatrice the Widow", "Charles the Doctor", 
    "Diana the Heiress", "Edward the Chauffeur", "Fiona the Maid", "George the Chef"
]

GOD_FLAVORS = {
    "Cosmic Horror": "A maddening whisper from the void echoes in your mind: {suspect} is not what they seem.",
    "Greek Pantheon": "Athena has blessed you with sudden clarity. {suspect} is lying. Pierce their deception.",
    "Divine Wrath": "A blinding light reveals that {suspect} is hiding a dark sin. Press them relentlessly."
}

# --- CELESTIAL THEME CSS ---
st.markdown("""
<style>
    .stApp { background-color: #0b0c10; color: #c5c6c7; }
    h1, h2, h3 { color: #f5d76e; font-family: 'Georgia', serif; text-align: center; }
    .stButton>button { border: 1px solid #f5d76e; color: #f5d76e; background-color: #1f2833; width: 100%; transition: 0.3s; }
    .stButton>button:hover { background-color: #f5d76e; color: #0b0c10; }
    .icon-box { text-align: center; font-size: 2.5rem; padding: 10px; background: #1f2833; border-radius: 10px; border: 1px solid #45a29e; }
    .dead-box { text-align: center; font-size: 2.5rem; padding: 10px; background: #000000; border-radius: 10px; border: 1px solid #ff0000; opacity: 0.5; }
    .active-speaker { font-size: 1.5rem; font-style: italic; color: #66fcf1; background: #1f2833; padding: 20px; border-radius: 10px; border-left: 5px solid #f5d76e; }
</style>
""", unsafe_allow_html=True)

# --- STATE MANAGEMENT ---
if 'game_phase' not in st.session_state:
    st.session_state.game_phase = 'setup'
    st.session_state.players = {}
    st.session_state.transcript = ""
    st.session_state.day = 1
    st.session_state.god_whispers = []
    st.session_state.detective_guess = None

# --- HELPER FUNCTIONS ---
def get_alive_players():
    return {k: v for k, v in st.session_state.players.items() if v['status'] == 'alive'}

def format_prompt(char_name, role, is_detective=False):
    """Generates strict instructions so the LLM doesn't break."""
    base = f"You are {char_name}. "
    if role == 'Killer':
        base += "You are the KILLER. You must lie, deflect, and act innocent. "
    elif is_detective:
        base += "You are the DETECTIVE trying to solve the murder. "
    else:
        base += "You are INNOCENT. Act nervous but honest. "
        
    base += "Respond with ONLY your spoken dialogue. Do not include your name. Keep it to exactly one sentence."
    return base

def stream_llm_response(sys_prompt, user_prompt):
    """Streams the text so characters appear to speak in real time."""
    messages = [
        {'role': 'system', 'content': sys_prompt},
        {'role': 'user', 'content': user_prompt}
    ]
    stream = ollama.chat(model=MODEL, messages=messages, stream=True)
    for chunk in stream:
        yield chunk['message']['content']

def generate_reveal(killer_name):
    """Generates the final confession."""
    sys_prompt = "You are a dramatic narrator. Reveal the murderer's means, motive, and opportunity."
    user_prompt = f"The killer was {killer_name}. Write a short, 3-sentence paragraph explaining how they did it, why they did it, and how they had the opportunity."
    response = ollama.chat(model=MODEL, messages=[{'role': 'system', 'content': sys_prompt}, {'role': 'user', 'content': user_prompt}])
    return response['message']['content']

def detective_accusation(detective_name, alive_names):
    """Forces the detective to make a guess based on the transcript."""
    sys_prompt = f"You are the Detective {detective_name}. Based on the conversation so far, you must guess who the killer is. You can ONLY reply with the exact name of one of these suspects: {', '.join(alive_names)}. No other words."
    user_prompt = f"Transcript:\n{st.session_state.transcript}\n\nWho is the killer?"
    response = ollama.chat(model=MODEL, messages=[{'role': 'system', 'content': sys_prompt}, {'role': 'user', 'content': user_prompt}])
    return response['message']['content'].strip()

# --- UI & GAME FLOW ---
st.title("✨ The Celestial Constabulary ✨")

# 1. SETUP
if st.session_state.game_phase == 'setup':
    st.write("### Forge the Mortals")
    player_count = st.slider("Number of Souls (4-7)", 4, 7, 5)
    god_flavor = st.selectbox("Choose your Divine Aspect", list(GOD_FLAVORS.keys()))
    
    if st.button("Breathe Life into the Game"):
        selected_chars = random.sample(ALL_CHARACTERS, player_count)
        roles = ['Detective', 'Killer'] + ['Innocent'] * (player_count - 2)
        random.shuffle(roles)
        
        for i, char in enumerate(selected_chars):
            st.session_state.players[char] = {'role': roles[i], 'status': 'alive'}
        
        st.session_state.god_flavor = god_flavor
        st.session_state.game_phase = 'prologue'
        st.rerun()

# --- VISUAL HUD (Always shows during the game) ---
if st.session_state.game_phase not in ['setup', 'prologue']:
    st.write(f"### ☀️ Day {st.session_state.day}")
    
    # Render Icons Instead of Chat Boxes
    cols = st.columns(len(st.session_state.players))
    for idx, (char, data) in enumerate(st.session_state.players.items()):
        with cols[idx]:
            if data['status'] == 'alive':
                st.markdown(f"<div class='icon-box'>👤<br><small>{char}</small></div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='dead-box'>💀<br><small>{char}</small></div>", unsafe_allow_html=True)
    
    st.write("---")

    # History Button (Hidden in an expander so it doesn't clutter the UI)
    with st.expander("📜 Scroll of Past Echoes (Conversation History)"):
        st.text(st.session_state.transcript if st.session_state.transcript else "The mortals have not yet spoken.")
    st.write("---")

# 2. PROLOGUE
if st.session_state.game_phase == 'prologue':
    st.markdown("""
    ### 🌑 A Shadow Falls
    Last night, Lord Blackwood was found murdered in his study, struck down in cold blood. 
    The estate is on lockdown. The killer is still among the guests, and if they are not 
    caught, they will strike again tonight. 
    
    *You are the silent God watching from above. Guide the Detective's hand.*
    """)
    if st.button("Begin the Interrogation"):
        st.session_state.game_phase = 'day_interrogation'
        st.rerun()

# 3. DAY PHASE: ONE ROUND OF SPEAKING
elif st.session_state.game_phase == 'day_interrogation':
    alive_players = get_alive_players()
    detective_name = [k for k, v in alive_players.items() if v['role'] == 'Detective'][0]
    suspects = [k for k, v in alive_players.items() if v['role'] != 'Detective']
    
    if st.button("Listen to the Mortals Speak"):
        speaker_container = st.empty() # Placeholder for the active speaker
        
        # A. Detective Speaks First
        sys_p = format_prompt(detective_name, 'Detective', True)
        if st.session_state.god_whispers:
            sys_p += f"\n\nDIVINE KNOWLEDGE: {st.session_state.god_whispers[-1]}"
            
        user_p = f"Transcript so far:\n{st.session_state.transcript}\n\nAsk your question to the suspects."
        
        with speaker_container.container():
            st.markdown(f"**🔍 {detective_name} (The Detective) is speaking...**")
            det_line = st.write_stream(stream_llm_response(sys_p, user_p))
            st.session_state.transcript += f"\nDetective {detective_name}: {det_line}"
            time.sleep(1) # Small pause for dramatic effect

        # B. Suspects Speak Sequentially
        for suspect in suspects:
            sys_p = format_prompt(suspect, st.session_state.players[suspect]['role'])
            user_p = f"Transcript so far:\n{st.session_state.transcript}\n\nAnswer the Detective."
            
            with speaker_container.container():
                st.markdown(f"**👤 {suspect} is speaking...**")
                susp_line = st.write_stream(stream_llm_response(sys_p, user_p))
                st.session_state.transcript += f"\n{suspect}: {susp_line}"
                time.sleep(1)
        
        # C. Detective makes a guess
        speaker_container.empty()
        with st.spinner(f"The Detective is deducing..."):
            guess = detective_accusation(detective_name, suspects)
            st.session_state.detective_guess = guess
            st.session_state.transcript += f"\nDetective's Official Guess for Today: {guess}"
            
        st.session_state.game_phase = 'detective_guess_eval'
        st.rerun()

# 4. DETECTIVE GUESS EVALUATION
elif st.session_state.game_phase == 'detective_guess_eval':
    alive_players = get_alive_players()
    killer_name = [k for k, v in st.session_state.players.items() if v['role'] == 'Killer'][0]
    detective_name = [k for k, v in alive_players.items() if v['role'] == 'Detective'][0]
    
    st.write(f"### The Detective's Deduction")
    st.warning(f"**{detective_name}** officially suspects: **{st.session_state.detective_guess}**")
    
    if st.session_state.detective_guess == killer_name:
        st.success("The Detective guessed correctly! The Killer is cornered!")
        if st.button("See the Killer's Confession"):
            st.session_state.game_phase = 'game_over_win'
            st.rerun()
    else:
        st.error("The Detective was wrong... The Killer remains hidden.")
        if st.button("Intervene (Enter God Phase)"):
            st.session_state.game_phase = 'god_phase'
            st.rerun()

# 5. GOD PHASE
elif st.session_state.game_phase == 'god_phase':
    st.write("### 🌩️ Divine Intervention")
    st.write("Who has incurred your suspicion? Whisper into the Detective's mind.")
    
    alive_suspects = [k for k, v in get_alive_players().items() if v['role'] != 'Detective']
    target = st.selectbox("Select a mortal to frame or investigate:", alive_suspects)
    
    if st.button("Cast Your Whisper"):
        flavor_text = GOD_FLAVORS[st.session_state.god_flavor].format(suspect=target)
        st.session_state.god_whispers.append(flavor_text)
        st.success(f"You whispered: '{flavor_text}'")
        time.sleep(2)
        st.session_state.game_phase = 'night_phase'
        st.rerun()

# 6. NIGHT PHASE
elif st.session_state.game_phase == 'night_phase':
    st.write("### 🌑 Night Falls...")
    if st.button("Let the Killer Strike"):
        with st.spinner("Blood is being spilled..."):
            alive_players = get_alive_players()
            killer_name = [k for k, v in alive_players.items() if v['role'] == 'Killer'][0]
            potential_victims = [k for k in alive_players.keys() if k != killer_name]
            
            # Simple fallback random kill if LLM fails formatting
            victim = random.choice(potential_victims) 
            
            # Try to let LLM pick
            sys_p = f"You are the Killer {killer_name}. Choose one person to murder from this list: {', '.join(potential_victims)}. Reply with ONLY their name."
            user_p = f"Transcript:\n{st.session_state.transcript}\n\nWho do you kill?"
            resp = ollama.chat(model=MODEL, messages=[{'role': 'system', 'content': sys_p}, {'role': 'user', 'content': user_p}])
            choice = resp['message']['content'].strip()
            
            for p in potential_victims:
                if p.lower() in choice.lower():
                    victim = p
                    break
            
            st.session_state.players[victim]['status'] = 'dead'
            
            if st.session_state.players[victim]['role'] == 'Detective':
                st.session_state.game_phase = 'game_over_loss'
            else:
                st.session_state.transcript += f"\n--- SYSTEM: {victim} was murdered in the night. ---"
                st.session_state.day += 1
                st.session_state.game_phase = 'day_interrogation'
        st.rerun()

# 7. GAME OVER SCREENS
elif st.session_state.game_phase == 'game_over_win':
    killer_name = [k for k, v in st.session_state.players.items() if v['role'] == 'Killer'][0]
    st.markdown(f"## ⚖️ JUSTICE IS SERVED")
    st.success(f"**{killer_name}** was the Killer!")
    
    with st.spinner("Extracting confession..."):
        reveal_text = generate_reveal(killer_name)
    st.write("### The Confession (Means, Motive, Opportunity)")
    st.info(reveal_text)
    
    if st.button("Play Again"):
        st.session_state.clear()
        st.rerun()

elif st.session_state.game_phase == 'game_over_loss':
    killer_name = [k for k, v in st.session_state.players.items() if v['role'] == 'Killer'][0]
    st.markdown(f"## 💀 THE GODS WEEP")
    st.error("The Killer murdered the Detective in the night! The mortals are doomed.")
    st.warning(f"The Killer was... **{killer_name}**!")
    
    with st.spinner("Viewing the Killer's triumph..."):
        reveal_text = generate_reveal(killer_name)
    st.write("### How They Got Away With It (Means, Motive, Opportunity)")
    st.info(reveal_text)
    
    if st.button("Play Again"):
        st.session_state.clear()
        st.rerun()
