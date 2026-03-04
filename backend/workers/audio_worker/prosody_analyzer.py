"""Prosody analysis using librosa — detect unnatural speech patterns."""

import logging
import numpy as np
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Thresholds calibrated for synthetic speech
_MIN_PITCH_STD_NATURAL = 20.0       # Hz — flat pitch < this = suspicious
_MAX_ZCR_UNIFORMITY = 0.85         # ZCR coefficient of variation — too uniform = suspicious
_MIN_ENERGY_VARIANCE = 0.01        # RMS energy variance threshold
_MIN_SILENCE_RATIO = 0.05          # Real speech has pauses; < 5% silence = suspicious


def analyze_prosody(audio_path: str) -> Dict[str, Any]:
    """Extract prosody features from WAV file.

    Returns:
        prosody_anomaly_score (0.0–1.0): 1.0 = highly anomalous (synthetic)
        component scores and raw features for explainability
    """
    import librosa

    try:
        y, sr = librosa.load(audio_path, sr=16000, mono=True)
    except Exception as e:
        logger.warning(f"Librosa load failed: {e}")
        return _neutral_result()

    duration = len(y) / sr
    if duration < 1.0:
        logger.warning("Audio too short for prosody analysis")
        return _neutral_result()

    scores = {}

    # ── 1. Pitch flatness ─────────────────────────────────────────
    # Synthetic TTS often has unnaturally flat or quantized pitch
    try:
        f0, voiced_flag, _ = librosa.pyin(
            y, fmin=librosa.note_to_hz("C2"), fmax=librosa.note_to_hz("C7"),
            sr=sr, frame_length=2048
        )
        voiced_f0 = f0[voiced_flag & ~np.isnan(f0)]
        if len(voiced_f0) > 10:
            pitch_std = float(np.std(voiced_f0))
            # Score: 0=natural (high std), 1=synthetic (flat)
            scores["pitch_flatness"] = max(0.0, 1.0 - (pitch_std / (_MIN_PITCH_STD_NATURAL * 2)))
        else:
            scores["pitch_flatness"] = 0.3   # Not enough voiced frames — neutral penalty
    except Exception as e:
        logger.debug(f"Pitch analysis failed: {e}")
        scores["pitch_flatness"] = 0.3

    # ── 2. Speaking rate uniformity ───────────────────────────────
    # Real speech has rhythm variation; TTS is metronomic
    try:
        # Zero-crossing rate as proxy for rhythmic structure
        zcr = librosa.feature.zero_crossing_rate(y, frame_length=2048, hop_length=512)[0]
        zcr_cv = float(np.std(zcr) / (np.mean(zcr) + 1e-8))   # coefficient of variation
        # Low CV = too uniform = more synthetic
        scores["rate_uniformity"] = max(0.0, 1.0 - (zcr_cv / _MAX_ZCR_UNIFORMITY))
    except Exception as e:
        logger.debug(f"ZCR analysis failed: {e}")
        scores["rate_uniformity"] = 0.2

    # ── 3. Energy dynamics ────────────────────────────────────────
    # Natural speech has dynamic energy variation; TTS is compressed
    try:
        rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=512)[0]
        rms_var = float(np.var(rms))
        # Low variance = too smooth = suspicious
        scores["energy_flatness"] = max(0.0, 1.0 - (rms_var / (_MIN_ENERGY_VARIANCE * 5)))
    except Exception as e:
        logger.debug(f"RMS analysis failed: {e}")
        scores["energy_flatness"] = 0.2

    # ── 4. Silence ratio (micro-pauses) ───────────────────────────
    # Human speech has natural pauses; some TTS eliminates them
    try:
        silence_intervals = librosa.effects.split(y, top_db=30)
        total_speech = sum(end - start for start, end in silence_intervals)
        silence_ratio = 1.0 - (total_speech / len(y))
        # Too little silence = possibly synthetic
        scores["silence_deficit"] = max(0.0, _MIN_SILENCE_RATIO - silence_ratio) / _MIN_SILENCE_RATIO
        scores["silence_deficit"] = min(1.0, scores["silence_deficit"])
    except Exception as e:
        logger.debug(f"Silence analysis failed: {e}")
        scores["silence_deficit"] = 0.1

    # ── Weighted aggregation ──────────────────────────────────────
    weights = {
        "pitch_flatness": 0.40,
        "rate_uniformity": 0.25,
        "energy_flatness": 0.20,
        "silence_deficit": 0.15,
    }
    prosody_anomaly = sum(weights[k] * scores[k] for k in weights)

    logger.info(
        f"Prosody: pitch_flat={scores['pitch_flatness']:.2f}, "
        f"rate_uniform={scores['rate_uniformity']:.2f}, "
        f"energy_flat={scores['energy_flatness']:.2f}, "
        f"silence_def={scores['silence_deficit']:.2f} "
        f"→ anomaly={prosody_anomaly:.3f}"
    )

    return {
        "prosody_anomaly_score": round(prosody_anomaly, 3),
        "pitch_flatness": round(scores["pitch_flatness"], 3),
        "rate_uniformity": round(scores["rate_uniformity"], 3),
        "energy_flatness": round(scores["energy_flatness"], 3),
        "silence_deficit": round(scores["silence_deficit"], 3),
        "duration_seconds": round(duration, 1),
    }


def _neutral_result() -> Dict[str, Any]:
    """Return neutral (non-penalizing) scores when analysis can't run."""
    return {
        "prosody_anomaly_score": 0.2,
        "pitch_flatness": 0.2,
        "rate_uniformity": 0.2,
        "energy_flatness": 0.2,
        "silence_deficit": 0.1,
        "duration_seconds": 0.0,
    }
