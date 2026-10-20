"""Multimodal forensic timeline and evidence consistency."""

from collections import defaultdict
from typing import Any


def _seconds(event: dict) -> float | None:
    """Extract a numeric timestamp from a normalized event."""

    for key in ("seconds", "timestamp", "start_raw", "time"):
        value = event.get(key)

        if isinstance(value, (int, float)):
            return float(value)

        if isinstance(value, str):
            value = value.strip()

            try:
                return float(value)
            except ValueError:
                parts = value.split(":")

                try:
                    if len(parts) == 2:
                        return float(parts[0]) * 60 + float(parts[1])

                    if len(parts) == 3:
                        return (
                            float(parts[0]) * 3600
                            + float(parts[1]) * 60
                            + float(parts[2])
                        )
                except ValueError:
                    pass

    return None


def _normalize_event(event: dict, source: str) -> dict:
    """Convert events from different modalities to a common schema."""

    timestamp = _seconds(event)

    return {
        **event,
        "seconds": timestamp,
        "source": event.get("source", source),
        "description": str(
            event.get("description")
            or event.get("event")
            or event.get("text")
            or event.get("caption")
            or "Unspecified event"
        ),
        "category": event.get("category", "observation"),
    }


def _keywords(text: str) -> set[str]:
    stop_words = {
        "the", "and", "was", "were", "with", "from", "that",
        "this", "then", "there", "have", "has", "for", "into",
        "near", "seen", "appears", "possibly", "unknown",
    }

    return {
        word.lower().strip(".,!?;:'\"()[]{}")
        for word in text.split()
        if len(word) > 2 and word.lower() not in stop_words
    }


def _similarity(first: str, second: str) -> float:
    a = _keywords(first)
    b = _keywords(second)

    if not a or not b:
        return 0.0

    return len(a & b) / len(a | b)


def _certainty(event: dict) -> str:
    confidence = event.get("confidence", 0.5)

    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = 0.5

    if confidence >= 0.8:
        return "high"
    if confidence >= 0.6:
        return "medium"

    return "low"


def build_unified_timeline(
    video_events: list[dict] | None = None,
    audio_events: list[dict] | None = None,
    tolerance_seconds: float = 1.0,
) -> dict:
    """Merge audiovisual events chronologically."""

    events = []

    for event in video_events or []:
        events.append(_normalize_event(event, "video"))

    for event in audio_events or []:
        events.append(_normalize_event(event, "audio"))

    events.sort(
        key=lambda item: (
            item["seconds"] is None,
            item["seconds"] if item["seconds"] is not None else float("inf"),
        )
    )

    matches = []
    conflicts = []
    used_audio = set()

    # Compare events only when both have timestamps.
    for video in events:
        if video["source"] != "video" or video["seconds"] is None:
            continue

        best_match = None
        best_score = 0.0

        for index, audio in enumerate(events):
            if audio["source"] != "audio" or index in used_audio:
                continue

            if audio["seconds"] is None:
                continue

            delta = abs(video["seconds"] - audio["seconds"])

            if delta > tolerance_seconds:
                continue

            score = _similarity(
                video["description"], audio["description"]
            )

            if score > best_score:
                best_score = score
                best_match = (index, audio, delta)

        if best_match:
            index, audio, delta = best_match
            used_audio.add(index)

            matches.append({
                "video_event": video,
                "audio_event": audio,
                "time_difference_seconds": round(delta, 3),
                "text_similarity": round(best_score, 3),
                "status": (
                    "potential_support"
                    if best_score >= 0.15
                    else "requires_review"
                ),
            })

    # Different descriptions at approximately the same time are
    # review candidates, not automatically proven contradictions.
    for video in events:
        if video["source"] != "video" or video["seconds"] is None:
            continue

        for audio in events:
            if audio["source"] != "audio" or audio["seconds"] is None:
                continue

            delta = abs(video["seconds"] - audio["seconds"])

            if (
                delta <= tolerance_seconds
                and _similarity(
                    video["description"], audio["description"]
                ) < 0.05
            ):
                conflicts.append({
                    "video_event": video,
                    "audio_event": audio,
                    "time_difference_seconds": round(delta, 3),
                    "status": "manual_review_required",
                })

    for event in events:
        event["certainty"] = _certainty(event)
        event["temporal_uncertainty"] = (
            "unknown" if event["seconds"] is None else "timestamp_available"
        )

    return {
        "timeline": events,
        "cross_modal_matches": matches,
        "potential_conflicts": conflicts,
        "metadata": {
            "video_event_count": sum(
                event["source"] == "video" for event in events
            ),
            "audio_event_count": sum(
                event["source"] == "audio" for event in events
            ),
            "time_tolerance_seconds": tolerance_seconds,
            "timestamp_unit": "seconds from start of recording",
        },
    }