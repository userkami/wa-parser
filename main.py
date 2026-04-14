#!/usr/bin/env python
"""
Main entry point for the WhatsApp Property Parser
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from whatsapp_parser.pipeline import ParsingPipeline


def main():
    """Run parser from command line."""
    if len(sys.argv) < 2:
        print("Usage: python main.py <path_to_chat_file.txt>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    if not Path(file_path).exists():
        print(f"Error: File not found: {file_path}")
        sys.exit(1)
    
    print(f"Parsing: {file_path}")
    
    pipeline = ParsingPipeline()
    result = pipeline.process(file_path)
    
    if result.get('parsing_status') == 'success':
        print(f"✅ Success!")
        print(f"   Messages: {result.get('messages_count')}")
        print(f"   Records: {len(result.get('parsed_records', []))}")
        print(f"   Export: {result.get('export_path')}")
    else:
        print(f"❌ Error: {result.get('error_message')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
