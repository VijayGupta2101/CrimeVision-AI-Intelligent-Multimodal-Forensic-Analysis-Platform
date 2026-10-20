"""Evidence-grounded forensic chatbot for CrimeVision AI."""

import json
import os
import re
from typing import Any

from services.session_store import get_session


def parse_time_from_question(question: str) -> float | None:
    """
    Extract a timestamp from questions such as:
    'What happened at 5 seconds?'
    'Who appeared at 01:25?'
    'Describe the event at 12.5s.'
    """
    patterns = [
        r"\b(\d+):([0-5]\d)(?:\.(\d+))?\b",
        r"\b(\d+(?:\.\d+)?)\s*(?:seconds?|secs?|sec|s)\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, question, re.IGNORECASE)

        if not match:
            continue

        if ":" in match.group(0):
            minutes = int(match.group(1))
            seconds = int(match.group(2))
            fraction = match.group(3)

            timestamp = minutes * 60 + seconds

            if fraction:
                timestamp += float("0." + fraction)

            return timestamp

        return float(match.group(1))

    return None


def _event_time(event: dict[str, Any]) -> float | None:
    """Read a numeric timestamp from a timeline event."""
    for key in (
        "seconds",
        "timestamp_seconds",
        "start_raw",
        "start",
        "time_seconds",
        "seconds_offset",
    ):
        value = event.get(key)

        if isinstance(value, (int, float)):
            return float(value)

        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                pass

    value = event.get("timestamp", event.get("time"))

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        match = re.fullmatch(
            r"\s*(?:(\d+):)?(\d+)(?:\.(\d+))?\s*",
            value,
        )

        if match:
            minutes = int(match.group(1) or 0)
            seconds = int(match.group(2))
            fraction = match.group(3)

            return minutes * 60 + seconds + (
                float("0." + fraction) if fraction else 0
            )

    return None


def get_event_at_time(
    timeline: list[dict[str, Any]],
    requested_time: float,
    tolerance: float = 0.5,
) -> dict[str, Any] | None:
    """Find an event that overlaps or is close to the requested time."""
    candidates = []

    for event in timeline:
        start = _event_time(event)

        if start is None:
            continue

        end_value = event.get("end_raw", event.get("end"))
        end = start

        if isinstance(end_value, (int, float)):
            end = float(end_value)
        elif isinstance(end_value, str):
            try:
                end = float(end_value)
            except ValueError:
                pass

        if start <= requested_time <= end:
            return event

        distance = abs(start - requested_time)

        if distance <= tolerance:
            candidates.append((distance, event))

    if candidates:
        candidates.sort(key=lambda item: item[0])
        return candidates[0][1]

    return None


def _json_safe_context(context: dict[str, Any]) -> str:
    """Serialize evidence into a prompt-safe JSON representation."""
    return json.dumps(
        context,
        ensure_ascii=False,
        indent=2,
        default=str,
    )


def _get_groq_client():
    """Create a Groq client when credentials are configured."""
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        return None

    try:
        from groq import Groq

        return Groq(api_key=api_key)

    except ImportError:
        return None


def query_chat(
    session_id: str,
    question: str,
    mode: str = "video",
) -> dict[str, Any]:
    """
    Answer a question using a saved forensic session.

    Returns a dictionary containing the answer and supporting evidence.
    """
    if not session_id:
        return {
            "success": False,
            "error": "A session_id is required.",
        }

    if not question or not question.strip():
        return {
            "success": False,
            "error": "A question is required.",
        }

    context = get_session(session_id)

    if context is None:
        return {
            "success": False,
            "error": "Analysis session not found. Analyze a file first.",
        }

    timeline = context.get("timeline", [])

    if not isinstance(timeline, list):
        timeline = []

    requested_time = parse_time_from_question(question)

    if requested_time is not None:
        event = get_event_at_time(timeline, requested_time)

        if event:
            return {
                "success": True,
                "answer": (
                    f"Evidence recorded near {requested_time:.2f} seconds: "
                    f"{event.get('description') or event.get('event') or event.get('text') or json.dumps(event, ensure_ascii=False)}"
                ),
                "evidence": event,
                "timestamp": requested_time,
                "source": "saved_timeline",
            }

        return {
            "success": True,
            "answer": (
                f"Information not found: no matching timeline event "
                f"was recorded near {requested_time:.2f} seconds."
            ),
            "evidence": [],
            "timestamp": requested_time,
            "source": "saved_timeline",
        }

    client = _get_groq_client()

    if client is None:
        return {
            "success": False,
            "error": (
                "Groq is unavailable. Check GROQ_API_KEY and install "
                "the groq package."
            ),
        }

    model = os.getenv(
        "GROQ_MODEL",
        "llama-3.3-70b-versatile",
    )

    prompt = f"""
You are the evidence-grounded forensic assistant for CrimeVision AI.

Answer the investigator's question using ONLY the supplied analysis data.

Rules:
1. Never invent people, actions, objects, locations, or timestamps.
2. Distinguish observed evidence from interpretations and hypotheses.
3. If the data does not support an answer, say:
   "Information not found in the available evidence."
4. Do not claim that a person committed a crime merely because an object
   or action was detected.
5. Include relevant timestamps and evidence sources when available.
6. If visual and audio findings conflict, disclose the conflict.
7. Treat scenario hypotheses as provisional, not established facts.

Analysis mode: {mode}

Saved forensic evidence:
{_json_safe_context(context)}

Investigator's question:
{question}

Provide a concise, factual answer.
"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a careful forensic evidence assistant. "
                        "Do not invent evidence."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.1,
            max_tokens=1200,
        )

        answer = response.choices[0].message.content or ""

        return {
            "success": True,
            "answer": answer.strip(),
            "source": "groq",
        }

    except Exception as exc:
        return {
            "success": False,
            "error": f"Chat request failed: {exc}",
        }