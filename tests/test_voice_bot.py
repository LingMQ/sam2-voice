import types as py_types

import pytest

from voice.bot import VoiceBot


class FakeGeminiLiveClient:
    def __init__(self, *args, **kwargs):
        self._on_turn_complete = None

    def set_audio_callback(self, callback):
        pass

    def set_text_callback(self, callback):
        pass

    def set_turn_complete_callback(self, callback):
        self._on_turn_complete = callback

    def set_audio_callback(self, callback):
        pass

    def set_text_callback(self, callback):
        pass

    async def connect(self):
        return True

    async def disconnect(self):
        return None

    def get_session_summary(self):
        return {}


@pytest.mark.asyncio
async def test_max_turns_stops_bot(monkeypatch):
    monkeypatch.setattr("voice.bot.GeminiLiveClient", FakeGeminiLiveClient)

    bot = VoiceBot(max_turns=1)
    bot._is_running = True

    bot._on_turn_complete()

    assert bot._is_running is False


def test_on_text_callback(monkeypatch):
    monkeypatch.setattr("voice.bot.GeminiLiveClient", FakeGeminiLiveClient)
    received = []

    bot = VoiceBot(on_text=lambda text: received.append(text))
    bot._on_text_response("hello")

    assert received == ["hello"]
