import os
from typing import Any, Dict


def get_config() -> Dict[str, Any]:
    """Return the Groq configuration used by the caption refinement flow."""
    return {
        "groq_model": os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
        "groq_api_key": os.getenv("GROQ_API_KEY"),
    }


def get_groq_client():
    """Return a configured Groq client if the SDK and API key are available."""
    api_key = get_config().get("groq_api_key")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not set. Caption refinement is disabled.")

    try:
        from groq import Groq
    except ImportError as exc:  # pragma: no cover - defensive fallback
        raise RuntimeError("The groq package is not installed.") from exc

    return Groq(api_key=api_key)
