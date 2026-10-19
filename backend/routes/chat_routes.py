"""Chatbot API routes."""

from flask import Blueprint, jsonify, request

from services.chat_service import query_chat

chat_bp = Blueprint("chat", __name__)


@chat_bp.get("/chat")
def chat_status():
    return jsonify({
        "status": "ok",
        "message": "Forensic chatbot ready",
    })


@chat_bp.post("/chat/<mode>")
def chat(mode):
    data = request.get_json(silent=True) or {}

    session_id = data.get("session_id")
    question = data.get("question", "").strip()

    if not session_id or not question:
        return jsonify({
            "status": "error",
            "answer": "session_id and question are required.",
        }), 400

    if mode not in {"video", "audio", "multimodal"}:
        return jsonify({
            "status": "error",
            "answer": "Unsupported chatbot mode.",
        }), 400

    result = query_chat(
        session_id=session_id,
        question=question,
        mode=mode,
    )

    status_code = (
        200 if result["status"] == "success" else 400
    )

    return jsonify(result), status_code