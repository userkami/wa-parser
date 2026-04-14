from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime
import uuid


@dataclass
class ParsedRecord:
    """Represents a structured property record extracted from messages."""
    
    record_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    raw_message_id: str = ""
    parent_raw_message_id: str = ""
    offer_index: int = 1
    import_id: str = ""
    message_datetime: Optional[datetime] = None
    sender_name: str = ""
    sender_phone: Optional[str] = None
    
    # Property fields
    phase: str = "unknown"  # phase_6, phase_7, phase_8, phase_9_prism, phase_10, other, unknown
    sub_phase: str = ""
    project_name: str = ""
    sector_or_block: str = ""
    plot_size_value: Optional[float] = None
    plot_size_unit: str = ""  # marla, kanal
    standardized_plot_size: str = "unknown"  # 5 marla, 10 marla, 1 kanal, 2 kanal, other, unknown
    property_category: str = "unknown"  # plot, file, house, commercial, apartment, shop, requirement, market_update, unknown
    property_subcategory: str = ""
    plot_number: str = ""
    road_width_if_found: Optional[str] = None
    facing_if_found: Optional[str] = None
    
    # Flags
    corner_flag: bool = False
    boulevard_flag: bool = False
    possession_flag: bool = False
    utility_paid_flag: bool = False
    urgency_flag: bool = False
    direct_client_flag: bool = False
    dealer_flag: bool = False
    
    # Price fields
    demand_amount_pkr: Optional[int] = None
    demand_amount_lakh: Optional[float] = None
    demand_amount_display: str = ""
    demand_amount_text: str = ""
    price_per_marla_pkr: Optional[int] = None
    
    # QA fields
    extraction_confidence: float = 0.0
    needs_review: bool = False
    review_reason: str = ""
    reviewed_by: Optional[str] = None
    reviewed_status: str = "pending"  # pending, approved, corrected, rejected
    keywords_detected: List[str] = field(default_factory=list)
    parser_version: str = "1.0.0"
    rule_version: str = "1.0.0"
    
    # Duplicate detection
    duplicate_group_id: str = ""
    duplicate_type: str = "none"  # none, exact, near_same_sender, possible_same_inventory
    is_latest_in_duplicate_group: bool = True
    duplicate_confidence: float = 0.0
    
    # Original content
    original_message: str = ""
    
    def to_dict(self) -> dict:
        """Convert to dictionary for DataFrame export."""
        return {
            "record_id": self.record_id,
            "raw_message_id": self.raw_message_id,
            "parent_raw_message_id": self.parent_raw_message_id,
            "offer_index": self.offer_index,
            "import_id": self.import_id,
            "message_datetime": self.message_datetime.isoformat() if self.message_datetime else None,
            "sender_name": self.sender_name,
            "sender_phone": self.sender_phone,
            "phase": self.phase,
            "sub_phase": self.sub_phase,
            "project_name": self.project_name,
            "sector_or_block": self.sector_or_block,
            "plot_size_value": self.plot_size_value,
            "plot_size_unit": self.plot_size_unit,
            "standardized_plot_size": self.standardized_plot_size,
            "property_category": self.property_category,
            "property_subcategory": self.property_subcategory,
            "plot_number": self.plot_number,
            "road_width_if_found": self.road_width_if_found,
            "facing_if_found": self.facing_if_found,
            "corner_flag": self.corner_flag,
            "boulevard_flag": self.boulevard_flag,
            "possession_flag": self.possession_flag,
            "utility_paid_flag": self.utility_paid_flag,
            "urgency_flag": self.urgency_flag,
            "direct_client_flag": self.direct_client_flag,
            "dealer_flag": self.dealer_flag,
            "demand_amount_pkr": self.demand_amount_pkr,
            "demand_amount_lakh": self.demand_amount_lakh,
            "demand_amount_display": self.demand_amount_display,
            "demand_amount_text": self.demand_amount_text,
            "price_per_marla_pkr": self.price_per_marla_pkr,
            "extraction_confidence": self.extraction_confidence,
            "needs_review": self.needs_review,
            "review_reason": self.review_reason,
            "reviewed_by": self.reviewed_by,
            "reviewed_status": self.reviewed_status,
            "keywords_detected": str(self.keywords_detected),
            "parser_version": self.parser_version,
            "rule_version": self.rule_version,
            "duplicate_group_id": self.duplicate_group_id,
            "duplicate_type": self.duplicate_type,
            "is_latest_in_duplicate_group": self.is_latest_in_duplicate_group,
            "duplicate_confidence": self.duplicate_confidence,
            "original_message": self.original_message,
        }
