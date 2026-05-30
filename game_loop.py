import ollama

# 1. Define the Character Sheets (System Prompts)
detective_prompt = """
You are a hard-boiled 1940s detective investigating a murder. 
Ask short, sharp, suspicious questions. Keep your response to exactly one sentence.
"""

suspect_prompt = """
You are Arthur, the Butler. You are innocent of the murder, but you are hiding a secret: 
you were stealing silver from the dining room at 8 PM (the time of the murder). 
Deflect, act nervous, and answer in exactly one sentence.
"""

# 2. Initialize the Master Transcript (The Game's Memory)
# We start by forcing the first question to kick off the loop
transcript = [
    {'role': 'user', 'content': "Detective: Where were you at 8 PM, Arthur?"}
]

print("Starting the Interrogation...\n")
print(f"{transcript[0]['content']}\n")

# 3. The Game Loop (Running for 3 turns)
for turn in range(3):
    
    # --- ARTHUR'S TURN ---
    # The Secretary hands Arthur his secret persona + the transcript history
    arthur_messages = [{'role': 'system', 'content': suspect_prompt}] + transcript
    
    # Generate Arthur's reply
    arthur_response = ollama.chat(model='llama3:8b', messages=arthur_messages)
    arthur_line = arthur_response['message']['content']
    
    print(f"Arthur: {arthur_line}\n")
    
    # Add Arthur's reply to the Master Transcript
    transcript.append({'role': 'assistant', 'content': f"Arthur: {arthur_line}"})
    
    # --- DETECTIVE'S TURN ---
    # The Secretary hands the Detective his persona + the updated transcript
    detective_messages = [{'role': 'system', 'content': detective_prompt}] + transcript
    
    # Generate the Detective's reply
    detective_response = ollama.chat(model='llama3:8b', messages=detective_messages)
    detective_line = detective_response['message']['content']
    
    print(f"Detective: {detective_line}\n")
    
    # Add the Detective's reply to the Master Transcript for the next loop
    transcript.append({'role': 'user', 'content': f"Detective: {detective_line}"})

print("Interrogation concluded.")
