"""Visual processing for CrimeVision AI."""

import json
import logging
import os
from collections import Counter

import cv2
import torch
from PIL import Image
from transformers import pipeline

from utils.groq_utils import get_groq_client

logger = logging.getLogger(__name__)

_detector = None
_captioner = None


def get_detector():
    """Load RT-DETR lazily."""

    global _detector

    if _detector is None:
        device = 0 if torch.cuda.is_available() else -1

        _detector = pipeline(
            "object-detection",
            model="PekingU/rtdetr_r50vd",
            device=device,
        )

    return _detector


def get_captioner():
    """Load an image-captioning model lazily."""

    global _captioner

    if _captioner is None:
        device = 0 if torch.cuda.is_available() else -1

        _captioner = pipeline(
            "image-to-text",
            model="Salesforce/blip-image-captioning-base",
            device=device,
        )

    return _captioner


def extract_frames(video_path, interval_seconds=1.0):
    """
    Extract frames at regular time intervals.

    Frame timestamps are offsets from the beginning of the video.
    """

    capture = cv2.VideoCapture(video_path)

    if not capture.isOpened():
        raise ValueError("Unable to open the video.")

    fps = capture.get(cv2.CAP_PROP_FPS)
    frame_count = int(
        capture.get(cv2.CAP_PROP_FRAME_COUNT)
    )

    if fps <= 0:
        capture.release()
        raise ValueError("Invalid video frame rate.")

    duration = frame_count / fps if frame_count > 0 else 0

    frames = []
    timestamp = 0.0

    try:
        while timestamp < duration:
            capture.set(
                cv2.CAP_PROP_POS_MSEC,
                timestamp * 1000,
            )

            success, frame = capture.read()

            if not success:
                break

            height, width = frame.shape[:2]

            # Resize only when necessary, preserving aspect ratio.
            max_dimension = 1280

            scale = min(
                1.0,
                max_dimension / max(width, height),
            )

            if scale < 1.0:
                frame = cv2.resize(
                    frame,
                    (
                        int(width * scale),
                        int(height * scale),
                    ),
                    interpolation=cv2.INTER_AREA,
                )

            rgb_frame = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2RGB,
            )

            frames.append({
                "timestamp": round(timestamp, 3),
                "image": Image.fromarray(rgb_frame),
            })

            timestamp += interval_seconds

    finally:
        capture.release()

    metadata = {
        "fps": round(fps, 3),
        "duration_seconds": round(duration, 3),
        "frame_count": frame_count,
        "sampled_frames": len(frames),
        "interval_seconds": interval_seconds,
    }

    return frames, metadata


def detect_objects_in_frames(frames):
    """Run RT-DETR on every extracted frame."""

    detector = get_detector()
    results = []

    for item in frames:
        predictions = detector(item["image"])

        detections = []

        for prediction in predictions:
            score = float(prediction.get("score", 0))

            detections.append({
                "label": str(
                    prediction.get("label", "unknown")
                ),
                "score": round(score, 4),
                "box": prediction.get("box", {}),
            })

        results.append({
            "timestamp": item["timestamp"],
            "detections": detections,
        })

    return results


def aggregate_objects(detections):
    """Summarize detected labels across sampled frames."""

    counts = Counter()

    for frame_result in detections:
        for detection in frame_result["detections"]:
            counts[detection["label"]] += 1

    return [
        {
            "label": label,
            "frame_detection_count": count,
        }
        for label, count in counts.most_common()
    ]


def generate_frame_captions(frames):
    """Generate a natural-language caption for each sampled frame."""

    captioner = get_captioner()
    results = []

    for item in frames:
        try:
            output = captioner(item["image"], text="a photo of")
        except (TypeError, ValueError):
            output = captioner(item["image"])

        caption = ""

        if output:
            caption = output[0].get(
                "generated_text",
                "",
            )

        results.append({
            "timestamp": item["timestamp"],
            "caption": caption,
        })

    return results


def summarize_captions(captions):
    """Create a concise summary of frame captions."""

    text = " ".join(
        item["caption"]
        for item in captions
        if item.get("caption")
    )

    return text[:12000]


def _parse_json(text):
    """Parse JSON returned by an LLM."""

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")

        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass

    return {
        "incident_assessment": "insufficient_information",
        "summary": text[:2000],
        "supporting_evidence": [],
        "limitations": [
            "The model did not return valid structured JSON."
        ],
    }


def classify_crime(detections, captions):
    """
    Ask Groq to assess the visual sequence.

    The output is a provisional assessment, not a legal finding.
    """
    try:
        client = get_groq_client()

        model = os.getenv(
            "GROQ_MODEL",
            "llama-3.3-70b-versatile",
        )

        # Keep context bounded for longer recordings.
        context = {
            "detections": detections[:120],
            "captions": captions[:120],
        }

        prompt = f"""
Analyze this sampled video evidence.

Return valid JSON with these fields:
- incident_assessment
- summary
- supporting_evidence: array of objects containing timestamp,
  observation, and evidence_source
- alternative_explanations: array of strings
- limitations: array of strings

Requirements:
- Do not invent actions that are not supported by the input.
- Do not infer guilt or identify a person as a suspect solely
  because an object was detected.
- Distinguish visible observations from interpretations.
- If the evidence is ambiguous, return
  "insufficient_information".
- Treat captions and detections as imperfect model outputs.

Evidence:
{json.dumps(context, ensure_ascii=False, default=str)}
"""

        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a cautious forensic evidence "
                        "analysis assistant."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.1,
        )

        resp_content = response.choices[0].message.content or "{}"
        return _parse_json(resp_content)

    except Exception as exc:
        logger.warning(f"Video Groq classification failed: {exc}")
        sampled_captions = [c.get("caption", "") for c in captions if c.get("caption")]
        all_labels = set(
            d.get("label", "")
            for f in detections
            for d in f.get("detections", [])
            if d.get("label")
        )
        return {
            "incident_assessment": "provisional_review",
            "summary": " ".join(sampled_captions[:3]) or f"Video analyzed with {len(detections)} sampled frames.",
            "actions": ["Observation recorded" if all_labels else "No distinct actions detected"],
            "supporting_evidence": [
                {
                    "timestamp": f.get("timestamp", 0.0),
                    "observation": f"Sampled frame with {len(f.get('detections', []))} detection(s): {', '.join(d.get('label', '') for d in f.get('detections', [])[:3])}",
                    "evidence_source": "vision_models",
                }
                for f in detections[:10] if f.get("detections")
            ],
            "limitations": [f"Groq LLM assessment was unavailable: {str(exc)}"],
        }


def build_timeline(
    detections,
    captions,
    incident_analysis,
):
    """Build a chronological timeline from sampled video evidence."""

    timeline = []

    caption_map = {
        item["timestamp"]: item.get("caption", "")
        for item in captions
    }

    for frame_result in detections:
        timestamp = float(frame_result["timestamp"])
        frame_detections = frame_result["detections"]

        caption = caption_map.get(timestamp, "")

        timeline.append({
            "timestamp": timestamp,
            "start": timestamp,
            "end": timestamp,
            "source": "video",
            "category": "visual_observation",
            "description": caption or (
                "Video frame processed."
            ),
            "detections": frame_detections,
            "verification_status": "unverified",
        })

    for event in incident_analysis.get(
        "supporting_evidence",
        [],
    ):
        try:
            timestamp = float(event["timestamp"])
        except (KeyError, TypeError, ValueError):
            continue

        timeline.append({
            "timestamp": timestamp,
            "start": timestamp,
            "end": timestamp,
            "source": "video_llm_assessment",
            "category": "provisional_interpretation",
            "description": str(
                event.get("observation", "")
            ),
            "evidence_source": event.get(
                "evidence_source",
                "model_assessment",
            ),
            "verification_status": "unverified",
        })

    timeline.sort(
        key=lambda item: item["timestamp"]
    )

    return timeline

# Shared vision service instance
vision_service = None