import re
from typing import Dict, Any, Tuple, List
from .base import BaseModule
from .dictionary_manager import DictionaryManager


class MessageClassifier(BaseModule):
    """
    Module D: Message Classification
    - Classifies messages into one of 6 categories
    - Uses rule-based signals
    - Assigns relevance scores
    """
    
    def __init__(self, dict_mgr: DictionaryManager = None):
        super().__init__()
        self.dict_mgr = dict_mgr or DictionaryManager()
    
    def process(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Input: {raw_messages: List[RawMessage]}
        Output: enriched with message_class and relevance_score on each
        """
        raw_messages = payload.get('raw_messages', [])
        
        for msg in raw_messages:
            msg_class, score, reason = self._classify(msg.normalized_text)
            msg.message_class = msg_class
            msg.relevance_score = score
            msg.classification_reason = reason
        
        payload['raw_messages'] = raw_messages
        return payload
    
    def _classify(self, text: str) -> Tuple[str, float, str]:
        """Classify message and return (class, score, reason)."""
        
        # Check for media placeholder or system message
        if self._is_system_message(text):
            return 'system_message', 0.0, 'media placeholder or system message'
        
        # Check for irrelevant chat
        if self._is_irrelevant(text):
            return 'irrelevant_chat', 0.0, 'greeting or irrelevant'
        
        # Check for property offer
        if self._is_property_offer(text):
            return 'property_offer', 0.9, 'matches property offer signals'
        
        # Check for buyer requirement
        if self._is_buyer_requirement(text):
            return 'buyer_requirement', 0.8, 'matches buyer requirement signals'
        
        # Check for market update
        if self._is_market_update(text):
            return 'market_update', 0.7, 'matches market update signals'
        
        return 'unclassified', 0.5, 'could not determine'
    
    def _is_system_message(self, text: str) -> bool:
        """Check if message is a system message."""
        patterns = [
            r'<[^>]*?media[^>]*?>',
            r'(image|video|sticker|audio|document|contact)\s*omitted',
            r'missed (voice )?call',
            r'(left the chat|added .+ to the group|removed .+ from the group)',
            r'changed (?:the group |group )?(?:icon|subject|description)',
        ]
        
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    def _is_irrelevant(self, text: str) -> bool:
        """Check if message is irrelevant chat."""
        ignore_keywords = self.dict_mgr.get_ignore_keywords()
        
        # If ONLY contains ignore keywords, it's irrelevant
        temp_text = text
        for keyword in ignore_keywords:
            temp_text = re.sub(r'\b' + re.escape(keyword) + r'\b', '', temp_text, flags=re.IGNORECASE)
        
        temp_text = re.sub(r'\s+', ' ', temp_text).strip()
        
        # If less than 10 characters left, likely irrelevant
        if len(temp_text) < 10:
            return True
        
        return False
    
    def _is_property_offer(self, text: str) -> bool:
        """Check if message looks like a property offer."""
        keywords = self.dict_mgr.get_property_offer_keywords()
        
        matched_keywords = 0
        for keyword in keywords:
            if re.search(r'\b' + re.escape(keyword) + r'\b', text, re.IGNORECASE):
                matched_keywords += 1
        
        # Look for size patterns (marla, kanal)
        has_size = bool(re.search(r'\b\d+\s*(?:marla|kanal|k|m)\b', text, re.IGNORECASE))
        
        # Look for price patterns (cr, lac, lakh)
        has_price = bool(re.search(r'\d+\s*(?:cr|crore|lac|lakh|lacs|lakhs)', text, re.IGNORECASE))
        
        # Look for phase patterns
        has_phase = bool(re.search(r'(?:phase|p)\s*\d+|prism|phase\s*\d+', text, re.IGNORECASE))
        
        # Multiple signals suggest property offer
        signals = sum([
            matched_keywords >= 2,  # At least 2 keywords
            has_size,
            has_price,
            has_phase,
        ])
        
        return signals >= 2
    
    def _is_buyer_requirement(self, text: str) -> bool:
        """Check if message is a buyer requirement."""
        keywords = self.dict_mgr.get_buyer_requirement_keywords()
        
        for keyword in keywords:
            if re.search(r'\b' + re.escape(keyword) + r'\b', text, re.IGNORECASE):
                # Check if it mentions a size or property type
                if re.search(r'\b(?:marla|kanal|house|plot|file|apartment)\b', text, re.IGNORECASE):
                    return True
        
        return False
    
    def _is_market_update(self, text: str) -> bool:
        """Check if message is a market update."""
        keywords = self.dict_mgr.get_market_update_keywords()
        
        for keyword in keywords:
            if re.search(r'\b' + re.escape(keyword) + r'\b', text, re.IGNORECASE):
                return True
        
        return False
