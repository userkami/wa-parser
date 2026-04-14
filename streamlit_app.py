#!/usr/bin/env python
"""
Streamlit app entry point for WhatsApp Property Parser
This is the main file Streamlit Cloud looks for.
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import and run the UI
from whatsapp_parser.ui.app import main

if __name__ == "__main__":
    main()
