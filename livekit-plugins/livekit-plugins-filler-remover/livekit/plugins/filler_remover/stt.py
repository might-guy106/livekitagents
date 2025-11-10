import logging
from typing import AsyncIterator, List

from livekit.agents import stt
from livekit.agents.types import (
    DEFAULT_API_CONNECT_OPTIONS,
    NOT_GIVEN,
    APIConnectOptions,
    NotGivenOr,
)
from livekit.agents.utils import AudioBuffer


class FillerRemoverSTT(stt.STT):
    """STT wrapper that filters out filler words from transcripts in real-time.

    This class wraps an underlying STT engine and removes configurable filler words
    (like "uh", "umm", "hmm") from the transcripts before returning them.
    """

    def __init__(self, underlying_stt: stt.STT, filler_words: List[str]):
        """Initialize the filler remover STT wrapper.

        Args:
            underlying_stt: The underlying STT engine to wrap
            filler_words: List of filler words to remove from transcripts
        """
        super().__init__(capabilities=underlying_stt.capabilities)
        self._underlying_stt = underlying_stt
        self._filler_words = [word.lower() for word in filler_words]
        self._logger = logging.getLogger(__name__)

        # Log initialization with configured filler words
        self._logger.warning(f"[FILLER-REMOVER] Initialized with filler words: {self._filler_words}")

    def _remove_fillers(self, text: str) -> str:
        """Remove filler words from the given text.

        Args:
            text: The text to filter

        Returns:
            Filtered text with filler words removed
        """
        words = text.split()
        # Naive implementation: remove filler words.
        # A more robust implementation would handle punctuation and capitalization.
        filtered_words = [word for word in words if word.lower() not in self._filler_words]
        return " ".join(filtered_words)

    async def _recognize_impl(
        self,
        buffer: AudioBuffer,
        *,
        language: NotGivenOr[str] = NOT_GIVEN,
        conn_options: APIConnectOptions,
    ) -> stt.SpeechEvent:
        """Internal recognize implementation with filler words removed.

        Args:
            buffer: Audio buffer to recognize
            language: Language code (optional)
            conn_options: API connection options

        Returns:
            SpeechEvent with filler words removed from transcript
        """
        # Call underlying STT's recognize
        event = await self._underlying_stt.recognize(
            buffer, language=language, conn_options=conn_options
        )

        if event.alternatives:
            original_text = event.alternatives[0].text
            cleaned_text = self._remove_fillers(original_text)

            if original_text != cleaned_text:
                self._logger.warning(f"[BATCH] FILLER REMOVED: '{original_text}' -> '{cleaned_text}'")
            else:
                self._logger.warning(f"[BATCH] NO FILLER: '{original_text}'")

            # If all words were fillers, return event with empty text
            new_alternative = stt.SpeechData(
                language=event.alternatives[0].language,
                text=cleaned_text,
                start_time=event.alternatives[0].start_time,
                end_time=event.alternatives[0].end_time,
                confidence=event.alternatives[0].confidence,
            )
            new_event = stt.SpeechEvent(
                type=event.type,
                alternatives=[new_alternative],
            )
            return new_event
        return event

    def stream(
        self,
        *,
        language: NotGivenOr[str] = NOT_GIVEN,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
    ) -> "FilteredRecognizeStream":
        """Stream transcription with filler words removed.

        Args:
            language: Language code (optional)
            conn_options: API connection options

        Returns:
            Async iterator of SpeechEvent objects with filler words removed
        """
        underlying_stream = self._underlying_stt.stream(
            language=language, conn_options=conn_options
        )
        return FilteredRecognizeStream(
            underlying_stream=underlying_stream,
            filler_words=self._filler_words,
            logger=self._logger,
        )


class FilteredRecognizeStream:
    """Async iterator wrapper that filters filler words from streaming results."""

    def __init__(
        self,
        underlying_stream,
        filler_words: List[str],
        logger: logging.Logger,
    ):
        self._underlying_stream = underlying_stream
        self._filler_words = filler_words
        self._logger = logger

    def _remove_fillers(self, text: str) -> str:
        """Remove filler words from the given text."""
        words = text.split()
        filtered_words = [word for word in words if word.lower() not in self._filler_words]
        return " ".join(filtered_words)

    def push_frame(self, frame):
        """Proxy push_frame to underlying stream."""
        return self._underlying_stream.push_frame(frame)

    def flush(self):
        """Proxy flush to underlying stream."""
        if hasattr(self._underlying_stream, "flush"):
            return self._underlying_stream.flush()

    def __aiter__(self):
        return self

    async def __anext__(self) -> stt.SpeechEvent:
        event = await self._underlying_stream.__anext__()

        # Log all events for debugging
        event_type = event.type if hasattr(event, 'type') else 'UNKNOWN'

        if (
            event.type == stt.SpeechEventType.INTERIM_TRANSCRIPT
            or event.type == stt.SpeechEventType.FINAL_TRANSCRIPT
        ):
            if not event.alternatives:
                self._logger.warning(f"[STREAM] Received {event_type} with no alternatives")
                return event

            original_text = event.alternatives[0].text
            self._logger.warning(f"[STREAM] STT Event: {event_type} - Original: '{original_text}'")

            cleaned_text = self._remove_fillers(original_text)

            if original_text != cleaned_text:
                self._logger.warning(f"[STREAM] FILLER REMOVED: '{original_text}' -> '{cleaned_text}'")
            else:
                self._logger.warning(f"[STREAM] NO FILLER: '{original_text}' (passed through)")

            # If all words were fillers, skip this event and get next
            if not cleaned_text.strip():
                self._logger.warning(f"[STREAM] All fillers removed, skipping empty event")
                return await self.__anext__()

            # Create a new event with the cleaned text
            new_alternative = stt.SpeechData(
                language=event.alternatives[0].language,
                text=cleaned_text,
                start_time=event.alternatives[0].start_time,
                end_time=event.alternatives[0].end_time,
                confidence=event.alternatives[0].confidence,
            )
            new_event = stt.SpeechEvent(
                type=event.type,
                alternatives=[new_alternative],
            )
            return new_event
        else:
            # Log non-transcript events too
            self._logger.debug(f"[STREAM] Non-transcript event: {event_type}")
            return event

    async def aclose(self):
        """Close the underlying stream."""
        if hasattr(self._underlying_stream, "aclose"):
            await self._underlying_stream.aclose()

    async def __aenter__(self):
        """Enter async context manager."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager."""
        await self.aclose()
        return False
