# chat_gemini.py
from fastapi import APIRouter
from pydantic import BaseModel
import google.generativeai as genai
import os

router = APIRouter()

# ✅ Correct configuration with working model
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))  # Or hardcode for dev: "your-key"

class ChatRequest(BaseModel):
    message: str

@router.post("/chat")
async def chat_with_gemini(request: ChatRequest):
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")  # ✅ use a correct model
        chat = model.start_chat()
        response = chat.send_message(request.message)
        return {"reply": response.text}
    except Exception as e:
        return {"reply": f"❌ Error: {str(e)}"}
