import types as py_types

import pytest

from voice.gemini_live import GeminiLiveClient, GeminiLiveConfig
from google.genai import types


class FakeSession:
    def __init__(self):
        self.realtime_inputs = []
        self.client_contents = []
        self.tool_responses = []

    async def send_realtime_input(self, **kwargs):
        self.realtime_inputs.append(kwargs)

    async def send_client_content(self, **kwargs):
        self.client_contents.append(kwargs)

    async def send_tool_response(self, **kwargs):
        self.tool_responses.append(kwargs)

    async def receive(self):
        if False:
            yield None


class FakeSessionCM:
    def __init__(self, session):
        self.session = session
        self.entered = False
        self.exited = False

    async def __aenter__(self):
        self.entered = True
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        self.exited = True


class FakeClient:
    def __init__(self, session_cm, connect_args):
        def connect(**kwargs):
            connect_args.update(kwargs)
            return session_cm

        self.aio = py_types.SimpleNamespace(
            live=py_types.SimpleNamespace(connect=connect)
        )


def install_fake_genai(monkeypatch):
    session = FakeSession()
    session_cm = FakeSessionCM(session)
    connect_args = {}
    monkeypatch.setattr(
        "voice.gemini_live.genai.Client",
        lambda api_key=None: FakeClient(session_cm, connect_args),
    )
    return session, session_cm, connect_args


@pytest.mark.asyncio
async def test_connect_uses_async_session_context_manager(monkeypatch):
    session, session_cm, connect_args = install_fake_genai(monkeypatch)

    client = GeminiLiveClient(config=GeminiLiveConfig(model="test-model"))
    connected = await client.connect()

    assert connected is True
    assert session_cm.entered is True
    assert client._session is session
    assert connect_args["model"] == "test-model"


@pytest.mark.asyncio
async def test_send_audio_uses_realtime_input(monkeypatch):
    install_fake_genai(monkeypatch)
    session = FakeSession()
    client = GeminiLiveClient(config=GeminiLiveConfig(sample_rate=16000))
    client._session = session

    await client.send_audio(b"\x00\x01")

    assert len(session.realtime_inputs) == 1
    media = session.realtime_inputs[0]["media"]
    assert isinstance(media, types.Blob)
    assert media.mime_type == "audio/pcm;rate=16000"
    assert media.data == b"\x00\x01"


@pytest.mark.asyncio
async def test_send_text_uses_client_content(monkeypatch):
    install_fake_genai(monkeypatch)
    session = FakeSession()
    client = GeminiLiveClient()
    client._session = session

    await client.send_text("hello")

    assert len(session.client_contents) == 1
    turns = session.client_contents[0]["turns"]
    assert len(turns) == 1
    assert turns[0].role == "user"
    assert turns[0].parts[0].text == "hello"
