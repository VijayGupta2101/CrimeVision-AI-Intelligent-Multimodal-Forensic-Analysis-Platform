import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
TEMP_DIR = str(BASE_DIR / "temp")
UPLOAD_FOLDER = str(BASE_DIR / "uploads")

for directory in (TEMP_DIR, UPLOAD_FOLDER):
    Path(directory).mkdir(parents=True, exist_ok=True)


class APIConfig:
    SECRET_KEY = os.getenv("SECRET_KEY", "crimevision-dev-secret-key")
    DEBUG = False
    TESTING = False
    JSON_SORT_KEYS = False
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024
    UPLOAD_FOLDER = UPLOAD_FOLDER
    TEMP_DIR = TEMP_DIR
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "bmp", "tif", "tiff", "mp4", "mp3", "wav", "pdf", "docx"}


API_CONFIG = APIConfig()

MODEL_CONFIG = {
    "rt_detr": {
        "confidence_threshold": 0.5,
        "max_detections": 100,
    },
    "sam": {
        "points_per_side": 32,
        "pred_iou_thresh": 0.88,
    },
    "clip": {
        "top_k": 5,
    },
    "blip2": {
        "max_new_tokens": 50,
    },
}

PROCESSING_CONFIG = {
    "image_size": 1024,
    "batch_size": 1,
    "confidence_threshold": 0.5,
    "max_workers": 2,
    "output_format": "json",
}
