"""Chat API route — free-form conversation with the LLM agent."""

from pydantic import BaseModel
from fastapi import APIRouter

from api.routes_game import _load_or_404
from agent.llm_client import LLMClient, LLMClientError
from agent.chat_prompt import CHAT_SYSTEM_PROMPT, build_chat_context

router = APIRouter(prefix="/api/game", tags=["chat"])

_client = LLMClient()

MAX_HISTORY = 20


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []


class ChatResponse(BaseModel):
    reply: str
    provider: str
    model: str
    llm_available: bool


@router.post("/{game_id}/chat")
def chat(game_id: str, req: ChatRequest) -> ChatResponse:
    """Free-form chat with the AI advisor about the current game.

    The LLM receives the full game context (state, upcoming cards,
    bottlenecks) plus conversation history. No JSON output constraints.
    """
    state = _load_or_404(game_id)

    if not _client.is_available():
        return ChatResponse(
            reply=(
                "LLM is not configured. Set `WHOP_LLM_PROVIDER` in your "
                "environment to enable chat (e.g. ollama, claude, openai)."
            ),
            provider="none",
            model="none",
            llm_available=False,
        )

    # Build system prompt with current game context
    context = build_chat_context(state)
    system = f"{CHAT_SYSTEM_PROMPT}\n\n{context}"

    # Truncate history to last N messages, then append current user message
    history = [{"role": m.role, "content": m.content} for m in req.history[-MAX_HISTORY:]]
    history.append({"role": "user", "content": req.message})

    try:
        resp = _client.chat(system, history)
        return ChatResponse(
            reply=resp.text,
            provider=resp.provider,
            model=resp.model,
            llm_available=True,
        )
    except LLMClientError as e:
        return ChatResponse(
            reply=f"LLM error: {e}. Try again or check your provider configuration.",
            provider=_client._provider,
            model="error",
            llm_available=True,
        )
