"""
Vision Service - Object Detection, Segmentation, and Vision-Language Matching
Handles RT-DETR, SAM, CLIP, and BLIP-2 models.
"""

import cv2
import torch
import numpy as np

from PIL import Image
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from config import MODEL_CONFIG, PROCESSING_CONFIG, TEMP_DIR
from utils.logger import setup_logger
from utils.model_loader import (
    load_rt_detr_model,
    load_clip_model,
    load_blip2_model,
    load_sam_model,
)
from utils.groq_utils import get_groq_client, get_config


logger = setup_logger("vision_service")


class VisionService:
    """Service for computer vision processing."""

    def __init__(self):
        """Initialize the vision service and model references."""

        self.rt_detr = None
        self.clip = None
        self.blip2 = None
        self.sam = None

        self.device = torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )

        logger.info(
            "VisionService initialized using device: %s",
            self.device,
        )

    # ---------------------------------------------------------
    # MODEL LOADING
    # ---------------------------------------------------------

    def _ensure_models_loaded(self):
        """Ensure required models are loaded."""

        if self.rt_detr is None:
            self.rt_detr = load_rt_detr_model()

        if self.clip is None:
            self.clip = load_clip_model()

        if self.blip2 is None:
            self.blip2 = load_blip2_model()

        if self.sam is None:
            self.sam = load_sam_model()

    # ---------------------------------------------------------
    # OBJECT DETECTION USING RT-DETR
    # ---------------------------------------------------------

    def detect_objects(
        self,
        image_path: str,
        confidence_threshold: float = None,
    ) -> Dict[str, Any]:
        """
        Detect objects in an image using RT-DETR.

        Args:
            image_path:
                Path to the image file.

            confidence_threshold:
                Minimum confidence score. If omitted, the configured
                RT-DETR confidence threshold is used.

        Returns:
            Dictionary containing detected objects, bounding boxes,
            confidence scores, image dimensions, and processing status.
        """

        try:
            self._ensure_models_loaded()

            image_path = Path(image_path)

            if not image_path.is_file():
                raise FileNotFoundError(
                    f"Image not found: {image_path}"
                )

            # Load image
            image = Image.open(image_path).convert("RGB")

            # Prepare model inputs
            processor = self.rt_detr["processor"]
            model = self.rt_detr["model"]
            device = self.rt_detr.get("device", self.device)

            inputs = processor(
                images=image,
                return_tensors="pt",
            ).to(device)

            # Run inference
            model.eval()

            with torch.no_grad():
                outputs = model(**inputs)

            # Post-process results
            rt_config = MODEL_CONFIG["rt_detr"]

            threshold = (
                confidence_threshold
                if confidence_threshold is not None
                else rt_config.get("confidence_threshold", 0.5)
            )

            target_sizes = torch.tensor(
                [[image.height, image.width]],
                device=device,
            )

            results = processor.post_process_object_detection(
                outputs,
                target_sizes=target_sizes,
                threshold=threshold,
            )

            detections = []

            if results:
                result = results[0]

                boxes = result["boxes"].detach().cpu().numpy()
                scores = result["scores"].detach().cpu().numpy()
                labels = result["labels"].detach().cpu().numpy()

                id2label = getattr(
                    model.config,
                    "id2label",
                    {},
                )

                for box, score, label_id in zip(
                    boxes,
                    scores,
                    labels,
                ):
                    x1, y1, x2, y2 = box.tolist()

                    label_id = int(label_id)

                    label = id2label.get(
                        label_id,
                        str(label_id),
                    )

                    detections.append(
                        {
                            "label": label,
                            "label_id": label_id,
                            "confidence": round(float(score), 4),
                            "bbox": {
                                "x1": round(float(x1), 2),
                                "y1": round(float(y1), 2),
                                "x2": round(float(x2), 2),
                                "y2": round(float(y2), 2),
                            },
                            "width": round(float(x2 - x1), 2),
                            "height": round(float(y2 - y1), 2),
                        }
                    )

            logger.info(
                "Detected %d objects in %s",
                len(detections),
                image_path.name,
            )

            return {
                "success": True,
                "image_path": str(image_path),
                "image_width": image.width,
                "image_height": image.height,
                "object_count": len(detections),
                "confidence_threshold": threshold,
                "detections": detections,
            }

        except Exception as exc:
            logger.exception("Object detection failed")

            return {
                "success": False,
                "error": str(exc),
                "detections": [],
                "object_count": 0,
            }

    # ---------------------------------------------------------
    # IMAGE SEGMENTATION USING SAM
    # ---------------------------------------------------------

    def segment_image(
        self,
        image_path: str,
        points: Optional[List[List[float]]] = None,
        labels: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """
        Segment an image using the Segment Anything Model.

        Args:
            image_path:
                Path to the input image.

            points:
                Optional foreground/background point coordinates.

            labels:
                Optional point labels: 1 for foreground and 0 for
                background. Must correspond to points.

        Returns:
            Segmentation masks and metadata.

        Note:
            The SAM model loader must return a predictor-compatible
            object or a dictionary containing a predictor.
        """

        try:
            self._ensure_models_loaded()

            image_path = Path(image_path)

            if not image_path.is_file():
                raise FileNotFoundError(
                    f"Image not found: {image_path}"
                )

            # Load image in RGB format
            image = Image.open(image_path).convert("RGB")
            image_array = np.array(image)

            # Resolve the predictor returned by your model loader
            if isinstance(self.sam, dict):
                predictor = self.sam.get("predictor")
            else:
                predictor = self.sam

            if predictor is None:
                raise RuntimeError(
                    "SAM predictor is unavailable. "
                    "Check load_sam_model() in utils/model_loader.py."
                )

            predictor.set_image(image_array)

            input_points = (
                np.asarray(points, dtype=np.float32)
                if points is not None
                else None
            )

            input_labels = (
                np.asarray(labels, dtype=np.int32)
                if labels is not None
                else None
            )

            if input_points is not None:
                if input_labels is None:
                    input_labels = np.ones(
                        len(input_points),
                        dtype=np.int32,
                    )

                if len(input_points) != len(input_labels):
                    raise ValueError(
                        "The number of points and labels must match."
                    )

            masks, scores, _ = predictor.predict(
                point_coords=input_points,
                point_labels=input_labels,
                multimask_output=True,
            )

            mask_results = []

            for index, (mask, score) in enumerate(
                zip(masks, scores)
            ):
                mask_results.append(
                    {
                        "mask_index": index,
                        "confidence": round(float(score), 4),
                        "area_pixels": int(np.count_nonzero(mask)),
                        "mask": mask.astype(np.uint8).tolist(),
                    }
                )

            logger.info(
                "Generated %d segmentation masks for %s",
                len(mask_results),
                image_path.name,
            )

            return {
                "success": True,
                "image_path": str(image_path),
                "image_width": image.width,
                "image_height": image.height,
                "mask_count": len(mask_results),
                "masks": mask_results,
            }

        except Exception as exc:
            logger.exception("Image segmentation failed")

            return {
                "success": False,
                "error": str(exc),
                "masks": [],
                "mask_count": 0,
            }

    # ---------------------------------------------------------
    # IMAGE-TEXT MATCHING USING CLIP
    # ---------------------------------------------------------

    def match_text(
        self,
        image_path: str,
        candidate_texts: List[str],
    ) -> Dict[str, Any]:
        """
        Compare an image with candidate descriptions using CLIP.

        Args:
            image_path:
                Path to the input image.

            candidate_texts:
                List of descriptions to compare with the image.

        Returns:
            Candidate descriptions ranked by similarity.

        Note:
            The CLIP loader must return a dictionary containing
            'model' and 'processor'.
        """

        try:
            self._ensure_models_loaded()

            image_path = Path(image_path)

            if not image_path.is_file():
                raise FileNotFoundError(
                    f"Image not found: {image_path}"
                )

            if not candidate_texts:
                raise ValueError(
                    "candidate_texts must contain at least one description."
                )

            image = Image.open(image_path).convert("RGB")

            model = self.clip["model"]
            processor = self.clip["processor"]
            device = self.clip.get("device", self.device)

            inputs = processor(
                text=candidate_texts,
                images=image,
                return_tensors="pt",
                padding=True,
                truncation=True,
            )

            inputs = {
                key: value.to(device)
                for key, value in inputs.items()
            }

            model.eval()

            with torch.no_grad():
                outputs = model(**inputs)

                logits = outputs.logits_per_image[0]

                probabilities = torch.softmax(
                    logits,
                    dim=0,
                )

            probabilities = probabilities.cpu().tolist()

            matches = [
                {
                    "text": text,
                    "similarity": round(float(score), 4),
                }
                for text, score in zip(
                    candidate_texts,
                    probabilities,
                )
            ]

            matches.sort(
                key=lambda item: item["similarity"],
                reverse=True,
            )

            return {
                "success": True,
                "image_path": str(image_path),
                "matches": matches,
                "best_match": matches[0],
            }

        except Exception as exc:
            logger.exception("CLIP text-image matching failed")

            return {
                "success": False,
                "error": str(exc),
                "matches": [],
            }

    # ---------------------------------------------------------
    # IMAGE CAPTIONING USING BLIP-2
    # ---------------------------------------------------------

    def generate_caption(
        self,
        image_path: str,
        max_new_tokens: int = 100,
    ) -> Dict[str, Any]:
        """
        Generate an image caption using BLIP-2.

        Args:
            image_path:
                Path to the input image.

            max_new_tokens:
                Maximum number of newly generated tokens.

        Returns:
            Generated image caption.
        """

        try:
            self._ensure_models_loaded()

            image_path = Path(image_path)

            if not image_path.is_file():
                raise FileNotFoundError(
                    f"Image not found: {image_path}"
                )

            image = Image.open(image_path).convert("RGB")

            model = self.blip2["model"]
            processor = self.blip2["processor"]
            device = self.blip2.get("device", self.device)

            inputs = processor(
                images=image,
                return_tensors="pt",
            )

            inputs = {
                key: value.to(device)
                for key, value in inputs.items()
            }

            model.eval()

            with torch.no_grad():
                generated_ids = model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                )

            caption = processor.batch_decode(
                generated_ids,
                skip_special_tokens=True,
            )[0].strip()

            return {
                "success": True,
                "image_path": str(image_path),
                "raw_caption": caption,
            }

        except Exception as exc:
            logger.exception("Image caption generation failed")

            return {
                "success": False,
                "error": str(exc),
                "raw_caption": "",
            }

    # ---------------------------------------------------------
    # CAPTION REFINEMENT USING GROQ
    # ---------------------------------------------------------

    def refine_caption(self, raw_caption: str) -> str:
        """
        Use Groq to refine a raw BLIP-2 caption into a concise,
        professional two-line summary.

        The generated summary should describe visible content
        without inventing evidence or asserting that an apparent
        object proves a crime.
        """

        if not raw_caption or not raw_caption.strip():
            return (
                "Summary Type: Image Description\n"
                "Brief Description: No usable image caption was generated."
            )

        try:
            client = get_groq_client()
            config = get_config()

            prompt = f"""
Refine the following raw image caption into a professional,
concise summary suitable for a forensic image review.

STRUCTURE:
Line 1: Summary Type: [Brief category, such as Scene,
Surveillance, Vehicle, Person, or Evidence]
Line 2: Brief Description: [Concise description of visible content]

Rules:
- Describe only information supported by the raw caption.
- Do not invent objects, actions, identities, locations, or events.
- Do not claim that an image proves criminal activity.
- Use neutral, objective language.
- Return exactly two lines.
- Do not add a heading or explanation outside those lines.

Raw Caption: {raw_caption}

Return ONLY the refined two-line summary.
""".strip()

            completion = client.chat.completions.create(
                model=config["groq_model"],
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                temperature=0.2,
                max_tokens=150,
            )

            refined_caption = (
                completion.choices[0].message.content or ""
            ).strip()

            if refined_caption:
                return refined_caption

            return (
                "Summary Type: Image Description\n"
                f"Brief Description: {raw_caption.strip()}"
            )

        except Exception:
            logger.exception("Caption refinement failed")

            # Return a useful fallback if Groq is unavailable.
            return (
                "Summary Type: Image Description\n"
                f"Brief Description: {raw_caption.strip()}"
            )


# -------------------------------------------------------------
# SHARED SERVICE INSTANCE
# -------------------------------------------------------------

vision_service = VisionService()