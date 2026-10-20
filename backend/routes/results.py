from flask import Blueprint, jsonify
from services.session_store import get_session, list_sessions, delete_session

results_bp = Blueprint("results", __name__)


@results_bp.get("/results")
def results_status():
    """Return results service status and recent session history."""
    sessions = list_sessions()
    return jsonify({
        "status": "ok",
        "success": True,
        "message": "Results endpoint ready",
        "total_sessions": len(sessions),
        "sessions": sessions,
    })


@results_bp.get("/results/<session_id>")
def get_session_results(session_id: str):
    """Retrieve full analysis results for a specific session."""
    session = get_session(session_id)
    if session is None:
        return jsonify({
            "success": False,
            "error": f"Session '{session_id}' not found.",
        }), 404

    return jsonify({
        "status": "success",
        "success": True,
        "session_id": session_id,
        "result": session,
    })


@results_bp.delete("/results/<session_id>")
def delete_session_results(session_id: str):
    """Delete an analysis session."""
    success = delete_session(session_id)
    if not success:
        return jsonify({
            "success": False,
            "error": f"Session '{session_id}' could not be deleted or does not exist.",
        }), 404

    return jsonify({
        "status": "success",
        "success": True,
        "message": f"Session '{session_id}' deleted successfully.",
    })
