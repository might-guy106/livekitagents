
import asyncio
import logging
from typing import AsyncIterator, List
from livekit.agents import stt
from livekit.agents.utils import AudioBuffer

class FillerRemoverSTT(stt.STT):
    def __init__(self, underlying_stt: stt.STT, filler_words: List[str]):
        super().__init__(streaming_supported=underlying_stt.streaming_supported)
        self._underlying_stt = underlying_stt
        self._filler_words = [word.lower() for word in filler_words]
        self._logger = logging.getLogger(__name__)

    def _remove_fillers(self, text: str) -> str:
        words = text.split()
        # Naive implementation: remove filler words.
        # A more robust implementation would handle punctuation and capitalization.
        filtered_words = [word for word in words if word.lower() not in self._filler_words]
        return " ".join(filtered_words)

    async def stream(
        self,
        audio_source: AsyncIterator[AudioBuffer],
    ) -> AsyncIterator[stt.SpeechEvent]:
        stream = self._underlying_stt.stream(audio_source)
        async for event in stream:
            if event.type == stt.SpeechEventType.INTERIM_TRANSCRIPT or event.type == stt.SpeechEventType.FINAL_TRANSCRIPT:
                original_text = event.alternatives[0].text
                cleaned_text = self._remove_fillers(original_text)

                if original_text != cleaned_text:
                    self._logger.info(f"Removed filler words: '{original_text}' -> '{cleaned_text}'")

                # If all words were fillers, we might get an empty string.
                # In that case, we can choose to not send the event at all.
                if not cleaned_text.strip():
                    continue

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
                yield new_event
            else:
                yield event

    async def recognize(
        self,
        buffer: AudioBuffer,
    ) -> stt.SpeechEvent:
        # For non-streaming recognition, we can just apply the same logic.
        event = await self._underlying_stt.recognize(buffer)
        if event.alternatives:
            original_text = event.alternatives[0].text
            cleaned_text = self._remove_fillers(original_text)

            if original_text != cleaned_text:
                self._logger.info(f"Removed filler words: '{original_text}' -> '{cleaned_text}'")

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
