import streamlit as st
import random
import time
import re
import os
from openai import OpenAI

# --- ENGINE SETUP (OPENROUTER) ---
api_key = os.environ.get("OPENROUTER_API_KEY")
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key,
)

# --- MODEL POOLS (VERIFIED ALLOWLIST) ---
MASTERMIND_MODELS = [
    "qwen/qwen3.6-plus"          # Exact ID for Qwen3.6 Plus
]

STANDARD_MODELS = [
    "z-ai/glm-5",                # Exact ID for GLM 5
    "moonshotai/kimi-k2.5"       # Exact ID for Kimi K2.5
]

WILDCARD_MODELS = [
    "minimax/minimax-m2.7"       # Exact ID for MiniMax M2.7
]


# --- CONFIGURATION & LORE ---
CHARACTERS_DB = [
    {"name": "Arthur the Butler", "style": "Formal and dry. Short sentences."},
    {"name": "Beatrice the Widow", "style": "Melodramatic and weeping."},
    {"name": "Charles the Doctor", "style": "Clinical and precise."},
    {"name": "Diana the Heiress", "style": "Snobby and bored."},
    {"name": "Edward the Chauffeur", "style": "Gruff and blunt."},
    {"name": "Fiona the Maid", "style": "Nervous and apologetic."},
    {"name": "George the Chef", "style": "Passionate and loud."},
    {"name": "Helen the Governess", "style": "Stern and reprimanding."},
    {"name": "Isaac the Clockmaker", "style": "Fixated on time."},
    {"name": "Josephine the Singer", "style": "Dramatic and poetic."},
    {"name": "Karl the Groundsman", "style": "Paranoid and defensive."},
    {"name": "Lydia the Journalist", "style": "Inquisitive and fast-talking."},
    {"name": "Reginald the Earl", "style": "Pompous and arrogant."},
    {"name": "Silas the Smuggler", "style": "Cryptic and suspicious."},
    {"name": "Clara the Niece", "style": "Naive and optimistic."},
    {"name": "Major Sterling", "style": "Barks short military sentences."},
    {"name": "Julian the Painter", "style": "Dramatic and descriptive."},
    {"name": "Eleanor the Socialite", "style": "Passive-aggressive."},
    {"name": "Professor Vance", "style": "Overly academic and correcting."},
    {"name": "Victor the Lawyer", "style": "Legalistic and defensive."},
    {"name": "Martha the Cook", "style": "Motherly but gossipy."},
    {"name": "Baron Von Althaus", "style": "Formal and proud."},
    {"name": "Tobias the Stableboy", "style": "Simple and deferential."},
    {"name": "Madame Zara", "style": "Cryptic and mysterious."},
    {"name": "Marcus the Mayor", "style": "Diplomatic and evasive."},
    {"name": "Nora the Seamstress", "style": "Quiet and observant."},
    {"name": "Oliver the Blacksmith", "style": "Booming and direct."},
    {"name": "Penelope the Astrologer", "style": "Dreamy and cosmic."},
    {"name": "Quentin the Banker", "style": "Obsessed with money."},
    {"name": "Rose the Botanist", "style": "Sweet but morbid."}
]

THEMES = {
    "The Omniscient Magistrate": {
        "god_prompt": "{suspect} is lying about their whereabouts. Press them.",
        "bg": "#f4f6f9", "box": "#ffffff", "primary": "#2c3e50", "border": "2px solid #2c3e50",
        "font": "Georgia, serif", "bubble_bg": "#ffffff", "border_radius": "5px",
        "button_bg": "#2c3e50", "button_text": "#ffffff", "button_hover": "#1a252f", "button_radius": "5px"
    },
    "The Eldritch Watcher": {
        "god_prompt": "A whisper from the void: {suspect} is masking their guilt. Confront them.",
        "bg": "#111412", "box": "#1e2621", "primary": "#43a047", "border": "2px dashed #43a047",
        "font": "'Courier New', Courier, monospace", "bubble_bg": "#1e2621", "border_radius": "0px",
        "button_bg": "#1b5e20", "button_text": "#a5d6a7", "button_hover": "#43a047", "button_radius": "0px"
    },
    "The Olympian": {
        "god_prompt": "Athena's wisdom reveals {suspect} is hiding the truth. Uncover it.",
        "bg": "#fdfbf7", "box": "#fcf5e3", "primary": "#b8860b", "border": "3px double #b8860b",
        "font": "'Palatino Linotype', 'Book Antiqua', Palatino, serif", "bubble_bg": "#fcf5e3", "border_radius": "15px",
        "button_bg": "#b8860b", "button_text": "#ffffff", "button_hover": "#daa520", "button_radius": "20px"
    }
}

VICTIMS = ["Lord Blackwood", "Lady Ashbury", "Professor Sterling", "Countess Richtofen", "Sir Vance"]
CAUSES = ["poisoned with rare hemlock", "bludgeoned with a brass candlestick", "thrown from the balcony", "strangled with a velvet cord", "stabbed with a letter opener"]

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
    st.session_state.whisper_cast = False
    st.session_state.custom_cast = random.sample(CHARACTERS_DB, 6)

# --- HELPER FUNCTIONS ---
def get_alive_players():
    return {k: v for k, v in st.session_state.players.items() if v['status'] == 'alive'}

def format_transcript_for_prompt(day):
    log = st.session_state.daily_transcripts[day]
    return "\n".join([f"{item['speaker']}: {item['text']}" for item in log])

def clean_llm_output(text, speaker_name, roster_names):
    leak_patterns = [
        r"Instruction.*", r"CRITICAL RULES.*", r"Transcript so far.*", 
        r"You are.*", r"CRITICAL:.*", r"(?i)Speak your line now\.?", 
        r"(?i)Now speak your line\.?", r"(?i)What do you say\??", 
        r"(?i)Write ONLY your next sentence.*", r"Log:.*"
    ]
    for p in leak_patterns:
        text = re.sub(p, "", text, flags=re.IGNORECASE | re.DOTALL)
        
    text = re.sub(r'\*.*?\*', '', text)
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'\(.*?\)', '', text)
    text = text.replace('"', '').replace('“', '').replace('”', '')
    
    text = text.strip()
    
    changed = True
    while changed:
        orig = text
        text = re.sub(r'^([A-Z][a-zA-Z]+(?:\s+[A-Za-z]+){0,3}):\s*', '', text).strip()
        if text.lower().startswith(speaker_name.lower() + ":"):
            text = text[len(speaker_name)+1:].strip()
        if text == orig:
            changed = False
            
    return text.strip()

def format_prompt(char_name, style):
    alive_names = list(get_alive_players().keys())
    roster_str = ", ".join(alive_names)
    
    base = f"Your name is {char_name}. Your style is: {style}. "
    base += "\nCRITICAL RULES FOR YOUR RESPONSE: "
    base += "\n1. NEVER declare your secret role. Do not use the words 'detective', 'killer', 'investigating', or 'murderer' about yourself. "
    base += "\n2. Use very simple, basic vocabulary. Do NOT use made-up words. Be concise. "
    base += "\n3. Provide ONLY your spoken dialogue. Do NOT include narration, actions, or quotation marks. "
    base += f"\n4. The ONLY people in this room are: {roster_str}. NEVER mention ANY other characters. "
    base += "\n5. Maximum length: 1 short sentence. Do NOT repeat the prompt."
    
    if 'memory_curse' in st.session_state.players[char_name]:
        base += f"\n\nDIVINE CURSE: You were killed and brought back to life. {st.session_state.players[char_name]['memory_curse']}"
        
    return base

# ENGINE UPDATE: Sending prompts to OpenRouter
def stream_llm_response(model_id, sys_prompt, user_prompt):
    messages = [{'role': 'system', 'content': sys_prompt}, {'role': 'user', 'content': user_prompt}]
    
    stream = client.chat.completions.create(
        model=model_id, 
        messages=messages, 
        stream=True
    )
    for chunk in stream:
        if chunk.choices[0].delta.content is not None:
            yield chunk.choices[0].delta.content
            time.sleep(0.02)

def generate_daily_summary(day, transcript_text):
    sys_p = "You are a concise narrator. Summarize the key clues from the transcript. Output EXACTLY 3 bullet points. Start each bullet point on a new line with a '-' dash. Do NOT use the bullet dot symbol. Keep language extremely simple."
    user_p = f"Transcript:\n{transcript_text}"
    
    resp = client.chat.completions.create(
        model=MASTERMIND_MODELS[0], 
        messages=[{'role': 'system', 'content': sys_p}, {'role': 'user', 'content': user_p}]
    )
    content = resp.choices[0].message.content.replace('•', '-')
    return content

# --- UI SETUP & CSS ---
st.set_page_config(layout="centered", page_title="Mystery Sim")
active_theme = THEMES.get(st.session_state.get('theme_choice', "The Omniscient Magistrate"))

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
    .stButton>button {{
        background-color: {active_theme['button_bg']} !important;
        color: {active_theme['button_text']} !important;
        border: {active_theme['border']} !important;
        border-radius: {active_theme['button_radius']} !important;
        font-family: {active_theme['font']} !important;
        font-weight: bold; transition: 0.3s;
    }}
    .stButton>button:hover {{ background-color: {active_theme['button_hover']} !important; box-shadow: 2px 2px 5px rgba(0,0,0,0.2); }}
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
    theme_choice = st.selectbox("Choose your Divine Aspect", list(THEMES.keys()))
    
    st.write("---")
    st.write("### 🎭 Customize the Cast")
    st.write("Edit names and personalities. You can add yourself or your friends! Whoever is in this list can be randomly selected as the hidden Killer or Detective. Add or delete rows to change player count (Min: 4, Max: 12).")
    
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🎲 Randomize Base Cast", use_container_width=True):
            st.session_state.custom_cast = random.sample(CHARACTERS_DB, random.randint(5, 8))
            st.rerun()
            
    with col1:
        edited_cast = st.data_editor(
            st.session_state.custom_cast,
            num_rows="dynamic",
            column_config={
                "name": st.column_config.TextColumn("Character Name", required=True),
                "style": st.column_config.TextColumn("Personality / Vibe", required=True)
            },
            use_container_width=True,
            key="cast_editor"
        )
    
    st.write("---")
    
    if st.button("Begin the Mystery", use_container_width=True):
        if len(edited_cast) < 4:
            st.error("You must have at least 4 characters to play!")
        elif len(edited_cast) > 12:
            st.error("You can have a maximum of 12 characters!")
        else:
            roles = ['Detective', 'Killer'] + ['Innocent'] * (len(edited_cast) - 2)
            random.shuffle(roles)
            used_names = []
            
            for i, char_data in enumerate(edited_cast):
                base_name = char_data.get('name', f"Unknown {i+1}").strip()
                if not base_name: base_name = f"Unknown {i+1}"
                
                name = base_name
                counter = 2
                while name in used_names:
                    name = f"{base_name} {counter}"
                    counter += 1
                used_names.append(name)
                
                style = char_data.get('style', "Normal.").strip()
                if not style: style = "Normal."
                
                # --- Dynamic Model Assignment ---
                assigned_role = roles[i]
                if assigned_role in ['Detective', 'Killer']:
                    assigned_model = random.choice(MASTERMIND_MODELS)
                elif style in ["Cryptic and mysterious.", "Paranoid and defensive.", "Dreamy and cosmic."]: 
                    assigned_model = random.choice(WILDCARD_MODELS)
                else:
                    assigned_model = random.choice(STANDARD_MODELS)
                
                st.session_state.players[name] = {
                    'role': assigned_role, 
                    'status': 'alive',
                    'style': style,
                    'model': assigned_model 
                }
            
            vic = random.choice(VICTIMS)
            cau = random.choice(CAUSES)
            st.session_state.prologue_text = f"The estate is in uproar. {vic} has been found dead—{cau}. The manor is sealed. The killer is in this room."
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
            sys_p = format_prompt(current_speaker, player_data['style'])
            
            if player_data['role'] == 'Killer':
                sys_p += " Deflect blame entirely onto someone else in the room."
            elif player_data['role'] == 'Detective':
                sys_p += " Subtly gather information. Do NOT sound like an investigator. Act like a normal guest."
                if st.session_state.god_whispers:
                    sys_p += f" You have a gut feeling: {st.session_state.god_whispers[-1]}. Weave this suspicion naturally into your dialogue without making it obvious."
                    
            formatted_log = format_transcript_for_prompt(st.session_state.day)
            user_p = f"Log:\n{formatted_log}\n\nWrite ONLY your next sentence. Do NOT write your name."
            
            with st.spinner(f"{current_speaker} is formulating their words..."):
                speaker_container = st.empty()
                raw_line = speaker_container.write_stream(stream_llm_response(player_data['model'], sys_p, user_p))
                
            clean_line = clean_llm_output(raw_line, current_speaker, list(alive_players.keys()))
            
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
    
    if 'current_guess' not in st.session_state:
        with st.spinner("The hidden Detective is reviewing the evidence..."):
            sys_p = f"You are the Detective. You MUST choose EXACTLY ONE name from this list: {', '.join(suspects)}. Output ONLY the name. Nothing else."
            formatted_log = format_transcript_for_prompt(st.session_state.day)
            user_p = f"Transcript:\n{formatted_log}\n\nWho is the killer? Name only."
            
            guess_resp = client.chat.completions.create(
                model=st.session_state.players[detective_name]['model'], 
                messages=[{'role': 'system', 'content': sys_p}, {'role': 'user', 'content': user_p}]
            )
            raw_guess = guess_resp.choices[0].message.content.strip()

            mentioned = [s for s in suspects if s.lower() in raw_guess.lower()]
            if len(mentioned) == 1:
                st.session_state.current_guess = mentioned[0] 
            elif len(mentioned) > 1:
                st.session_state.current_guess = random.choice(mentioned) 
            else:
                st.session_state.current_guess = random.choice(suspects)
                
            st.rerun() 

    final_guess = st.session_state.current_guess

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
    
    if not st.session_state.whisper_cast:
        target = st.selectbox("Select a mortal to point the Detective toward:", list(get_alive_players().keys()))
        
        if st.button("Cast Your Whisper", use_container_width=True):
            flavor_text = active_theme['god_prompt'].format(suspect=target)
            st.session_state.god_whispers.append(flavor_text)
            st.session_state.whisper_cast = True
            st.rerun()
    else:
        st.success(f"You whispered into the ether: '{st.session_state.god_whispers[-1]}'")
        
        if st.button("Continue to Night Phase", use_container_width=True):
            st.session_state.whisper_cast = False 
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
            
            resp = client.chat.completions.create(
                model=killer_model, 
                messages=[{'role': 'system', 'content': sys_p}, {'role': 'user', 'content': user_p}]
            )
            choice = resp.choices[0].message.content.strip()
            
            victim = random.choice(potential_victims)
            for p in potential_victims:
                if p.lower() in choice.lower():
                    victim = p
                    break
            
            st.session_state.players[victim]['status'] = 'dead'
            
            if 'current_guess' in st.session_state:
                del st.session_state.current_guess
            
            if st.session_state.players[victim]['role'] == 'Detective':
                st.session_state.game_phase = 'game_over_loss'
            else:
                summary = generate_daily_summary(st.session_state.day, formatted_log)
                st.session_state.day += 1
                st.session_state.summaries[st.session_state.day] = summary
                
                next_day_log = [{"speaker": "SYSTEM", "text": f"{victim} was found murdered in the night."}]
                
                dead_players = [k for k, v in st.session_state.players.items() if v['status'] == 'dead' and v['role'] != 'Detective']
                if dead_players and random.random() < 0.05:
                    revived = random.choice(dead_players)
                    st.session_state.players[revived]['status'] = 'alive'
                    
                    curses = [
                        "You suffer from complete memory loss. You do not remember who anyone is.",
                        "You remember everything EXCEPT how you were killed.",
                        "Your memories are completely wrong. Accuse random people of wild things."
                    ]
                    st.session_state.players[revived]['memory_curse'] = random.choice(curses)
                    
                    next_day_log.append({"speaker": "DIVINE", "text": f"A MIRACLE! {revived} has been revived by an angel... but their mind is altered."})
                
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
            sys_p = "You are a dark narrator. Write a 2-paragraph story. Use simple language."
            user_p = f"The killer ({killer_name}) successfully murdered the detective ({detective_name}). Paragraph 1: How {killer_name} got away with it. Paragraph 2: What dark things {killer_name} did with the rest of their life. NO confessions."
            
            resp = client.chat.completions.create(
                model=MASTERMIND_MODELS[0], 
                messages=[{'role': 'system', 'content': sys_p}, {'role': 'user', 'content': user_p}]
            )
        
    else:
        st.success("Justice has been served!")
        st.markdown(f"### **The triumphant Detective was:** 🔍 {detective_name}")
        st.markdown(f"### **The captured Killer was:** 🔪 {killer_name}")
        
        with st.spinner("Extracting the confession and epilogue..."):
            sys_p = "You are an uplifting narrator. Write a 2-paragraph story. Use simple language."
            user_p = f"The detective ({detective_name}) cornered the killer ({killer_name}). Paragraph 1: Detail the killer's exact Means, Motive, and Opportunity. Paragraph 2: What uplifting things the Detective did with the rest of their life."
            
            resp = client.chat.completions.create(
                model=MASTERMIND_MODELS[0], 
                messages=[{'role': 'system', 'content': sys_p}, {'role': 'user', 'content': user_p}]
            )
        
    st.markdown(f"<div class='summary-box'>{resp.choices[0].message.content}</div>", unsafe_allow_html=True)
    
    with st.expander("🛠️ Behind the Curtain: Reveal AI Models Used"):
        st.write("Here are the specific AI models that were powering each character during this game:")
        for char, data in st.session_state.players.items():
            role_hint = f" ({data['role']})" if data['role'] in ['Detective', 'Killer'] else ""
            st.write(f"- **{char}**{role_hint}: `🧠 {data['model']}`")

    if st.button("Start a New Mystery", use_container_width=True):
        st.session_state.clear()
        st.rerun()
