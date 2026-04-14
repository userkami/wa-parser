from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
import uuid


@dataclass
class RawMessage:
    """Represents a raw WhatsApp message extracted from the chat export."""
    
    raw_message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    import_id: str = ""
    message_date: Optional[str] = None
    message_time: Optional[str] = None
    message_datetime: Optional[datetime] = None
    sender_raw: str = ""
    sender_normalized: str = ""
    message_text_raw: str = ""
    normalized_text: str = ""
    message_class: str = "unclassified"  # property_offer, buyer_requirement, market_update, irrelevant_chat, system_message, unclassified
    relevance_score: float = 0.0
    classification_reason: str = ""
    is_multiline: bool = False
    is_forwarded: bool = False
    is_media_placeholder: bool = False
    format_detected: str = ""
    parse_status: str = "pending"  # pending, success, already_imported, empty_body, error
    line_start: int = 0
    line_end: int = 0
    message_fingerprint: str = ""
    
    def to_dict(self) -> dict:
        """Convert to dictionary for DataFrame export."""
        return {
            "raw_message_id": self.raw_message_id,
            "import_id": self.import_id,
            "message_date": self.message_date,
            "message_time": self.message_time,
            "message_datetime": self.message_datetime.isoformat() if self.message_datetime else None,
            "sender_raw": self.sender_raw,
            "sender_normalized": self.sender_normalized,
            "message_text_raw": self.message_text_raw,
            "normalized_text": self.normalized_text,
            "message_class": self.message_class,
            "relevance_score": self.relevance_score,
            "classification_reason": self.classification_reason,
            "is_multiline": self.is_multiline,
            "is_forwarded": self.is_forwarded,
            "is_media_placeholder": self.is_media_placeholder,
            "format_detected": self.format_detected,
            "parse_status": self.parse_status,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "message_fingerprint": self.message_fingerprint,
        }
