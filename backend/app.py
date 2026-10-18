"""Main Flask application for the CrimeVision AI platform."""

import os

# Environment variables must be set before importing heavier ML dependencies.
os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")
os.environ.setdefault("USE_TF", "NO")
os.environ.setdefault("USE_TORCH", "YES")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")

from flask import Flask, jsonify
from flask_cors import CORS

from config import API_CONFIG
from routes import processing_bp, results_bp, upload_bp
from routes.chat_routes import chat_bp
from audio_module.api import audio_analysis_bp
from video_module.api import video_analysis_bp
from utils.logger import app_logger, setup_logger
from utils.model_loader import preload_models

app = Flask(__name__)
app.config.from_object(API_CONFIG)
CORS(app)

logger = setup_logger("crimevision.app")
logger.info("Starting CrimeVision AI backend")

try:
    preload_models()
except Exception as exc:  # pragma: no cover - defensive safety net
    app_logger.warning("Model preloading failed: %s", exc)

app.register_blueprint(upload_bp, url_prefix="/api")
app.register_blueprint(processing_bp, url_prefix="/api")
app.register_blueprint(results_bp, url_prefix="/api")
app.register_blueprint(chat_bp, url_prefix="/api")
app.register_blueprint(audio_analysis_bp, url_prefix="/api")
app.register_blueprint(video_analysis_bp, url_prefix="/api")


@app.get("/")
def index():
    return jsonify({"service": "CrimeVision AI", "status": "ok"})


@app.get("/health")
def health_check():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
