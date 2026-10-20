from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

BACKEND_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BACKEND_DIR.parent / "frontend"
load_dotenv(BACKEND_DIR / ".env")

from audio_module.api import audio_analysis_bp
from routes.chat_routes import chat_bp
from routes.processing import processing_bp
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


@app.route("/", methods=["GET"])
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/<path:asset>", methods=["GET"])
def frontend_asset(asset):
    return send_from_directory(FRONTEND_DIR, asset)


@app.route("/api", methods=["GET"])
def api_status():
    return jsonify({
        "success": True,
        "message": "CrimeVision AI API is running"
    })


if __name__ == "__main__":
    print("\n========== REGISTERED FLASK ROUTES ==========")
    print(app.url_map)

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )