import re
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
import hashlib
from .base import BaseModule, ModuleError, ErrorLevel
from ..models import RawMessage


class MessageSplitter(BaseModule):
    """
    Module B: Message Segmentation (Highest Risk)
    - Detects WhatsApp format
    - Splits raw text into individual messages
    - Handles multiline messages
    - Generates message fingerprints
    """
    
    # Format patterns
    ANDROID_V1_PATTERN = r'^(\d{1,2}/\d{1,2}/\d{4}),\s*(\d{1,2}:\d{2}\s*(?:am|pm|AM|PM))\s*-\s*(.+?):\s*(.*?)$'
    ANDROID_V2_PATTERN = r'^(\d{1,2}/\d{1,2}/\d{4}),\s*(\d{1,2}:\d{2})\s*-\s*(.+?):\s*(.*?)$'
    IOS_V1_PATTERN = r'^\[(\d{1,2}/\d{1,2}/\d{4}),\s*(\d{1,2}:\d{2}:\d{2}\s*(?:AM|PM|am|pm))\]\s*(.+?):\s*(.*?)$'
    IOS_V2_PATTERN = r'^\[(\d{1,2}\.\d{1,2}\.\d{4}),\s*(\d{1,2}:\d{2}:\d{2})\]\s*(.+?):\s*(.*?)$'
    
    FORMAT_PATTERNS = {
        'android_v1': ANDROID_V1_PATTERN,
        'android_v2': ANDROID_V2_PATTERN,
        'ios_v1': IOS_V1_PATTERN,
        'ios_v2': IOS_V2_PATTERN,
    }
    
    def process(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Input: {lines: List[str], ...}
        Output: enriched with {
            format_detected: str,
            raw_messages: List[RawMessage],
            messages_count: int
        }
        """
        lines = payload.get('lines', [])
        import_id = payload.get('import_id', '')
        
        if not lines:
            raise ModuleError(
                level=ErrorLevel.FATAL,
                message="No lines to process",
                error_type="no_lines"
            )
        
        # Detect format
        format_detected = self._detect_format(lines)
        if not format_detected:
            # Continue with best effort
            format_detected = 'unknown'
        
        # Split messages
        raw_messages = self._split_messages(lines, import_id, format_detected)
        
        payload['format_detected'] = format_detected
        payload['raw_messages'] = raw_messages
        payload['messages_count'] = len(raw_messages)
        
        return payload
    
    def _detect_format(self, lines: List[str]) -> Optional[str]:
        """Detect WhatsApp message format from first 50 lines."""
        format_scores = {fmt: 0 for fmt in self.FORMAT_PATTERNS.keys()}
        
        sample_lines = lines[:min(50, len(lines))]
        
        for line in sample_lines:
            line = line.strip()
            if not line:
                continue
            
            for fmt_name, pattern in self.FORMAT_PATTERNS.items():
                if re.match(pattern, line):
                    format_scores[fmt_name] += 1
        
        # Find format with highest score
        best_format = max(format_scores.items(), key=lambda x: x[1])
        
        # Require minimum threshold of 5 matches
        if best_format[1] >= 5:
            return best_format[0]
        
        return None
    
    def _split_messages(self, lines: List[str], import_id: str, format_detected: str) -> List[RawMessage]:
        """Split raw lines into individual messages."""
        messages = []
        current_message_lines = []
        current_line_start = 0
        
        pattern = self.FORMAT_PATTERNS.get(format_detected) if format_detected != 'unknown' else None
        
        for line_num, line in enumerate(lines):
            if not line.strip():
                continue
            
            # Check if this line starts a new message
            is_new_message = False
            if pattern:
                is_new_message = bool(re.match(pattern, line))
            else:
                # For unknown format, try all patterns
                is_new_message = any(
                    re.match(p, line) 
                    for p in self.FORMAT_PATTERNS.values()
                )
            
            if is_new_message and current_message_lines:
                # Process previous message
                msg = self._create_raw_message(
                    current_message_lines,
                    current_line_start,
                    line_num - 1,
                    import_id,
                    format_detected or 'unknown',
                    pattern
                )
                if msg:
                    messages.append(msg)
                
                current_message_lines = [line]
                current_line_start = line_num
            else:
                current_message_lines.append(line)
        
        # Process last message
        if current_message_lines:
            msg = self._create_raw_message(
                current_message_lines,
                current_line_start,
                len(lines) - 1,
                import_id,
                format_detected or 'unknown',
                pattern
            )
            if msg:
                messages.append(msg)
        
        return messages
    
    def _create_raw_message(
        self,
        lines: List[str],
        line_start: int,
        line_end: int,
        import_id: str,
        format_detected: str,
        pattern: Optional[str]
    ) -> Optional[RawMessage]:
        """Create a RawMessage from message lines."""
        if not lines or not lines[0].strip():
            return None
        
        first_line = lines[0]
        msg_text = '\n'.join(lines)
        
        # Check for media placeholder
        is_media = bool(re.search(r'<[^>]*?[Mm]edia[^>]*?>', msg_text)) or \
                   bool(re.search(r'(image|video|sticker|audio|document)\s*omitted', msg_text, re.IGNORECASE))
        
        # Check for forwarded
        is_forwarded = bool(re.search(r'forwarded', msg_text, re.IGNORECASE))
        
        # Parse sender and content
        sender_raw = ""
        sender_normalized = ""
        message_text_raw = msg_text
        message_datetime = None
        message_date = None
        message_time = None
        
        if pattern:
            match = re.match(pattern, first_line)
            if match:
                date_str, time_str, sender_raw = match.groups()[:3]
                message_text_raw = match.group(4) + '\n'.join(lines[1:]) if len(lines) > 1 else match.group(4)
                
                sender_normalized = sender_raw.lower().strip()
                
                # Try to parse datetime
                try:
                    message_datetime = self._parse_datetime(date_str, time_str, format_detected)
                    message_date = message_datetime.date().isoformat()
                    message_time = message_datetime.time().isoformat()
                except:
                    pass
        
        # Generate fingerprint
        fingerprint = self._generate_fingerprint(sender_normalized, message_text_raw)
        
        raw_msg = RawMessage(
            import_id=import_id,
            message_date=message_date,
            message_time=message_time,
            message_datetime=message_datetime,
            sender_raw=sender_raw,
            sender_normalized=sender_normalized,
            message_text_raw=message_text_raw,
            is_multiline=(len(lines) > 1),
            is_forwarded=is_forwarded,
            is_media_placeholder=is_media,
            format_detected=format_detected,
            line_start=line_start,
            line_end=line_end,
            message_fingerprint=fingerprint,
            parse_status='success'
        )
        
        return raw_msg
    
    def _parse_datetime(self, date_str: str, time_str: str, format_detected: str) -> Optional[datetime]:
        """Parse datetime from extracted components."""
        try:
            if format_detected == 'ios_v2':
                # DD.MM.YYYY format
                date_part = datetime.strptime(date_str, '%d.%m.%Y').date()
            else:
                # DD/MM/YYYY format
                date_part = datetime.strptime(date_str, '%d/%m/%Y').date()
            
            # Parse time
            if 'am' in time_str.lower() or 'pm' in time_str.lower():
                time_part = datetime.strptime(time_str, '%I:%M %p').time()
            elif ':' in time_str and len(time_str.split(':')) == 3:
                time_part = datetime.strptime(time_str, '%H:%M:%S').time()
            else:
                time_part = datetime.strptime(time_str, '%H:%M').time()
            
            return datetime.combine(date_part, time_part)
        except:
            return None
    
    def _generate_fingerprint(self, sender: str, message: str) -> str:
        """Generate SHA256 fingerprint for message."""
        combined = f"{sender}:{message}".lower()
        return hashlib.sha256(combined.encode()).hexdigest()
