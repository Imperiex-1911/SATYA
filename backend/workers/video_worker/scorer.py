"""
Video score aggregation.
Implements the weighted formula from design.md §5.1.3:

  video_score = 100 - (
      w_deepfake × avg(deepfake_scores)     # 0.40
      w_temporal × temporal_anomaly_score   # 0.25
      w_gan      × gan_fingerprint_score    # 0.20
      w_metadata × metadata_anomaly_score   # 0.15
  ) × 100
"""
from typing import List, Dict, Any
from dataclasses import dataclass
import numpy as np
import logging

logger = logging.getLogger(__name__)

WEIGHTS = {
    "deepfake": 0.40,
    "temporal": 0.25,
    "gan":       0.20,
    "metadata":  0.15,
}


@dataclass
class VideoScoreResult:
    video_score: float          # 0–100 (higher = more authentic)
    deepfake_score: float       # 0–1 (higher = more fake)
    temporal_score: float       # 0–1
    gan_score: float            # 0–1
    metadata_score: float       # 0–1
    faces_detected: int
    frames_analyzed: int
    findings: List[Dict[str, Any]]


def aggregate_video_score(
    dct_scores: List[float],        # per-face DCT anomaly scores
    boundary_scores: List[float],   # per-face boundary artifact scores
    temporal_score: float,          # SSIM temporal anomaly
    metadata_result: Dict[str, Any],
    frames_analyzed: int,
) -> VideoScoreResult:
    """Combine all signals into a final video authenticity score."""

    # ── Deepfake component: combine DCT + boundary signals ──────────────────
    if dct_scores or boundary_scores:
        all_face_scores = [d * 0.65 + b * 0.35
                           for d, b in zip(dct_scores, boundary_scores)]
        deepfake_component = float(np.mean(all_face_scores)) if all_face_scores else 0.0
    else:
        # No faces detected — mild penalty (could be faceless AI video)
        deepfake_component = 0.15
        logger.info("No faces detected in video — applying default deepfake component")

    # ── GAN component: from DCT analysis ────────────────────────────────────
    gan_component = float(np.mean(dct_scores)) if dct_scores else 0.10

    # ── Metadata component ───────────────────────────────────────────────────
    metadata_component = metadata_result.get("metadata_anomaly_score", 0.0)

    # ── Weighted fusion (design.md §5.1.3) ──────────────────────────────────
    fake_probability = (
        WEIGHTS["deepfake"] * deepfake_component +
        WEIGHTS["temporal"] * temporal_score +
        WEIGHTS["gan"]      * gan_component +
        WEIGHTS["metadata"] * metadata_component
    )

    video_score = round(max(0.0, min(100.0, 100.0 - fake_probability * 100)), 1)

    # ── Build findings ───────────────────────────────────────────────────────
    findings = []

    if deepfake_component > 0.5:
        findings.append({
            "module": "video_forensics",
            "signal": "deepfake_face",
            "severity": "HIGH" if deepfake_component > 0.7 else "MEDIUM",
            "detail": (
                f"Face boundary artifacts detected. "
                f"Anomaly score: {deepfake_component:.2f}"
            ),
        })

    if temporal_score > 0.4:
        findings.append({
            "module": "video_forensics",
            "signal": "temporal_inconsistency",
            "severity": "HIGH" if temporal_score > 0.6 else "MEDIUM",
            "detail": (
                f"Frame-to-frame consistency anomalies detected. "
                f"SSIM deviation score: {temporal_score:.2f}"
            ),
        })

    if gan_component > 0.5:
        findings.append({
            "module": "video_forensics",
            "signal": "gan_fingerprint",
            "severity": "MEDIUM",
            "detail": (
                f"DCT frequency analysis suggests GAN/diffusion generation artifacts. "
                f"Score: {gan_component:.2f}"
            ),
        })

    for flag in metadata_result.get("flags", []):
        findings.append({
            "module": "video_forensics",
            "signal": "metadata_anomaly",
            "severity": "LOW",
            "detail": f"Metadata flag: {flag}",
        })

    return VideoScoreResult(
        video_score=video_score,
        deepfake_score=round(deepfake_component, 3),
        temporal_score=round(temporal_score, 3),
        gan_score=round(gan_component, 3),
        metadata_score=round(metadata_component, 3),
        faces_detected=len(dct_scores),
        frames_analyzed=frames_analyzed,
        findings=findings,
    )
