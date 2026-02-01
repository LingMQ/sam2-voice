import asyncio
import base64
import json
import os
from pathlib import Path

from dotenv import load_dotenv
import weave

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from voice.gemini_live import GeminiLiveClient, GeminiLiveConfig
from memory.redis_memory import RedisUserMemory
from memory.health import MemoryHealthCheck
from memory.debug import MemoryDebugger
from memory.user_profile import UserProfileManager, UserAuthManager

load_dotenv()

# Initialize Weave for observability
try:
    project = os.getenv("WEAVE_PROJECT", "sam2-voice")
    weave.init(project)
    print(f"Weave initialized: {project}")
except Exception as e:
    print(f"Weave initialization skipped: {e}")

app = FastAPI()
static_dir = Path(__file__).parent / "static"

# Always mount static for browser_audio.html
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
def index():
    """Serve the main UI (ADHD/Autism-friendly design)."""
    return FileResponse(static_dir / "index.html")


@app.get("/classic")
def classic_ui():
    """Serve the classic browser audio page."""
    return FileResponse(static_dir / "browser_audio.html")


@app.get("/calm")
def calm_ui():
    """Serve the calm UI (alternate design)."""
    return FileResponse(static_dir / "calm_ui.html")


@app.get("/test")
def test_page():
    """Serve the memory test page."""
    return FileResponse(static_dir / "memory_test.html")


# =============================================
# Authentication Endpoints
# =============================================

@app.post("/api/auth/register")
async def register_user(
    name: str = Query(..., min_length=1),
    email: str = Query(..., min_length=3),
    password: str = Query(..., min_length=4)
):
    """Register a new user account."""
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        return JSONResponse({"success": False, "error": "REDIS_URL not configured"}, status_code=500)

    try:
        auth = UserAuthManager(redis_url)
        success, message, account = await auth.register(name, password, email if email else None)

        if not success:
            return JSONResponse({"success": False, "error": message}, status_code=400)

        # Also create a profile for the user
        profile_manager = UserProfileManager(redis_url)
        await profile_manager.get_or_create(account.user_id)

        return JSONResponse({
            "success": True,
            "message": message,
            "user": {
                "id": account.user_id,
                "name": account.name,
                "email": account.email,
                "created_at": account.created_at
            }
        })
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.post("/api/auth/login")
async def login_user(
    email: str = Query(...),
    password: str = Query(...)
):
    """Login with email and password."""
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        return JSONResponse({"success": False, "error": "REDIS_URL not configured"}, status_code=500)

    try:
        auth = UserAuthManager(redis_url)
        success, message, account = await auth.login(email, password)

        if not success:
            return JSONResponse({"success": False, "error": message}, status_code=401)

        return JSONResponse({
            "success": True,
            "message": message,
            "user": {
                "id": account.user_id,
                "name": account.name,
                "email": account.email,
                "last_login": account.last_login
            }
        })
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.get("/api/auth/check")
async def check_user_exists(email: str = Query(...)):
    """Check if a user with the given email exists."""
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        return JSONResponse({"exists": False, "error": "REDIS_URL not configured"})

    try:
        auth = UserAuthManager(redis_url)
        exists = await auth.user_exists(email)
        return JSONResponse({"exists": exists})
    except Exception as e:
        return JSONResponse({"exists": False, "error": str(e)})


@app.get("/api/health")
async def health_check(user_id: str = Query(default="browser_user")):
    """Health check endpoint."""
    try:
        redis_url = os.getenv("REDIS_URL")
        if not redis_url:
            return JSONResponse({
                "status": "unhealthy",
                "error": "REDIS_URL not configured"
            })

        health = MemoryHealthCheck(redis_url)
        status = health.get_comprehensive_health(user_id)

        # Ensure all values are JSON serializable
        def make_serializable(obj):
            if isinstance(obj, dict):
                return {k: make_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [make_serializable(item) for item in obj]
            elif isinstance(obj, (int, float, str, bool, type(None))):
                return obj
            else:
                return str(obj)

        serializable_status = make_serializable(status)
        return JSONResponse(serializable_status)
    except Exception as e:
        return JSONResponse({
            "status": "unhealthy",
            "error": str(e)
        }, status_code=500)


@app.get("/api/memory/stats")
async def memory_stats(user_id: str = Query(default="browser_user")):
    """Get memory statistics for a specific user."""
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        return JSONResponse({"error": "REDIS_URL not configured"})

    try:
        memory = RedisUserMemory(user_id=user_id, redis_url=redis_url)
        stats = memory.get_stats()
        stats["user_id"] = user_id
        return JSONResponse(stats)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/memory/debug")
async def memory_debug(user_id: str = Query(default="browser_user")):
    """Get memory debug information for a specific user."""
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        return JSONResponse({"error": "REDIS_URL not configured"})

    try:
        memory = RedisUserMemory(user_id=user_id, redis_url=redis_url)
        debugger = MemoryDebugger(memory)
        summary = debugger.get_memory_summary()
        summary["user_id"] = user_id
        return JSONResponse(summary)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/memory/interventions")
async def get_interventions(
    user_id: str = Query(default="browser_user"),
    limit: int = Query(default=20, ge=1, le=100)
):
    """Get stored interventions for a specific user."""
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        return JSONResponse({"error": "REDIS_URL not configured"})

    try:
        memory = RedisUserMemory(user_id=user_id, redis_url=redis_url)
        debugger = MemoryDebugger(memory)
        interventions = debugger.inspect_interventions(limit=limit)
        return JSONResponse({
            "user_id": user_id,
            "interventions": interventions,
            "count": len(interventions)
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/memory/reflections")
async def get_reflections(
    user_id: str = Query(default="browser_user"),
    limit: int = Query(default=10, ge=1, le=50)
):
    """Get stored reflections for a specific user."""
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        return JSONResponse({"error": "REDIS_URL not configured"})

    try:
        memory = RedisUserMemory(user_id=user_id, redis_url=redis_url)
        debugger = MemoryDebugger(memory)
        reflections = debugger.inspect_reflections(limit=limit)
        return JSONResponse({
            "user_id": user_id,
            "reflections": reflections,
            "count": len(reflections)
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/user/profile")
async def get_user_profile(user_id: str = Query(...)):
    """Get user profile information."""
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        return JSONResponse({"error": "REDIS_URL not configured"})

    try:
        manager = UserProfileManager(redis_url)
        profile = await manager.get_or_create(user_id)
        return JSONResponse({
            "user_id": profile.user_id,
            "diagnosis": profile.diagnosis,
            "diagnosis_source": profile.diagnosis_source,
            "onboarding_complete": profile.onboarding_complete,
            "preferred_checkin_interval": profile.preferred_checkin_interval,
            "sensory_sensitivities": profile.sensory_sensitivities
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/user/profile")
async def update_user_profile(
    user_id: str = Query(...),
    diagnosis: str = Query(default=None),
    diagnosis_source: str = Query(default=None)
):
    """Update user profile diagnosis information."""
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        return JSONResponse({"error": "REDIS_URL not configured"})

    try:
        manager = UserProfileManager(redis_url)
        if diagnosis and diagnosis_source:
            await manager.update_diagnosis(user_id, diagnosis, diagnosis_source)
        profile = await manager.get_or_create(user_id)
        return JSONResponse({
            "success": True,
            "user_id": profile.user_id,
            "diagnosis": profile.diagnosis,
            "diagnosis_source": profile.diagnosis_source,
            "onboarding_complete": profile.onboarding_complete
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.websocket("/ws/audio")
async def ws_audio_endpoint(websocket: WebSocket):
    """WebSocket endpoint for browser-based audio streaming."""
    await websocket.accept()

    client: GeminiLiveClient | None = None
    receive_task: asyncio.Task | None = None
    checkin_task: asyncio.Task | None = None
    is_running = False
    memory: RedisUserMemory | None = None
    session_id = "browser"

    async def send_text(text: str):
        """Send text message to browser."""
        try:
            # Ensure text is a string and not bytes
            text_str = text.decode('utf-8') if isinstance(text, bytes) else str(text)
            await websocket.send_text(json.dumps({"type": "text", "payload": text_str}))
        except (UnicodeDecodeError, TypeError) as e:
            # If we can't decode, send a safe message
            try:
                await websocket.send_text(json.dumps({"type": "text", "payload": f"[Message: {type(text).__name__}]"}))
            except:
                pass
        except Exception as e:
            print(f"Error sending text: {e}")
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
                    # Audio data is bytes - send as binary
                    if isinstance(response["data"], bytes):
                        await send_audio(response["data"])
                    else:
                        # If it's not bytes, skip it
                        continue
                elif response["type"] == "text":
                    await send_text(str(response["data"]))
                elif response["type"] == "tool_call":
                    # Safely convert result to string
                    result = response.get('result', '')
                    if isinstance(result, bytes):
                        result_str = f"<{len(result)} bytes>"
                    else:
                        result_str = str(result)[:100]  # Truncate long results
                    await send_text(f"[Tool: {response.get('name', 'unknown')} -> {result_str}]")
                elif response["type"] == "turn_complete":
                    await send_text("[Turn complete]")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            try:
                error_msg = str(e)[:500]  # Limit error message length
                await websocket.send_text(json.dumps({"type": "error", "payload": error_msg}))
            except Exception as send_error:
                # If we can't send error, just log it
                print(f"Error in receive_responses: {e}")
                print(f"Failed to send error to client: {send_error}")

    async def checkin_monitor():
        """Background task that monitors scheduled check-ins and triggers them when time expires."""
        nonlocal is_running, client, session_id
        try:
            while is_running:
                # Check for expired check-ins every 5 seconds
                await asyncio.sleep(5.0)
                
                if not is_running or not client or not client.is_connected:
                    continue
                
                # Check if there's a scheduled check-in for this session
                if session_id in _scheduled_checkins:
                    checkin_time = _scheduled_checkins[session_id]
                    now = datetime.now()
                    
                    # If check-in time has passed, trigger it
                    if now >= checkin_time:
                        # Remove from schedule to prevent duplicate triggers
                        del _scheduled_checkins[session_id]
                        
                        # Send a check-in message to the user
                        checkin_message = "Check-in: How are you doing? Still on track?"
                        print(f"🔔 Triggering scheduled check-in...")
                        await client.send_text(checkin_message)
                        await send_text(f"[Check-in triggered]")
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Check-in monitor error: {e}")
            try:
                await send_text(f"[Check-in monitor error: {str(e)[:100]}]")
            except:
                pass

    try:
        while True:
            message = await websocket.receive()

            # Handle binary audio data
            if "bytes" in message:
                if client and client.is_connected and is_running:
                    try:
                        audio_bytes = message["bytes"]
                        if isinstance(audio_bytes, bytes):
                            await client.send_audio(audio_bytes)
                        else:
                            # Try to convert if it's not bytes
                            await client.send_audio(bytes(audio_bytes))
                    except Exception as e:
                        print(f"Error sending audio: {e}")
                continue

            # Handle text messages (JSON commands)
            if "text" in message:
                data = json.loads(message["text"])
                action = data.get("action")

                if action == "start":
                    if client is None or not client.is_connected:
                        # Initialize memory if available
                        redis_url = os.getenv("REDIS_URL")
                        if redis_url:
                            try:
                                user_id = data.get("user_id", "browser_user")
                                memory = RedisUserMemory(user_id=user_id, redis_url=redis_url)
                                await send_text(f"[Memory system initialized for user: {user_id}]")
                                
                                # Show memory context (non-blocking)
                                try:
                                    context = await memory.get_context_for_prompt()
                                    if context and context != "New user - no history yet.":
                                        await send_text(f"[Memory context loaded: {len(context)} chars]")
                                except Exception as e:
                                    await send_text(f"[Memory context load warning: {str(e)[:100]}]")
                            except Exception as e:
                                await send_text(f"[Memory system unavailable: {str(e)[:100]}]")
                        
                        # Create and connect Gemini client
                        config = GeminiLiveConfig(
                            voice="Puck",
                            sample_rate=16000,
                        )
                        client = GeminiLiveClient(
                            config=config,
                            session_id="browser",
                            user_id=data.get("user_id", "browser_user"),
                            memory=memory,
                        )

                        if await client.connect():
                            is_running = True
                            session_id = "browser"  # Use consistent session ID
                            receive_task = asyncio.create_task(receive_responses())
                            checkin_task = asyncio.create_task(checkin_monitor())
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
                    if checkin_task:
                        checkin_task.cancel()
                        try:
                            await checkin_task
                        except asyncio.CancelledError:
                            pass
                    
                    # Generate reflection if memory is available
                    if memory and client:
                        try:
                            transcript = client.get_transcript()
                            if transcript and len(transcript) > 0:
                                from memory.reflection import generate_reflection
                                reflection = await generate_reflection(memory, transcript)
                                await send_text(f"[Session reflection: {reflection[:200]}]")
                        except Exception as e:
                            await send_text(f"[Reflection generation failed: {str(e)[:100]}]")
                    
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
        if checkin_task:
            checkin_task.cancel()
            try:
                await checkin_task
            except asyncio.CancelledError:
                pass
        if client:
            await client.disconnect()
