import streamlit as st
import ollama
import random
import time

# --- CONFIGURATION & LORE ---
# The models that will power the different characters
AVAILABLE_MODELS = ['llama3:8b', 'phi3', 'qwen2:1.5b']

# Expanded Character Database with 30 distinct communication styles
CHARACTERS_DB = [
    # The Original 12
    {"name": "Arthur the Butler", "style": "Highly formal, stiff, dry British vocabulary. Never stutters."},
    {"name": "Beatrice the Widow", "style": "Melodramatic, weeping, uses exclamation points."},
    {"name": "Charles the Doctor", "style": "Clinical, precise, cold, and slightly arrogant."},
    {"name": "Diana the Heiress", "style": "Snobby, dismissive, bored, uses modern slang ironically."},
    {"name": "Edward the Chauffeur", "style": "Gruff, working-class, uses short and blunt sentences."},
    {"name": "Fiona the Maid", "style": "Highly nervous, apologetic, and stutters frequently (e.g., 'I-I didn't do it!')."},
    {"name": "George the Chef", "style": "Passionate, loud, uses culinary metaphors."},
    {"name": "Helen the Governess", "style": "Stern, reprimanding, speaks like she is scolding a child."},
    {"name": "Isaac the Clockmaker", "style": "Distracted, rambling, fixated on time and precision."},
    {"name": "Josephine the Singer", "style": "Flirtatious, dramatic, speaks poetically."},
    {"name": "Karl the Groundsman", "style": "Paranoid, aggressive, highly defensive."},
    {"name": "Lydia the Journalist", "style": "Inquisitive, fast-talking, treats everything like an interview."},
    # The 18 New Additions
    {"name": "Reginald the Earl", "style": "Extremely pompous, uses archaic words like 'poppycock' and talks down to everyone."},
    {"name": "Silas the Smuggler", "style": "Cryptic, uses underworld slang, and constantly answers questions with a question."},
    {"name": "Clara the Niece", "style": "Highly naive, overly sweet, and uses relentlessly optimistic language."},
    {"name": "Major Sterling", "style": "Barks out sentences, uses military jargon, and is extremely brief and structured."},
    {"name": "Julian the Painter", "style": "Pretentious, overly descriptive, and takes dramatic, artistic pauses."},
    {"name": "Eleanor the Socialite", "style": "Passive-aggressive, catty, and always drops veiled insults about the other guests."},
    {"name": "Professor Vance", "style": "Pedantic, uses overly complex academic words, and constantly corrects others' grammar."},
    {"name": "Victor the Lawyer", "style": "Legalistic, refuses to answer directly, and uses phrases like 'allegedly' and 'without prejudice'."},
    {"name": "Martha the Cook", "style": "Motherly but fiercely gossipy, uses terms of endearment like 'dearie' and 'sweetheart'."},
    {"name": "Baron Von Althaus", "style": "Highly formal, incredibly proud, and speaks with a slightly stiff European syntax."},
    {"name": "Tobias the Stableboy", "style": "Simple vocabulary, highly deferential, and ends almost every sentence with 'sir' or 'ma'am'."},
    {"name": "Madame Zara", "style": "Cryptic, speaks in riddles, and frequently references spirits, auras, and the beyond."},
    {"name": "Marcus the Mayor", "style": "Politician-speak, overly diplomatic, dodges questions, and avoids taking a hard stance."},
    {"name": "Nora the Seamstress", "style": "Quiet, sharply observant, and weaves sewing metaphors into her speech (e.g., 'threads of truth')."},
    {"name": "Oliver the Blacksmith", "style": "Booming voice, uses simple but heavy-hitting words, extremely direct and intimidating."},
    {"name": "Penelope the Astrologer", "style": "Dreamy tone, constantly speaking about cosmic alignments, stars, and fate."},
    {"name": "Quentin the Banker", "style": "Obsessed with money and ledgers, speaks entirely in transactional terms and numbers."},
    {"name": "Rose the Botanist", "style": "Sweet tone but highly morbid, constantly comparing people to poisonous plants."}
]

THEMES = {
    "The Omniscient Magistrate": {
        "prologue": "A high-society gala has ended in bloodshed. A prominent guest lies dead in the atrium. The killer is in the room. Guide the hidden Detective to the truth.",
        "god_prompt": "An undeniable instinct guides your thoughts: {suspect} is lying. Press them relentlessly.",
        "primary": "#2c3e50", "bg": "#f8f9fa", "box": "#ffffff"
    },
    "The Eldritch Watcher": {
        "prologue": "The coastal fog hides a grisly scene. A scholar was found butchered in the old library. Nudge the hidden investigator toward the prey.",
        "god_prompt": "A maddening whisper from the void echoes in your mind: {suspect} is masking their guilt. Break them.",
        "primary": "#16a085", "bg": "#eef2f3", "box": "#ffffff"
    }
}

# --- STATE MANAGEMENT ---
if 'game_phase' not in st.session_state:
    st.session_state.game_phase = 'setup'
    st.session_state.players = {}
    st.session_state.daily_transcripts = {1: ""}
    st.session_state.summaries = {}
    st.session_state.day = 1
    st.session_state.god_whispers = []
    st.session_state.daily_order = []
    st.session_state.speaker_idx = 0

# --- HELPER FUNCTIONS ---
def get_alive_players():
    return {k: v for k, v in st.session_state.players.items() if v['status'] == 'alive'}

def format_prompt(char_name, role, style):
    base = f"You are {char_name}. Your personality is: {style}. "
    if role == 'Killer':
        base += "You are the hidden KILLER. Lie, deflect, and cast suspicion on others. "
    elif role == 'Detective':
        base += "You are the hidden DETECTIVE trying to solve the murder. Ask sharp questions. "
    else:
        base += "You are INNOCENT. Defend yourself based on your personality. "
    base += "Respond with ONLY your spoken dialogue. Do not include your name. Keep it to exactly 1 or 2 sentences."
    return base

def stream_llm_response(model, sys_prompt, user_prompt):
    messages = [{'role': 'system', 'content': sys_prompt}, {'role': 'user', 'content': user_prompt}]
    stream = ollama.chat(model=model, messages=messages, stream=True)
    for chunk in stream:
        yield chunk['message']['content']
        time.sleep(0.02)

def generate_daily_summary(day, transcript):
    """Uses Llama 3 to summarize the day's events."""
    sys_p = "You are a concise narrator. Summarize the key clues and suspicions from today's interrogation in exactly 3 short bullet points."
    user_p = f"Day {day} Transcript:\n{transcript}"
    resp = ollama.chat(model='llama3:8b', messages=[{'role': 'system', 'content': sys_p}, {'role': 'user', 'content': user_p}])
    return resp['message']['content']

# --- UI SETUP & CSS ---
st.set_page_config(layout="centered", page_title="Mystery Sim")
active_theme = THEMES.get(st.session_state.get('theme_choice', "The Omniscient Magistrate"))

st.markdown(f"""
<style>
    .stApp {{ background-color: {active_theme['bg']}; color: #333333; font-family: 'Georgia', serif; }}
    h1, h2, h3 {{ color: {active_theme['primary']}; text-align: center; }}
    .player-container {{ display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; margin-bottom: 20px; }}
    .icon-box {{ background: {active_theme['box']}; border: 2px solid {active_theme['primary']}; border-radius: 8px; padding: 10px; width: 120px; text-align: center; font-size: 0.85rem; font-weight: bold; color: #333333; }}
    .dead-box {{ background: #dddddd; border: 2px solid #999999; border-radius: 8px; padding: 10px; width: 120px; text-align: center; font-size: 0.85rem; color: #777777; text-decoration: line-through; opacity: 0.7; }}
    .chat-bubble {{ background: #ffffff; border-left: 4px solid {active_theme['primary']}; padding: 15px; margin-bottom: 10px; border-radius: 5px; box-shadow: 1px 1px 4px rgba(0,0,0,0.05); font-size: 0.95rem; }}
    .summary-box {{ background: #e8f4f8; padding: 15px; border-radius: 5px; margin-bottom: 20px; border: 1px dashed {active_theme['primary']}; }}
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR: CONVERSATION ARCHIVES ---
with st.sidebar:
    st.header("📜 Archives")
    if st.session_state.day > 1:
        for d in range(1, st.session_state.day):
            with st.expander(f"Day {d} Log"):
                st.markdown(st.session_state.daily_transcripts[d])
    else:
        st.write("No past archives yet.")

st.title("⚖️ The Hidden Inquiry")

# --- 1. SETUP PHASE ---
if st.session_state.game_phase == 'setup':
    st.write("### Prepare the Board")
    player_count = st.slider("Number of Suspects (4 to 12)", 4, 12, 6)
    theme_choice = st.selectbox("Choose your Divine Aspect", list(THEMES.keys()))
    
    if st.button("Begin the Mystery", use_container_width=True):
        selected_chars = random.sample(CHARACTERS_DB, player_count)
        roles = ['Detective', 'Killer'] + ['Innocent'] * (player_count - 2)
        random.shuffle(roles)
        
        for i, char_data in enumerate(selected_chars):
            # Assign a random model and the specific personality to each character
            st.session_state.players[char_data['name']] = {
                'role': roles[i], 
                'status': 'alive',
                'style': char_data['style'],
                'model': random.choice(AVAILABLE_MODELS)
            }
        
        st.session_state.theme_choice = theme_choice
        st.session_state.game_phase = 'prologue'
        st.rerun()

# --- CONSTANT HUD ---
if st.session_state.game_phase != 'setup':
    html_roster = "<div class='player-container'>"
    for char, data in st.session_state.players.items():
        # Display the character name and the specific model powering their brain
        model_tag = f"<br><span style='font-size:0.6rem; color:#888;'>🧠 {data['model']}</span>"
        if data['status'] == 'alive':
            html_roster += f"<div class='icon-box'>👤<br>{char}{model_tag}</div>"
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

# --- 3. DAY PHASE (PARTIAL RANDOM CONVERSATIONS) ---
elif st.session_state.game_phase == 'day_interrogation':
    alive_players = get_alive_players()
    
    # Display Daily Summary if it exists
    if st.session_state.day in st.session_state.summaries:
        st.markdown("### 📌 Recap of Yesterday")
        st.markdown(f"<div class='summary-box'>{st.session_state.summaries[st.session_state.day]}</div>", unsafe_allow_html=True)

    # Initialize the random speaking order for the day
    if not st.session_state.daily_order:
        detective_name = [k for k, v in alive_players.items() if v['role'] == 'Detective'][0]
        others = [k for k in alive_players.keys() if k != detective_name]
        
        # If > 6 players, only ~1/3 of the suspects speak to save time. 
        if len(alive_players) > 6:
            num_speakers = max(3, len(alive_players) // 3)
            chosen_others = random.sample(others, num_speakers - 1)
        else:
            chosen_others = others
            random.shuffle(chosen_others)
            
        # Detective always speaks first to lead the conversation
        st.session_state.daily_order = [detective_name] + chosen_others
        st.session_state.speaker_idx = 0

    # Render Today's Conversation Log
    if st.session_state.daily_transcripts[st.session_state.day]:
        st.markdown(f"### Day {st.session_state.day} Log")
        for line in st.session_state.daily_transcripts[st.session_state.day].split('\n'):
            if line.strip():
                st.markdown(f"<div class='chat-bubble'>{line}</div>", unsafe_allow_html=True)

    # Step-by-Step Logic
    if st.session_state.speaker_idx < len(st.session_state.daily_order):
        current_speaker = st.session_state.daily_order[st.session_state.speaker_idx]
        player_data = st.session_state.players[current_speaker]
        
        if st.button(f"Let {current_speaker} Speak", type="primary", use_container_width=True):
            sys_p = format_prompt(current_speaker, player_data['role'], player_data['style'])
            
            if player_data['role'] == 'Detective' and st.session_state.god_whispers:
                sys_p += f"\n\nDIVINE KNOWLEDGE: {st.session_state.god_whispers[-1]}"
                
            user_p = f"Transcript so far:\n{st.session_state.daily_transcripts[st.session_state.day]}\n\nWhat do you say?"
            
            with st.spinner(f"{current_speaker} is formulating their words..."):
                speaker_container = st.empty()
                # Pass the assigned model to the stream function
                line = speaker_container.write_stream(stream_llm_response(player_data['model'], sys_p, user_p))
                
            # Bold the character name in the log
            st.session_state.daily_transcripts[st.session_state.day] += f"\n**{current_speaker}:** {line}"
            st.session_state.speaker_idx += 1
            st.rerun()
    else:
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
        sys_p = f"You are the hidden Detective. Based on the transcript, guess who the killer is. Reply with ONLY the exact name from this list: {', '.join(suspects)}."
        user_p = f"Transcript:\n{st.session_state.daily_transcripts[st.session_state.day]}\n\nWho is the killer?"
        guess_resp = ollama.chat(model=st.session_state.players[detective_name]['model'], messages=[{'role': 'system', 'content': sys_p}, {'role': 'user', 'content': user_p}])
        guess = guess_resp['message']['content'].strip()

    st.markdown("### The Accusation")
    st.markdown(f"<div class='chat-bubble'>The hidden Detective officially suspects: <b>{guess}</b></div>", unsafe_allow_html=True)
    
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
            killer_model = st.session_state.players[killer_name]['model']
            potential_victims = [k for k in alive_players.keys() if k != killer_name]
            
            # The Killer chooses a victim using their specific model
            sys_p = f"You are the Killer. Choose one person to murder from this list: {', '.join(potential_victims)}. Reply with ONLY their name."
            user_p = f"Transcript:\n{st.session_state.daily_transcripts[st.session_state.day]}\n\nWho do you kill?"
            resp = ollama.chat(model=killer_model, messages=[{'role': 'system', 'content': sys_p}, {'role': 'user', 'content': user_p}])
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
                # Generate the summary for the day that just ended
                summary = generate_daily_summary(st.session_state.day, st.session_state.daily_transcripts[st.session_state.day])
                st.session_state.day += 1
                st.session_state.summaries[st.session_state.day] = summary
                
                # Prep the next day
                st.session_state.daily_transcripts[st.session_state.day] = f"**SYSTEM:** {victim} was found murdered in the night."
                st.session_state.daily_order = [] 
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
        
    st.markdown(f"### **The hidden Detective was:** 🔍 {detective_name}")
    st.markdown(f"### **The hidden Killer was:** 🔪 {killer_name}")
    
    with st.spinner("Extracting the confession..."):
        sys_p = "You are a dramatic narrator. Reveal the murderer's means, motive, and opportunity."
        user_p = f"The killer was {killer_name}. Write a 3-sentence summary."
        resp = ollama.chat(model='llama3:8b', messages=[{'role': 'system', 'content': sys_p}, {'role': 'user', 'content': user_p}])
        
    st.info(resp['message']['content'])
    
    if st.button("Start a New Mystery", use_container_width=True):
        st.session_state.clear()
        st.rerun()
