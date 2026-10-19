"""CrimeVision AI video-analysis API."""

import logging
import uuid
from pathlib import Path

import cv2
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

        frames, metadata = extract_frames(
            str(saved_path),
            interval_seconds=interval,
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

        session_id = uuid.uuid4().hex

        result = {
            "success": True,
            "session_id": session_id,
            "filename": original_filename,
            "metadata": metadata,
            "detections": detections,
            "object_summary": object_summary,
            "captions": captions,
            "caption_summary": caption_summary,
            "forensic_analysis": incident_analysis,
            "timeline": timeline,
        }

        session_store.update_session(
            session_id,
            {
                **result,
                "source": "video",
            },
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