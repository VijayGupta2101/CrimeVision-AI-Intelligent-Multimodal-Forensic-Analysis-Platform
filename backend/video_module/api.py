from flask import Blueprint, jsonify

video_analysis_bp = Blueprint("video_analysis", __name__)


@video_analysis_bp.get("/video")
def video_status():
    return jsonify({"status": "ok", "message": "Video analysis service ready"})
