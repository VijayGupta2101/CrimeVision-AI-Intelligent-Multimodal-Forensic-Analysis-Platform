"""Forensic chatbot with timestamp-aware evidence retrieval."""

import json
import os
import re

from services.session_store import session_store
from utils.groq_utils import get_groq_client


def parse_time_from_question(question):
    """Extract time references such as 'at 12 seconds'."""

    patterns = [
        r"\b(\d+(?:\.\d+)?)\s*(?:seconds?|secs?)\b",
        r"\b(?:at|around|near)\s+(\d+(?:\.\d+)?)\s*s\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, question.lower())

        if match:
            return float(match.group(1))

    return None


def get_event_at_time(timeline, timestamp, tolerance=1.0):
    """Retrieve timeline events near a requested time."""

    results = []

    for event in timeline:
        try:
            start = float(
                event.get(
                    "start",
                    event.get("timestamp", 0),
                )
            )
            end = float(event.get("end", start))
        except (TypeError, ValueError):
            continue

        if start - tolerance <= timestamp <= end + tolerance:
            results.append(event)

    return results


def query_chat(session_id, question, mode="video"):
    """Answer questions using stored analysis results."""

    context = session_store.get_session(session_id)

    if context is None:
        return {
            "status": "error",
            "answer": (
                "No analysis exists for this session. "
                "Analyze the evidence first."
            ),
        }

    timeline = context.get("timeline", [])

    requested_time = parse_time_from_question(question)

    if requested_time is not None:
        events = get_event_at_time(
            timeline,
            requested_time,
        )

        if events:
            return {
                "status": "success",
                "answer": (
                    f"Found {len(events)} indexed event(s) "
                    f"near {requested_time:.2f} seconds."
                ),
                "events": events,
            }

    try:
        client = get_groq_client()

        model = os.getenv(
            "GROQ_MODEL",
            "llama-3.3-70b-versatile",
        )

        evidence = {
            "transcript": context.get("transcript", ""),
            "timeline": timeline[:100],
            "forensic_analysis": context.get(
                "forensic_analysis",
                {},
            ),
        }

        prompt = f"""
Answer the user's question using only the supplied analysis.

Requirements:
- Do not invent facts or timestamps.
- Distinguish observed evidence from model interpretations.
- Mention uncertainty and missing evidence.
- Use timestamps when relevant.
- Do not claim that an incident is a proven crime.

Analysis mode: {mode}

Evidence:
{json.dumps(evidence, ensure_ascii=False, default=str)}

Question:
{question}
"""

        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an evidence-grounded "
                        "forensic analysis assistant."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.2,
        )

        answer = response.choices[0].message.content or (
            "The model returned no answer."
        )

        return {
            "status": "success",
            "answer": answer,
            "events": [],
        }

    except Exception:
        return {
            "status": "error",
            "answer": (
                "Chat analysis failed. Check the backend "
                "configuration and logs."
            ),
        }