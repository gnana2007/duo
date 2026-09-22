"""
TimeSensei Interaction Detector
───────────────────────────────
Touch, punch, and fist-grab features disabled as of now.
Clones remain peaceful, stationary, and locked in space.
"""
from typing import List, Dict, Any, Optional
from interaction.memories import MemoryManager
from interaction.audio import TimeSenseiAudio


class InteractionDetector:
    """Manages physical clone interactions (disabled as of now)."""

    def __init__(self, audio: Optional[TimeSenseiAudio] = None):
        self.audio = audio

    def update(self, memory_mgr: MemoryManager, hands: List[Dict[str, Any]], poses: List[Dict[str, Any]]):
        """Touch and punch interactions disabled — clones remain stationary."""
        pass
