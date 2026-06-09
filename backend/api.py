from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

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

# Standard endpoint for quick, non-streaming tasks (like the day summary)
@app.post("/generate-response")
async def generate_response(request: Request):
    data = await request.json()
    model_id = data.get("model")
    sys_prompt = data.get("sys_prompt")
    user_prompt = data.get("user_prompt")
    max_tokens = data.get("max_tokens", 60) 
    
    completion = client.chat.completions.create(
        model=model_id,
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_prompt}  
        ],
        max_tokens=max_tokens
    )
    return {"response": completion.choices[0].message.content}

# NEW STREAMING ENDPOINT
@app.post("/generate-response-stream")
async def generate_response_stream(request: Request):
    data = await request.json()
    model_id = data.get("model")
    sys_prompt = data.get("sys_prompt")
    user_prompt = data.get("user_prompt")
    max_tokens = data.get("max_tokens", 400) 
    
    def event_stream():
        stream = client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=max_tokens,
            stream=True # This tells OpenRouter to open a live pipe
        )
        for chunk in stream:
            # Yield the raw text chunks as they arrive
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    return StreamingResponse(event_stream(), media_type="text/plain")
