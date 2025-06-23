"""
Simple wrapper script that maintains compatibility with the original run_codex_todo.py
while using the new modular architecture.
"""

import sys
from pathlib import Path

# Add the parent directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from scripts.run_codex_enhanced import main

if __name__ == "__main__":
    main()
