import re
from typing import Dict, Any, Optional, Tuple
from .base import BaseModule


class PKRNormalizer(BaseModule):
    """
    Module 8: PKR Price Normalization
    - Converts all price variants to canonical integer PKR value
    - 1 Crore = 10,000,000 PKR
    - 1 Lakh = 100,000 PKR
    """
    
    def process(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Input: {parsed_records: List[ParsedRecord]}
        Output: enriched with PKR price fields on each record
        """
        parsed_records = payload.get('parsed_records', [])
        
        for record in parsed_records:
            if record.demand_amount_text:
                pkr_amount = self._normalize_price(record.demand_amount_text)
                if pkr_amount is not None:
                    record.demand_amount_pkr = pkr_amount
                    record.demand_amount_lakh = pkr_amount / 100_000
                    record.demand_amount_display = self._format_display(pkr_amount)
                    
                    # Calculate price per marla if size known
                    if record.plot_size_value and record.plot_size_unit == 'marla':
                        record.price_per_marla_pkr = int(pkr_amount / record.plot_size_value)
        
        payload['parsed_records'] = parsed_records
        return payload
    
    def _normalize_price(self, price_text: str) -> Optional[int]:
        """
        Parse price text and return PKR integer.
        Handles: "2.95 cr", "2 crore 95 lac", "295 lakh" etc.
        """
        price_text = price_text.lower().strip()
        
        # Initialize crore and lakh amounts
        crore_amount = 0.0
        lakh_amount = 0.0
        
        # Extract crore value
        crore_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:cr|crore)', price_text)
        if crore_match:
            crore_amount = float(crore_match.group(1))
        
        # Extract lakh value
        lakh_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:lac|lakh)', price_text)
        if lakh_match:
            lakh_amount = float(lakh_match.group(1))
        
        # If we found at least something, calculate PKR
        if crore_amount > 0 or lakh_amount > 0:
            pkr = (crore_amount * 10_000_000) + (lakh_amount * 100_000)
            return int(pkr)
        
        # Try alternative: just find a number followed by crore/lakh
        # Handle cases like "295 lakh" or "2.95 crore"
        alt_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:crore|cr|lakh|lac)', price_text)
        if alt_match:
            amount = float(alt_match.group(1))
            if 'cr' in price_text[alt_match.start():alt_match.end()]:
                return int(amount * 10_000_000)
            else:
                return int(amount * 100_000)
        
        return None
    
    def _format_display(self, pkr: int) -> str:
        """
        Format PKR amount as human-readable display.
        E.g., 29,500,000 -> "2.95 Crore"
        """
        crore = pkr / 10_000_000
        
        if crore >= 1:
            if crore == int(crore):
                return f"{int(crore)} Crore"
            else:
                # Round to 2 decimal places
                return f"{crore:.2f} Crore"
        
        lakh = pkr / 100_000
        if lakh >= 1:
            if lakh == int(lakh):
                return f"{int(lakh)} Lakh"
            else:
                return f"{lakh:.2f} Lakh"
        
        return f"{pkr:,} PKR"
