from flask import Blueprint, jsonify

results_bp = Blueprint("results", __name__)


@results_bp.get("/results")
def results_status():
    return jsonify({"status": "ok", "message": "Results endpoint ready"})
