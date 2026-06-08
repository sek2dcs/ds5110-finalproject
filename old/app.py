import streamlit as st
import ollama
import random

# --- CONFIGURATION & PROMPTS ---
MODEL = 'llama3:8b'

ALL_CHARACTERS = [
    "Arthur the Butler", "Beatrice the Widow", "Charles the Doctor", 
    "Diana the Heiress", "Edward the Chauffeur", "Fiona the Maid", "George the Chef"
]

GOD_FLAVORS = {
    "Old Testament": "A burning bush has revealed that {suspect} is hiding a dark sin. Press them relentlessly.",
    "Cosmic Horror": "A maddening whisper from the void echoes in your mind: {suspect} is not what they seem.",
    "Greek Pantheon": "Athena has blessed you with sudden clarity. {suspect} is lying. Pierce their deception."
}

# --- STATE MANAGEMENT ---
# Streamlit reruns from top to bottom every time a button is clicked. 
# We use session_state to remember the game data between clicks.
if 'game_phase' not in st.session_state:
    st.session_state.game_phase = 'setup'
    st.session_state.players = {}
    st.session_state.transcript = []
    st.session_state.day = 1
    st.session_state.god_whispers = []

# --- HELPER FUNCTIONS (THE SECRETARY) ---
def generate_response(system_prompt, role_name):
    """Packages the transcript and sends it to Ollama."""
    messages = [{'role': 'system', 'content': system_prompt}] + st.session_state.transcript
    response = ollama.chat(model=MODEL, messages=messages)
    return response['message']['content']

def night_phase_kill(killer_name, alive_targets):
    """A secret, isolated API call just for the killer to pick a victim."""
    system_instruction = f"""
    You are {killer_name}. You are the secret murderer. 
    It is night time. Here is the list of people still alive: {', '.join(alive_targets)}.
    Reply with ONLY the exact name of the person you want to kill tonight. No other words.
    """
    # Notice we give them the transcript so they know who has been suspicious!
    messages = [{'role': 'system', 'content': system_instruction}] + st.session_state.transcript
    response = ollama.chat(model=MODEL, messages=messages)
    
    # Clean up the output to try and match a name exactly
    choice = response['message']['content'].strip()
    return choice

# --- UI & GAME FLOW ---
st.title("🕵️‍♂️ LLM Murder Mystery: Voice of God")

# PHASE 1: SETUP
if st.session_state.game_phase == 'setup':
    st.header("Configure the Game")
    
    player_count = st.slider("Number of Players (including Detective & Killer)", min_value=4, max_value=7, value=5)
    god_flavor = st.selectbox("Choose your Divine Denomination", options=list(GOD_FLAVORS.keys()))
    
    if st.button("Start Game"):
        # Assign Roles
        selected_chars = random.sample(ALL_CHARACTERS, player_count)
        roles = ['Detective', 'Killer'] + ['Innocent'] * (player_count - 2)
        random.shuffle(roles)
        
        for i, char in enumerate(selected_chars):
            st.session_state.players[char] = {
                'role': roles[i],
                'status': 'alive'
            }
        
        st.session_state.god_flavor = god_flavor
        st.session_state.game_phase = 'day_interrogation'
        st.rerun()

# PHASE 2 & 3: GAME LOOP
if st.session_state.game_phase != 'setup':
    
    # --- Sidebar: Game Status ---
    with st.sidebar:
        st.header(f"Day {st.session_state.day}")
        st.subheader("Player Status")
        for char, data in st.session_state.players.items():
            icon = "💀" if data['status'] == 'dead' else "👤"
            role_hint = f" ({data['role']})" if data['role'] in ['Detective', 'Killer'] else ""
            st.write(f"{icon} {char}{role_hint}")
            
    # --- Main Screen: The Master Transcript ---
    st.header("The Interrogation Room")
    for msg in st.session_state.transcript:
        if msg['role'] == 'assistant':
            st.info(msg['content'])
        else:
            st.warning(msg['content'])

    # --- Day Phase: Let the LLMs talk ---
    if st.session_state.game_phase == 'day_interrogation':
        if st.button("Run Next Interrogation Round"):
            with st.spinner("The AI characters are speaking..."):
                alive_players = {k: v for k, v in st.session_state.players.items() if v['status'] == 'alive'}
                detective_name = [k for k, v in alive_players.items() if v['role'] == 'Detective'][0]
                suspects = [k for k, v in alive_players.items() if v['role'] != 'Detective']
                
                # 1. Detective Speaks
                det_sys = f"You are {detective_name}, a brilliant detective. Ask a sharp question to the group. Keep it to one sentence."
                if st.session_state.god_whispers:
                    det_sys += f"\n\nSECRET INFO: {st.session_state.god_whispers[-1]}"
                
                det_line = generate_response(det_sys, detective_name)
                st.session_state.transcript.append({'role': 'user', 'content': f"{detective_name} (Detective): {det_line}"})
                
                # 2. Suspects Reply
                for suspect in suspects:
                    role = st.session_state.players[suspect]['role']
                    if role == 'Killer':
                        susp_sys = f"You are {suspect}. You are the KILLER. Deflect, lie, and cast suspicion on someone else. One sentence only."
                    else:
                        susp_sys = f"You are {suspect}. You are innocent. Answer the detective nervously but honestly. One sentence only."
                    
                    susp_line = generate_response(susp_sys, suspect)
                    st.session_state.transcript.append({'role': 'assistant', 'content': f"{suspect}: {susp_line}"})
            
            st.rerun()
            
        if st.button("End Day & Intervene (God Phase)"):
            st.session_state.game_phase = 'god_phase'
            st.rerun()

    # --- God Phase: User Input ---
    elif st.session_state.game_phase == 'god_phase':
        st.header("Divine Intervention")
        st.write("Who has incurred your suspicion? Point the Detective in their direction.")
        
        alive_suspects = [k for k, v in st.session_state.players.items() if v['status'] == 'alive' and v['role'] != 'Detective']
        target = st.selectbox("Select a suspect to frame/investigate:", alive_suspects)
        
        if st.button("Whisper to the Detective"):
            flavor_text = GOD_FLAVORS[st.session_state.god_flavor].format(suspect=target)
            st.session_state.god_whispers.append(flavor_text)
            st.success(f"You have whispered: '{flavor_text}'")
            st.session_state.game_phase = 'night_phase'
            st.rerun()

    # --- Night Phase: The Killer Strikes ---
    elif st.session_state.game_phase == 'night_phase':
        st.header("Night Falls...")
        if st.button("Let the Killer Strike"):
            with st.spinner("The Killer is choosing a victim..."):
                alive_players = {k: v for k, v in st.session_state.players.items() if v['status'] == 'alive'}
                killer_name = [k for k, v in alive_players.items() if v['role'] == 'Killer'][0]
                
                # Killer can't kill themselves
                potential_victims = [k for k in alive_players.keys() if k != killer_name]
                
                victim = night_phase_kill(killer_name, potential_victims)
                
                # Fallback in case the LLM hallucinates a name not on the list
                if victim not in potential_victims:
                    victim = random.choice(potential_victims) 
                
                st.session_state.players[victim]['status'] = 'dead'
                
                if st.session_state.players[victim]['role'] == 'Detective':
                    st.session_state.game_phase = 'game_over_loss'
                else:
                    st.session_state.transcript.append({'role': 'system', 'content': f"--- SYSTEM ANNOUNCEMENT: {victim} was found dead in the morning. ---"})
                    st.session_state.day += 1
                    st.session_state.game_phase = 'day_interrogation'
                
            st.rerun()

    # --- Game Over Conditions ---
    elif st.session_state.game_phase == 'game_over_loss':
        st.error("💀 GAME OVER")
        st.write("The Killer murdered the Detective in the night! The mystery remains unsolved.")
        if st.button("Play Again"):
            st.session_state.clear()
            st.rerun()
