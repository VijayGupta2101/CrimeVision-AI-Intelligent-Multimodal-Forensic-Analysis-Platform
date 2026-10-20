from flask import Blueprint, request, jsonify

from services.chat_service import chat_service

chat_bp = Blueprint("chat", __name__)


def handle_chat():
    data = request.get_json(silent=True) or {}

    question = data.get("question", "")
    session_id = data.get("session_id", "default")
    context = data.get("context", {})

    result = chat_service.chat(
        question=question,
        session_id=session_id,
        context=context,
    )

    status_code = 200 if result.get("success") else 500

    return jsonify(result), status_code


@chat_bp.route("/chat", methods=["POST"])
def general_chat():
    return handle_chat()


@chat_bp.route("/chat/<mode>", methods=["POST"])
def mode_chat(mode):
    allowed_modes = {"image", "audio", "video"}

    if mode not in allowed_modes:
        return jsonify({
            "success": False,
            "error": "Unsupported chat mode.",
        }), 400

    return handle_chat()


@chat_bp.route("/chat", methods=["GET"])
def chat_status():
    return jsonify({
        "success": True,
        "message": "Chat service ready",
    })