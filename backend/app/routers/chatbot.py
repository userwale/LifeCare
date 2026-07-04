"""
app/routers/chatbot.py – LLaMA-powered chatbot endpoints.
"""
from __future__ import annotations

import logging
from typing import List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_active_user
from app.database import get_db
from app.models.user import User

router = APIRouter(prefix="/api/v1/chatbot", tags=["Chatbot"])
logger = logging.getLogger(__name__)

OLLAMA_API_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "llama3"  # Standard Ollama model name, user can override


class ChatMessage(BaseModel):
    role: str       # "user" | "assistant" | "system"
    content: str


class ChatQueryRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []


class ChatQueryResponse(BaseModel):
    response: str
    model_used: str
    simulated: bool


# ── MOCK FALLBACK SYSTEM ──────────────────────────────────────────────────────
# Generates realistic clinical / ergonomic responses when Ollama is offline.
MOCK_ANSWERS = {
    "cervical": (
        "Cervicalgie refers to neck pain that can arise from poor posture, such as looking down at your phone "
        "or computer screen for extended periods (often called 'text neck').\n\n"
        "**Ergonomic tips to alleviate neck strain:**\n"
        "1. **Adjust screen height:** The top of your computer monitor should be at or slightly below eye level.\n"
        "2. **Take micro-breaks:** Follow the 20-20-20 rule: every 20 minutes, look at an object 20 feet away for 20 seconds.\n"
        "3. **Neck stretches:** Gently tilt your ear toward your shoulder and hold for 15 seconds. Repeat on both sides."
    ),
    "lombal": (
        "Lombalgie (lower back pain) is extremely common and is frequently linked to a sedentary lifestyle, "
        "poor seating postures, or weak core stabilizers.\n\n"
        "**Best practices for lower back health:**\n"
        "1. **Support your lumbar curve:** Use a chair with dedicated lumbar support or place a rolled-up towel behind your lower back.\n"
        "2. **Maintain a 90-90-90 rule:** Keep your knees, hips, and elbows bent at 90 degrees with your feet flat on the floor.\n"
        "3. **Stay active:** Make sure to stand up and walk around for at least 5 minutes every hour."
    ),
    "radiculopathie": (
        "Radiculopathy occurs when a nerve root in the spine is compressed or irritated, leading to pain, "
        "numbness, or tingling that radiates down the arm (cervical radiculopathy) or leg (sciatica).\n\n"
        "**Crucial steps to take:**\n"
        "1. **Consult a professional:** If you experience radiating numbness, muscle weakness, or shooting pain, "
        "please consult a medical specialist or physiotherapist.\n"
        "2. **Avoid static postures:** Avoid sitting or standing in one position for too long; change position frequently.\n"
        "3. **Gentle mobility:** Focus on pain-free movements. Never force a stretch or exercise that causes radiating discomfort."
    ),
    "posture": (
        "Good posture is not about a rigid, frozen position, but rather maintaining a dynamic and neutral alignment of the spine.\n\n"
        "**Key pillars of ergonomic posture:**\n"
        "- **Head:** Centered directly over the shoulders, ears aligned with your collarbone.\n"
        "- **Shoulders:** Relaxed and rolled back, not hunched or rounded forward.\n"
        "- **Spine:** Supported in its natural 'S' shape.\n"
        "- **Feet:** Resting flat on the floor or a footrest."
    ),
    "ergonom": (
        "Ergonomics is the science of designing the workplace to fit the user, rather than forcing the user to adapt to the equipment.\n\n"
        "**Quick office ergonomics checklist:**\n"
        "- Is your keyboard and mouse close enough so your elbows remain at your sides?\n"
        "- Is your chair adjusted so your thighs are parallel to the floor?\n"
        "- Is your workspace well-lit to prevent eye strain?"
    )
}

DEFAULT_MOCK = (
    "Hello! I am the **LifeCare AI Virtual Assistant**. I am here to help you understand posture analysis, "
    "diagnose ergonomics issues, and suggest therapeutic exercises.\n\n"
    "To help me assist you, feel free to ask about:\n"
    "- **Neck pain** (Cervicalgie) or **low back pain** (Lombalgie)\n"
    "- **Nerve irritation** (Radiculopathie)\n"
    "- **Ergonomic office setup** guidelines\n"
    "- **Correct sitting and standing postures**"
)


def _generate_mock_response(query: str) -> str:
    query_lower = query.lower()
    for key, answer in MOCK_ANSWERS.items():
        if key in query_lower:
            return answer
    return DEFAULT_MOCK


# ── POST /query ───────────────────────────────────────────────────────────────
@router.post(
    "/query",
    response_model=ChatQueryResponse,
    summary="Query the LLaMA virtual health assistant",
)
async def query_chatbot(
    payload: ChatQueryRequest,
    current_user: User = Depends(get_current_active_user),
) -> dict:
    # 1. Structure the system prompt
    system_prompt = (
        "You are the LifeCare AI Virtual Health & Posture Assistant. Your primary goal is to help users "
        "understand their ergonomic setup, prevent muscle pain (like cervicalgie, lombalgie, radiculopathie), "
        "recommend safe stretches, and guide them in interpreting their posture analysis results. "
        "Keep your answers helpful, highly professional, encouraging, and structured in clear markdown lists. "
        "If a user asks about severe symptoms, always remind them to consult a qualified physician."
    )

    # 2. Build Chat payload for Ollama
    # Convert history
    ollama_messages = [{"role": "system", "content": system_prompt}]
    for msg in payload.history:
        ollama_messages.append({"role": msg.role, "content": msg.content})
    
    # Append the user's latest query
    ollama_messages.append({"role": "user", "content": payload.message})

    # 3. Attempt Ollama API query
    async with httpx.AsyncClient() as client:
        try:
            logger.info("Attempting to connect to Ollama LLaMA service at %s", OLLAMA_API_URL)
            # Timeout is set to 8.0 seconds to prevent locking resources
            response = await client.post(
                OLLAMA_API_URL,
                json={
                    "model": OLLAMA_MODEL,
                    "messages": ollama_messages,
                    "stream": False,
                },
                timeout=8.0,
            )
            if response.status_code == 200:
                data = response.json()
                llama_reply = data["message"]["content"]
                return {
                    "response": llama_reply,
                    "model_used": f"LLaMA (Ollama: {OLLAMA_MODEL})",
                    "simulated": False,
                }
            else:
                logger.warning("Ollama returned status code %s. Falling back.", response.status_code)
        except (httpx.ConnectError, httpx.TimeoutException) as err:
            logger.warning("Ollama connection failed or timed out: %s. Initiating mock fallback.", err)
        except Exception as exc:
            logger.error("Unexpected error contacting Ollama: %s", exc)

    # 4. Fallback to high-quality simulated response
    mock_reply = _generate_mock_response(payload.message)
    return {
        "response": mock_reply,
        "model_used": "LifeCare Rule-Based AI Engine (LLaMA Offline)",
        "simulated": True,
    }
