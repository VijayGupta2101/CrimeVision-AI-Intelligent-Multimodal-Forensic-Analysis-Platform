import os
import json
import logging
from threading import Lock

from groq import Groq

logger = logging.getLogger(__name__)

_client = None
_client_lock = Lock()


def get_client():
    """Create the Groq client once."""
    global _client

    if _client is None:
        with _client_lock:
            if _client is None:
                api_key = os.getenv("GROQ_API_KEY")

                if not api_key:
                    raise RuntimeError(
                        "GROQ_API_KEY is missing. "
                        "Add it to your backend .env file."
                    )

                _client = Groq(api_key=api_key)

    return _client


class ChatService:
    """Conversational assistant for general and forensic questions."""

    def __init__(self):
        self.model = os.getenv(
            "GROQ_MODEL",
            "openai/gpt-oss-120b",
        )

        # Keep conversation history separately for each session.
        self.sessions = {}
        self.sessions_lock = Lock()
        self.max_history_messages = 20

    def chat(
        self,
        question,
        session_id="default",
        context=None,
    ):
        if not isinstance(question, str) or not question.strip():
            return {
                "success": False,
                "error": "Please enter a question.",
            }

        question = question.strip()
        session_id = str(session_id or "default")

        system_prompt = """
You are CrimeVision AI Assistant, a helpful conversational AI.

CONVERSATION:
- Respond naturally, clearly, and directly.
- Answer the actual question being asked.
- Never repeat a previous answer unless the user asks you to repeat it.
- Remember earlier messages in the current conversation.
- Understand follow-up questions using the conversation history.
- Ask a clarifying question if the request is genuinely ambiguous.
- Help with general knowledge, explanations, coding, writing,
  reasoning, and questions about the user's project.
- Use headings, numbered steps, or code blocks when useful.
- If the user asks for code, provide usable code and explain where it goes.

FORENSIC EVIDENCE:
- When the question concerns uploaded evidence, use the supplied
  analysis context.
- Distinguish visible or recorded observations from interpretations.
- Never invent evidence, identities, locations, timestamps, or facts.
- Clearly state when the available evidence cannot answer a question.
- Treat generated hypotheses as provisional, not established facts.
- Do not claim to have examined a file that is not in the supplied context.

IMPORTANT:
You are a conversational assistant, not a fixed-response FAQ bot.
Generate a new answer based on the current question, the conversation,
and the relevant context.
"""

        # Keep evidence context bounded to avoid excessively large prompts.
        if context is None:
            context = {}

        if not isinstance(context, (dict, list, str)):
            context = str(context)

        try:
            context_text = json.dumps(
                context,
                ensure_ascii=False,
                default=str,
            )

            if len(context_text) > 18000:
                context_text = context_text[:18000] + (
                    "\n[Context shortened because it was too large.]"
                )

            messages = [
                {
                    "role": "system",
                    "content": system_prompt
                    + "\n\nCURRENT EVIDENCE CONTEXT:\n"
                    + context_text,
                }
            ]

            # Retrieve recent conversation history.
            with self.sessions_lock:
                history = list(
                    self.sessions.get(session_id, [])
                )

            messages.extend(history)
            messages.append({
                "role": "user",
                "content": question,
            })

            response = get_client().chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=1500,
            )

            answer = (
                response.choices[0].message.content or ""
            ).strip()

            if not answer:
                answer = (
                    "I couldn't generate a response. "
                    "Please try asking your question another way."
                )

            # Save this exchange for future follow-up questions.
            with self.sessions_lock:
                history = self.sessions.setdefault(
                    session_id,
                    [],
                )

                history.extend([
                    {
                        "role": "user",
                        "content": question,
                    },
                    {
                        "role": "assistant",
                        "content": answer,
                    },
                ])

                self.sessions[session_id] = history[
                    -self.max_history_messages:
                ]

            return {
                "success": True,
                "answer": answer,
                "session_id": session_id,
            }

        except Exception as exc:
            logger.exception("Chat generation failed")

            return {
                "success": False,
                "error": str(exc),
            }


chat_service = ChatService()