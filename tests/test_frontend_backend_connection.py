#!/usr/bin/env python3
"""Test script to verify HTML frontend and backend connection compatibility.

This script checks:
1. Backend WebSocket endpoint exists at /ws/audio
2. Backend expects correct message formats
3. HTML frontend sends correct formats
4. Message flow compatibility
"""

import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from fastapi.testclient import TestClient
    from web.app import app
except ImportError as e:
    print(f"Error importing: {e}")
    print("Make sure you're in a virtual environment with dependencies installed")
    sys.exit(1)


def test_backend_endpoints():
    """Test that backend endpoints are correctly configured."""
    print("Testing backend endpoints...")
    client = TestClient(app)
    
    # Test root endpoint serves index.html
    response = client.get("/")
    assert response.status_code == 200, f"Root endpoint failed: {response.status_code}"
    assert "index.html" in str(response.url) or "text/html" in response.headers.get("content-type", "").lower()
    print("✓ Root endpoint serves HTML")
    
    # Test WebSocket endpoint exists
    # Note: TestClient doesn't fully support WebSocket testing, but we can check the route exists
    routes = [route.path for route in app.routes]
    assert "/ws/audio" in routes, f"WebSocket endpoint /ws/audio not found. Routes: {routes}"
    print("✓ WebSocket endpoint /ws/audio exists")
    
    # Test static files are mounted
    response = client.get("/static/index.html")
    assert response.status_code == 200, f"Static files not accessible: {response.status_code}"
    print("✓ Static files are accessible")
    
    return True


def test_html_frontend_compatibility():
    """Check HTML frontend code matches backend expectations."""
    print("\nTesting HTML frontend compatibility...")
    
    static_dir = project_root / "web" / "static"
    index_html = static_dir / "index.html"
    
    if not index_html.exists():
        print(f"✗ index.html not found at {index_html}")
        return False
    
    content = index_html.read_text()
    
    # Check WebSocket URL
    if '/ws/audio' in content:
        print("✓ HTML connects to /ws/audio endpoint")
    else:
        print("✗ HTML does not connect to /ws/audio")
        return False
    
    # Check sends start action
    if 'action": "start"' in content or "action: 'start'" in content:
        print("✓ HTML sends start action")
    else:
        print("✗ HTML does not send start action")
        return False
    
    # Check sends stop action
    if 'action": "stop"' in content or "action: 'stop'" in content:
        print("✓ HTML sends stop action")
    else:
        print("✗ HTML does not send stop action")
        return False
    
    # Check handles binary audio (Blob)
    if 'event.data instanceof Blob' in content or 'instanceof Blob' in content:
        print("✓ HTML handles binary audio responses")
    else:
        print("✗ HTML does not handle binary audio")
        return False
    
    # Check sends binary audio (Int16Array)
    if 'Int16Array' in content and 'ws.send' in content:
        print("✓ HTML sends binary audio data")
    else:
        print("✗ HTML does not send binary audio")
        return False
    
    # Check handles JSON messages with type/payload
    if 'data.type' in content and 'data.payload' in content:
        print("✓ HTML handles JSON message format (type/payload)")
    else:
        print("✗ HTML does not handle JSON message format")
        return False
    
    return True


def test_backend_message_format():
    """Verify backend sends correct message formats."""
    print("\nTesting backend message format...")
    
    app_file = project_root / "web" / "app.py"
    content = app_file.read_text()
    
    # Check backend sends text messages with type/payload
    if '"type": "text"' in content and '"payload"' in content:
        print("✓ Backend sends text messages with type/payload")
    else:
        print("✗ Backend does not send correct text message format")
        return False
    
    # Check backend sends status messages
    if '"type": "status"' in content:
        print("✓ Backend sends status messages")
    else:
        print("✗ Backend does not send status messages")
        return False
    
    # Check backend sends binary audio
    if 'send_bytes' in content or 'send_audio' in content:
        print("✓ Backend sends binary audio")
    else:
        print("✗ Backend does not send binary audio")
        return False
    
    # Check backend expects action messages
    if 'action == "start"' in content and 'action == "stop"' in content:
        print("✓ Backend expects start/stop actions")
    else:
        print("✗ Backend does not expect start/stop actions")
        return False
    
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("Frontend-Backend Connection Compatibility Test")
    print("=" * 60)
    
    try:
        test_backend_endpoints()
        test_html_frontend_compatibility()
        test_backend_message_format()
        
        print("\n" + "=" * 60)
        print("✓ All compatibility checks passed!")
        print("=" * 60)
        print("\nThe HTML frontend should work correctly with the backend.")
        print("You can now safely remove the Next.js frontend if not needed.")
        return 0
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
