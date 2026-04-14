from enum import Enum
from typing import List, Dict, Any
from dataclasses import dataclass, field


class ErrorLevel(Enum):
    """Error severity levels."""
    FATAL = "FATAL"  # Reject entire file
    IMPORT_PARTIAL = "IMPORT_PARTIAL"  # Partial file processed
    RECORD_FAIL = "RECORD_FAIL"  # Individual message failed
    FIELD_FAIL = "FIELD_FAIL"  # Individual field failed


@dataclass
class ModuleError(Exception):
    """Exception raised by pipeline modules."""
    level: ErrorLevel
    message: str
    raw_message_id: str = ""
    line_start: int = 0
    line_end: int = 0
    error_type: str = ""
    

@dataclass
class ErrorLog:
    """Tracks all errors during import."""
    import_id: str
    errors: List[Dict[str, Any]] = field(default_factory=list)
    
    def add_error(self, error: ModuleError):
        """Add an error to the log."""
        self.errors.append({
            "level": error.level.value,
            "message": error.message,
            "raw_message_id": error.raw_message_id,
            "line_start": error.line_start,
            "line_end": error.line_end,
            "error_type": error.error_type,
        })


class BaseModule:
    """Base class for all pipeline modules."""
    
    def __init__(self, error_log: ErrorLog = None):
        self.error_log = error_log
    
    def process(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the payload and return enriched payload.
        
        Raises:
            ModuleError: With appropriate level
        """
        raise NotImplementedError
