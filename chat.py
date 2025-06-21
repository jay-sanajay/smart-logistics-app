from fastapi import APIRouter
from pydantic import BaseModel
import requests
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

class ChatRequest(BaseModel):
    message: str

@router.post("/chat")
async def chat_with_huggingface(request: ChatRequest):
    api_key = os.getenv("HUGGINGFACE_API_KEY")
    if not api_key:
        return {"reply": "❌ HuggingFace API key not found."}

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "inputs": f"Answer this question: {request.message}"
    }

    try:
        response = requests.post(
    "https://api-inference.huggingface.co/models/sshleifer/tiny-gpt2",
    headers=headers,
    json=payload
)
        response.raise_for_status()
        result = response.json()

        # Extract reply based on expected format
        if isinstance(result, list) and "generated_text" in result[0]:
            reply = result[0]["generated_text"]
        elif isinstance(result, dict) and "generated_text" in result:
            reply = result["generated_text"]
        else:
            reply = "🤖 No response generated."

        return {"reply": reply.strip()}
    except Exception as e:
        return {"reply": f"⚠️ Error: {str(e)}"}
