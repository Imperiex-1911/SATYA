"""Text score aggregation — implements design.md §5.3.2 formula."""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Weights from design.md §5.3.2
_WEIGHTS = {
    "llm_detection": 0.40,    # perplexity / LLM detection
    "burstiness": 0.25,       # sentence uniformity
    "bot_comment": 0.20,      # engagement manipulation
    "coordinated": 0.15,      # coordinated campaign signals
}


def compute_text_score(
    llm_result: Dict[str, Any],
    bot_result: Dict[str, Any],
) -> Dict[str, Any]:
    """Compute text authenticity score (0–100).

    Higher = more authentic content. Inputs are probability scores (0–1)
    where 1 indicates manipulation/deception.
    """
    llm_score = llm_result.get("llm_detection_score", 0.15)
    burstiness_score = llm_result.get("burstiness_score", 0.15)
    bot_score = bot_result.get("bot_comment_score", 0.1)
    coordinated_score = bot_result.get("coordinated_score", 0.0)

    fake_probability = (
        _WEIGHTS["llm_detection"] * llm_score
        + _WEIGHTS["burstiness"] * burstiness_score
        + _WEIGHTS["bot_comment"] * bot_score
        + _WEIGHTS["coordinated"] * coordinated_score
    )

    text_score = round(max(0.0, min(100.0, 100.0 - fake_probability * 100)), 1)

    logger.info(
        f"Text score: llm={llm_score:.2f}, burst={burstiness_score:.2f}, "
        f"bot={bot_score:.2f}, coord={coordinated_score:.2f} "
        f"→ fake_prob={fake_probability:.3f}, score={text_score}"
    )

    return {
        "text_score": text_score,
        "fake_probability": round(fake_probability, 3),
        "llm_detection_score": llm_score,
        "burstiness_score": burstiness_score,
        "bot_comment_score": bot_score,
        "coordinated_score": coordinated_score,
        "word_count": llm_result.get("word_count", 0),
        "tag_count": bot_result.get("tag_count", 0),
        "engagement_anomaly": bot_result.get("engagement_anomaly", 0.0),
    }
