# LiveKit Agents - Filler Remover Plugin

This plugin provides a Speech-to-Text (STT) wrapper that removes filler words from the transcript.

## Installation

```bash
pip install livekit-plugins-filler-remover
```

## Usage

```python
import os
from livekit.plugins import assemblyai
from livekit.plugins.filler_remover import FillerRemoverSTT
from livekit.agents import AgentSession

# A list of words to ignore
filler_words_str = os.environ.get("FILLER_WORDS", "uh,umm,hmm,haan")
filler_words = [word.strip() for word in filler_words_str.split(',')]

stt = FillerRemoverSTT(
    underlying_stt=assemblyai.STT(),
    filler_words=filler_words,
)

session = AgentSession(
    stt=stt,
    # ... other options
)
```

## Configuration

The list of filler words can be configured through the `FILLER_WORDS` environment variable. It should be a comma-separated list of words.
