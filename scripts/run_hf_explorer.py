#!/usr/bin/env python3
"""
HuggingFace Model Explorer - Launcher Script
Run the GUI application with proper environment setup
"""

import os
import sys

# Add scripts directory to path
scripts_dir = os.path.dirname(os.path.abspath(__file__))
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)

from hf_model_explorer import main

if __name__ == "__main__":
    main()
