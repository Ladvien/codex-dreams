#!/usr/bin/env python3
"""
Biological Rhythm Pipeline Orchestration Launcher

This script launches the biological rhythm scheduler with neuroscience-based
timing patterns for optimal memory consolidation.

Usage:
    python run_biological_orchestration.py              # Start scheduler
    python run_biological_orchestration.py --daemon     # Run in background
    python run_biological_orchestration.py --status     # Show current status
    python run_biological_orchestration.py --help       # Show help

Research Foundation:
- Miller (1956): Working memory capacity and timing
- McGaugh (2000): Memory consolidation windows
- Dement & Kleitman (1957): REM sleep patterns
- Tononi & Cirelli (2006): Synaptic homeostasis
"""

import os
import sys
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

if __name__ == "__main__":
    try:
        from orchestration.biological_rhythm_scheduler import main

        main()
    except ImportError as e:
        print(f"Error importing biological rhythm scheduler: {e}")
        print("Make sure you're in the correct directory and dependencies are installed.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nBiological rhythm scheduler stopped by user.")
        sys.exit(0)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)
