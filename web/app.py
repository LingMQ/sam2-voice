import asyncio
import base64
import json
import os
from pathlib import Path

from dotenv import load_dotenv

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from voice.gemini_live import GeminiLiveClient, GeminiLiveConfig


load_dotenv()
app = FastAPI()
static_dir = Path(__file__).parent / "static"
frontend_out = Path(__file__).resolve().parents[1] / "frontend" / "out"

# Always mount static for browser_audio.html
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
def index():
    """Serve the browser audio page."""
    return FileResponse(static_dir / "browser_audio.html")


@app.websocket("/ws/audio")
async def ws_audio_endpoint(websocket: WebSocket):
    """WebSocket endpoint for browser-based audio streaming."""
    await websocket.accept()

    client: GeminiLiveClient | None = None
    receive_task: asyncio.Task | None = None
    is_running = False

    async def send_text(text: str):
        """Send text message to browser."""
        try:
            await websocket.send_text(json.dumps({"type": "text", "payload": text}))
        except:
            pass

    async def send_status(status: str):
        """Send status message to browser."""
        try:
            await websocket.send_text(json.dumps({"type": "status", "payload": status}))
        except:
            pass

    async def send_audio(audio_data: bytes):
        """Send audio data to browser."""
        try:
            await websocket.send_bytes(audio_data)
        except:
            pass

    async def receive_responses():
        """Background task for receiving responses from Gemini."""
        nonlocal is_running
        try:
            async for response in client.receive_responses():
                if not is_running:
                    break
                if response["type"] == "audio":
                    await send_audio(response["data"])
                elif response["type"] == "text":
                    await send_text(response["data"])
                elif response["type"] == "tool_call":
                    await send_text(f"[Tool: {response['name']}]")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            await websocket.send_text(json.dumps({"type": "error", "payload": str(e)}))

    try:
        while True:
            message = await websocket.receive()

            # Handle binary audio data
            if "bytes" in message:
                if client and client.is_connected and is_running:
                    await client.send_audio(message["bytes"])
                continue

            # Handle text messages (JSON commands)
            if "text" in message:
                data = json.loads(message["text"])
                action = data.get("action")

                if action == "start":
                    if client is None or not client.is_connected:
                        # Create and connect Gemini client
                        config = GeminiLiveConfig(
                            voice="Puck",
                            sample_rate=16000,
                        )
                        client = GeminiLiveClient(
                            config=config,
                            session_id="browser",
                            user_id="browser_user",
                        )

                        # Don't set callbacks - we use receive_responses instead
                        # This avoids duplicate audio

                        if await client.connect():
                            is_running = True
                            receive_task = asyncio.create_task(receive_responses())
                            await send_status("ready")
                        else:
                            await websocket.send_text(json.dumps({
                                "type": "error",
                                "payload": "Failed to connect to Gemini"
                            }))
                    else:
                        await send_status("already_running")

                elif action == "stop":
                    is_running = False
                    if receive_task:
                        receive_task.cancel()
                        try:
                            await receive_task
                        except asyncio.CancelledError:
                            pass
                    if client:
                        await client.disconnect()
                        client = None
                    await send_status("stopped")

    except WebSocketDisconnect:
        pass
    finally:
        is_running = False
        if receive_task:
            receive_task.cancel()
            try:
                await receive_task
            except asyncio.CancelledError:
                pass
        if client:
            await client.disconnect()
