"""SATYA score fusion — implements design.md §6.1 adaptive weighting.

Called by the scoring worker after all component scores are written.
"""

from typing import Optional, Dict, Any, Tuple


# ── Verdict thresholds (design.md §6.3) ──────────────────────────
def get_verdict(score: float) -> str:
    if score >= 85:
        return "AUTHENTIC"
    elif score >= 70:
        return "UNCERTAIN"
    elif score >= 50:
        return "SUSPICIOUS"
    else:
        return "HIGH_RISK"


def get_confidence(
    video_score: Optional[float],
    audio_score: Optional[float],
    text_score: Optional[float],
) -> str:
    """Confidence reflects how many modalities contributed and how aligned they are."""
    available = [s for s in [video_score, audio_score, text_score] if s is not None]
    count = len(available)

    if count == 3:
        spread = max(available) - min(available)
        if spread <= 15:
            return "HIGH"
        elif spread <= 30:
            return "MEDIUM"
        else:
            return "LOW"
    elif count == 2:
        return "MEDIUM"
    else:
        return "LOW"


def compute_satya_score(
    video_score: Optional[float],
    audio_score: Optional[float],
    text_score: Optional[float],
) -> Tuple[float, str, str, Dict[str, float]]:
    """Fuse component scores into final SATYA score.

    Applies adaptive weighting from design.md §6.1 when a modality is missing.

    Returns:
        (satya_score, verdict, confidence, weights_used)
    """
    has_video = video_score is not None
    has_audio = audio_score is not None
    has_text = text_score is not None

    # Adaptive weight table (design.md §6.1)
    if has_video and has_audio and has_text:
        w_video, w_audio, w_text = 0.50, 0.30, 0.20
    elif has_video and not has_audio and has_text:
        w_video, w_audio, w_text = 0.65, 0.00, 0.35
    elif has_video and has_audio and not has_text:
        w_video, w_audio, w_text = 0.55, 0.35, 0.10
    elif has_video and not has_audio and not has_text:
        w_video, w_audio, w_text = 1.00, 0.00, 0.00
    elif not has_video and has_audio and has_text:
        w_video, w_audio, w_text = 0.00, 0.50, 0.50
    else:
        # Fallback: equal weight on whatever is available
        n = sum([has_video, has_audio, has_text])
        w = 1.0 / max(n, 1)
        w_video = w if has_video else 0.0
        w_audio = w if has_audio else 0.0
        w_text = w if has_text else 0.0

    satya_score = (
        w_video * (video_score or 0.0)
        + w_audio * (audio_score or 0.0)
        + w_text * (text_score or 0.0)
    )
    satya_score = round(max(0.0, min(100.0, satya_score)), 1)

    verdict    = get_verdict(satya_score)
    confidence = get_confidence(video_score, audio_score, text_score)
    weights    = {"video": round(w_video, 2), "audio": round(w_audio, 2), "text": round(w_text, 2)}

    return satya_score, verdict, confidence, weights


def build_findings(item: Dict[str, Any]) -> list:
    """Extract key forensic signals from worker results for the findings list."""
    findings = []

    # ── Video findings ────────────────────────────────────────────
    video_result = item.get("video_result", {})
    if video_result:
        components = video_result.get("components", {})

        deepfake = float(components.get("deepfake", 0))
        if deepfake > 0.5:
            findings.append({
                "module": "video_forensics",
                "signal": "deepfake_face",
                "severity": "HIGH" if deepfake > 0.7 else "MEDIUM",
                "detail": f"Face boundary artifacts detected (score: {deepfake:.2f})",
            })

        temporal = float(components.get("temporal", 0))
        if temporal > 0.4:
            findings.append({
                "module": "video_forensics",
                "signal": "temporal_inconsistency",
                "severity": "HIGH" if temporal > 0.65 else "MEDIUM",
                "detail": f"Frame-to-frame temporal inconsistency detected (score: {temporal:.2f})",
            })

        gan = float(components.get("gan", 0))
        if gan > 0.4:
            findings.append({
                "module": "video_forensics",
                "signal": "gan_artifacts",
                "severity": "MEDIUM",
                "detail": f"GAN-like frequency artifacts detected in frames (score: {gan:.2f})",
            })

        faces = int(video_result.get("faces_detected", 0))
        frames = int(video_result.get("frames_analysed", 0))
        if faces > 0 and frames > 0:
            findings.append({
                "module": "video_forensics",
                "signal": "face_detection",
                "severity": "INFO",
                "detail": f"Detected {faces} face instances across {frames} frames",
            })

    # ── Audio findings ────────────────────────────────────────────
    audio_result = item.get("audio_result", {})
    if audio_result:
        clone = float(audio_result.get("voice_clone_score", 0))
        if clone > 0.4:
            findings.append({
                "module": "audio_forensics",
                "signal": "voice_clone",
                "severity": "HIGH" if clone > 0.65 else "MEDIUM",
                "detail": f"Spectral patterns consistent with synthetic voice (score: {clone:.2f})",
            })

        prosody = float(audio_result.get("prosody_anomaly_score", 0))
        if prosody > 0.5:
            findings.append({
                "module": "audio_forensics",
                "signal": "prosody_anomaly",
                "severity": "HIGH" if prosody > 0.7 else "MEDIUM",
                "detail": f"Unnatural prosody patterns detected — flat pitch or uniform rhythm (score: {prosody:.2f})",
            })

        words = int(audio_result.get("word_count", 0))
        lang = audio_result.get("language", "")
        if words > 0:
            findings.append({
                "module": "audio_forensics",
                "signal": "transcription",
                "severity": "INFO",
                "detail": f"Transcribed {words} words, detected language: {lang}",
            })

    # ── Text findings ─────────────────────────────────────────────
    text_result = item.get("text_result", {})
    if text_result:
        llm = float(text_result.get("llm_detection_score", 0))
        if llm > 0.4:
            findings.append({
                "module": "text_analysis",
                "signal": "llm_generated_text",
                "severity": "HIGH" if llm > 0.65 else "MEDIUM",
                "detail": f"Title/description statistical patterns suggest AI-generated text (score: {llm:.2f})",
            })

        bot = float(text_result.get("bot_comment_score", 0))
        if bot > 0.3:
            findings.append({
                "module": "text_analysis",
                "signal": "bot_engagement",
                "severity": "MEDIUM",
                "detail": f"Engagement pattern anomalies suggesting bot activity (score: {bot:.2f})",
            })

    return findings


def build_recommendations(verdict: str) -> list:
    """Return actionable recommendations based on verdict."""
    if verdict == "HIGH_RISK":
        return [
            "Do not share this content",
            "Report to the platform as AI-generated or manipulated media",
            "Verify with original source before drawing conclusions",
            "Check if the person depicted has publicly addressed this content",
        ]
    elif verdict == "SUSPICIOUS":
        return [
            "Exercise caution before sharing",
            "Seek independent verification from trusted news sources",
            "Look for official statements from people depicted in the content",
        ]
    elif verdict == "UNCERTAIN":
        return [
            "Analysis is inconclusive — manual review recommended",
            "Cross-check with other sources before sharing",
        ]
    else:  # AUTHENTIC
        return [
            "Content appears authentic based on forensic analysis",
            "Always verify context and source before sharing",
        ]
