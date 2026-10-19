"""Groq client configuration."""

import os

from groq import Groq


def get_groq_client():
    """Create a Groq client using the environment API key."""

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is missing. Configure it in your "
            "backend environment."
        )

    return Groq(api_key=api_key)


def get_config():
    """Return the model configuration."""

    return {
        "GROQ_MODEL": os.getenv(
            "GROQ_MODEL",
            "llama-3.3-70b-versatile",
        ),
    }