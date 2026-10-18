from flask import Blueprint, jsonify

chat_bp = Blueprint("chat", __name__)


@chat_bp.get("/chat")
def chat_status():
    return jsonify({"status": "ok", "message": "Chat service ready"})
