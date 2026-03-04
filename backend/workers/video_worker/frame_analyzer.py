"""
Frame-level forensic analysis:
  1. DCT frequency analysis  — detects GAN checkerboard / diffusion artifacts
  2. SSIM temporal consistency — detects unnatural frame-to-frame changes
  3. Face quality scoring    — detects blurring, boundary artifacts
"""
import cv2
import numpy as np
from scipy.fft import dct
from skimage.metrics import structural_similarity as ssim
from typing import List, Tuple
import logging

logger = logging.getLogger(__name__)


class FrameAnalyzer:

    # ── DCT Frequency Analysis ──────────────────────────────────────────────
    def analyze_dct(self, face_crop: np.ndarray) -> float:
        """
        Compute a GAN artifact score via DCT frequency analysis.

        GAN-generated faces tend to have energy concentrated at regular
        grid frequencies (checkerboard pattern) in the DCT spectrum.
        Returns P(fake) ∈ [0, 1].
        """
        gray = cv2.cvtColor(face_crop, cv2.COLOR_RGB2GRAY).astype(np.float32)

        # Block-wise 8x8 DCT (same as JPEG compression analysis)
        h, w = gray.shape
        block_anomalies = []

        for i in range(0, h - 8, 8):
            for j in range(0, w - 8, 8):
                block = gray[i:i + 8, j:j + 8]
                d = dct(dct(block.T, norm='ortho').T, norm='ortho')

                # High-frequency energy ratio — GAN faces have unnatural HF patterns
                total_energy = np.sum(d ** 2) + 1e-9
                # Top-left 4x4 = low frequency; rest = high frequency
                lf_energy = np.sum(d[:4, :4] ** 2)
                hf_energy = total_energy - lf_energy
                hf_ratio = hf_energy / total_energy

                # GAN checkerboard: look for energy spikes at (4,0), (0,4), (4,4)
                checkerboard = (d[4, 0] ** 2 + d[0, 4] ** 2 + d[4, 4] ** 2) / total_energy

                block_anomalies.append(hf_ratio * 0.6 + checkerboard * 0.4)

        if not block_anomalies:
            return 0.0

        avg_anomaly = float(np.mean(block_anomalies))

        # Normalize: real images typically have avg_anomaly ~0.3-0.5
        # GAN images often score > 0.55
        score = max(0.0, min(1.0, (avg_anomaly - 0.30) / 0.35))
        return score

    # ── Face Boundary Artifact Detection ───────────────────────────────────
    def analyze_face_boundary(self, face_crop: np.ndarray) -> float:
        """
        Detect blending artifacts at face boundaries.
        Deepfakes often show sharp inconsistencies at the face/background edge.
        Returns P(artifact) ∈ [0, 1].
        """
        gray = cv2.cvtColor(face_crop, cv2.COLOR_RGB2GRAY)

        # Edge detection — look for unnatural sharp edges at the face border
        edges = cv2.Canny(gray, 50, 150)

        # Border region (outer 15% of image)
        h, w = edges.shape
        border_mask = np.zeros_like(edges)
        border_px = int(min(h, w) * 0.15)
        border_mask[:border_px, :] = 1
        border_mask[-border_px:, :] = 1
        border_mask[:, :border_px] = 1
        border_mask[:, -border_px:] = 1
        interior_mask = 1 - border_mask

        border_edges = np.sum(edges * border_mask)
        interior_edges = np.sum(edges * interior_mask) + 1

        # High border/interior edge ratio → boundary artifacts
        ratio = border_edges / interior_edges
        score = max(0.0, min(1.0, (ratio - 0.3) / 0.7))
        return score

    # ── SSIM Temporal Consistency ───────────────────────────────────────────
    def analyze_temporal_consistency(
        self, frame_paths: List[str]
    ) -> Tuple[float, List[float]]:
        """
        Check frame-to-frame consistency using SSIM.

        Real videos have smooth transitions; deepfakes often show
        sudden texture/lighting discontinuities between frames.
        Returns (temporal_anomaly_score, per_frame_anomaly_list).
        """
        if len(frame_paths) < 2:
            return 0.0, []

        anomalies = []
        prev_gray = None

        for path in frame_paths:
            img = cv2.imread(path)
            if img is None:
                continue
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            gray = cv2.resize(gray, (320, 240))

            if prev_gray is not None:
                score, _ = ssim(prev_gray, gray, full=True)
                # Low SSIM between consecutive frames = temporal anomaly
                # Normal video: SSIM ~0.85–0.98; deepfakes often drop to <0.70
                anomaly = max(0.0, (0.85 - score) / 0.85)
                anomalies.append(float(anomaly))

            prev_gray = gray

        if not anomalies:
            return 0.0, []

        # Weight: penalise sudden spikes more (max anomaly matters)
        avg_anomaly = float(np.mean(anomalies))
        max_anomaly = float(np.max(anomalies))
        temporal_score = avg_anomaly * 0.6 + max_anomaly * 0.4

        return min(1.0, temporal_score), anomalies
