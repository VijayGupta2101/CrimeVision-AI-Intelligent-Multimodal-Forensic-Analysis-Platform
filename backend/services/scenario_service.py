"""Evidence-grounded scenario hypothesis generation."""

import json
import os

from groq import Groq


def generate_scenarios(forensic_facts: dict) -> dict:
    """Generate three hypotheses without treating them as proven facts."""

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        return {
            "status": "error",
            "error": "GROQ_API_KEY is not configured.",
            "scenarios": [],
        }

    client = Groq(api_key=api_key)
    model = os.getenv(
        "GROQ_MODEL", "llama-3.3-70b-versatile"
    )

    prompt = f"""
You are assisting with preliminary forensic evidence review.

Analyze only the supplied evidence:
{json.dumps(forensic_facts, ensure_ascii=False, default=str)}

Return exactly three provisional hypotheses:
1. Primary scenario: best supported by available evidence.
2. Alternative scenario: a plausible competing explanation.
3. Low-support scenario: a plausible but weakly supported alternative.

Rules:
- Do not declare any person guilty.
- Do not invent people, actions, timestamps, or objects.
- Separate observed facts from interpretations.
- Explicitly state evidence gaps and contradictory information.
- Do not assign numerical probabilities unless validated numerical
  probabilities are present in the input.
- If the evidence is insufficient, say so.
- Treat audio statements as statements in the recording, not
  independently verified facts.

Return valid JSON only, using this schema:
{{
  "scenarios": [
    {{
      "title": "Primary scenario",
      "explanation": "string",
      "supporting_evidence": ["string"],
      "contradicting_evidence": ["string"],
      "missing_evidence": ["string"],
      "status": "provisional"
    }},
    {{
      "title": "Alternative scenario",
      "explanation": "string",
      "supporting_evidence": ["string"],
      "contradicting_evidence": ["string"],
      "missing_evidence": ["string"],
      "status": "provisional"
    }},
    {{
      "title": "Low-support scenario",
      "explanation": "string",
      "supporting_evidence": ["string"],
      "contradicting_evidence": ["string"],
      "missing_evidence": ["string"],
      "status": "provisional"
    }}
  ]
}}
"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Return evidence-grounded JSON. "
                        "Do not fabricate facts."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=2500,
        )

        content = response.choices[0].message.content or ""
        start = content.find("{")
        end = content.rfind("}")

        if start == -1 or end == -1:
            raise ValueError("Model did not return a JSON object.")

        result = json.loads(content[start:end + 1])
        scenarios = result.get("scenarios", [])

        if len(scenarios) != 3:
            raise ValueError(
                "Expected exactly three scenario hypotheses."
            )

        return {
            "status": "success",
            "scenarios": scenarios,
            "disclaimer": (
                "These are provisional investigative hypotheses, "
                "not findings of guilt or validated probabilities."
            ),
        }

    except Exception as exc:
        return {
            "status": "error",
            "error": str(exc),
            "scenarios": [],
        }