import hashlib
from typing import Dict, Any, List, Set
from collections import defaultdict
import uuid
from .base import BaseModule


class Deduper(BaseModule):
    """
    Module G: Duplicate and Similarity Detection
    - Exact duplicate detection (same sender + text + time)
    - Near duplicate detection (same seller, same inventory, different time)
    - Similar inventory detection (different sellers, same property)
    """
    
    def __init__(self, existing_fingerprints: Set[str] = None):
        super().__init__()
        self.existing_fingerprints = existing_fingerprints or set()
    
    def process(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Input: {parsed_records: List[ParsedRecord]}
        Output: enriched with duplicate detection fields
        """
        parsed_records = payload.get('parsed_records', [])
        
        # Find duplicates within this import
        self._mark_duplicates(parsed_records)
        
        payload['parsed_records'] = parsed_records
        return payload
    
    def _mark_duplicates(self, records):
        """Mark duplicates in the record list."""
        
        # Group by duplicate group
        dup_groups = defaultdict(list)
        
        for record in records:
            # Level 1: Exact duplicates
            # Same sender + same normalized text + same time window
            level1_key = self._create_level1_key(record)
            dup_groups[f"level1_{level1_key}"].append(record)
            
            # Level 2: Near duplicates (same sender)
            if record.phase != "unknown" and record.standardized_plot_size != "unknown":
                level2_key = self._create_level2_key(record)
                dup_groups[f"level2_{level2_key}"].append(record)
            
            # Level 3: Possible same inventory (different sellers)
            if record.plot_number:
                level3_key = self._create_level3_key(record)
                dup_groups[f"level3_{level3_key}"].append(record)
        
        # Process each group
        for group_key, group_records in dup_groups.items():
            if len(group_records) > 1:
                group_id = str(uuid.uuid4())
                
                # Determine duplicate type and confidence
                level = group_key.split('_')[0]
                
                for i, record in enumerate(group_records):
                    if i < len(group_records) - 1 or record in group_records:
                        record.duplicate_group_id = group_id
                        
                        if level == "level1":
                            record.duplicate_type = "exact"
                            record.duplicate_confidence = 0.99
                        elif level == "level2":
                            record.duplicate_type = "near_same_sender"
                            record.duplicate_confidence = 0.75
                        else:
                            record.duplicate_type = "possible_same_inventory"
                            record.duplicate_confidence = 0.6
                
                # Mark latest as the one to show
                latest = max(group_records, key=lambda r: r.message_datetime or "")
                for record in group_records:
                    record.is_latest_in_duplicate_group = (record == latest)
    
    def _create_level1_key(self, record) -> str:
        """Create key for exact duplicate detection."""
        # Same sender, same normalized text, same day
        sender = record.sender_name.lower().strip()
        date = record.message_datetime.date().isoformat() if record.message_datetime else "unknown"
        text_hash = hashlib.md5(record.original_message.lower().encode()).hexdigest()[:8]
        return f"{sender}|{date}|{text_hash}"
    
    def _create_level2_key(self, record) -> str:
        """Create key for near duplicate detection (same seller)."""
        sender = record.sender_name.lower().strip()
        phase = record.phase
        size = record.standardized_plot_size
        block = record.sector_or_block.lower().strip() if record.sector_or_block else "unknown"
        price_bucket = self._price_bucket(record.demand_amount_pkr)
        
        return f"{sender}|{phase}|{size}|{block}|{price_bucket}"
    
    def _create_level3_key(self, record) -> str:
        """Create key for same inventory different seller."""
        phase = record.phase
        size = record.standardized_plot_size
        block = record.sector_or_block.lower().strip() if record.sector_or_block else "unknown"
        plot = record.plot_number.lower().strip()
        
        return f"{phase}|{size}|{block}|{plot}"
    
    def _price_bucket(self, price: int) -> str:
        """Bucket price into ranges for comparison (±5%)."""
        if not price:
            return "unknown"
        
        # Bucket by 5% ranges
        bucket_size = max(1_000_000, int(price * 0.05))
        bucket = (price // bucket_size) * bucket_size
        
        return f"{bucket}"
