"""
Face detection using MediaPipe.
Extracts face regions from JPEG frames for deepfake analysis.
"""
import mediapipe as mp
import cv2
import numpy as np
from dataclasses import dataclass
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

mp_face_detection = mp.solutions.face_detection


@dataclass
class DetectedFace:
    frame_index: int
    bbox: tuple          # (x, y, w, h) in pixels
    confidence: float
    face_crop: np.ndarray  # cropped face region (224x224 RGB)
    landmarks: Optional[List[tuple]] = None


class FaceDetector:
    def __init__(self, min_detection_confidence: float = 0.5):
        self.detector = mp_face_detection.FaceDetection(
            model_selection=1,  # 1 = full-range model (better for varied distances)
            min_detection_confidence=min_detection_confidence,
        )

    def detect_faces(self, frame_path: str, frame_index: int) -> List[DetectedFace]:
        """Detect all faces in a single frame. Returns list of DetectedFace."""
        img = cv2.imread(frame_path)
        if img is None:
            logger.warning(f"Could not read frame: {frame_path}")
            return []

        h, w = img.shape[:2]
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        results = self.detector.process(rgb)

        faces = []
        if not results.detections:
            return faces

        for detection in results.detections:
            bbox_rel = detection.location_data.relative_bounding_box
            x = max(0, int(bbox_rel.xmin * w))
            y = max(0, int(bbox_rel.ymin * h))
            fw = min(int(bbox_rel.width * w), w - x)
            fh = min(int(bbox_rel.height * h), h - y)

            if fw < 20 or fh < 20:
                continue  # skip tiny faces

            # Crop and resize face to 224x224 for classifier
            face_crop = rgb[y:y + fh, x:x + fw]
            face_crop_resized = cv2.resize(face_crop, (224, 224))

            faces.append(DetectedFace(
                frame_index=frame_index,
                bbox=(x, y, fw, fh),
                confidence=detection.score[0],
                face_crop=face_crop_resized,
            ))

        return faces

    def close(self):
        self.detector.close()
