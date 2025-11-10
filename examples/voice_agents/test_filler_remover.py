import asyncio
import logging
from typing import AsyncIterator, Union

from livekit import rtc
from livekit.agents import stt
from livekit.agents.types import NOT_GIVEN, APIConnectOptions, NotGivenOr
from livekit.plugins.filler_remover import FillerRemoverSTT

# AudioBuffer is a type alias for Union[list[rtc.AudioFrame], rtc.AudioFrame]
AudioBuffer = Union[list[rtc.AudioFrame], rtc.AudioFrame]


async def main():
    logging.basicConfig(level=logging.INFO)

    class MockSTT(stt.STT):
        """Mock STT for testing filler word removal"""

        def __init__(self):
            super().__init__(
                capabilities=stt.STTCapabilities(
                    streaming=True,
                    interim_results=True,
                )
            )

        async def _recognize_impl(
            self,
            buffer: AudioBuffer,
            *,
            language: NotGivenOr[str] = NOT_GIVEN,
            conn_options: APIConnectOptions,
        ) -> stt.SpeechEvent:
            """Mock recognize implementation - buffer parameter ignored for testing"""
            return stt.SpeechEvent(
                type=stt.SpeechEventType.FINAL_TRANSCRIPT,
                alternatives=[stt.SpeechData(text="uh hello world", language="en")],
            )

        def stream(
            self,
            *,
            language: NotGivenOr[str] = NOT_GIVEN,
            conn_options: APIConnectOptions,
        ) -> "MockRecognizeStream":
            """Return mock streaming interface"""
            return MockRecognizeStream()

    class MockRecognizeStream:
        """Mock streaming interface for testing"""

        def __init__(self):
            self._events = [
                stt.SpeechEvent(
                    type=stt.SpeechEventType.INTERIM_TRANSCRIPT,
                    alternatives=[stt.SpeechData(text="uh hello", language="en")],
                ),
                stt.SpeechEvent(
                    type=stt.SpeechEventType.FINAL_TRANSCRIPT,
                    alternatives=[stt.SpeechData(text="uh hello world", language="en")],
                ),
                stt.SpeechEvent(
                    type=stt.SpeechEventType.INTERIM_TRANSCRIPT,
                    alternatives=[stt.SpeechData(text="umm", language="en")],
                ),
                stt.SpeechEvent(
                    type=stt.SpeechEventType.FINAL_TRANSCRIPT,
                    alternatives=[stt.SpeechData(text="umm", language="en")],
                ),
            ]
            self._index = 0

        def __aiter__(self):
            return self

        async def __anext__(self) -> stt.SpeechEvent:
            if self._index >= len(self._events):
                raise StopAsyncIteration
            event = self._events[self._index]
            self._index += 1
            return event

        async def aclose(self):
            pass

    # Test configuration
    filler_words = ["uh", "umm"]
    mock_stt = MockSTT()
    stt_wrapper = FillerRemoverSTT(underlying_stt=mock_stt, filler_words=filler_words)

    print("=" * 60)
    print("FILLER REMOVER TEST")
    print("=" * 60)
    print(f"Filler words configured: {filler_words}")
    print()

    # Test streaming
    print("--- Streaming Test ---")
    print("Testing real-time transcript filtering...")
    print()

    stream = stt_wrapper.stream()
    event_count = 0
    async for event in stream:
        event_count += 1
        if event.alternatives:
            text = event.alternatives[0].text
            print(f"Event {event_count}: [{event.type}] '{text}'")

    print(f"\nTotal events received: {event_count}")
    print("Expected: 2 (filler-only events should be filtered)")
    print()

    # Test batch recognition
    print("--- Recognition Test ---")
    print("Testing batch transcript filtering...")
    print()

    # Create a mock AudioFrame
    buffer = rtc.AudioFrame(
        data=b"\x00" * 1000,
        sample_rate=16000,
        num_channels=1,
        samples_per_channel=500,
    )
    event = await stt_wrapper.recognize(buffer)

    if event.alternatives:
        text = event.alternatives[0].text
        print(f"Result: '{text}'")
        print(f"Expected: 'hello world' (without 'uh')")

    print()
    print("=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
