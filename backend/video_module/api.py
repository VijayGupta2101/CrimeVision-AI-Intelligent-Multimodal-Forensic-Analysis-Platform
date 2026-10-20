"""CrimeVision AI video-analysis API."""

import logging
import uuid
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request
from werkzeug.utils import secure_filename

from services.vision import (
    extract_frames,
    detect_objects_in_frames,
    aggregate_objects,
    generate_frame_captions,
    summarize_captions,
    classify_crime,
    build_timeline,
)
from services.session_store import session_store

video_analysis_bp = Blueprint(
    "video_analysis",
    __name__,
)

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {
    ".mp4", ".avi", ".mov", ".mkv", ".webm"
}


def allowed_video(filename):
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def analyze_video_file(
    video_path: str,
    original_filename: str | None = None,
    interval_seconds: float = 1.0,
) -> dict:
    """Analyze a saved video and persist its findings for evidence Q&A."""
    frames, metadata = extract_frames(
        video_path,
        interval_seconds=interval_seconds,
    )

    if not frames:
        raise ValueError("No video frames could be extracted.")

    detections = detect_objects_in_frames(frames)
    object_summary = aggregate_objects(detections)
    captions = generate_frame_captions(frames)
    caption_summary = summarize_captions(captions)
    incident_analysis = classify_crime(
        detections=detections,
        captions=captions,
    )
    timeline = build_timeline(
        detections=detections,
        captions=captions,
        incident_analysis=incident_analysis,
    )

    total_detections = sum(
        len(frame_result.get("detections", []))
        for frame_result in detections
    )
    people_count = sum(
        detection.get("label", "").lower() == "person"
        for frame_result in detections
        for detection in frame_result.get("detections", [])
    )
    summary = caption_summary or incident_analysis.get(
        "summary",
        "Video analysis completed; no visual summary was returned.",
    )

    result = {
        "success": True,
        "filename": original_filename or Path(video_path).name,
        "metadata": metadata,
        "detections": detections,
        "objects": object_summary,
        "object_summary": object_summary,
        "object_count": total_detections,
        "people_count": people_count,
        "location": "Not established from video alone",
        "actions": incident_analysis.get("actions", []),
        "captions": captions,
        "caption_summary": caption_summary,
        "visual_summary": summary,
        "summary": summary,
        "forensic_analysis": incident_analysis,
        "timeline": timeline,
    }
    result["session_id"] = session_store.create_session({
        "source": "video",
        **result,
    })
    return result


@video_analysis_bp.get("/video")
def video_status():
    return jsonify({
        "status": "ok",
        "message": "Video analysis service ready",
    })


@video_analysis_bp.post("/analyze-video")
def analyze_video():
    """Analyze video frames and construct a forensic timeline."""

    if "video" not in request.files:
        return jsonify({
            "status": "error",
            "error": "Upload a video using the 'video' form field.",
        }), 400

    uploaded_file = request.files["video"]

    if not uploaded_file.filename:
        return jsonify({
            "status": "error",
            "error": "No video filename supplied.",
        }), 400

    if not allowed_video(uploaded_file.filename):
        return jsonify({
            "status": "error",
            "error": "Unsupported video format.",
        }), 400

    try:
        interval = float(
            request.form.get("interval_seconds", "1.0")
        )

        if not 0.25 <= interval <= 60:
            raise ValueError(
                "interval_seconds must be between 0.25 and 60."
            )
    except ValueError as exc:
        return jsonify({
            "status": "error",
            "error": str(exc),
        }), 400

    upload_dir = (
        Path(current_app.root_path)
        / "uploads"
        / "video"
    )
    upload_dir.mkdir(parents=True, exist_ok=True)

    original_filename = secure_filename(uploaded_file.filename)
    extension = Path(original_filename).suffix.lower()
    saved_path = upload_dir / f"{uuid.uuid4().hex}{extension}"

    try:
        uploaded_file.save(saved_path)

        result = analyze_video_file(
            str(saved_path),
            original_filename=original_filename,
            interval_seconds=interval,
        )
        return jsonify(result), 200

    except ValueError as exc:
        return jsonify({
            "success": False,
            "error": str(exc),
        }), 400

    except Exception:
        logger.exception("Video analysis failed")

        return jsonify({
            "success": False,
            "error": (
                "Video analysis failed. "
                "Check the backend terminal for details."
            ),
        }), 500