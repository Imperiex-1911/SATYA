"""Voice clone detector — spectral feature analysis using librosa.

Detects synthetic/cloned voices by analyzing:
- MFCC statistics (unnatural consistency in TTS)
- Spectral flux (smoothness indicates synthesis)
- Harmonic-to-noise ratio (synthesizers produce cleaner harmonics)
- Spectral centroid variance
"""

import logging
import numpy as np
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Thresholds derived from analysis of natural vs synthetic speech datasets
_MFCC_STD_THRESHOLD = 8.0         # Below = suspiciously consistent MFCCs
_SPECTRAL_FLUX_THRESHOLD = 0.003  # Below = overly smooth spectrum
_HNR_THRESHOLD = 18.0             # Above = too clean (synthesizer artifact)
_CENTROID_CV_THRESHOLD = 0.15     # Below = flat spectral centroid over time


def detect_voice_clone(audio_path: str) -> Dict[str, Any]:
    """Analyze audio for synthetic voice characteristics.

    Returns:
        voice_clone_score (0.0–1.0): probability voice is cloned/synthesized
        component scores for explainability
    """
    import librosa

    try:
        y, sr = librosa.load(audio_path, sr=16000, mono=True)
    except Exception as e:
        logger.warning(f"Librosa load failed in voice clone detector: {e}")
        return _neutral_result()

    duration = len(y) / sr
    if duration < 2.0:
        logger.warning("Audio too short for voice clone detection")
        return _neutral_result()

    scores = {}

    # ── 1. MFCC consistency ───────────────────────────────────────
    # TTS produces unnaturally consistent MFCCs across time
    try:
        mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13, hop_length=512)
        # Average std across all 13 MFCC coefficients over time
        mfcc_time_std = float(np.mean(np.std(mfccs, axis=1)))
        # Low std = too consistent = suspicious
        scores["mfcc_consistency"] = max(0.0, 1.0 - (mfcc_time_std / (_MFCC_STD_THRESHOLD * 2)))
    except Exception as e:
        logger.debug(f"MFCC analysis failed: {e}")
        scores["mfcc_consistency"] = 0.2

    # ── 2. Spectral flux ──────────────────────────────────────────
    # Natural voice has rapid spectral changes; TTS is smoother
    try:
        stft = np.abs(librosa.stft(y, hop_length=512))
        # Spectral flux = mean frame-to-frame spectral change
        flux = np.mean(np.diff(stft, axis=1) ** 2)
        scores["spectral_smoothness"] = max(0.0, 1.0 - (flux / (_SPECTRAL_FLUX_THRESHOLD * 10)))
    except Exception as e:
        logger.debug(f"Spectral flux failed: {e}")
        scores["spectral_smoothness"] = 0.2

    # ── 3. Harmonic-to-noise ratio ───────────────────────────────
    # Synthesizers produce tonal harmonics with low noise floor
    try:
        harmonic, percussive = librosa.effects.hpss(y)
        harmonic_power = float(np.mean(harmonic ** 2))
        noise_power = float(np.mean((y - harmonic) ** 2)) + 1e-10
        hnr_db = 10 * np.log10(harmonic_power / noise_power + 1e-10)
        # Very high HNR = too clean = synthesizer artifact
        scores["hnr_anomaly"] = min(1.0, max(0.0, (hnr_db - _HNR_THRESHOLD) / 15.0))
    except Exception as e:
        logger.debug(f"HNR analysis failed: {e}")
        scores["hnr_anomaly"] = 0.2

    # ── 4. Spectral centroid variance ────────────────────────────
    # Real voice: centroid varies; TTS: unnaturally stable centroid
    try:
        centroid = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=512)[0]
        centroid_cv = float(np.std(centroid) / (np.mean(centroid) + 1e-8))
        # Low CV = too stable = suspicious
        scores["centroid_flatness"] = max(0.0, 1.0 - (centroid_cv / (_CENTROID_CV_THRESHOLD * 3)))
    except Exception as e:
        logger.debug(f"Spectral centroid failed: {e}")
        scores["centroid_flatness"] = 0.2

    # ── Weighted aggregation ──────────────────────────────────────
    weights = {
        "mfcc_consistency": 0.35,
        "spectral_smoothness": 0.30,
        "hnr_anomaly": 0.20,
        "centroid_flatness": 0.15,
    }
    clone_score = sum(weights[k] * scores[k] for k in weights)

    logger.info(
        f"VoiceClone: mfcc={scores['mfcc_consistency']:.2f}, "
        f"flux={scores['spectral_smoothness']:.2f}, "
        f"hnr={scores['hnr_anomaly']:.2f}, "
        f"centroid={scores['centroid_flatness']:.2f} "
        f"→ clone_score={clone_score:.3f}"
    )

    return {
        "voice_clone_score": round(clone_score, 3),
        "mfcc_consistency": round(scores["mfcc_consistency"], 3),
        "spectral_smoothness": round(scores["spectral_smoothness"], 3),
        "hnr_anomaly": round(scores["hnr_anomaly"], 3),
        "centroid_flatness": round(scores["centroid_flatness"], 3),
    }


def _neutral_result() -> Dict[str, Any]:
    return {
        "voice_clone_score": 0.2,
        "mfcc_consistency": 0.2,
        "spectral_smoothness": 0.2,
        "hnr_anomaly": 0.2,
        "centroid_flatness": 0.2,
    }
