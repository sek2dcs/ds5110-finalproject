from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import os
from dotenv import load_dotenv
load_dotenv() # This loads the variables from your .env file

app = FastAPI()

# Allow your local HTML file to "talk" to this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY"),
)

@app.post("/generate-response")
async def generate_response(request: Request):
    data = await request.json()
    model_id = data.get("model")
    sys_prompt = data.get("sys_prompt")
    user_prompt = data.get("user_prompt")
    
    # Send request to OpenRouter
    completion = client.chat.completions.create(
        model=model_id,
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )
    
    return {"response": completion.choices[0].message.content}
