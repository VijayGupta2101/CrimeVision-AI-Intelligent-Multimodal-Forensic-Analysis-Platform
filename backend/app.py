from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

BACKEND_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BACKEND_DIR.parent / "frontend"
UPLOADS_DIR = BACKEND_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv(BACKEND_DIR / ".env")

from audio_module.api import audio_analysis_bp
from routes.chat_routes import chat_bp
from routes.processing import processing_bp
from routes.results import results_bp
from routes.upload import upload_bp
from video_module.api import video_analysis_bp

app = Flask(__name__, static_folder=None)
CORS(app)

app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024

# Register API routes.
app.register_blueprint(processing_bp, url_prefix="/api")
app.register_blueprint(upload_bp, url_prefix="/api")
app.register_blueprint(chat_bp, url_prefix="/api")
app.register_blueprint(audio_analysis_bp, url_prefix="/api")
app.register_blueprint(video_analysis_bp, url_prefix="/api")
app.register_blueprint(results_bp, url_prefix="/api")


@app.route("/", methods=["GET"])
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/uploads/<path:filename>", methods=["GET"])
def uploaded_file(filename):
    return send_from_directory(UPLOADS_DIR, filename)


@app.route("/<path:asset>", methods=["GET"])
def frontend_asset(asset):
    asset_file = FRONTEND_DIR / asset
    if asset_file.is_file():
        return send_from_directory(FRONTEND_DIR, asset)
    # Default fallback to index.html for client-side routing
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/api", methods=["GET"])
def api_status():
    return jsonify({
        "success": True,
        "message": "CrimeVision AI API is running",
        "endpoints": {
            "health": "/api/health",
            "image_analysis": "/api/image/analyze",
            "audio_analysis": "/api/audio/analyze",
            "video_analysis": "/api/video/analyze",
            "chat": "/api/chat/<mode>",
            "upload": "/api/upload",
            "results": "/api/results",
        }
    })


if __name__ == "__main__":
    print("\n========== REGISTERED FLASK ROUTES ==========")
    print(app.url_map)

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )