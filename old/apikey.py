import requests

# Put the professor's API key here
api_key = "YOUR_OPENROUTER_API_KEY"

response = requests.get(
    "https://openrouter.ai/api/v1/models",
    headers={"Authorization": f"Bearer {api_key}"}
)

models = response.json().get("data", [])

print("--- OPENROUTER MODEL IDs ---")
for m in models:
    # Filter for the names in your screenshot
    name = m['name'].lower()
    if "qwen" in name or "minimax" in name or "glm" in name or "kimi" in name:
        print(f"Display Name: {m['name']} -> API ID: {m['id']}")
