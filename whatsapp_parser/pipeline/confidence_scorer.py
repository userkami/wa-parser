from typing import Dict, Any
from .base import BaseModule


class ConfidenceScorer(BaseModule):
    """
    Module H: Confidence and Review Scoring
    - Scores each record 0.0-1.0
    - Flags records needing review
    - Provides review reasons
    """
    
    def process(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Input: {parsed_records: List[ParsedRecord]}
        Output: enriched with confidence scores and review flags
        """
        parsed_records = payload.get('parsed_records', [])
        
        for record in parsed_records:
            confidence, needs_review, reason = self._calculate_confidence(record)
            record.extraction_confidence = confidence
            record.needs_review = needs_review
            record.review_reason = reason
        
        payload['parsed_records'] = parsed_records
        return payload
    
    def _calculate_confidence(self, record) -> tuple:
        """
        Calculate confidence score and determine if needs review.
        Returns (confidence: float, needs_review: bool, reason: str)
        """
        score = 0.0
        penalties = []
        
        # Base score for having core fields
        has_phase = record.phase != "unknown"
        has_size = record.standardized_plot_size != "unknown"
        has_price = record.demand_amount_pkr is not None
        
        # Strong indicators - add to base
        if has_phase and has_size and has_price:
            score = 0.6
        elif has_phase and has_size:
            score = 0.5
        elif has_size and has_price:
            score = 0.5
        elif has_phase and has_price:
            score = 0.4
        elif has_phase or has_size:
            score = 0.3
        else:
            score = 0.1
        
        # Additional points for extra fields
        if record.sector_or_block:
            score += 0.1
        
        if record.plot_number:
            score += 0.05
        
        # Flags add small confidence boost
        flag_count = sum([
            record.corner_flag,
            record.boulevard_flag,
            record.possession_flag,
            record.utility_paid_flag,
            record.urgency_flag,
            record.direct_client_flag,
        ])
        if flag_count > 0:
            score += min(0.1, flag_count * 0.02)
        
        # Penalties for uncertainties
        if not has_phase:
            penalties.append("phase missing")
            score -= 0.2
        
        if not has_size:
            penalties.append("size missing")
            score -= 0.2
        
        if not has_price:
            penalties.append("price missing")
            score -= 0.1
        
        # Flag weak block extraction
        if record.sector_or_block and len(record.sector_or_block) <= 2:
            penalties.append("block weak")
            score -= 0.1
        
        # Flag if plot number is uncertain
        if record.plot_number and not record.phase:
            penalties.append("plot uncertain")
            score -= 0.05
        
        # Clamp score
        score = max(0.0, min(1.0, score))
        
        # Determine if needs review
        needs_review = False
        reason = ""
        
        if score < 0.5:
            needs_review = True
            reason = " + ".join(penalties) if penalties else "low confidence"
        elif score < 0.7 and not has_price:
            needs_review = True
            reason = "price ambiguous"
        elif score < 0.7 and not has_phase:
            needs_review = True
            reason = "phase missing"
        
        return score, needs_review, reason
