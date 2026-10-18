import os
from typing import Any, Dict

from config import MODEL_CONFIG
from .logger import app_logger


def _get_device() -> str:
    try:
        import torch

        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        return "cpu"


def load_rt_detr_model() -> Dict[str, Any]:
    """Load RT-DETR configuration or return safe placeholders."""
    try:
        from transformers import AutoImageProcessor, AutoModelForObjectDetection

        model_name = os.getenv("RT_DETR_MODEL", "PekingU/rtdetr_r50vd")
        processor = AutoImageProcessor.from_pretrained(model_name)
        model = AutoModelForObjectDetection.from_pretrained(model_name)
        return {
            "model": model,
            "processor": processor,
            "device": _get_device(),
            "config": MODEL_CONFIG.get("rt_detr", {}),
        }
    except Exception as exc:  # pragma: no cover - defensive fallback
        app_logger.warning("RT-DETR model unavailable: %s", exc)
        return {"model": None, "processor": None, "device": _get_device()}


def load_clip_model() -> Dict[str, Any]:
    """Load CLIP configuration or return safe placeholders."""
    try:
        from transformers import CLIPModel, CLIPProcessor

        model_name = os.getenv("CLIP_MODEL", "openai/clip-vit-base-patch32")
        model = CLIPModel.from_pretrained(model_name)
        processor = CLIPProcessor.from_pretrained(model_name)
        return {
            "model": model,
            "processor": processor,
            "device": _get_device(),
            "config": MODEL_CONFIG.get("clip", {}),
        }
    except Exception as exc:  # pragma: no cover - defensive fallback
        app_logger.warning("CLIP model unavailable: %s", exc)
        return {"model": None, "processor": None, "device": _get_device()}


def load_blip2_model() -> Dict[str, Any]:
    """Load BLIP-2 configuration or return safe placeholders."""
    try:
        from transformers import Blip2ForConditionalGeneration, Blip2Processor

        model_name = os.getenv("BLIP2_MODEL", "Salesforce/blip2-opt-2.7b")
        model = Blip2ForConditionalGeneration.from_pretrained(model_name)
        processor = Blip2Processor.from_pretrained(model_name)
        return {
            "model": model,
            "processor": processor,
            "device": _get_device(),
            "config": MODEL_CONFIG.get("blip2", {}),
        }
    except Exception as exc:  # pragma: no cover - defensive fallback
        app_logger.warning("BLIP-2 model unavailable: %s", exc)
        return {"model": None, "processor": None, "device": _get_device()}


def load_sam_model() -> Dict[str, Any]:
    """Load SAM configuration or return safe placeholders."""
    try:
        from transformers import SamModel, SamProcessor

        model_name = os.getenv("SAM_MODEL", "facebook/sam-vit-base")
        model = SamModel.from_pretrained(model_name)
        processor = SamProcessor.from_pretrained(model_name)
        return {
            "model": model,
            "processor": processor,
            "predictor": None,
            "device": _get_device(),
            "config": MODEL_CONFIG.get("sam", {}),
        }
    except Exception as exc:  # pragma: no cover - defensive fallback
        app_logger.warning("SAM model unavailable: %s", exc)
        return {"model": None, "processor": None, "predictor": None, "device": _get_device()}


def preload_models() -> Dict[str, Any]:
    """Load expensive AI models lazily or as a no-op for now."""
    app_logger.info("Model preloading is not configured in this starter build.")
    return {"status": "deferred", "models": {"rt_detr": None, "clip": None, "blip2": None, "sam": None}}
