import streamlit as st
import ollama
import random
import time
import re

# --- CONFIGURATION & LORE ---
AVAILABLE_MODELS = ['llama3:8b', 'phi3', 'qwen2:1.5b']

CHARACTERS_DB = [
    {"name": "Arthur the Butler", "style": "Highly formal, stiff, dry British vocabulary. Never stutters."},
    {"name": "Beatrice the Widow", "style": "Melodramatic, weeping, uses exclamation points."},
    {"name": "Charles the Doctor", "style": "Clinical, precise, cold, and slightly arrogant."},
    {"name": "Diana the Heiress", "style": "Snobby, dismissive, bored, uses modern slang ironically."},
    {"name": "Edward the Chauffeur", "style": "Gruff, working-class, uses short and blunt sentences."},
    {"name": "Fiona the Maid", "style": "Highly nervous, apologetic, and stutters frequently."},
    {"name": "George the Chef", "style": "Passionate, loud, uses culinary metaphors."},
    {"name": "Helen the Governess", "style": "Stern, reprimanding, speaks like she is scolding a child."},
    {"name": "Isaac the Clockmaker", "style": "Distracted, rambling, fixated on time and precision."},
    {"name": "Josephine the Singer", "style": "Flirtatious, dramatic, speaks poetically."},
    {"name": "Karl the Groundsman", "style": "Paranoid, aggressive, highly defensive."},
    {"name": "Lydia the Journalist", "style": "Inquisitive, fast-talking, treats everything like an interview."},
    {"name": "Reginald the Earl", "style": "Extremely pompous, uses archaic words like 'poppycock'."},
    {"name": "Silas the Smuggler", "style": "Cryptic, uses underworld slang."},
    {"name": "Clara the Niece", "style": "Highly naive, overly sweet, and relentlessly optimistic."},
    {"name": "Major Sterling", "style": "Barks out sentences, uses military jargon."},
    {"name": "Julian the Painter", "style": "Pretentious, overly descriptive, dramatic pauses."},
    {"name": "Eleanor the Socialite", "style": "Passive-aggressive, catty, veiled insults."},
    {"name": "Professor Vance", "style": "Pedantic, overly complex academic words."},
    {"name": "Victor the Lawyer", "style": "Legalistic, uses phrases like 'allegedly'."},
    {"name": "Martha the Cook", "style": "Motherly but gossipy, calls people 'dearie'."},
    {"name": "Baron Von Althaus", "style": "Highly formal, proud, stiff European syntax."},
    {"name": "Tobias the Stableboy", "style": "Simple vocabulary, ends sentences with 'sir' or 'ma'am'."},
    {"name": "Madame Zara", "style": "Cryptic, references spirits and auras."},
    {"name": "Marcus the Mayor", "style": "Politician-speak, overly diplomatic, dodges questions."},
    {"name": "Nora the Seamstress", "style": "Quiet, observant, uses sewing metaphors."},
    {"name": "Oliver the Blacksmith", "style": "Booming voice, simple heavy-hitting words."},
    {"name": "Penelope the Astrologer", "style": "Dreamy tone, talks about cosmic alignments."},
    {"name": "Quentin the Banker", "style": "Obsessed with money and ledgers."},
    {"name": "Rose the Botanist", "style": "Sweet tone but highly morbid, plant metaphors."}
]

# Deeper Themes: Fonts, Borders, Backgrounds, Button Styling
THEMES = {
    "The Omniscient Magistrate": {
        "god_prompt": "An undeniable instinct guides your thoughts: {suspect} is lying. Press them relentlessly.",
        "bg": "#f4f6f9", "box": "#ffffff", "primary": "#2c3e50", "border": "2px solid #2c3e50",
        "font": "Georgia, serif", "bubble_bg": "#ffffff", "border_radius": "5px",
        "button_bg": "#2c3e50", "button_text": "#ffffff", "button_hover": "#1a252f", "button_radius": "5px"
    },
    "The Eldritch Watcher": {
        "god_prompt": "A maddening whisper from the void echoes in your mind: {suspect} is masking their guilt. Break them.",
        "bg": "#111412", "box": "#1e2621", "primary": "#43a047", "border": "2px dashed #43a047",
        "font": "'Courier New', Courier, monospace", "bubble_bg": "#1e2621", "border_radius": "0px",
        "button_bg": "#1b5e20", "button_text": "#a5d6a7", "button_hover": "#43a047", "button_radius": "0px"
    },
    "The Olympian": {
        "god_prompt": "Athena's wisdom pierces the veil of lies. {suspect} is hiding the truth. Uncover it.",
        "bg": "#fdfbf7", "box": "#fcf5e3", "primary": "#b8860b", "border": "3px double #b8860b",
        "font": "'Palatino Linotype', 'Book Antiqua', Palatino, serif", "bubble_bg": "#fcf5e3", "border_radius": "15px",
        "button_bg": "#b8860b", "button_text": "#ffffff", "button_hover": "#daa520", "button_radius": "20px"
    }
}

VICTIMS = ["Lord Reginald Blackwood", "Lady Margaret Ashbury", "Professor Alistair Sterling", "Countess Von Richtofen", "Sir Reginald Vance"]
CAUSES = ["poisoned with rare hemlock", "bludgeoned with a heavy brass candlestick", "thrown from the observatory balcony", "strangled with a velvet cord", "stabbed with an antique letter opener"]

# --- STATE MANAGEMENT ---
if 'game_phase' not in st.session_state:
    st.session_state.game_phase = 'setup'
    st.session_state.players = {}
    st.session_state.daily_transcripts = {1: []} 
    st.session_state.summaries = {}
    st.session_state.day = 1
    st.session_state.god_whispers = []
    st.session_state.daily_order = []
    st.session_state.speaker_idx = 0
    st.session_state.prologue_text = ""

# --- HELPER FUNCTIONS ---
def get_alive_players():
    return {k: v for k, v in st.session_state.players.items() if v['status'] == 'alive'}

def format_transcript_for_prompt(day):
    log = st.session_state.daily_transcripts[day]
    return "\n".join([f"{item['speaker']}: {item['text']}" for item in log])

def clean_llm_output(text, speaker_name):
    # Strip instructions and prompt leaks
    text = re.sub(r'## Instruction.*?\n', '', text, flags=re.IGNORECASE)
    text = text.replace("(High Diff 03)", "").strip()
    
    # Catch "Transcript so far" or "What do you say" leaks
    if "What do you say" in text:
        text = text.split("What do you say")[-1].strip()
    if text.startswith("?") or text.startswith(":"): 
        text = text[1:].strip()
        
    # Strip duplicated name prefixes
    name_prefix = speaker_name.lower() + ":"
    first_name_prefix = speaker_name.split()[0].lower() + ":"
    if text.lower().startswith(name_prefix):
        text = text[len(speaker_name)+1:].strip()
    elif text.lower().startswith(first_name_prefix):
        text = text[len(speaker_name.split()[0])+1:].strip()
        
    return text.strip()

def format_prompt(char_name, role, style):
    alive_names = list(get_alive_players().keys())
    roster_str = ", ".join(alive_names)
    
    base = f"You are {char_name}. Your personality is: {style}. "
    if role == 'Killer':
        base += "You are the hidden KILLER. Lie, deflect, and cast suspicion on others. "
    elif role == 'Detective':
        base += "You are the hidden DETECTIVE trying to solve the murder. Ask sharp questions. "
    else:
        base += "You are INNOCENT. Defend yourself based on your personality. "
        
    base += f"\nCRITICAL RULES: The ONLY people in this room are: {roster_str}. DO NOT invent, mention, or speak to any other characters (like 'Mr. Greenwood'). "
    base += "Do NOT echo the prompt or say 'Transcript so far'. Respond with ONLY your spoken dialogue. Keep it to exactly 1 or 2 sentences."
    
    # Angelic Revival Memory Curse Logic
    if 'memory_curse' in st.session_state.players[char_name]:
        base += f"\n\nDIVINE CURSE: You have recently been resurrected from the dead. {st.session_state.players[char_name]['memory_curse']}"
        
    return base

def stream_llm_response(model, sys_prompt, user_prompt):
    messages = [{'role': 'system', 'content': sys_prompt}, {'role': 'user', 'content': user_prompt}]
    stream = ollama.chat(model=model, messages=messages, stream=True)
    for chunk in stream:
        yield chunk['message']['content']
        time.sleep(0.02)

def generate_daily_summary(day, transcript_text):
    sys_p = "You are a concise narrator. Summarize the key clues from today's interrogation. You MUST output EXACTLY 3 bullet points. Start each bullet point on a NEW LINE using a dash '-' character. Do NOT use the bullet symbol '•'."
    user_p = f"Day {day} Transcript:\n{transcript_text}"
    resp = ollama.chat(model='llama3:8b', messages=[{'role': 'system', 'content': sys_p}, {'role': 'user', 'content': user_p}])
    return resp['message']['content']

# --- UI SETUP & CSS ---
st.set_page_config(layout="centered", page_title="Mystery Sim")
active_theme = THEMES.get(st.session_state.get('theme_choice', "The Omniscient Magistrate"))

# Deeply Customized CSS per Denomination
st.markdown(f"""
<style>
    .stApp {{ background-color: {active_theme['bg']}; color: {active_theme['primary']}; font-family: {active_theme['font']}; }}
    h1, h2, h3 {{ color: {active_theme['primary']}; text-align: center; font-family: {active_theme['font']}; }}
    .player-container {{ display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; margin-bottom: 20px; }}
    .icon-box {{ background: {active_theme['box']}; border: {active_theme['border']}; border-radius: {active_theme['border_radius']}; padding: 10px; width: 120px; text-align: center; font-size: 0.85rem; font-weight: bold; color: {active_theme['primary']}; }}
    .dead-box {{ background: #555555; border: 2px solid #333333; border-radius: {active_theme['border_radius']}; padding: 10px; width: 120px; text-align: center; font-size: 0.85rem; color: #aaaaaa; text-decoration: line-through; opacity: 0.7; }}
    .chat-bubble {{ background: {active_theme['bubble_bg']}; border-left: 5px solid {active_theme['primary']}; padding: 15px; margin-bottom: 10px; border-radius: {active_theme['border_radius']}; box-shadow: 1px 1px 4px rgba(0,0,0,0.05); font-size: 0.95rem; color: {active_theme['primary']}; }}
    .sys-bubble {{ background: #e8c3c3; border: 1px solid #cc0000; padding: 10px; margin-bottom: 10px; border-radius: 5px; text-align: center; font-weight: bold; color: #cc0000; }}
    .revive-bubble {{ background: #fffacd; border: 2px dashed #ffae42; padding: 10px; margin-bottom: 10px; border-radius: 5px; text-align: center; font-weight: bold; color: #b8860b; }}
    .summary-box {{ background: {active_theme['box']}; padding: 15px; border-radius: {active_theme['border_radius']}; margin-bottom: 20px; border: {active_theme['border']}; color: {active_theme['primary']}; white-space: pre-wrap; }}
    
    /* Global Button Styling Overrides */
    .stButton>button {{
        background-color: {active_theme['button_bg']} !important;
        color: {active_theme['button_text']} !important;
        border: {active_theme['border']} !important;
        border-radius: {active_theme['button_radius']} !important;
        font-family: {active_theme['font']} !important;
        font-weight: bold;
        transition: 0.3s;
    }}
    .stButton>button:hover {{
        background-color: {active_theme['button_hover']} !important;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.2);
    }}
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR: ARCHIVES ---
with st.sidebar:
    st.header("📜 Archives")
    if st.session_state.day > 1:
        for d in range(1, st.session_state.day):
            with st.expander(f"Day {d} Log"):
                for item in st.session_state.daily_transcripts[d]:
                    if item['speaker'] == "SYSTEM":
                        st.markdown(f"<div class='sys-bubble'>{item['text']}</div>", unsafe_allow_html=True)
                    elif item['speaker'] == "DIVINE":
                        st.markdown(f"<div class='revive-bubble'>✨ {item['text']} ✨</div>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<div class='chat-bubble'><b>{item['speaker']}:</b> {item['text']}</div>", unsafe_allow_html=True)
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
            st.session_state.players[char_data['name']] = {
                'role': roles[i], 
                'status': 'alive',
                'style': char_data['style'],
                'model': random.choice(AVAILABLE_MODELS)
            }
        
        # Generate the dynamic backstory
        vic = random.choice(VICTIMS)
        cau = random.choice(CAUSES)
        st.session_state.prologue_text = f"The estate is in uproar. {vic} has been found dead—{cau}. The manor is sealed. The killer is still in this very room. Guide the hidden Detective to the truth."
        
        st.session_state.theme_choice = theme_choice
        st.session_state.game_phase = 'prologue'
        st.rerun()

# --- CONSTANT HUD ---
if st.session_state.game_phase != 'setup':
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
    st.markdown(f"<div class='chat-bubble'><em>{st.session_state.prologue_text}</em></div>", unsafe_allow_html=True)
    if st.button("Step into the Interrogation Room", use_container_width=True):
        st.session_state.game_phase = 'day_interrogation'
        st.rerun()

# --- 3. DAY PHASE ---
elif st.session_state.game_phase == 'day_interrogation':
    alive_players = get_alive_players()
    
    if st.session_state.day in st.session_state.summaries:
        st.markdown("### 📌 Recap of Yesterday")
        st.markdown(f"<div class='summary-box'>{st.session_state.summaries[st.session_state.day]}</div>", unsafe_allow_html=True)

    if not st.session_state.daily_order:
        detective_name = [k for k, v in alive_players.items() if v['role'] == 'Detective'][0]
        others = [k for k in alive_players.keys() if k != detective_name]
        
        if len(alive_players) > 6:
            num_speakers = max(3, len(alive_players) // 3)
            chosen_others = random.sample(others, num_speakers - 1)
        else:
            chosen_others = others
            random.shuffle(chosen_others)
            
        st.session_state.daily_order = [detective_name] + chosen_others
        st.session_state.speaker_idx = 0

    if st.session_state.daily_transcripts[st.session_state.day]:
        st.markdown(f"### Day {st.session_state.day} Log")
        for item in st.session_state.daily_transcripts[st.session_state.day]:
            if item['speaker'] == "SYSTEM":
                st.markdown(f"<div class='sys-bubble'>{item['text']}</div>", unsafe_allow_html=True)
            elif item['speaker'] == "DIVINE":
                st.markdown(f"<div class='revive-bubble'>✨ {item['text']} ✨</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='chat-bubble'><b>{item['speaker']}:</b> {item['text']}</div>", unsafe_allow_html=True)

    if st.session_state.speaker_idx < len(st.session_state.daily_order):
        current_speaker = st.session_state.daily_order[st.session_state.speaker_idx]
        player_data = st.session_state.players[current_speaker]
        
        if st.button(f"Let {current_speaker} Speak", use_container_width=True):
            sys_p = format_prompt(current_speaker, player_data['role'], player_data['style'])
            if player_data['role'] == 'Detective' and st.session_state.god_whispers:
                sys_p += f"\n\nDIVINE KNOWLEDGE: {st.session_state.god_whispers[-1]}"
                
            formatted_log = format_transcript_for_prompt(st.session_state.day)
            user_p = f"Transcript so far:\n{formatted_log}\n\nWhat do you say?"
            
            with st.spinner(f"{current_speaker} is formulating their words..."):
                speaker_container = st.empty()
                raw_line = speaker_container.write_stream(stream_llm_response(player_data['model'], sys_p, user_p))
                
            clean_line = clean_llm_output(raw_line, current_speaker)
            
            st.session_state.daily_transcripts[st.session_state.day].append({
                "speaker": current_speaker,
                "text": clean_line
            })
            st.session_state.speaker_idx += 1
            st.rerun()
    else:
        if st.button("The room falls silent. Proceed to Accusations.", use_container_width=True):
            st.session_state.game_phase = 'detective_guess_eval'
            st.rerun()

# --- 4. STRICT DETECTIVE EVALUATION ---
elif st.session_state.game_phase == 'detective_guess_eval':
    alive_players = get_alive_players()
    killer_name = [k for k, v in st.session_state.players.items() if v['role'] == 'Killer'][0]
    detective_name = [k for k, v in alive_players.items() if v['role'] == 'Detective'][0]
    suspects = [k for k in alive_players.keys() if k != detective_name]
    
    with st.spinner("The hidden Detective is reviewing the evidence..."):
        sys_p = f"You are the Detective. You MUST choose EXACTLY ONE name from this list: {', '.join(suspects)}. Do not explain your reasoning. Output just the name."
        formatted_log = format_transcript_for_prompt(st.session_state.day)
        user_p = f"Transcript:\n{formatted_log}\n\nWho is the killer? Name only."
        
        guess_resp = ollama.chat(model=st.session_state.players[detective_name]['model'], messages=[{'role': 'system', 'content': sys_p}, {'role': 'user', 'content': user_p}])
        raw_guess = guess_resp['message']['content'].strip()

        mentioned = [s for s in suspects if s.lower() in raw_guess.lower()]
        if len(mentioned) == 1:
            final_guess = mentioned[0] 
        elif len(mentioned) > 1:
            final_guess = random.choice(mentioned) 
        else:
            final_guess = random.choice(suspects) 

    st.markdown("### The Accusation")
    st.markdown(f"<div class='chat-bubble'>The hidden Detective officially suspects: <b>{final_guess}</b></div>", unsafe_allow_html=True)
    
    if final_guess == killer_name:
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

# --- 6. NIGHT PHASE & ANGELIC REVIVAL ---
elif st.session_state.game_phase == 'night_phase':
    st.write("### 🌑 Night Falls...")
    if st.button("Let the Hidden Killer Strike", use_container_width=True):
        with st.spinner("Blood is being spilled..."):
            alive_players = get_alive_players()
            killer_name = [k for k, v in alive_players.items() if v['role'] == 'Killer'][0]
            killer_model = st.session_state.players[killer_name]['model']
            potential_victims = [k for k in alive_players.keys() if k != killer_name]
            
            sys_p = f"You are the Killer. Choose one person to murder from this list: {', '.join(potential_victims)}. Reply with ONLY their name."
            formatted_log = format_transcript_for_prompt(st.session_state.day)
            user_p = f"Transcript:\n{formatted_log}\n\nWho do you kill?"
            resp = ollama.chat(model=killer_model, messages=[{'role': 'system', 'content': sys_p}, {'role': 'user', 'content': user_p}])
            choice = resp['message']['content'].strip()
            
            victim = random.choice(potential_victims)
            for p in potential_victims:
                if p.lower() in choice.lower():
                    victim = p
                    break
            
            st.session_state.players[victim]['status'] = 'dead'
            
            if st.session_state.players[victim]['role'] == 'Detective':
                st.session_state.game_phase = 'game_over_loss'
            else:
                summary = generate_daily_summary(st.session_state.day, formatted_log)
                st.session_state.day += 1
                st.session_state.summaries[st.session_state.day] = summary
                
                # Prep next day's log
                next_day_log = [{"speaker": "SYSTEM", "text": f"{victim} was found murdered in the night."}]
                
                # --- ANGELIC REVIVAL MECHANIC (5% Chance) ---
                dead_players = [k for k, v in st.session_state.players.items() if v['status'] == 'dead' and v['role'] != 'Detective']
                if dead_players and random.random() < 0.05: # 5% chance
                    revived = random.choice(dead_players)
                    st.session_state.players[revived]['status'] = 'alive'
                    
                    curses = [
                        "Complete memory loss: You do not remember who anyone is, where you are, or what happened.",
                        "Partial memory: You remember everything EXCEPT how you were killed or who killed you.",
                        "Delusional memory: Your memories are completely wrong. You fiercely accuse innocent people of absurd things."
                    ]
                    st.session_state.players[revived]['memory_curse'] = random.choice(curses)
                    
                    next_day_log.append({"speaker": "DIVINE", "text": f"A MIRACLE! {revived} has been revived by an angelic presence... but their mind is permanently altered."})
                
                st.session_state.daily_transcripts[st.session_state.day] = next_day_log
                st.session_state.daily_order = [] 
                st.session_state.game_phase = 'day_interrogation'
        st.rerun()

# --- 7. ENDING SCREENS & EPILOGUES ---
elif st.session_state.game_phase in ['game_over_win', 'game_over_loss']:
    killer_name = [k for k, v in st.session_state.players.items() if v['role'] == 'Killer'][0]
    detective_name = [k for k, v in st.session_state.players.items() if v['role'] == 'Detective'][0]
    
    st.markdown("## 🎭 THE CURTAIN FALLS")
    
    if st.session_state.game_phase == 'game_over_loss':
        st.error("The hidden Killer successfully assassinated the hidden Detective in the night! The mortals are doomed.")
        st.markdown(f"### **The murdered Detective was:** 🔍 {detective_name}")
        st.markdown(f"### **The victorious Killer was:** 🔪 {killer_name}")
        
        with st.spinner("Generating the dark epilogue..."):
            sys_p = "You are a dark, dramatic narrator. Write a 2-paragraph epilogue."
            user_p = f"The killer ({killer_name}) successfully murdered the detective ({detective_name}) and was never caught. Paragraph 1: Explain how {killer_name} got away with the murder and hid the detective's body. Paragraph 2: Explain the dark, sinister, or luxurious things {killer_name} went on to do with their life now that they are free. Do NOT include a confession."
            resp = ollama.chat(model='llama3:8b', messages=[{'role': 'system', 'content': sys_p}, {'role': 'user', 'content': user_p}])
        
    else:
        st.success("Justice has been served!")
        st.markdown(f"### **The triumphant Detective was:** 🔍 {detective_name}")
        st.markdown(f"### **The captured Killer was:** 🔪 {killer_name}")
        
        with st.spinner("Extracting the confession and epilogue..."):
            sys_p = "You are an uplifting dramatic narrator. Write a 2-paragraph epilogue."
            user_p = f"The detective ({detective_name}) successfully cornered the killer ({killer_name}). Paragraph 1: Force the killer to confess, detailing the exact Means, Motive, and Opportunity of how they committed the original murder. Paragraph 2: Explain what uplifting and successful things the Detective and the remaining innocents went on to do with their lives."
            resp = ollama.chat(model='llama3:8b', messages=[{'role': 'system', 'content': sys_p}, {'role': 'user', 'content': user_p}])
        
    st.markdown(f"<div class='summary-box'>{resp['message']['content']}</div>", unsafe_allow_html=True)
    
    with st.expander("🛠️ Behind the Curtain: Reveal AI Models Used"):
        st.write("Here are the specific AI models that were powering each character during this game:")
        for char, data in st.session_state.players.items():
            role_hint = f" ({data['role']})" if data['role'] in ['Detective', 'Killer'] else ""
            st.write(f"- **{char}**{role_hint}: `🧠 {data['model']}`")

    if st.button("Start a New Mystery", use_container_width=True):
        st.session_state.clear()
        st.rerun()
