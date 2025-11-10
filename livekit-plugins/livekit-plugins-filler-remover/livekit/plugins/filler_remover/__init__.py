"""LiveKit Filler Remover Plugin

This plugin provides a wrapper around STT engines to filter out filler words
from transcripts in real-time.
"""

from .stt import FillerRemoverSTT
from .version import __version__

__all__ = ["FillerRemoverSTT", "__version__"]
