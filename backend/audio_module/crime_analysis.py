"""Audio forensic analysis for the CrimeVision AI platform."""

import json
import os
from pathlib import Path
from typing import Any

from services.audio_service import audio_service


class CrimeAnalysis:
    """Analyze audio and extract evidence-based forensic findings."""

    def __init__(self):
        self.audio_service = audio_service

    def transcribe_audio(
        self,
        audio_path: str,
        language: str | None = None,
    ) -> dict[str, Any]:
        """
        Transcribe an audio file and return timestamped speech segments.

        Supported language examples:
        Telugu, Hindi, French, and English.
        """
        path = Path(audio_path)

        if not path.is_file():
            return {
                "success": False,
                "error": f"Audio file not found: {audio_path}",
            }

        try:
            result = self.audio_service.transcribe_audio(
                str(path),
                language=language,
            )

            if not isinstance(result, dict):
                return {
                    "success": False,
                    "error": "Audio service returned an invalid response.",
                }

            return result

        except Exception as exc:
            return {
                "success": False,
                "error": f"Audio transcription failed: {exc}",
            }

    @staticmethod
    def _normalize_segments(
        segments: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Normalize timestamped speech segments."""
        normalized = []

        for segment in segments:
            if not isinstance(segment, dict):
                continue

            start = segment.get(
                "start",
                segment.get("start_raw", 0.0),
            )
            end = segment.get(
                "end",
                segment.get("end_raw", start),
            )

            try:
                start = float(start or 0.0)
                end = float(end if end is not None else start)
            except (TypeError, ValueError):
                continue

            normalized.append(
                {
                    "start": start,
                    "end": max(start, end),
                    "text": str(segment.get("text", "")).strip(),
                    "source": "audio",
                    "verification_status": "unverified",
                }
            )

        return sorted(normalized, key=lambda item: item["start"])

    def generate_scenarios(
        self,
        forensic_facts: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Generate three provisional scenarios from extracted audio evidence.

        These are investigative hypotheses, not conclusions of guilt.
        """
        api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            return [
                {
                    "scenario": "Primary scenario",
                    "status": "not_generated",
                    "reason": "GROQ_API_KEY is not configured.",
                },
                {
                    "scenario": "Alternative scenario",
                    "status": "not_generated",
                    "reason": "GROQ_API_KEY is not configured.",
                },
                {
                    "scenario": "Low-probability scenario",
                    "status": "not_generated",
                    "reason": "GROQ_API_KEY is not configured.",
                },
            ]

        try:
            from groq import Groq

            client = Groq(api_key=api_key)

            prompt = f"""
You are assisting with a forensic audio investigation.

Analyze only the supplied audio analysis data.

Generate exactly three provisional investigative hypotheses:
1. Primary scenario: the explanation most consistent with the evidence.
2. Alternative scenario: another plausible explanation.
3. Low-probability scenario: a less likely but plausible explanation.

Requirements:
- Do not invent statements, people, locations, or events.
- Do not assume that an allegation is true.
- Distinguish recorded speech from interpretation.
- Include supporting evidence and missing evidence.
- Explain uncertainty and possible alternative interpretations.
- Do not identify anyone as guilty.
- If evidence is insufficient, state that clearly.

Return valid JSON in this format:
{{
  "scenarios": [
    {{
      "type": "primary",
      "description": "...",
      "supporting_evidence": [],
      "missing_evidence": [],
      "uncertainties": [],
      "status": "provisional"
    }},
    {{
      "type": "alternative",
      "description": "...",
      "supporting_evidence": [],
      "missing_evidence": [],
      "uncertainties": [],
      "status": "provisional"
    }},
    {{
      "type": "low_probability",
      "description": "...",
      "supporting_evidence": [],
      "missing_evidence": [],
      "uncertainties": [],
      "status": "provisional"
    }}
  ]
}}

Audio forensic findings:
{json.dumps(forensic_facts, ensure_ascii=False, default=str)}
"""

            response = client.chat.completions.create(
                model=os.getenv(
                    "GROQ_MODEL",
                    "llama-3.3-70b-versatile",
                ),
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a cautious forensic analysis assistant. "
                            "Never fabricate evidence."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                temperature=0.1,
                max_tokens=1800,
            )

            content = response.choices[0].message.content or ""
            content = content.strip()

            # Handle JSON enclosed in Markdown code fences.
            if content.startswith("```"):
                content = content.split("\n", 1)[-1]
                if content.endswith("```"):
                    content = content[:-3]

            parsed = json.loads(content)
            scenarios = parsed.get("scenarios", [])

            if not isinstance(scenarios, list):
                raise ValueError("The model returned an invalid scenarios list.")

            return scenarios[:3]

        except Exception as exc:
            return [
                {
                    "scenario": "Scenario generation",
                    "status": "failed",
                    "reason": str(exc),
                }
            ]

    def analyze_audio(
        self,
        audio_path: str,
        language: str | None = None,
    ) -> dict[str, Any]:
        """Run transcription and build timestamped audio findings."""
        transcription = self.transcribe_audio(
            audio_path,
            language=language,
        )

        if not transcription.get("success"):
            return transcription

        transcript = str(transcription.get("transcript", ""))
        segments = self._normalize_segments(
            transcription.get("segments", [])
        )

        timeline = self.audio_service.generate_timeline(segments)

        # Use the existing audio service's forensic extraction methods.
        facts = self.audio_service.extract_forensic_facts(transcript)

        if not isinstance(facts, dict):
            facts = {
                "observations": [],
                "uncertainties": [
                    "Forensic fact extraction returned no structured result."
                ],
            }

        scenarios = self.generate_scenarios(
            {
                "transcript": transcript,
                "segments": segments,
                "timeline": timeline,
                "facts": facts,
            }
        )

        return {
            "success": True,
            "analysis_type": "audio_forensics",
            "audio_path": str(Path(audio_path).resolve()),
            "language": language,
            "transcript": transcript,
            "segments": segments,
            "timeline": timeline,
            "forensic_facts": facts,
            "scenario_hypotheses": scenarios,
            "metadata": {
                "segment_count": len(segments),
                "timeline_event_count": len(timeline),
                "scenario_count": len(scenarios),
                "verification_status": "unverified",
            },
        }


crime_analysis = CrimeAnalysis()


def analyze_audio(
    audio_path: str,
    language: str | None = None,
) -> dict[str, Any]:
    """Convenience function for API modules."""
    return crime_analysis.analyze_audio(
        audio_path,
        language=language,
    )