import streamlit as st
import random
import time
import re
import os
from huggingface_hub import InferenceClient

# --- ENGINE SETUP (HUGGING FACE) ---
# This pulls the HF_TOKEN you saved in your Space's "Secrets"
hf_token = os.environ.get("HF_TOKEN")
client = InferenceClient(token=hf_token)

# The model powering the simulation in the cloud
MODEL = "meta-llama/Meta-Llama-3-8B-Instruct"

# --- CONFIGURATION & LORE ---
CHARACTERS_DB = [
    {"name": "Arthur the Butler", "style": "Formal and dry."},
    {"name": "Beatrice the Widow", "style": "Melodramatic and weeping."},
    {"name": "Charles the Doctor", "style": "Clinical and precise."},
    {"name": "Diana the Heiress", "style": "Snobby and bored."},
    {"name": "Edward the Chauffeur", "style": "Gruff and blunt."},
    {"name": "Lydia the Journalist", "style": "Inquisitive and fast-talking."},
    {"name": "Reginald the Earl", "style": "Pompous and arrogant."},
    {"name": "Victor the Lawyer", "style": "Legalistic and defensive."},
    {"name": "Clara the Niece", "style": "Naive and optimistic."},
    {"name": "Marcus the Mayor", "style": "Diplomatic and evasive."}
]

THEMES = {
    "The Omniscient Magistrate": {
        "god_prompt": "{suspect} is lying. Press them.",
        "bg": "#f4f6f9", "box": "#ffffff", "primary": "#2c3e50", "border": "2px solid #2c3e50"
    }
}

VICTIMS = ["Lord Blackwood", "Lady Ashbury", "Professor Sterling"]
CAUSES = ["poisoned", "bludgeoned", "thrown from the balcony"]

# --- STATE MANAGEMENT ---
if 'game_phase' not in st.session_state:
    st.session_state.game_phase = 'setup'
    st.session_state.players = {}
    st.session_state.daily_transcripts = {1: []}
    st.session_state.day = 1
    st.session_state.daily_order = []
    st.session_state.speaker_idx = 0
    st.session_state.custom_cast = random.sample(CHARACTERS_DB, 6)

# --- CLOUD ENGINE FUNCTIONS ---
def stream_llm_response(sys_prompt, user_prompt, temp=0.5):
    messages = [{"role": "system", "content": sys_prompt}, {"role": "user", "content": user_prompt}]
    stream = client.chat_completion(model=MODEL, messages=messages, temperature=temp, stream=True)
    for chunk in stream:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content

def get_llm_response(sys_prompt, user_prompt):
    messages = [{"role": "system", "content": sys_prompt}, {"role": "user", "content": user_prompt}]
    resp = client.chat_completion(model=MODEL, messages=messages)
    return resp.choices[0].message.content

# --- UI & LOGIC ---
st.set_page_config(page_title="Mystery Sim", layout="centered")

if st.session_state.game_phase == 'setup':
    st.title("⚖️ The Hidden Inquiry")
    cast = st.data_editor(st.session_state.custom_cast, num_rows="dynamic")
    if st.button("Begin the Mystery"):
        roles = ['Detective', 'Killer'] + ['Innocent'] * (len(cast) - 2)
        random.shuffle(roles)
        for i, char in enumerate(cast):
            st.session_state.players[char['name']] = {'role': roles[i], 'status': 'alive', 'style': char['style']}
        st.session_state.game_phase = 'day_interrogation'
        st.rerun()

elif st.session_state.game_phase == 'day_interrogation':
    st.write(f"### Day {st.session_state.day}")
    
    # Initialize order
    if not st.session_state.daily_order:
        players = list(st.session_state.players.keys())
        random.shuffle(players)
        st.session_state.daily_order = players
        
    current_speaker = st.session_state.daily_order[st.session_state.speaker_idx]
    
    if st.button(f"Let {current_speaker} Speak"):
        sys_p = f"You are {current_speaker}. Style: {st.session_state.players[current_speaker]['style']}. Rules: Speak 1 sentence. No narration."
        user_p = "What do you say?"
        
        with st.spinner("Thinking..."):
            line = "".join(stream_llm_response(sys_p, user_p))
            st.session_state.daily_transcripts[st.session_state.day].append({"speaker": current_speaker, "text": line})
            st.session_state.speaker_idx += 1
            if st.session_state.speaker_idx >= len(st.session_state.daily_order):
                st.session_state.game_phase = 'night_phase'
            st.rerun()

    # Display Log
    for item in st.session_state.daily_transcripts[st.session_state.day]:
        st.markdown(f"**{item['speaker']}:** {item['text']}")

elif st.session_state.game_phase == 'night_phase':
    st.write("### Night falls...")
    if st.button("End Day"):
        st.session_state.day += 1
        st.session_state.daily_order = []
        st.session_state.speaker_idx = 0
        st.session_state.daily_transcripts[st.session_state.day] = []
        st.session_state.game_phase = 'day_interrogation'
        st.rerun()
