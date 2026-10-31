import re
import logging
from typing import Optional

logger = logging.getLogger("krisis.nlp")

# Urgent tokens for emergency escalation
CRITICAL_KEYWORDS = ["trapped", "fire", "emergency", "blocked", "help", "collapse"]

_classifier = None


def get_nlp_pipeline():
    """Lazy loader for lightweight zero-shot classification or sentiment pipeline."""
    global _classifier
    if _classifier is None:
        try:
            from transformers import pipeline
            # Use lightweight distilbert for zero-shot or sentiment/urgency
            _classifier = pipeline(
                "zero-shot-classification",
                model="typeform/distilbert-base-uncased-mnli",
                device=-1  # Force CPU for local dev to avoid OOM
            )
            logger.info("DistilBERT zero-shot classifier initialized successfully on CPU.")
        except Exception as e:
            logger.warning(f"Could not load HuggingFace pipeline: {e}. Using rule-based fallback.")
            _classifier = False
    return _classifier


def assess_urgency(text: str) -> tuple[float, bool]:
    """
    Assess urgency using a lightweight Hugging Face pipeline or regex token scoring.
    
    Returns:
        (nlp_urgency, contains_critical_keywords)
        nlp_urgency: float between 0.0 and 1.0
        contains_critical_keywords: bool indicating presence of critical distress terms
    """
    if not text:
        return 0.20, False

    text_lower = text.lower()
    critical_matches = [kw for kw in CRITICAL_KEYWORDS if re.search(rf"\b{kw}\b", text_lower)]
    contains_critical = len(critical_matches) > 0

    classifier = get_nlp_pipeline()
    if classifier:
        try:
            candidate_labels = ["life-threatening emergency", "urgent infrastructure blockage", "minor incident", "routine inquiry"]
            res = classifier(text, candidate_labels=candidate_labels)
            labels = res.get("labels", [])
            scores = res.get("scores", [])
            label_score_map = dict(zip(labels, scores))
            
            emergency_score = label_score_map.get("life-threatening emergency", 0.0)
            urgent_score = label_score_map.get("urgent infrastructure blockage", 0.0)
            
            combined_score = (emergency_score * 0.7) + (urgent_score * 0.3)
            if contains_critical:
                combined_score = max(combined_score, 0.75 + (0.05 * len(critical_matches)))
            return round(min(1.0, max(0.1, combined_score)), 2), contains_critical
        except Exception as e:
            logger.warning(f"Transformer pipeline inference failed: {e}. Using keyword heuristic.")

    # Rule-based fallback calculation
    base_urgency = 0.30
    if contains_critical:
        base_urgency += 0.25 * len(critical_matches)
    if "!" in text or text.isupper():
        base_urgency += 0.15

    # Secondary context keywords
    secondary_tokens = ["urgent", "water", "flood", "injured", "danger", "hazard", "rescue", "drowning", "ambulance"]
    sec_matches = sum(1 for st in secondary_tokens if st in text_lower)
    base_urgency += sec_matches * 0.08

    final_score = min(1.0, max(0.1, base_urgency))
    return round(final_score, 2), contains_critical

