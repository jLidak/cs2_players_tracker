"""
WebSocket routing module.
Provides real-time communication (server status, live clock) to connected clients.
"""

from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """
    Handles an active WebSocket connection.
    Continuously sends the current server time and 'Online' status
    in response to incoming messages (pings) from the client.

    Args:
        websocket (WebSocket): The active WebSocket connection object.
    """
    await websocket.accept()
    try:
        while True:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            await websocket.send_json({"status": "Online", "timestamp": now})
            # Wait for the next ping from the client before sending the next update
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
