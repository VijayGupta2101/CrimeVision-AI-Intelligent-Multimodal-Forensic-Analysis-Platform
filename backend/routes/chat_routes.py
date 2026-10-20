"""Chat API routes for forensic evidence queries."""

from flask import Blueprint, jsonify, request

from services.chat_service import query_chat

chat_bp = Blueprint("chat", __name__)


@chat_bp.get("/chat")
def chat_status():
    """Check whether the chatbot route is available."""
    return jsonify({
        "status": "ok",
        "message": "Forensic chatbot service ready",
    })


@chat_bp.post("/chat/<mode>")
def chat(mode: str):
    """Answer questions about saved forensic analysis."""
    if mode not in {"image", "video", "audio", "multimodal"}:
        return jsonify({
            "success": False,
            "error": "Mode must be image, video, audio, or multimodal.",
        }), 400

    data = request.get_json(silent=True) or {}

    session_id = data.get("session_id")
    question = data.get("question")

    if not isinstance(session_id, str) or not session_id.strip():
        return jsonify({
            "success": False,
            "error": "session_id is required.",
        }), 400

    if not isinstance(question, str) or not question.strip():
        return jsonify({
            "success": False,
            "error": "question is required.",
        }), 400

    result = query_chat(
        session_id=session_id.strip(),
        question=question.strip(),
        mode=mode,
    )

    if not result.get("success"):
        return jsonify(result), 400

    return jsonify({
        "status": "success",
        **result,
    })