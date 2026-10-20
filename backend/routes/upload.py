from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from pathlib import Path
import uuid

upload_bp = Blueprint("upload", __name__)

UPLOAD_FOLDER = Path(__file__).resolve().parent.parent / "uploads"
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {
    "image": {"jpg", "jpeg", "png", "webp", "bmp"},
    "audio": {"mp3", "wav", "m4a", "ogg", "flac"},
    "video": {"mp4", "mov", "avi", "mkv", "webm"}
}


@upload_bp.route("/upload", methods=["GET"])
def upload_status():
    return jsonify({
        "success": True,
        "message": "Upload service ready"
    })


@upload_bp.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({
            "success": False,
            "error": "No file found. Use the 'file' form field."
        }), 400

    uploaded_file = request.files["file"]

    if not uploaded_file.filename:
        return jsonify({
            "success": False,
            "error": "Please select a file."
        }), 400

    filename = secure_filename(uploaded_file.filename)

    if not filename:
        return jsonify({
            "success": False,
            "error": "Invalid filename."
        }), 400

    if "." not in filename:
        return jsonify({
            "success": False,
            "error": "File must have an extension."
        }), 400

    extension = Path(filename).suffix.lower().lstrip(".")
    media_type = next(
        (
            kind
            for kind, extensions in ALLOWED_EXTENSIONS.items()
            if extension in extensions
        ),
        None,
    )

    if media_type is None:
        return jsonify({
            "success": False,
            "error": "Unsupported image, audio, or video format."
        }), 400

    media_folder = UPLOAD_FOLDER / media_type
    media_folder.mkdir(parents=True, exist_ok=True)
    unique_filename = f"{uuid.uuid4().hex}_{filename}"
    save_path = media_folder / unique_filename

    uploaded_file.save(str(save_path))

    return jsonify({
        "success": True,
        "message": "File uploaded successfully",
        "media_type": media_type,
        "filename": unique_filename,
        "original_filename": filename,
        "file_path": f"{media_type}/{unique_filename}"
    }), 200