import re
from typing import Dict, Any, List, Tuple
from .base import BaseModule
from .dictionary_manager import DictionaryManager


class MultiOfferSplitter(BaseModule):
    """
    Module F: Multi-Offer Splitter
    - Detects if a message contains multiple property listings
    - Splits into child records with parent reference
    - Marks ambiguous cases for review
    """
    
    def __init__(self, dict_mgr: DictionaryManager = None):
        super().__init__()
        self.dict_mgr = dict_mgr or DictionaryManager()
    
    def process(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Input: {raw_messages: List[RawMessage]}
        Output: adds multi_offer_splits info for later processing
        """
        raw_messages = payload.get('raw_messages', [])
        
        multi_offer_map = {}
        for msg in raw_messages:
            is_multi, splits = self._detect_multi_offer(msg.normalized_text)
            if is_multi and splits:
                multi_offer_map[msg.raw_message_id] = splits
        
        payload['multi_offer_map'] = multi_offer_map
        return payload
    
    def _detect_multi_offer(self, text: str) -> Tuple[bool, List[str]]:
        """
        Detect and split multi-offer messages.
        Returns (is_multi_offer, list_of_offer_texts)
        """
        # Split on common delimiters
        lines = text.split('\n')
        
        # Filter out empty lines
        non_empty_lines = [line.strip() for line in lines if line.strip()]
        
        # If only one line, not multi-offer
        if len(non_empty_lines) <= 1:
            return False, []
        
        # Check for numbered or bulleted lists
        offer_lines = []
        current_offer = []
        
        for line in non_empty_lines:
            # Check if line starts a new offer
            if self._is_offer_start(line):
                if current_offer:
                    offer_lines.append(' '.join(current_offer))
                current_offer = [line]
            else:
                if current_offer:
                    current_offer.append(line)
        
        if current_offer:
            offer_lines.append(' '.join(current_offer))
        
        # Count distinct property indicators
        if len(offer_lines) > 1:
            # Check if each line has property signals
            property_lines = []
            for line in offer_lines:
                if self._has_property_signals(line):
                    property_lines.append(line)
            
            if len(property_lines) > 1:
                return True, property_lines
        
        # Alternative: check for multiple sizes or phases
        size_count = len(re.findall(r'\b\d+\s*(?:marla|kanal|k|m)\b', text, re.IGNORECASE))
        phase_count = len(re.findall(r'(?:phase|p)\s*\d+|prism', text, re.IGNORECASE))
        
        if (size_count > 1 or phase_count > 1) and len(non_empty_lines) > 1:
            return True, non_empty_lines
        
        return False, []
    
    def _is_offer_start(self, line: str) -> bool:
        """Check if a line starts a new offer (numbered, bulleted, etc.)."""
        # Numbered list
        if re.match(r'^\d+[\.\)]\s', line):
            return True
        
        # Bulleted list
        if re.match(r'^[-•]\s', line):
            return True
        
        # Has property size at start
        if re.match(r'^\d+\s*(?:marla|kanal|k)', line, re.IGNORECASE):
            return True
        
        return False
    
    def _has_property_signals(self, text: str) -> bool:
        """Check if text has property offer signals."""
        # Must have at least size or price
        has_size = bool(re.search(r'\b\d+\s*(?:marla|kanal|k)\b', text, re.IGNORECASE))
        has_price = bool(re.search(r'\d+\s*(?:cr|lac)', text, re.IGNORECASE))
        
        return has_size or has_price
