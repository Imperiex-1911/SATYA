"""Bedrock explainability — uses the Bedrock Converse API (model-agnostic)
to generate human-readable analysis summaries.
Default model: Amazon Nova Micro (no Marketplace subscription required).
Supports multilingual output for Indian languages.
"""

import json
import logging
from typing import Dict, Any, Optional

from api.config import get_settings, get_boto3_session

logger = logging.getLogger(__name__)

# Languages where we generate native-language summaries
_INDIC_LANG_NAMES = {
    "hi": "Hindi",
    "ta": "Tamil",
    "te": "Telugu",
    "bn": "Bengali",
    "mr": "Marathi",
    "kn": "Kannada",
    "ml": "Malayalam",
    "gu": "Gujarati",
    "pa": "Punjabi",
    "or": "Odia",
    "ur": "Urdu",
}


def _build_prompt(
    satya_score: float,
    verdict: str,
    confidence: str,
    video_score: Optional[float],
    audio_score: Optional[float],
    text_score: Optional[float],
    findings: list,
    title: str,
    language: str,
) -> str:
    """Build the Claude prompt for explanation generation."""

    lang_name = _INDIC_LANG_NAMES.get(language[:2].lower() if language else "en", None)
    lang_instruction = (
        f"Write the 'summary' field in {lang_name} (the regional Indian language). "
        f"Write all other fields in English."
        if lang_name
        else "Write all fields in English."
    )

    scores_text = f"- Video forensics score: {video_score if video_score is not None else 'N/A'}/100\n"
    scores_text += f"- Audio forensics score: {audio_score if audio_score is not None else 'N/A'}/100\n"
    scores_text += f"- Text/metadata score: {text_score if text_score is not None else 'N/A'}/100\n"
    scores_text += f"- Final SATYA score: {satya_score}/100\n"
    scores_text += f"- Verdict: {verdict} | Confidence: {confidence}\n"

    findings_text = ""
    for f in findings:
        if f.get("severity") in ("HIGH", "MEDIUM"):
            findings_text += f"  * [{f['severity']}] {f['signal']}: {f['detail']}\n"

    if not findings_text:
        findings_text = "  * No significant anomalies detected\n"

    prompt = f"""You are SATYA, an AI content authenticity system. Analyze the following forensic results for a video titled: "{title}"

FORENSIC SCORES:
{scores_text}
KEY FINDINGS:
{findings_text}

{lang_instruction}

Respond ONLY with a valid JSON object in this exact format:
{{
  "summary": "2-3 sentence plain-language explanation of the verdict for a non-technical user",
  "key_concern": "The single most important finding in one sentence (English only)",
  "confidence_reason": "Why the confidence level is {confidence} (English only)"
}}

Do not include any text outside the JSON object."""

    return prompt


def generate_explanation(
    satya_score: float,
    verdict: str,
    confidence: str,
    video_score: Optional[float],
    audio_score: Optional[float],
    text_score: Optional[float],
    findings: list,
    title: str,
    language: str,
) -> Dict[str, Any]:
    """Call Claude 3 Haiku via Bedrock to generate explanation.

    Returns dict with: summary, key_concern, confidence_reason
    Falls back to rule-based summary if Bedrock call fails.
    """
    settings = get_settings()
    session = get_boto3_session()

    prompt = _build_prompt(
        satya_score, verdict, confidence,
        video_score, audio_score, text_score,
        findings, title, language,
    )

    try:
        # Bedrock Converse API — model-agnostic, works with Nova, Claude, Titan, etc.
        bedrock = session.client("bedrock-runtime", region_name="us-east-1")
        response = bedrock.converse(
            modelId=settings.bedrock_model_id,
            messages=[
                {"role": "user", "content": [{"text": prompt}]},
            ],
            inferenceConfig={
                "maxTokens": 512,
                "temperature": 0.3,
            },
        )

        raw_text = response["output"]["message"]["content"][0]["text"].strip()

        # Extract JSON — handle case where model wraps in markdown
        if "```" in raw_text:
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]

        result = json.loads(raw_text)
        logger.info(f"Bedrock explanation generated for verdict={verdict}, score={satya_score}")
        return result

    except Exception as e:
        logger.warning(f"Bedrock explanation failed (using fallback): {e}")
        return _fallback_explanation(satya_score, verdict, confidence)


def _fallback_explanation(satya_score: float, verdict: str, confidence: str) -> Dict[str, Any]:
    """Rule-based fallback when Bedrock is unavailable."""
    summaries = {
        "HIGH_RISK": (
            f"This content scored {satya_score}/100 and is likely AI-generated or manipulated. "
            "Forensic analysis detected significant anomalies. Do not share without verification."
        ),
        "SUSPICIOUS": (
            f"This content scored {satya_score}/100 and shows suspicious patterns. "
            "Some signals suggest possible manipulation. Exercise caution."
        ),
        "UNCERTAIN": (
            f"This content scored {satya_score}/100. Analysis is inconclusive. "
            "Forensic signals are mixed — manual review is recommended."
        ),
        "AUTHENTIC": (
            f"This content scored {satya_score}/100 and appears authentic. "
            "No significant manipulation was detected across forensic checks."
        ),
    }
    return {
        "summary": summaries.get(verdict, f"SATYA score: {satya_score}/100. Verdict: {verdict}."),
        "key_concern": "See detailed findings for signal breakdown.",
        "confidence_reason": f"Confidence is {confidence} based on available modality data.",
    }
