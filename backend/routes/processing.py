from flask import Blueprint, jsonify

processing_bp = Blueprint("processing", __name__)


@processing_bp.get("/processing")
def processing_status():
    return jsonify({"status": "ok", "message": "Processing pipeline ready"})
