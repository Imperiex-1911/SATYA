"""Bot comment detection — analyze engagement signals for inauthentic patterns.

Signals analyzed:
1. Comment count vs. like ratio (bot farms inflate comments)
2. View count vs. like ratio (inorganic engagement ratios)
3. Tag stuffing (keyword spam common in disinformation)
4. Title–description similarity (duplicated content = programmatic)
"""

import re
import math
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# YouTube organic engagement benchmarks (median values)
_ORGANIC_LIKE_TO_VIEW_RATIO = 0.04       # 4% of views like
_ORGANIC_COMMENT_TO_VIEW_RATIO = 0.005  # 0.5% of views comment
_MAX_TAG_COUNT_ORGANIC = 25              # More than 25 tags = stuffing


def _jaccard_similarity(text1: str, text2: str) -> float:
    """Word-level Jaccard similarity between two text strings."""
    if not text1 or not text2:
        return 0.0
    set1 = set(text1.lower().split())
    set2 = set(text2.lower().split())
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    return intersection / union if union > 0 else 0.0


def _engagement_anomaly_score(
    view_count: int,
    like_count: int,
    comment_count: int,
) -> float:
    """Detect abnormal engagement ratios.

    Very high comment:view ratio with low like:view ratio indicates bot comments.
    Near-zero engagement on an old video with high view count can also indicate
    purchased views.
    """
    if view_count <= 0:
        return 0.2   # Can't determine

    like_ratio = like_count / view_count
    comment_ratio = comment_count / view_count

    score = 0.0

    # Bot pattern 1: excessively high comment-to-view ratio
    if comment_ratio > _ORGANIC_COMMENT_TO_VIEW_RATIO * 5:
        score += 0.4

    # Bot pattern 2: very low like ratio despite high views
    if view_count > 10000 and like_ratio < 0.001:
        score += 0.3

    # Bot pattern 3: comment:like ratio > 0.5 (more commenters than likers is unusual)
    if like_count > 0 and comment_count / like_count > 0.5:
        score += 0.2

    return min(1.0, score)


def _tag_stuffing_score(tags: List[str]) -> float:
    """Score based on number of tags (keyword stuffing = disinformation signal)."""
    tag_count = len(tags)
    if tag_count <= _MAX_TAG_COUNT_ORGANIC:
        return 0.0
    # Each extra tag beyond threshold adds to score
    return min(1.0, (tag_count - _MAX_TAG_COUNT_ORGANIC) / 20.0)


def _coordinated_content_score(title: str, description: str) -> float:
    """Detect programmatic/templated content by measuring title-description overlap.

    Organic content: title and description convey different information.
    Bot content: title is copy-pasted into description = high overlap.
    """
    if not title or not description:
        return 0.0
    similarity = _jaccard_similarity(title, description)
    # Very high overlap in a longer description is suspicious
    if len(description.split()) > 20 and similarity > 0.5:
        return min(1.0, (similarity - 0.5) * 2.0)
    return 0.0


def detect_bot_signals(
    title: str,
    description: str,
    tags: List[str],
    view_count: int,
    like_count: int,
    comment_count: int,
) -> Dict[str, Any]:
    """Analyze metadata for bot/coordinated inauthentic behavior.

    Returns:
        bot_comment_score (0.0–1.0): probability of bot manipulation
        coordinated_score (0.0–1.0): probability of coordinated campaign
    """
    engagement_score = _engagement_anomaly_score(view_count, like_count, comment_count)
    tag_score = _tag_stuffing_score(tags)
    coord_score = _coordinated_content_score(title, description)

    # Bot comment score: engagement anomalies + tag stuffing
    bot_score = 0.65 * engagement_score + 0.35 * tag_score

    logger.info(
        f"Bot signals: engagement={engagement_score:.2f}, "
        f"tags={tag_score:.2f}(count={len(tags)}), "
        f"coordinated={coord_score:.2f} "
        f"→ bot={bot_score:.3f}"
    )

    return {
        "bot_comment_score": round(bot_score, 3),
        "coordinated_score": round(coord_score, 3),
        "engagement_anomaly": round(engagement_score, 3),
        "tag_stuffing": round(tag_score, 3),
        "tag_count": len(tags),
        "like_to_view_ratio": round(like_count / max(view_count, 1), 4),
        "comment_to_view_ratio": round(comment_count / max(view_count, 1), 5),
    }
