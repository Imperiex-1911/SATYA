"""Audio score aggregation — implements design.md §5.2.4 formula."""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Weights from design.md §5.2.4
# Note: lip_sync_deviation (w=0.25) is a cross-modal signal requiring video frames.
# In this worker we don't have access to video frames, so we redistribute its
# weight proportionally across the remaining three signals.
# Redistributed: voice_clone=0.35+0.09=0.44, prosody=0.25+0.08=0.33, spectral=0.15+0.08=0.23
_WEIGHTS = {
    "voice_clone": 0.44,
    "prosody": 0.33,
    "spectral": 0.23,
}


def compute_audio_score(
    voice_clone_result: Dict[str, Any],
    prosody_result: Dict[str, Any],
    transcribe_result: Dict[str, Any],
) -> Dict[str, Any]:
    """Compute audio authenticity score (0–100).

    Higher = more authentic. Components:
    - voice_clone_score: 0=natural, 1=cloned
    - prosody_anomaly_score: 0=natural, 1=synthetic prosody
    - spectral_anomaly_score: derived from voice clone detector sub-scores
    """
    voice_clone_score = voice_clone_result.get("voice_clone_score", 0.2)
    prosody_anomaly_score = prosody_result.get("prosody_anomaly_score", 0.2)

    # Spectral anomaly: average of MFCC consistency + spectral smoothness
    mfcc_c = voice_clone_result.get("mfcc_consistency", 0.2)
    spec_s = voice_clone_result.get("spectral_smoothness", 0.2)
    spectral_anomaly_score = (mfcc_c + spec_s) / 2.0

    fake_probability = (
        _WEIGHTS["voice_clone"] * voice_clone_score
        + _WEIGHTS["prosody"] * prosody_anomaly_score
        + _WEIGHTS["spectral"] * spectral_anomaly_score
    )

    audio_score = round(max(0.0, min(100.0, 100.0 - fake_probability * 100)), 1)

    # Transcription confidence adjustment: very low confidence → slight penalty
    transcribe_confidence = transcribe_result.get("confidence", 1.0)
    if transcribe_confidence > 0 and transcribe_confidence < 0.5:
        # Low transcription confidence may indicate garbled/synthetic speech
        confidence_penalty = (0.5 - transcribe_confidence) * 10.0
        audio_score = round(max(0.0, audio_score - confidence_penalty), 1)

    logger.info(
        f"Audio score: clone={voice_clone_score:.2f}, "
        f"prosody={prosody_anomaly_score:.2f}, "
        f"spectral={spectral_anomaly_score:.2f} "
        f"→ fake_prob={fake_probability:.3f}, score={audio_score}"
    )

    return {
        "audio_score": audio_score,
        "fake_probability": round(fake_probability, 3),
        "voice_clone_score": voice_clone_score,
        "prosody_anomaly_score": prosody_anomaly_score,
        "spectral_anomaly_score": round(spectral_anomaly_score, 3),
        "transcription_confidence": round(transcribe_confidence, 3),
        "word_count": transcribe_result.get("word_count", 0),
        "speaker_count": transcribe_result.get("speaker_count", 1),
    }
