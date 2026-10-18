from flask import Blueprint, jsonify

audio_analysis_bp = Blueprint("audio_analysis", __name__)


@audio_analysis_bp.get("/audio")
def audio_status():
    return jsonify({"status": "ok", "message": "Audio analysis service ready"})
