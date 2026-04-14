import re
import json
from pathlib import Path
from typing import Dict, Any, List


class DictionaryManager:
    """Loads and manages all alias and keyword dictionaries."""
    
    def __init__(self, dict_dir: str = None):
        if dict_dir is None:
            dict_dir = Path(__file__).parent.parent / "dictionaries"
        
        self.dict_dir = Path(dict_dir)
        self.phase_aliases = self._load_json("phase_aliases.json")
        self.size_aliases = self._load_json("size_aliases.json")
        self.block_aliases = self._load_json("block_aliases.json")
        self.keyword_signals = self._load_json("keyword_signals.json")
        self.ignore_keywords = self._load_json("ignore_keywords.json")
        
        # Build reverse lookup maps for faster matching
        self.phase_reverse = self._build_reverse_map(self.phase_aliases)
        self.size_reverse = self._build_reverse_map(self.size_aliases)
        self.block_reverse = self._build_reverse_map(self.block_aliases)
    
    def _load_json(self, filename: str) -> Dict:
        """Load a JSON dictionary file."""
        filepath = self.dict_dir / filename
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _build_reverse_map(self, alias_dict: Dict[str, List[str]]) -> Dict[str, str]:
        """Build reverse map from aliases to canonical values."""
        reverse = {}
        for canonical, aliases in alias_dict.items():
            for alias in aliases:
                reverse[alias.lower()] = canonical
        return reverse
    
    def resolve_phase(self, text: str) -> str:
        """Resolve phase from text. Returns canonical phase or 'unknown'."""
        text_lower = text.lower().strip()
        
        # Try exact match first
        if text_lower in self.phase_reverse:
            return self.phase_reverse[text_lower]
        
        # Try substring matching
        for alias, canonical in self.phase_reverse.items():
            if alias in text_lower:
                return canonical
        
        return "unknown"
    
    def resolve_size(self, text: str) -> str:
        """Resolve size from text. Returns standardized size or 'unknown'."""
        text_lower = text.lower().strip()
        
        if text_lower in self.size_reverse:
            return self.size_reverse[text_lower]
        
        # Try substring matching for sizes
        for alias, canonical in self.size_reverse.items():
            if re.search(r'\b' + re.escape(alias) + r'\b', text_lower):
                return canonical
        
        return "unknown"
    
    def resolve_block(self, text: str) -> str:
        """Resolve block from text. Returns canonical block or empty string."""
        text_lower = text.lower().strip()
        
        if text_lower in self.block_reverse:
            return self.block_reverse[text_lower]
        
        # Try substring matching
        for alias, canonical in self.block_reverse.items():
            if re.search(r'\b' + re.escape(alias) + r'\b', text_lower):
                return canonical
        
        return ""
    
    def get_property_offer_keywords(self) -> List[str]:
        """Get property offer keywords."""
        return self.keyword_signals.get("property_offer_keywords", [])
    
    def get_buyer_requirement_keywords(self) -> List[str]:
        """Get buyer requirement keywords."""
        return self.keyword_signals.get("buyer_requirement_keywords", [])
    
    def get_market_update_keywords(self) -> List[str]:
        """Get market update keywords."""
        return self.keyword_signals.get("market_update_keywords", [])
    
    def get_irrelevant_keywords(self) -> List[str]:
        """Get irrelevant chat keywords."""
        return self.keyword_signals.get("irrelevant_keywords", [])
    
    def get_ignore_keywords(self) -> List[str]:
        """Get ignore keywords."""
        return self.ignore_keywords.get("ignore_keywords", [])
