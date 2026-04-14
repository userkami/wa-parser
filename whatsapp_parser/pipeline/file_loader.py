import chardet
from pathlib import Path
from typing import Tuple, Dict, Any
from .base import BaseModule, ModuleError, ErrorLevel
import uuid


class FileLoader(BaseModule):
    """
    Module A: File Intake
    - Validates file type
    - Detects encoding
    - Normalizes line endings
    - Stores metadata
    """
    
    def process(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Input: {file_path: str}
        Output: enriched with {
            import_id, file_name, file_size,
            raw_content, encoding_detected,
            total_lines, normalized_lines
        }
        """
        file_path = payload.get("file_path")
        
        if not file_path:
            raise ModuleError(
                level=ErrorLevel.FATAL,
                message="No file path provided",
                error_type="missing_input"
            )
        
        file_path = Path(file_path)
        
        # Validate file type
        if not file_path.exists():
            raise ModuleError(
                level=ErrorLevel.FATAL,
                message=f"File not found: {file_path}",
                error_type="file_not_found"
            )
        
        if file_path.suffix.lower() != '.txt':
            raise ModuleError(
                level=ErrorLevel.FATAL,
                message=f"Invalid file type: {file_path.suffix}. Only .txt files supported.",
                error_type="invalid_file_type"
            )
        
        # Read raw bytes
        try:
            with open(file_path, 'rb') as f:
                raw_bytes = f.read()
        except Exception as e:
            raise ModuleError(
                level=ErrorLevel.FATAL,
                message=f"Error reading file: {str(e)}",
                error_type="file_read_error"
            )
        
        # Detect encoding
        encoding_detected = self._detect_encoding(raw_bytes)
        
        # Decode content
        try:
            raw_content = raw_bytes.decode(encoding_detected)
        except UnicodeDecodeError:
            # Fallback to latin-1
            try:
                raw_content = raw_bytes.decode('latin-1')
                encoding_detected = 'latin-1'
            except Exception as e:
                raise ModuleError(
                    level=ErrorLevel.FATAL,
                    message=f"Could not decode file: {str(e)}",
                    error_type="encoding_error"
                )
        
        # Normalize line endings
        raw_content = raw_content.replace('\r\n', '\n').replace('\r', '\n')
        
        # Check for empty file
        if not raw_content.strip():
            raise ModuleError(
                level=ErrorLevel.FATAL,
                message="File is empty",
                error_type="empty_file"
            )
        
        # Split into lines
        lines = raw_content.split('\n')
        
        # Build payload
        payload['import_id'] = str(uuid.uuid4())
        payload['file_name'] = file_path.name
        payload['file_size'] = len(raw_bytes)
        payload['raw_content'] = raw_content
        payload['encoding_detected'] = encoding_detected
        payload['total_lines'] = len(lines)
        payload['lines'] = lines  # Store for next module
        
        return payload
    
    def _detect_encoding(self, raw_bytes: bytes) -> str:
        """Detect encoding from raw bytes."""
        # Check for BOM signatures
        if raw_bytes.startswith(b'\xff\xfe'):
            return 'utf-16-le'
        if raw_bytes.startswith(b'\xfe\xff'):
            return 'utf-16-be'
        if raw_bytes.startswith(b'\xef\xbb\xbf'):
            return 'utf-8-sig'
        
        # Use chardet for detection
        detected = chardet.detect(raw_bytes)
        if detected and detected.get('encoding'):
            return detected['encoding']
        
        # Fallback
        return 'utf-8'
