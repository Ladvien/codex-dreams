"""
Biological Memory Orchestration Package

This package provides neuroscience-based orchestration for the biological memory system.
Implements timing patterns based on chronobiology research for optimal memory consolidation.

Key Components:
- BiologicalRhythmScheduler: Main scheduler implementing circadian and ultradian rhythms
- BiologicalMemoryProcessor: Executes specific memory processing tasks
- CircadianPhase: Tracks biological timing phases
- BiologicalRhythmType: Defines different rhythm types with neuroscience timing

Research Foundation:
- Miller, G. A. (1956). The magical number seven, plus or minus two
- McGaugh, J. L. (2000). Memory--a century of consolidation
- Diekelmann, S. & Born, J. (2010). The memory function of sleep
- Tononi, G. & Cirelli, C. (2006). Sleep-dependent synaptic homeostasis
- Kleitman, N. & Rosenberg, R. S. (1953). Basic rest-activity cycle

Usage:
    from orchestration import BiologicalRhythmScheduler

    scheduler = BiologicalRhythmScheduler()
    scheduler.start()  # Starts biological rhythm processing
"""

from .biological_rhythm_scheduler import (
    BiologicalMemoryProcessor,
    BiologicalRhythmScheduler,
    BiologicalRhythmType,
    CircadianPhase,
)

__version__ = "1.0.0"
__author__ = "Biological Memory Research Team"

__all__ = [
    "BiologicalRhythmScheduler",
    "BiologicalMemoryProcessor",
    "BiologicalRhythmType",
    "CircadianPhase",
]
