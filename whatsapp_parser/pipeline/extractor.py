import re
from typing import Dict, Any, List, Optional, Tuple
from .base import BaseModule
from .dictionary_manager import DictionaryManager
from ..models import ParsedRecord


class FieldExtractor(BaseModule):
    """
    Module E: Structured Field Extraction
    - Extracts all property fields from classified messages
    - Handles multi-offer splitting
    - Marks low-confidence extractions
    """
    
    def __init__(self, dict_mgr: DictionaryManager = None):
        super().__init__()
        self.dict_mgr = dict_mgr or DictionaryManager()
    
    def process(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Input: {raw_messages: List[RawMessage], multi_offer_map: Dict}
        Output: enriched with parsed_records: List[ParsedRecord]
        """
        raw_messages = payload.get('raw_messages', [])
        multi_offer_map = payload.get('multi_offer_map', {})
        import_id = payload.get('import_id', '')
        
        parsed_records = []
        
        for msg in raw_messages:
            # Skip non-property messages
            if msg.message_class not in ['property_offer', 'buyer_requirement', 'market_update']:
                continue
            
            # Check if this message has multiple offers
            if msg.raw_message_id in multi_offer_map:
                offer_texts = multi_offer_map[msg.raw_message_id]
                for idx, offer_text in enumerate(offer_texts, 1):
                    record = self._extract_fields(
                        offer_text,
                        msg,
                        import_id,
                        offer_index=idx,
                        parent_id=msg.raw_message_id if len(offer_texts) > 1 else msg.raw_message_id
                    )
                    parsed_records.append(record)
            else:
                # Single offer
                record = self._extract_fields(
                    msg.normalized_text,
                    msg,
                    import_id,
                    offer_index=1,
                    parent_id=msg.raw_message_id
                )
                parsed_records.append(record)
        
        payload['parsed_records'] = parsed_records
        return payload
    
    def _extract_fields(
        self,
        text: str,
        raw_msg,
        import_id: str,
        offer_index: int = 1,
        parent_id: str = ""
    ) -> ParsedRecord:
        """Extract all fields from a message."""
        record = ParsedRecord(
            raw_message_id=raw_msg.raw_message_id,
            parent_raw_message_id=parent_id,
            offer_index=offer_index,
            import_id=import_id,
            message_datetime=raw_msg.message_datetime,
            sender_name=raw_msg.sender_normalized,
            original_message=raw_msg.message_text_raw,
        )
        
        # Extract phase
        record.phase = self.dict_mgr.resolve_phase(text)
        
        # Extract size
        record.standardized_plot_size = self.dict_mgr.resolve_size(text)
        size_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:marla|kanal)', text, re.IGNORECASE)
        if size_match:
            record.plot_size_value = float(size_match.group(1))
            record.plot_size_unit = 'marla' if 'marla' in size_match.group(0).lower() else 'kanal'
        
        # Extract block
        record.sector_or_block = self.dict_mgr.resolve_block(text)
        
        # Extract plot number
        record.plot_number = self._extract_plot_number(text)
        
        # Extract property category
        record.property_category = self._extract_property_type(text)
        
        # Extract flags
        self._extract_flags(text, record)
        
        # Extract keywords
        record.keywords_detected = self._extract_keywords(text)
        
        # Extract price (will be normalized later)
        record.demand_amount_text = self._extract_price_text(text)
        
        return record
    
    def _extract_plot_number(self, text: str) -> str:
        """Extract plot number from text."""
        patterns = [
            r'plot\s*(?:no|no\.|number|#)?\s*(\d+)',
            r'#(\d+)',
            r'(\d+)\s*plot',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return ""
    
    def _extract_property_type(self, text: str) -> str:
        """Extract property type/category."""
        types = {
            'plot': [r'\bplot\b', r'\blot\b'],
            'file': [r'\bfile\b'],
            'house': [r'\bhouse\b', r'\bvilla\b'],
            'apartment': [r'\bapartment\b', r'\bapt\b', r'\bflat\b'],
            'shop': [r'\bshop\b'],
            'commercial': [r'\bcommercial\b'],
        }
        
        for prop_type, patterns in types.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return prop_type
        
        return "unknown"
    
    def _extract_flags(self, text: str, record: ParsedRecord):
        """Extract boolean flags from text."""
        flag_patterns = {
            'corner_flag': [r'\bcorner\b', r'\bcrner\b'],
            'boulevard_flag': [r'\boulevard\b', r'\bmain\s*boulevard\b'],
            'possession_flag': [r'\bpossession\b', r'\bpossesion\b', r'\bposs\b'],
            'utility_paid_flag': [r'\butility\s*paid\b', r'\butilities\s*paid\b'],
            'urgency_flag': [r'\burgent\b', r'\bugent\b', r'\burgen\b', r'\basap\b'],
            'direct_client_flag': [r'\bdirect\b', r'\bdirect\s*client\b', r'\bowner\b'],
            'dealer_flag': [r'\bdealer\b', r'\bagent\b', r'\bestate\b'],
        }
        
        for flag_name, patterns in flag_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    setattr(record, flag_name, True)
                    break
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract detected keywords."""
        all_keywords = (
            self.dict_mgr.get_property_offer_keywords() +
            self.dict_mgr.get_buyer_requirement_keywords() +
            self.dict_mgr.get_market_update_keywords()
        )
        
        detected = []
        for keyword in all_keywords:
            if re.search(r'\b' + re.escape(keyword) + r'\b', text, re.IGNORECASE):
                detected.append(keyword)
        
        return detected
    
    def _extract_price_text(self, text: str) -> str:
        """Extract price text from message."""
        # Look for price patterns
        patterns = [
            r'(?:asking|demand|rate|price|pkr)?\s*(\d+(?:\.\d+)?)\s*(?:cr|crore|lac|lakh|lacs|lakhs)',
            r'(\d+(?:\.\d+)?)\s*(?:million|lakh)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # Extract full context around price
                start = max(0, match.start() - 20)
                end = min(len(text), match.end() + 20)
                return text[start:end].strip()
        
        return ""
