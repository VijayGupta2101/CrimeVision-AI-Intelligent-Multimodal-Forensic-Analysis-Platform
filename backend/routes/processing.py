from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from pathlib import Path
import logging
import uuid

from services.session_store import session_store

processing_bp = Blueprint("processing", __name__)
logger = logging.getLogger(__name__)

# Upload directory
UPLOAD_FOLDER = Path(__file__).resolve().parent.parent / "uploads"
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)


@processing_bp.route("/health", methods=["GET"])
def processing_health():
    return jsonify({
        "success": True,
        "message": "Processing API is running"
    })


@processing_bp.route("/image/analyze", methods=["POST"])
def analyze_image():
    """Analyze an uploaded image using the existing vision models."""

    if "file" not in request.files:
        return jsonify({
            "success": False,
            "error": "No image was uploaded. Use the form field 'file'."
        }), 400

    uploaded_file = request.files["file"]

    if not uploaded_file.filename:
        return jsonify({
            "success": False,
            "error": "Please select an image."
        }), 400

    filename = secure_filename(uploaded_file.filename)

    if not filename:
        return jsonify({
            "success": False,
            "error": "Invalid filename."
        }), 400

    extension = Path(filename).suffix.lower()

    if extension not in {
        ".jpg", ".jpeg", ".png", ".webp", ".bmp"
    }:
        return jsonify({
            "success": False,
            "error": "Unsupported image format."
        }), 400

    image_path = UPLOAD_FOLDER / f"{uuid.uuid4().hex}{extension}"
    uploaded_file.save(str(image_path))

    try:
        # Import your existing image-processing module.
        from services.vision import (
            get_detector,
            get_captioner,
        )
        from PIL import Image

        image = Image.open(image_path).convert("RGB")

        # Detect objects.
        detector = get_detector()
        detections = detector(image)

        objects = [
            {
                "label": str(item.get("label", "unknown")),
                "score": round(float(item.get("score", 0)), 4),
                "box": item.get("box", {}),
            }
            for item in detections
        ]

        # Generate image caption.
        captioner = get_captioner()
        caption_output = captioner(image)

        summary = (
            caption_output[0].get("generated_text", "")
            if caption_output else ""
        )

        # Return results to the frontend and persist them for evidence Q&A.
        result = {
            "success": True,
            "message": "Image analysis completed",
            "filename": filename,
            "visual_summary": summary,
            "summary": summary,
            "objects": objects,
            "detected_objects": objects,
            "object_count": len(objects),
            "people_count": sum(
                1 for item in objects
                if item["label"].lower() == "person"
            ),
            "location": "Not established from image alone",
            "actions": [],
            "evidence_facts": [
                {
                    "observation": item["label"],
                    "confidence": item["score"],
                    "source": "object_detection_model",
                }
                for item in objects
            ],
            "hypotheses": [],
        }
        result["session_id"] = session_store.create_session({
            "source": "image",
            **result,
        })
        return jsonify(result)

    except Exception as exc:
        logger.exception("Image analysis failed")

        return jsonify({
            "success": False,
            "error": f"Image analysis failed: {str(exc)}"
        }), 500


@processing_bp.route("/audio/analyze", methods=["POST"])
def analyze_audio():
    """Analyze an uploaded audio file."""

    if "file" not in request.files:
        return jsonify({
            "success": False,
            "error": "No audio file was uploaded."
        }), 400

    uploaded_file = request.files["file"]

    if not uploaded_file.filename:
        return jsonify({
            "success": False,
            "error": "Please select an audio file."
        }), 400

    filename = secure_filename(uploaded_file.filename)

    if not filename:
        return jsonify({
            "success": False,
            "error": "Invalid filename."
        }), 400

    extension = Path(filename).suffix.lower()

    if extension not in {
        ".mp3", ".wav", ".m4a", ".ogg", ".flac"
    }:
        return jsonify({
            "success": False,
            "error": "Unsupported audio format."
        }), 400

    audio_path = UPLOAD_FOLDER / f"{uuid.uuid4().hex}{extension}"
    uploaded_file.save(str(audio_path))

    try:
        # Use your existing audio service.
        from services.audio_service import audio_service

        result = audio_service.analyze_audio(str(audio_path))

        if not result.get("success"):
            return jsonify({
                "success": False,
                "error": result.get("error", "Audio analysis failed")
            }), 500

        result["session_id"] = session_store.create_session({
            "source": "audio",
            **result,
        })
        return jsonify(result)

    except Exception as exc:
        logger.exception("Audio analysis failed")

        return jsonify({
            "success": False,
            "error": f"Audio analysis failed: {str(exc)}"
        }), 500


@processing_bp.route("/video/analyze", methods=["POST"])
def analyze_video():
    """Analyze an uploaded video."""

    if "file" not in request.files:
        return jsonify({
            "success": False,
            "error": "No video file was uploaded."
        }), 400

    uploaded_file = request.files["file"]

    if not uploaded_file.filename:
        return jsonify({
            "success": False,
            "error": "Please select a video."
        }), 400

    filename = secure_filename(uploaded_file.filename)

    if not filename:
        return jsonify({
            "success": False,
            "error": "Invalid filename."
        }), 400

    extension = Path(filename).suffix.lower()

    if extension not in {
        ".mp4", ".mov", ".avi", ".mkv", ".webm"
    }:
        return jsonify({
            "success": False,
            "error": "Unsupported video format."
        }), 400

    video_path = UPLOAD_FOLDER / f"{uuid.uuid4().hex}{extension}"
    uploaded_file.save(str(video_path))

    try:
        from video_module.api import analyze_video_file

        result = analyze_video_file(
            str(video_path),
            original_filename=filename,
        )

        return jsonify(result)

    except Exception as exc:
        logger.exception("Video analysis failed")

        return jsonify({
            "success": False,
            "error": f"Video analysis failed: {str(exc)}"
        }), 500