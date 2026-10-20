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


def extract_scene_location(summary: str, objects: list) -> str:
    """Extract a concise forensic scene location descriptor from visual cues."""
    summary_lower = (summary or "").lower()
    labels = [
        item.get("label", "").lower()
        for item in (objects or [])
        if isinstance(item, dict)
    ]

    if "living room" in summary_lower or any(l in labels for l in ["couch", "sofa"]):
        return "Indoor (Living Room)"
    if "bedroom" in summary_lower or "bed" in labels:
        return "Indoor (Bedroom)"
    if "kitchen" in summary_lower or any(l in labels for l in ["refrigerator", "microwave", "oven"]):
        return "Indoor (Kitchen / Dining)"
    if "office" in summary_lower or any(l in labels for l in ["laptop", "keyboard", "mouse"]):
        return "Indoor (Office / Workspace)"
    if any(k in summary_lower for k in ["store", "shop", "supermarket", "counter"]):
        return "Commercial (Store / Retail)"
    if any(k in summary_lower for k in ["street", "road", "sidewalk", "highway"]) or any(l in labels for l in ["traffic light", "stop sign"]):
        return "Outdoor (Street / Roadway)"
    if any(k in summary_lower for k in ["park", "garden", "forest", "field"]):
        return "Outdoor (Park / Open Area)"
    if any(k in summary_lower for k in ["parking", "garage"]):
        return "Parking / Garage"
    if any(k in summary_lower for k in ["indoor", "room"]) or any(l in labels for l in ["chair", "table", "tv", "clock"]):
        return "Indoor (General Scene)"
    if any(l in labels for l in ["car", "truck", "bus", "motorcycle", "bicycle"]):
        return "Outdoor (Roadway / Vehicles)"

    return "Scene Location Unspecified"


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
        try:
            caption_output = captioner(image, text="a photo of")
        except (TypeError, ValueError):
            caption_output = captioner(image)

        summary = (
            caption_output[0].get("generated_text", "")
            if caption_output else ""
        )

        # Extract observed actions and provisional hypotheses
        actions = []
        labels_lower = [item["label"].lower() for item in objects]
        if any(w in labels_lower for w in ["knife", "gun", "weapon", "scissors", "baseball bat"]):
            actions.append("Potential weapon item detected in frame")
        if "person" in labels_lower:
            actions.append("Subject / Person presence observed")
        if not actions and summary:
            actions.append(f"Visual scene context: {summary[:55]}")

        hypotheses = []
        try:
            from services.scenario_service import generate_scenarios
            scenario_res = generate_scenarios({
                "objects": [o["label"] for o in objects],
                "summary": summary,
                "people_count": sum(1 for item in objects if item["label"].lower() == "person"),
            })
            if scenario_res.get("scenarios"):
                hypotheses = scenario_res["scenarios"]
        except Exception:
            pass

        if not hypotheses:
            hypotheses = [
                {
                    "title": "Primary Scenario",
                    "description": f"Visual observation confirms {len(objects)} object(s) with scene context '{summary or 'unspecified'}'.",
                    "status": "provisional"
                },
                {
                    "title": "Alternative Context",
                    "description": "Evidence requires corroboration from environmental conditions and timeline analysis.",
                    "status": "provisional"
                }
            ]

        # Return results to the frontend and persist them for evidence Q&A.
        result = {
            "success": True,
            "message": "Image analysis completed",
            "filename": filename,
            "file_url": f"/uploads/{image_path.name}",
            "visual_summary": summary,
            "summary": summary,
            "objects": objects,
            "detected_objects": objects,
            "object_count": len(objects),
            "people_count": sum(
                1 for item in objects
                if item["label"].lower() == "person"
            ),
            "location": extract_scene_location(summary, objects),
            "actions": actions,
            "evidence_facts": [
                {
                    "observation": item["label"],
                    "confidence": item["score"],
                    "source": "object_detection_model",
                }
                for item in objects
            ],
            "hypotheses": hypotheses,
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

        result["file_url"] = f"/uploads/{audio_path.name}"
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

        result["file_url"] = f"/uploads/{video_path.name}"
        return jsonify(result)

    except Exception as exc:
        logger.exception("Video analysis failed")

        return jsonify({
            "success": False,
            "error": f"Video analysis failed: {str(exc)}"
        }), 500