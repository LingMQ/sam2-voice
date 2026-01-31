import asyncio
import json
from pathlib import Path

from dotenv import load_dotenv

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from voice.bot import VoiceBot


load_dotenv()
app = FastAPI()
static_dir = Path(__file__).parent / "static"
frontend_out = Path(__file__).resolve().parents[1] / "frontend" / "out"

if not frontend_out.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

bot_task: asyncio.Task | None = None
bot_instance: VoiceBot | None = None


@app.get("/")
def index():
    if frontend_out.exists():
        index_file = frontend_out / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return PlainTextResponse("Frontend build missing index.html", status_code=404)

    return HTMLResponse((static_dir / "index.html").read_text())


@app.get("/{path:path}")
def frontend_assets(path: str):
    if not frontend_out.exists():
        return PlainTextResponse("Not found", status_code=404)

    asset = frontend_out / path
    if asset.is_file():
        return FileResponse(asset)

    index_file = frontend_out / "index.html"
    if index_file.exists():
        return FileResponse(index_file)

    return PlainTextResponse("Frontend build missing index.html", status_code=404)


async def _run_bot(event_queue: asyncio.Queue):
    global bot_instance

    def emit(event_type: str, payload: str | dict | None = None):
        event_queue.put_nowait({"type": event_type, "payload": payload})

    try:
        bot_instance = VoiceBot(
            on_text=lambda text: emit("text", text),
            on_status=lambda status: emit("status", status),
            on_error=lambda error: emit("error", error),
            on_turn_complete=lambda: emit("turn_complete"),
        )

        await bot_instance.run()
    except Exception as exc:
        emit("error", str(exc))
        emit("status", "stopped")


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    global bot_task, bot_instance
    await websocket.accept()
    event_queue: asyncio.Queue = asyncio.Queue()

    async def sender():
        while True:
            event = await event_queue.get()
            await websocket.send_text(json.dumps(event))

    sender_task = asyncio.create_task(sender())

    try:
        while True:
            message = await websocket.receive_text()
            data = json.loads(message)
            action = data.get("action")

            if action == "start":
                if bot_task is None or bot_task.done():
                    bot_task = asyncio.create_task(_run_bot(event_queue))
                    await event_queue.put({"type": "status", "payload": "starting"})
                else:
                    await event_queue.put({"type": "status", "payload": "already_running"})
            elif action == "stop":
                if bot_instance:
                    await bot_instance.stop()
                    bot_instance = None
                if bot_task and not bot_task.done():
                    bot_task.cancel()
                await event_queue.put({"type": "status", "payload": "stopped"})
    except WebSocketDisconnect:
        if bot_instance:
            await bot_instance.stop()
            bot_instance = None
        if bot_task and not bot_task.done():
            bot_task.cancel()
    finally:
        sender_task.cancel()
