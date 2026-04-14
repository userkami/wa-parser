import unicodedata
import re
from typing import Dict, Any, List
from .base import BaseModule
from .dictionary_manager import DictionaryManager


class Normalizer(BaseModule):
    """
    Module C: Normalization Layer
    - Lowercases text
    - Normalizes unicode
    - Removes extra whitespace
    - Normalizes punctuation
    - Maps Urdu phonetics
    """
    
    def __init__(self, dict_mgr: DictionaryManager = None):
        super().__init__()
        self.dict_mgr = dict_mgr or DictionaryManager()
    
    def process(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Input: {raw_messages: List[RawMessage]}
        Output: enriched with normalized_text on each message
        """
        raw_messages = payload.get('raw_messages', [])
        
        for msg in raw_messages:
            msg.normalized_text = self._normalize(msg.message_text_raw)
        
        payload['raw_messages'] = raw_messages
        return payload
    
    def _normalize(self, text: str) -> str:
        """Normalize text for extraction."""
        if not text:
            return ""
        
        # Unicode normalization (NFC)
        text = unicodedata.normalize('NFC', text)
        
        # Lowercase
        text = text.lower()
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Normalize common URL/punctuation variants
        text = text.replace('–', '-').replace('—', '-')
        text = text.replace(''', "'").replace(''', "'")
        text = text.replace('"', '"').replace('"', '"')
        
        # Urdu phonetic mapping
        text = self._map_urdu_phonetics(text)
        
        return text
    
    def _map_urdu_phonetics(self, text: str) -> str:
        """Map Urdu phonetic words to English equivalents."""
        # Common Urdu words in property messages
        urdu_mappings = {
            r'\bfarosh\b': 'for sale',
            r'\bfarokht\b': 'for sale',
            r'\bdastiyab\b': 'available',
            r'\bdastiyabb\b': 'available',
            r'\bdarkaar\b': 'required',
            r'\bdarkaran\b': 'required',
            r'\bchahiye\b': 'required',
            r'\bzarurat\b': 'required',
            r'\bqeemat\b': 'price',
            r'\bqimat\b': 'price',
            r'\braqba\b': 'area',
            r'\braqbah\b': 'area',
        }
        
        for urdu_word, english_word in urdu_mappings.items():
            text = re.sub(urdu_word, english_word, text)
        
        return text
