"""LLM-generated text detector — statistical analysis without heavy models.

Approach: Feature-based detection using:
- Type-token ratio (vocabulary richness — LLMs reuse tokens predictably)
- Sentence length variance (LLMs produce uniform sentence lengths)
- Burstiness score (human text has bursty complexity; LLM text is uniform)
- Lexical density (ratio of content words — LLMs are verbose)
- Repetition patterns (n-gram repetition)
"""

import re
import math
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# Thresholds (calibrated empirically)
_MIN_TTR_HUMAN = 0.55       # Type-token ratio — below = repetitive = LLM indicator
_MAX_SENT_LEN_CV = 0.30     # Sentence length CV — below = too uniform = LLM indicator
_MIN_BURSTINESS = 0.40      # Burstiness — below = flat complexity = LLM indicator


def _tokenize(text: str) -> List[str]:
    """Simple whitespace + punctuation tokenizer."""
    tokens = re.findall(r'\b[a-zA-Z\u0900-\u097F\u0B80-\u0BFF\u0C00-\u0C7F]+\b', text.lower())
    return tokens


def _split_sentences(text: str) -> List[str]:
    """Split text into sentences by punctuation."""
    sentences = re.split(r'[.!?।\n]+', text)
    return [s.strip() for s in sentences if len(s.strip()) > 5]


def _type_token_ratio(tokens: List[str]) -> float:
    """Vocabulary richness: unique / total tokens (normalized for length)."""
    if not tokens:
        return 1.0
    # Corrected TTR using root (RTYPE) to normalize for text length
    return len(set(tokens)) / math.sqrt(len(tokens))


def _sentence_length_cv(sentences: List[str]) -> float:
    """Coefficient of variation of sentence lengths."""
    if len(sentences) < 3:
        return 1.0   # Can't determine — return high CV (natural-looking)
    lengths = [len(s.split()) for s in sentences]
    mean = sum(lengths) / len(lengths)
    if mean == 0:
        return 0.0
    variance = sum((l - mean) ** 2 for l in lengths) / len(lengths)
    return (variance ** 0.5) / mean


def _burstiness(sentences: List[str]) -> float:
    """Burstiness of sentence complexity.

    Human text alternates between simple and complex sentences.
    LLM text has uniform complexity throughout.
    B = (std - mean) / (std + mean) where values are per-sentence word counts.
    Range: -1 (anti-bursty) to 1 (bursty). Human ≈ 0.3–0.8.
    """
    if len(sentences) < 4:
        return 0.5   # Not enough data — neutral

    lengths = [len(s.split()) for s in sentences]
    mean = sum(lengths) / len(lengths)
    std = (sum((l - mean) ** 2 for l in lengths) / len(lengths)) ** 0.5

    if mean + std == 0:
        return 0.0
    return (std - mean) / (std + mean)


def _ngram_repetition(tokens: List[str], n: int = 3) -> float:
    """Fraction of n-grams that are repeated — LLMs repeat phrases."""
    if len(tokens) < n + 2:
        return 0.0
    ngrams = [tuple(tokens[i:i+n]) for i in range(len(tokens) - n + 1)]
    if not ngrams:
        return 0.0
    repeated = len(ngrams) - len(set(ngrams))
    return repeated / len(ngrams)


def detect_llm_text(title: str, description: str) -> Dict[str, Any]:
    """Analyze title + description for LLM-generated content.

    Returns:
        llm_detection_score (0.0–1.0): 1.0 = likely LLM-generated
        burstiness_score (0.0–1.0): 1.0 = suspiciously uniform (LLM)
    """
    text = f"{title} {description}".strip()

    if len(text) < 30:
        logger.debug("Text too short for LLM detection")
        return {"llm_detection_score": 0.15, "burstiness_score": 0.15, "word_count": 0}

    tokens = _tokenize(text)
    sentences = _split_sentences(text)
    word_count = len(tokens)

    if word_count < 10:
        return {"llm_detection_score": 0.15, "burstiness_score": 0.15, "word_count": word_count}

    # Feature extraction
    ttr = _type_token_ratio(tokens)
    sent_cv = _sentence_length_cv(sentences)
    burstiness = _burstiness(sentences)
    repetition = _ngram_repetition(tokens)

    # Convert to anomaly scores (0=natural, 1=LLM-like)
    # Low TTR = repetitive vocabulary = LLM-like
    ttr_score = max(0.0, 1.0 - (ttr / (_MIN_TTR_HUMAN * 1.5)))

    # Low sent_cv = uniform sentence length = LLM-like
    cv_score = max(0.0, 1.0 - (sent_cv / (_MAX_SENT_LEN_CV * 3)))

    # Low burstiness = flat complexity = LLM-like (-1 = most LLM-like)
    burstiness_score = max(0.0, (_MIN_BURSTINESS - burstiness) / (_MIN_BURSTINESS + 1.0))

    # High n-gram repetition = copy-paste pattern
    repetition_score = min(1.0, repetition * 5.0)

    # Weighted LLM detection score
    llm_score = (
        0.35 * ttr_score
        + 0.25 * cv_score
        + 0.25 * burstiness_score
        + 0.15 * repetition_score
    )

    logger.info(
        f"LLM detection: ttr={ttr:.2f}({ttr_score:.2f}), "
        f"cv={sent_cv:.2f}({cv_score:.2f}), "
        f"burst={burstiness:.2f}({burstiness_score:.2f}), "
        f"rep={repetition:.2f}({repetition_score:.2f}) "
        f"→ llm={llm_score:.3f}"
    )

    return {
        "llm_detection_score": round(llm_score, 3),
        "burstiness_score": round(burstiness_score, 3),
        "type_token_ratio": round(ttr, 3),
        "sentence_length_cv": round(sent_cv, 3),
        "ngram_repetition": round(repetition, 3),
        "word_count": word_count,
    }
