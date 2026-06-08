import streamlit as st
import ollama
import random
import time

# --- CONFIGURATION & LORE ---
MODEL = 'llama3:8b'

# Expanded pool so every game feels fresh
ALL_CHARACTERS = [
    "Arthur the Butler", "Beatrice the Widow", "Charles the Doctor", 
    "Diana the Heiress", "Edward the Chauffeur", "Fiona the Maid", 
    "George the Chef", "Helen the Governess", "Isaac the Clockmaker", 
    "Josephine the Singer", "Karl the Groundsman", "Lydia the Journalist",
    "Marcus the Mayor", "Nora the Seamstress", "Oliver the Blacksmith",
    "Penelope the Astrologer", "Quentin the Banker", "Rose the Botanist"
]

# Thematic dictionary controlling UI colors, backstory, and God powers
THEMES = {
    "The Omniscient Magistrate": {
        "prologue": "A high-society gala has ended in bloodshed. A prominent guest lies dead in the atrium. The doors are locked. The killer is in the room. As the invisible hand of justice, you must guide the hidden Detective to the truth.",
        "god_prompt": "An undeniable instinct guides your thoughts: {suspect} is lying. Press them relentlessly.",
        "primary": "#2c3e50", "bg": "#f8f9fa", "box": "#ffffff"
    },
    "The Eldritch Watcher": {
        "prologue": "The coastal fog hides a grisly scene. A scholar was found butchered in the old library. As an entity from beyond the veil, you watch the mortals scramble in terror. Nudge the hidden investigator toward the prey.",
        "god_prompt": "A maddening whisper from the void echoes in your mind: {suspect} is masking their guilt. Break them.",
        "primary": "#16a085", "bg": "#eef2f3", "box": "#ffffff"
    },
    "The Olympian": {
        "prologue": "Tragedy strikes the sunlit terraces! A beloved patron has been poisoned with hemlock. As a god of Olympus, you gaze down at the ensuing chaos. Grant clarity to the mortal seeking truth.",
        "god_prompt": "Athena's wisdom pierces the veil of lies. {suspect} is hiding the truth. Uncover it.",
        "primary": "#d35400", "bg": "#fdfefe", "box": "#fcf3cf"
    }
}

# --- STATE MANAGEMENT ---
if 'game_phase' not in st.session_state:
    st.session_state.game_phase = 'setup'
    st.session_state.players = {}
    st.session_state.transcript = ""
    st.session_state.day = 1
    st.session_state.god_whispers = []
    st.session_state.daily_order = []
    st.session_state.speaker_idx = 0

# --- HELPER FUNCTIONS ---
def get_alive_players():
    return {k: v for k, v in st.session_state.players.items() if v['status'] == 'alive'}

def format_prompt(char_name, role):
    base = f"You are {char_name}. "
    if role == 'Killer':
        base += "You are the hidden KILLER. Lie, deflect, and act innocent. "
    elif role == 'Detective':
        base += "You are the hidden DETECTIVE trying to solve the murder. Ask sharp questions or make deductions. "
    else:
        base += "You are INNOCENT. Act nervous but honest. "
    base += "Respond with ONLY your spoken dialogue. Do not include your name. Keep it to exactly one or two sentences."
    return base

def stream_llm_response(sys_prompt, user_prompt):
    messages = [{'role': 'system', 'content': sys_prompt}, {'role': 'user', 'content': user_prompt}]
    stream = ollama.chat(model=MODEL, messages=messages, stream=True)
    for chunk in stream:
        yield chunk['message']['content']
        time.sleep(0.02) # Artificial slow down for readability

# --- UI SETUP & CSS ---
st.set_page_config(layout="centered", page_title="Mystery Sim")

# Inject dynamic theme if selected, else default light mode
active_theme = THEMES.get(st.session_state.get('theme_choice', "The Omniscient Magistrate"))

st.markdown(f"""
<style>
    .stApp {{ background-color: {active_theme['bg']}; color: #333333; font-family: 'Georgia', serif; }}
    h1, h2, h3 {{ color: {active_theme['primary']}; text-align: center; }}
    .player-container {{ display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; margin-bottom: 20px; }}
    .icon-box {{ background: {active_theme['box']}; border: 2px solid {active_theme['primary']}; border-radius: 8px; padding: 10px; width: 120px; text-align: center; font-size: 0.85rem; font-weight: bold; word-wrap: break-word; color: #333333; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); }}
    .dead-box {{ background: #dddddd; border: 2px solid #999999; border-radius: 8px; padding: 10px; width: 120px; text-align: center; font-size: 0.85rem; color: #777777; text-decoration: line-through; opacity: 0.7; }}
    .chat-bubble {{ background: #ffffff; border-left: 4px solid {active_theme['primary']}; padding: 15px; margin-bottom: 10px; border-radius: 5px; box-shadow: 1px 1px 4px rgba(0,0,0,0.05); font-size: 0.95rem; }}
</style>
""", unsafe_allow_html=True)

st.title("⚖️ The Hidden Inquiry")

# --- 1. SETUP PHASE ---
if st.session_state.game_phase == 'setup':
    st.write("### Prepare the Board")
    player_count = st.slider("Number of Suspects (Max 12)", 4, 12, 6)
    theme_choice = st.selectbox("Choose your Divine Aspect", list(THEMES.keys()))
    
    if st.button("Begin the Mystery", use_container_width=True):
        selected_chars = random.sample(ALL_CHARACTERS, player_count)
        roles = ['Detective', 'Killer'] + ['Innocent'] * (player_count - 2)
        random.shuffle(roles) # Roles are completely randomized and hidden
        
        for i, char in enumerate(selected_chars):
            st.session_state.players[char] = {'role': roles[i], 'status': 'alive'}
        
        st.session_state.theme_choice = theme_choice
        st.session_state.game_phase = 'prologue'
        st.rerun()

# --- CONSTANT HUD: PLAYER ROSTER ---
if st.session_state.game_phase != 'setup':
    st.write(f"### Day {st.session_state.day} Roster")
    # Using HTML Flexbox to gracefully wrap up to 12 characters
    html_roster = "<div class='player-container'>"
    for char, data in st.session_state.players.items():
        if data['status'] == 'alive':
            html_roster += f"<div class='icon-box'>👤<br>{char}</div>"
        else:
            html_roster += f"<div class='dead-box'>💀<br>{char}</div>"
    html_roster += "</div><hr>"
    st.markdown(html_roster, unsafe_allow_html=True)

# --- 2. PROLOGUE ---
if st.session_state.game_phase == 'prologue':
    st.markdown(f"<div class='chat-bubble'><em>{active_theme['prologue']}</em></div>", unsafe_allow_html=True)
    if st.button("Step into the Interrogation Room", use_container_width=True):
        st.session_state.game_phase = 'day_interrogation'
        st.rerun()

# --- 3. DAY PHASE (STEP-BY-STEP CHAT) ---
elif st.session_state.game_phase == 'day_interrogation':
    alive_players = get_alive_players()
    
    # Initialize the random speaking order for the day
    if not st.session_state.daily_order:
        st.session_state.daily_order = list(alive_players.keys())
        random.shuffle(st.session_state.daily_order)
        st.session_state.speaker_idx = 0

    # Render Conversation History
    if st.session_state.transcript:
        st.markdown("### Conversation Log")
        for line in st.session_state.transcript.split('\n'):
            if line.strip():
                st.markdown(f"<div class='chat-bubble'>{line}</div>", unsafe_allow_html=True)

    # Step-by-Step Logic
    if st.session_state.speaker_idx < len(st.session_state.daily_order):
        current_speaker = st.session_state.daily_order[st.session_state.speaker_idx]
        
        st.write(f"**Waiting on {current_speaker}...**")
        if st.button(f"Let {current_speaker} Speak", type="primary", use_container_width=True):
            role = st.session_state.players[current_speaker]['role']
            sys_p = format_prompt(current_speaker, role)
            
            # Inject God Whisper if the current speaker happens to be the Detective
            if role == 'Detective' and st.session_state.god_whispers:
                sys_p += f"\n\nDIVINE KNOWLEDGE: {st.session_state.god_whispers[-1]}"
                
            user_p = f"Transcript so far:\n{st.session_state.transcript}\n\nWhat do you say to the group?"
            
            with st.spinner(f"{current_speaker} is formulating their words..."):
                speaker_container = st.empty()
                line = speaker_container.write_stream(stream_llm_response(sys_p, user_p))
                
            st.session_state.transcript += f"\n**{current_speaker}:** {line}"
            st.session_state.speaker_idx += 1
            st.rerun()
    else:
        # Everyone has spoken
        if st.button("The room falls silent. Proceed to Accusations.", use_container_width=True):
            st.session_state.game_phase = 'detective_guess_eval'
            st.rerun()

# --- 4. HIDDEN DETECTIVE EVALUATION ---
elif st.session_state.game_phase == 'detective_guess_eval':
    alive_players = get_alive_players()
    killer_name = [k for k, v in st.session_state.players.items() if v['role'] == 'Killer'][0]
    detective_name = [k for k, v in alive_players.items() if v['role'] == 'Detective'][0]
    suspects = [k for k in alive_players.keys() if k != detective_name]
    
    with st.spinner("The hidden Detective is reviewing the evidence..."):
        sys_p = f"You are the hidden Detective. Based on the transcript, you MUST guess who the killer is. Reply with ONLY the exact name of your top suspect from this list: {', '.join(suspects)}."
        user_p = f"Transcript:\n{st.session_state.transcript}\n\nWho is the killer?"
        guess_resp = ollama.chat(model=MODEL, messages=[{'role': 'system', 'content': sys_p}, {'role': 'user', 'content': user_p}])
        guess = guess_resp['message']['content'].strip()

    st.markdown("### The Accusation")
    st.markdown(f"<div class='chat-bubble'>The hidden Detective has made their official accusation. They suspect: <b>{guess}</b></div>", unsafe_allow_html=True)
    
    if killer_name.lower() in guess.lower():
        st.success("The Detective deduced correctly! The Killer is cornered!")
        if st.button("Reveal the Truth", use_container_width=True):
            st.session_state.game_phase = 'game_over_win'
            st.rerun()
    else:
        st.error("The Detective's guess was incorrect... The Killer remains hidden.")
        if st.button("Intervene before Night Falls (God Phase)", use_container_width=True):
            st.session_state.game_phase = 'god_phase'
            st.rerun()

# --- 5. GOD PHASE ---
elif st.session_state.game_phase == 'god_phase':
    st.write("### 🌩️ Divine Intervention")
    st.write("Even though you do not know who the Detective is, you may plant a seed of suspicion in their mind.")
    
    target = st.selectbox("Select a mortal to point the Detective toward:", list(get_alive_players().keys()))
    
    if st.button("Cast Your Whisper", use_container_width=True):
        flavor_text = active_theme['god_prompt'].format(suspect=target)
        st.session_state.god_whispers.append(flavor_text)
        st.success(f"You whispered into the ether: '{flavor_text}'")
        time.sleep(2)
        st.session_state.game_phase = 'night_phase'
        st.rerun()

# --- 6. NIGHT PHASE ---
elif st.session_state.game_phase == 'night_phase':
    st.write("### 🌑 Night Falls...")
    if st.button("Let the Hidden Killer Strike", use_container_width=True):
        with st.spinner("Blood is being spilled..."):
            alive_players = get_alive_players()
            killer_name = [k for k, v in alive_players.items() if v['role'] == 'Killer'][0]
            potential_victims = [k for k in alive_players.keys() if k != killer_name]
            
            sys_p = f"You are the Killer. Choose one person to murder from this list: {', '.join(potential_victims)}. Reply with ONLY their name."
            user_p = f"Transcript:\n{st.session_state.transcript}\n\nWho do you kill to protect your secret?"
            resp = ollama.chat(model=MODEL, messages=[{'role': 'system', 'content': sys_p}, {'role': 'user', 'content': user_p}])
            choice = resp['message']['content'].strip()
            
            victim = random.choice(potential_victims) # Fallback
            for p in potential_victims:
                if p.lower() in choice.lower():
                    victim = p
                    break
            
            st.session_state.players[victim]['status'] = 'dead'
            
            if st.session_state.players[victim]['role'] == 'Detective':
                st.session_state.game_phase = 'game_over_loss'
            else:
                st.session_state.transcript += f"\n\n--- THE NEXT MORNING ---\n**SYSTEM:** {victim} was found murdered in the night."
                st.session_state.day += 1
                st.session_state.daily_order = [] # Reset order for the new day
                st.session_state.game_phase = 'day_interrogation'
        st.rerun()

# --- 7. ENDING SCREENS ---
elif st.session_state.game_phase in ['game_over_win', 'game_over_loss']:
    killer_name = [k for k, v in st.session_state.players.items() if v['role'] == 'Killer'][0]
    detective_name = [k for k, v in st.session_state.players.items() if v['role'] == 'Detective'][0]
    
    st.markdown("## 🎭 THE CURTAIN FALLS")
    
    if st.session_state.game_phase == 'game_over_loss':
        st.error("The hidden Killer successfully assassinated the hidden Detective in the night! The mortals are doomed.")
    else:
        st.success("Justice has been served!")
        
    st.markdown(f"**The hidden Detective was:** {detective_name}")
    st.markdown(f"**The hidden Killer was:** {killer_name}")
    
    with st.spinner("Extracting the confession..."):
        sys_p = "You are a dramatic narrator. Reveal the murderer's means, motive, and opportunity based on the transcript."
        user_p = f"The killer was {killer_name}. The detective was {detective_name}. Transcript:\n{st.session_state.transcript}\n\nWrite a 3-sentence summary of the crime."
        resp = ollama.chat(model=MODEL, messages=[{'role': 'system', 'content': sys_p}, {'role': 'user', 'content': user_p}])
        
    st.info(resp['message']['content'])
    
    if st.button("Start a New Mystery", use_container_width=True):
        st.session_state.clear()
        st.rerun()
