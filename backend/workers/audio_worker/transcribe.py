"""Speech-to-text transcription using faster-whisper (local, CPU-based).

Replaces Amazon Transcribe — no AWS dependency, supports all Indian languages.
Model is loaded once as a module-level singleton on first use.

Supported Indian languages (Whisper ISO 639-1 codes):
    hi=Hindi, ta=Tamil, te=Telugu, bn=Bengali, mr=Marathi,
    kn=Kannada, ml=Malayalam, gu=Gujarati, pa=Punjabi, ur=Urdu
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Model size trade-offs:
#   tiny  (~75MB)  — fastest, lower accuracy
#   base  (~145MB) — good balance for short clips
#   small (~244MB) — recommended: accurate + reasonable CPU speed
#   medium(~1.5GB) — best accuracy, slow on CPU
_WHISPER_MODEL_SIZE = "small"

# Module-level singleton — loaded once, reused across all jobs
_model = None


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        logger.info(f"Loading Whisper '{_WHISPER_MODEL_SIZE}' model (first-time download may take a minute)...")
        _model = WhisperModel(
            _WHISPER_MODEL_SIZE,
            device="cpu",
            compute_type="int8",   # quantized — 4x faster, same accuracy
        )
        logger.info("Whisper model loaded.")
    return _model


def run_transcription(
    analysis_id: str,
    local_audio_path: str,
    language: str = "en",
) -> Dict[str, Any]:
    """Transcribe a local audio file using faster-whisper.

    Args:
        analysis_id: For logging only.
        local_audio_path: Absolute path to the WAV/MP3/M4A file.
        language: ISO 639-1 hint (e.g. 'hi', 'ta', 'en'). If empty, auto-detect.

    Returns:
        dict with keys: transcript, language, confidence, word_count, speaker_count
    """
    try:
        model = _get_model()

        # Use language hint if provided; Whisper auto-detects if None
        lang_hint: Optional[str] = language[:2].lower() if language else None
        if lang_hint == "en":
            lang_hint = None   # Let Whisper distinguish en-IN / en-GB automatically

        logger.info(f"[{analysis_id}] Starting Whisper transcription (lang_hint={lang_hint})")

        segments, info = model.transcribe(
            local_audio_path,
            language=lang_hint,
            beam_size=3,           # faster than default beam_size=5
            vad_filter=True,       # skip silence
            vad_parameters={"min_silence_duration_ms": 500},
        )

        # Materialise segments (generator)
        segment_list = list(segments)
        full_text = " ".join(seg.text.strip() for seg in segment_list)
        word_count = len(full_text.split()) if full_text.strip() else 0

        # Average per-segment no_speech_prob as inverse confidence
        if segment_list:
            avg_no_speech = sum(s.no_speech_prob for s in segment_list) / len(segment_list)
            confidence = round(1.0 - avg_no_speech, 3)
        else:
            confidence = 0.0

        detected_lang = info.language or "unknown"
        lang_prob = round(info.language_probability, 3)

        logger.info(
            f"[{analysis_id}] Whisper done: {word_count} words, "
            f"lang={detected_lang}({lang_prob:.2f}), confidence={confidence:.2f}"
        )

        return {
            "transcript": full_text[:2000],   # cap stored transcript at 2KB
            "language": detected_lang,
            "language_probability": lang_prob,
            "confidence": confidence,
            "word_count": word_count,
            "speaker_count": 1,   # faster-whisper base models don't do diarisation
        }

    except Exception as e:
        logger.warning(f"[{analysis_id}] Whisper transcription failed: {e}")
        return {
            "transcript": "",
            "language": language or "unknown",
            "language_probability": 0.0,
            "confidence": 0.0,
            "word_count": 0,
            "speaker_count": 1,
        }
