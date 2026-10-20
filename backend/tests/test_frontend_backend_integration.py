import io
import sys
import wave
from pathlib import Path

import cv2
import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import app
from services.session_store import session_store


@pytest.fixture
def client():
    app.config.update(TESTING=True)
    return app.test_client()


@pytest.fixture(autouse=True)
def isolated_sessions(tmp_path, monkeypatch):
    monkeypatch.setattr(session_store, "_sessions", {})
    monkeypatch.setattr(session_store, "storage_dir", tmp_path / "sessions")
    session_store.storage_dir.mkdir()
    from routes import processing

    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    monkeypatch.setattr(processing, "UPLOAD_FOLDER", upload_dir)


def _image_upload():
    image_data = io.BytesIO()
    Image.new("RGB", (16, 12), color="navy").save(image_data, format="PNG")
    image_data.seek(0)
    return {"file": (image_data, "evidence.png")}


def test_frontend_and_health_are_served_by_flask(client):
    page = client.get("/")
    health = client.get("/api/health")
    script = client.get("/app.js")
    stylesheet = client.get("/styles.css")

    assert page.status_code == 200
    assert b"CrimeVision AI" in page.data
    assert health.status_code == 200
    assert health.get_json()["success"] is True
    assert script.status_code == 200
    assert stylesheet.status_code == 200
    assert client.get("/api").status_code == 200
    assert client.get("/api/chat").status_code == 200
    assert client.get("/api/audio").status_code == 200
    assert client.get("/api/video").status_code == 200
    assert client.get("/api/upload").status_code == 200
    assert client.get("/api/results").status_code == 200


def test_image_analysis_upload_returns_evidence_session(client, monkeypatch):
    from services import vision

    monkeypatch.setattr(
        vision,
        "get_detector",
        lambda: lambda image: [
            {
                "label": "person",
                "score": 0.97,
                "box": {"xmin": 1, "ymin": 2, "xmax": 8, "ymax": 10},
            }
        ],
    )
    monkeypatch.setattr(
        vision,
        "get_captioner",
        lambda: lambda image: [{"generated_text": "A person in a room."}],
    )

    response = client.post(
        "/api/image/analyze",
        data=_image_upload(),
        content_type="multipart/form-data",
    )

    result = response.get_json()
    assert response.status_code == 200
    assert result["success"] is True
    assert result["summary"] == "A person in a room."
    assert result["people_count"] == 1
    assert result["session_id"]
    assert session_store.get_session(result["session_id"])["source"] == "image"


def test_audio_analysis_session_supports_evidence_chat(client, monkeypatch):
    from services.audio_service import audio_service

    monkeypatch.setattr(
        audio_service,
        "analyze_audio",
        lambda path: {
            "success": True,
            "transcript": "A person entered the room.",
            "segments": [{"start": 3, "end": 4, "text": "entered the room"}],
            "timeline": [
                {
                    "start_raw": 3,
                    "end_raw": 4,
                    "description": "A speaker reported someone entering.",
                }
            ],
        },
    )
    audio = io.BytesIO()
    with wave.open(audio, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(8000)
        wav_file.writeframes(b"\x00\x00" * 800)
    audio.seek(0)
    response = client.post(
        "/api/audio/analyze",
        data={"file": (audio, "evidence.wav")},
        content_type="multipart/form-data",
    )

    result = response.get_json()
    assert response.status_code == 200
    assert result["success"] is True
    assert result["session_id"]

    chat = client.post(
        "/api/chat/audio",
        json={
            "session_id": result["session_id"],
            "question": "What happened at 00:03?",
        },
    )
    assert chat.status_code == 200
    assert "speaker reported someone entering" in chat.get_json()["answer"]


def test_video_analysis_upload_returns_timeline_and_session(
    client,
    monkeypatch,
    tmp_path,
):
    import video_module.api as video_api

    monkeypatch.setattr(
        video_api,
        "detect_objects_in_frames",
        lambda frames: [
            {
                "timestamp": 0.0,
                "detections": [{"label": "person", "score": 0.95, "box": {}}],
            }
        ],
    )
    monkeypatch.setattr(
        video_api,
        "generate_frame_captions",
        lambda frames: [{"timestamp": 0.0, "caption": "A person is visible."}],
    )
    monkeypatch.setattr(
        video_api,
        "classify_crime",
        lambda detections, captions: {
            "incident_assessment": "insufficient_information",
            "summary": "A person is visible in the sampled frame.",
            "actions": [],
        },
    )

    video_path = tmp_path / "evidence.avi"
    writer = cv2.VideoWriter(
        str(video_path),
        cv2.VideoWriter_fourcc(*"MJPG"),
        2,
        (64, 48),
    )
    if not writer.isOpened():
        pytest.skip("OpenCV MJPG video encoding is unavailable.")
    for color in ((0, 0, 255), (0, 255, 0), (255, 0, 0), (0, 0, 0)):
        writer.write(np.full((48, 64, 3), color, dtype=np.uint8))
    writer.release()

    response = client.post(
        "/api/video/analyze",
        data={
            "file": (
                io.BytesIO(video_path.read_bytes()),
                "evidence.avi",
            )
        },
        content_type="multipart/form-data",
    )

    result = response.get_json()
    assert response.status_code == 200
    assert result["success"] is True
    assert result["people_count"] == 1
    assert result["metadata"]["sampled_frames"] >= 1
    assert result["timeline"][0]["description"] == "A person is visible."
    assert result["session_id"]
    assert session_store.get_session(result["session_id"])["source"] == "video"


def test_analysis_endpoint_rejects_wrong_media_type(client):
    response = client.post(
        "/api/image/analyze",
        data={"file": (io.BytesIO(b"not an image"), "evidence.mp4")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert response.get_json()["success"] is False


def test_results_endpoint_lifecycle(client):
    sid = session_store.create_session({
        "source": "image",
        "summary": "Laboratory testing scene",
        "objects": [{"label": "computer", "score": 0.99}],
        "people_count": 0,
    })

    # Retrieve all results
    all_res = client.get("/api/results")
    assert all_res.status_code == 200
    data = all_res.get_json()
    assert data["success"] is True
    assert any(s["session_id"] == sid for s in data["sessions"])

    # Retrieve single session
    single = client.get(f"/api/results/{sid}")
    assert single.status_code == 200
    single_data = single.get_json()
    assert single_data["success"] is True
    assert single_data["result"]["source"] == "image"

    # Delete session
    del_res = client.delete(f"/api/results/{sid}")
    assert del_res.status_code == 200
    assert del_res.get_json()["success"] is True

    # Ensure 404 after deletion
    after_del = client.get(f"/api/results/{sid}")
    assert after_del.status_code == 404


def test_file_upload_endpoint(client):
    data = io.BytesIO(b"fake audio data")
    response = client.post(
        "/api/upload",
        data={"file": (data, "recording.mp3")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    res = response.get_json()
    assert res["success"] is True
    assert res["media_type"] == "audio"


def test_chat_rule_based_fallback(client):
    sid = session_store.create_session({
        "source": "image",
        "summary": "Suspect seen near the entrance.",
        "people_count": 2,
        "objects": [{"label": "person", "score": 0.98}, {"label": "knife", "score": 0.95}],
    })

    # Ask about people
    chat_res = client.post(
        "/api/chat/image",
        json={"session_id": sid, "question": "How many people were detected?"},
    )
    assert chat_res.status_code == 200
    assert "2 person" in chat_res.get_json()["answer"]

    # Ask about weapons
    chat_weapon = client.post(
        "/api/chat/image",
        json={"session_id": sid, "question": "Are there any weapons?"},
    )
    assert chat_weapon.status_code == 200
    assert "weapon" in chat_weapon.get_json()["answer"].lower()
