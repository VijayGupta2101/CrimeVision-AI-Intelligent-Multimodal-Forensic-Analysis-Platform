"""
Audio Service - Speech-to-Text and Forensic Intelligence

Features:
- Multilingual transcription using Transformers Whisper-base.
- Timestamped audio segmentation.
- Groq-powered forensic fact extraction.
- AI-powered anchor-event classification.
- Chronological forensic timeline generation.
- Three provisional investigative hypotheses.
"""

import json
import os
import re

import torch

from pathlib import Path
from typing import Dict, Any, List, Optional
from transformers import pipeline

from config import MODEL_CONFIG
from utils.logger import setup_logger


logger = setup_logger("audio_service")


class AudioService:
    """Audio transcription and forensic intelligence service."""

    def __init__(self):
        self.pipe = None

    # ---------------------------------------------------------
    # MODEL LOADING
    # ---------------------------------------------------------

    def _ensure_model_loaded(self):
        """Load the Whisper-base pipeline when needed."""

        if self.pipe is not None:
            return

        try:
            device = 0 if torch.cuda.is_available() else -1

            logger.info(
                "Loading Whisper-base on %s...",
                "CUDA" if device == 0 else "CPU",
            )

            self.pipe = pipeline(
                "automatic-speech-recognition",
                model="openai/whisper-base",
                device=device,
                chunk_length_s=30,
                return_timestamps=True,
            )

            logger.info("Whisper-base loaded successfully.")

        except Exception:
            logger.exception("Failed to load Whisper model.")
            raise

    # ---------------------------------------------------------
    # AUDIO TRANSCRIPTION
    # ---------------------------------------------------------

    def transcribe_audio(
        self,
        audio_path: str,
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Transcribe audio and preserve Whisper segment timestamps.

        Supported language names:
        Telugu, Hindi, French, English.

        Timestamps represent positions within the recording.
        """

        try:
            audio_file = Path(audio_path)

            if not audio_file.is_file():
                raise FileNotFoundError(
                    f"Audio file not found: {audio_file}"
                )

            self._ensure_model_loaded()

            supported_languages = {
                "telugu": "te",
                "hindi": "hi",
                "french": "fr",
                "english": "en",
            }

            generate_kwargs = {}

            if language:
                normalized_language = language.strip().lower()

                language_code = supported_languages.get(
                    normalized_language,
                    normalized_language,
                )

                generate_kwargs = {
                    "language": language_code,
                    "task": "transcribe",
                }

            logger.info(
                "Transcribing audio file: %s",
                audio_file.name,
            )

            result = self.pipe(
                str(audio_file),
                return_timestamps=True,
                generate_kwargs=generate_kwargs or None,
            )

            transcript = result.get("text", "").strip()

            raw_chunks = result.get("chunks", [])

            segments = []

            for chunk in raw_chunks:
                timestamp = chunk.get("timestamp")

                if not timestamp:
                    continue

                start, end = timestamp

                segments.append(
                    {
                        "start": (
                            float(start)
                            if start is not None
                            else None
                        ),
                        "end": (
                            float(end)
                            if end is not None
                            else None
                        ),
                        "text": chunk.get("text", "").strip(),
                    }
                )

            logger.info(
                "Transcription completed: %d characters, %d segments",
                len(transcript),
                len(segments),
            )

            return {
                "success": True,
                "audio_path": str(audio_file),
                "language": language,
                "transcript": transcript,
                "segments": segments,
                "segment_count": len(segments),
            }

        except Exception as exc:
            logger.exception("Audio transcription failed.")

            return {
                "success": False,
                "audio_path": str(audio_path),
                "error": str(exc),
                "transcript": "",
                "segments": [],
                "segment_count": 0,
            }

    # ---------------------------------------------------------
    # TRANSCRIPT CLEANING
    # ---------------------------------------------------------

    @staticmethod
    def clean_transcript(transcript: str) -> str:
        """Normalize transcript whitespace."""

        if not transcript:
            return ""

        return re.sub(r"\s+", " ", transcript).strip()

    # ---------------------------------------------------------
    # TIMELINE EVENT CATEGORIZATION
    # ---------------------------------------------------------

    @staticmethod
    def _categorize_event(text: str) -> str:
        """
        Apply simple keyword-based categorization.

        This is a fallback when AI classification is unavailable.
        """

        text_lower = text.lower()

        categories = {
            "threat": [
                "threat",
                "threatened",
                "kill",
                "attack",
                " धमकी",
                "धमकी",
            ],
            "physical_struggle": [
                "fight",
                "fighting",
                "struggle",
                "hit",
                "punch",
                "मारपीट",
                "लड़ाई",
            ],
            "movement": [
                "entered",
                "arrived",
                "left",
                "escaped",
                "ran away",
                "entered the room",
                "आया",
                "गया",
                "प्रवेश",
            ],
            "identification": [
                "identified",
                "name",
                "called himself",
                "introduced himself",
                "नाम",
                "पहचान",
            ],
            "location": [
                "bedroom",
                "road",
                "street",
                "house",
                "room",
                "घर",
                "सड़क",
                "कमरा",
            ],
        }

        for category, keywords in categories.items():
            if any(keyword in text_lower for keyword in keywords):
                return category

        return "statement"

    # ---------------------------------------------------------
    # BASIC CHRONOLOGICAL TIMELINE
    # ---------------------------------------------------------

    def generate_timeline(
        self,
        segments: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Create a timeline from Whisper's timestamped segments.

        Each event includes:
        - start_raw
        - end_raw
        - timestamp
        - category
        - description
        - source
        - verification_status
        """

        timeline = []

        for segment in segments:
            text = segment.get("text", "").strip()

            if not text:
                continue

            start = segment.get("start")
            end = segment.get("end")

            timeline.append(
                {
                    "event_id": len(timeline) + 1,
                    "start_raw": (
                        float(start)
                        if start is not None
                        else None
                    ),
                    "end_raw": (
                        float(end)
                        if end is not None
                        else None
                    ),
                    "timestamp": (
                        float(start)
                        if start is not None
                        else None
                    ),
                    "start": start,
                    "end": end,
                    "category": self._categorize_event(text),
                    "description": text,
                    "evidence_quote": text,
                    "source": "whisper_transcript",
                    "verification_status": "unverified",
                }
            )

        timeline.sort(
            key=lambda event: (
                event["start_raw"] is None,
                (
                    event["start_raw"]
                    if event["start_raw"] is not None
                    else 0
                ),
            )
        )

        for index, event in enumerate(timeline, start=1):
            event["event_id"] = index

        return timeline

    # ---------------------------------------------------------
    # GROQ REASONING CLIENT
    # ---------------------------------------------------------

    @staticmethod
    def _get_groq_response(prompt: str) -> str:
        """
        Send a prompt to the Groq API.

        Requires:
            GROQ_API_KEY environment variable.
            groq Python package.
        """

        from groq import Groq

        api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not configured."
            )

        client = Groq(api_key=api_key)

        model_name = os.getenv(
            "GROQ_MODEL",
            "llama-3.3-70b-versatile",
        )

        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You assist with neutral forensic evidence "
                        "organization. Distinguish reported statements "
                        "from verified facts. Never invent evidence, "
                        "timestamps, identities, or physical details. "
                        "Do not present allegations as verified facts."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.2,
            max_tokens=3000,
        )

        content = response.choices[0].message.content or ""

        return content.strip()

    # ---------------------------------------------------------
    # JSON RESPONSE PARSING
    # ---------------------------------------------------------

    @staticmethod
    def _parse_json_response(response: str) -> Dict[str, Any]:
        """Parse JSON returned by the reasoning model."""

        response = re.sub(
            r"^\s*```(?:json)?\s*|\s*```\s*$",
            "",
            response.strip(),
            flags=re.IGNORECASE,
        )

        data = json.loads(response)

        if not isinstance(data, dict):
            raise ValueError(
                "The reasoning model did not return a JSON object."
            )

        return data

    # ---------------------------------------------------------
    # AI ANCHOR-EVENT EXTRACTION
    # ---------------------------------------------------------

    def extract_anchor_events(
        self,
        segments: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Identify meaningful forensic events from timestamped segments.

        The model returns segment indices, not timestamps.
        The actual timestamps are assigned later from Whisper.
        """

        if not segments:
            return {
                "success": True,
                "events": [],
            }

        # Limit prompt size for lengthy recordings.
        max_segments_per_request = 60

        all_events = []

        try:
            for batch_start in range(
                0,
                len(segments),
                max_segments_per_request,
            ):
                batch = segments[
                    batch_start:
                    batch_start + max_segments_per_request
                ]

                indexed_segments = []

                for local_index, segment in enumerate(batch):
                    indexed_segments.append(
                        {
                            "segment_index": local_index,
                            "text": segment.get("text", ""),
                        }
                    )

                prompt = f"""
Analyze these timestamped witness-transcription segments.

Identify meaningful investigative anchor events, including:
- Reported threats
- Reported physical struggles
- Arrival or departure
- Identification statements
- Important reported actions
- Spatial movement
- Relevant location references

Return ONLY valid JSON using this schema:

{{
  "events": [
    {{
      "segment_index": 0,
      "category": "movement",
      "description": "A witness reports that a person entered a building.",
      "evidence_quote": "He entered the building."
    }}
  ]
}}

Rules:
1. segment_index must refer to the zero-based index in this batch.
2. Only select events supported by the supplied words.
3. Do not invent identities, actions, timestamps, or evidence.
4. Preserve the difference between an allegation and a verified fact.
5. Do not infer guilt.
6. Skip segments without a meaningful event.
7. Use concise descriptions.
8. Return an empty events list when appropriate.

Segments:
{json.dumps(indexed_segments, ensure_ascii=False)}
"""

                response = self._get_groq_response(prompt)

                data = self._parse_json_response(response)

                batch_events = data.get("events", [])

                if not isinstance(batch_events, list):
                    raise ValueError(
                        "Groq returned an invalid events list."
                    )

                for event in batch_events:
                    if not isinstance(event, dict):
                        continue

                    local_index = event.get("segment_index")

                    if not isinstance(local_index, int):
                        continue

                    if (
                        local_index < 0
                        or local_index >= len(batch)
                    ):
                        continue

                    # Convert the batch-local index into the
                    # index of the original complete segment list.
                    event["segment_index"] = (
                        batch_start + local_index
                    )

                    all_events.append(event)

            return {
                "success": True,
                "events": all_events,
            }

        except Exception as exc:
            logger.exception(
                "Anchor-event extraction failed."
            )

            return {
                "success": False,
                "error": str(exc),
                "events": [],
            }

    # ---------------------------------------------------------
    # MAP AI EVENTS TO WHISPER TIMESTAMPS
    # ---------------------------------------------------------

    def merge_anchor_events(
        self,
        segments: List[Dict[str, Any]],
        anchor_events: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Attach AI-classified events to original Whisper timestamps.

        Timestamps always originate from the transcription segments.
        """

        timeline = []

        for event in anchor_events:
            if not isinstance(event, dict):
                continue

            segment_index = event.get("segment_index")

            if not isinstance(segment_index, int):
                continue

            if not 0 <= segment_index < len(segments):
                continue

            segment = segments[segment_index]

            description = str(
                event.get("description", "")
            ).strip()

            if not description:
                continue

            start = segment.get("start")
            end = segment.get("end")

            evidence_quote = str(
                event.get("evidence_quote", "")
            ).strip()

            # Fall back to the actual transcript segment.
            if not evidence_quote:
                evidence_quote = segment.get("text", "")

            timeline.append(
                {
                    "event_id": len(timeline) + 1,
                    "start_raw": (
                        float(start)
                        if start is not None
                        else None
                    ),
                    "end_raw": (
                        float(end)
                        if end is not None
                        else None
                    ),
                    "timestamp": (
                        float(start)
                        if start is not None
                        else None
                    ),
                    "start": start,
                    "end": end,
                    "category": event.get(
                        "category",
                        "statement",
                    ),
                    "description": description,
                    "evidence_quote": evidence_quote,
                    "transcript_segment": segment.get(
                        "text",
                        "",
                    ),
                    "segment_index": segment_index,
                    "source": "whisper_timestamp_groq_classification",
                    "verification_status": "unverified",
                }
            )

        timeline.sort(
            key=lambda event: (
                event["start_raw"] is None,
                (
                    event["start_raw"]
                    if event["start_raw"] is not None
                    else 0
                ),
            )
        )

        # Remove duplicate events referring to the same segment
        # and category.
        deduplicated = []
        seen = set()

        for event in timeline:
            key = (
                event.get("segment_index"),
                event.get("category"),
                event.get("description", "").casefold(),
            )

            if key in seen:
                continue

            seen.add(key)
            deduplicated.append(event)

        for index, event in enumerate(
            deduplicated,
            start=1,
        ):
            event["event_id"] = index

        return deduplicated

    # ---------------------------------------------------------
    # FORENSIC FACT EXTRACTION
    # ---------------------------------------------------------

    def extract_forensic_facts(
        self,
        transcript: str,
    ) -> Dict[str, Any]:
        """
        Extract reported people, locations, times, actions,
        scene type, and a neutral description.

        Extracted information remains unverified until independently
        corroborated.
        """

        transcript = self.clean_transcript(transcript)

        if not transcript:
            return {
                "success": False,
                "error": "Transcript is empty.",
                "facts": {},
            }

        prompt = f"""
Analyze the following witness transcript for forensic review.

Return ONLY valid JSON with these keys:

{{
  "people_mentioned": [],
  "location_mentions": [],
  "time_mentions": [],
  "reported_actions": [],
  "scene_type": "unknown",
  "scene_type_evidence": [],
  "suspect_description": "unknown",
  "key_observations": [],
  "uncertainties": []
}}

Instructions:
- Use only information supported by the transcript.
- Do not invent identities, physical characteristics, locations, or times.
- Use "unknown" when information is unavailable.
- Treat witness statements as reported claims, not verified facts.
- Scene type may be road, bedroom, outdoor area, building,
  vehicle, or unknown.
- Do not infer a person's guilt.
- Include uncertainty when wording is ambiguous.

Transcript:
{transcript}
"""

        try:
            response = self._get_groq_response(prompt)

            facts = self._parse_json_response(response)

            return {
                "success": True,
                "facts": facts,
                "source": "transcript_analysis",
                "verification_status": "unverified",
            }

        except Exception as exc:
            logger.exception(
                "Forensic fact extraction failed."
            )

            return {
                "success": False,
                "error": str(exc),
                "facts": {},
            }

    # ---------------------------------------------------------
    # SCENARIO HYPOTHESES
    # ---------------------------------------------------------

    def generate_hypotheses(
        self,
        transcript: str,
        facts: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generate three provisional investigative hypotheses.

        These hypotheses are possibilities, not factual conclusions.
        """

        transcript = self.clean_transcript(transcript)

        if not transcript:
            return {
                "success": False,
                "error": "Transcript is empty.",
                "hypotheses": [],
            }

        prompt = f"""
Based on the witness transcript and extracted facts below,
produce exactly three distinct investigative hypotheses.

For each hypothesis, provide:
- hypothesis: a concise possible explanation
- supporting_statements: statements in the supplied evidence
- missing_evidence: evidence needed to evaluate it
- alternative_explanation: another plausible interpretation
- status: "unverified"

Rules:
- Do not invent evidence.
- Do not assume a crime occurred.
- Do not accuse or identify a real person.
- Treat each hypothesis as provisional.
- If evidence is insufficient, state that explicitly.
- Do not assign numerical probabilities.

Return ONLY valid JSON:

{{
  "hypotheses": [
    {{
      "hypothesis": "...",
      "supporting_statements": [],
      "missing_evidence": [],
      "alternative_explanation": "...",
      "status": "unverified"
    }},
    {{
      "hypothesis": "...",
      "supporting_statements": [],
      "missing_evidence": [],
      "alternative_explanation": "...",
      "status": "unverified"
    }},
    {{
      "hypothesis": "...",
      "supporting_statements": [],
      "missing_evidence": [],
      "alternative_explanation": "...",
      "status": "unverified"
    }}
  ]
}}

Extracted facts:
{json.dumps(facts or {}, ensure_ascii=False)}

Witness transcript:
{transcript}
"""

        try:
            response = self._get_groq_response(prompt)

            data = self._parse_json_response(response)

            hypotheses = data.get("hypotheses", [])

            if (
                not isinstance(hypotheses, list)
                or len(hypotheses) != 3
            ):
                raise ValueError(
                    "The reasoning model did not return "
                    "exactly three hypotheses."
                )

            return {
                "success": True,
                "hypotheses": hypotheses,
                "status": "unverified",
            }

        except Exception as exc:
            logger.exception(
                "Hypothesis generation failed."
            )

            return {
                "success": False,
                "error": str(exc),
                "hypotheses": [],
            }

    # ---------------------------------------------------------
    # COMPLETE AUDIO ANALYSIS
    # ---------------------------------------------------------

    def analyze_audio(
        self,
        audio_path: str,
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Run the complete audio-analysis pipeline:

        1. Whisper transcription.
        2. Timestamped speech segmentation.
        3. Initial timeline generation.
        4. Groq anchor-event extraction.
        5. Timeline mapping.
        6. Forensic fact extraction.
        7. Three provisional hypotheses.
        """

        # Step 1: Transcribe audio.
        transcription = self.transcribe_audio(
            audio_path=audio_path,
            language=language,
        )

        if not transcription.get("success"):
            return {
                "success": False,
                "error": transcription.get(
                    "error",
                    "Transcription failed.",
                ),
                "transcription": transcription,
            }

        transcript = transcription["transcript"]
        segments = transcription["segments"]

        # Step 2: Build the complete speech timeline.
        timeline = self.generate_timeline(segments)

        # Step 3: Extract AI-classified anchor events.
        anchor_result = self.extract_anchor_events(segments)

        # Step 4: Replace the initial timeline with the
        # AI-classified timeline when extraction succeeds.
        if anchor_result.get("success"):
            anchor_timeline = self.merge_anchor_events(
                segments=segments,
                anchor_events=anchor_result.get(
                    "events",
                    [],
                ),
            )

            # Keep the full transcription timeline if the model
            # returned no meaningful anchor events.
            if anchor_timeline:
                timeline = anchor_timeline

        # Step 5: Extract structured forensic facts.
        facts_result = self.extract_forensic_facts(
            transcript
        )

        facts = facts_result.get("facts", {})

        # Step 6: Generate provisional hypotheses.
        hypotheses_result = self.generate_hypotheses(
            transcript=transcript,
            facts=facts,
        )

        # Step 7: Return a unified response.
        return {
            "success": True,
            "audio_path": transcription["audio_path"],
            "language": transcription["language"],
            "transcript": transcript,
            "segments": segments,
            "timeline": timeline,
            "anchor_events": anchor_result,
            "forensic_analysis": facts_result,
            "hypothesis_analysis": hypotheses_result,
            "metadata": {
                "segment_count": len(segments),
                "timeline_event_count": len(timeline),
                "transcription_success": True,
                "anchor_event_extraction_success": (
                    anchor_result.get("success", False)
                ),
                "fact_extraction_success": (
                    facts_result.get("success", False)
                ),
                "hypothesis_generation_success": (
                    hypotheses_result.get("success", False)
                ),
            },
        }


# -------------------------------------------------------------
# SHARED SERVICE INSTANCE
# -------------------------------------------------------------

audio_service = AudioService()