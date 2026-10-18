from flask import Blueprint, jsonify

upload_bp = Blueprint("upload", __name__)


@upload_bp.get("/upload")
def upload_status():
    return jsonify({"status": "ok", "message": "Upload service ready"})
