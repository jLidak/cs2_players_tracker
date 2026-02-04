"""
Moduł obsługujący WebSocket.
Zapewnia komunikację w czasie rzeczywistym (status serwera, zegar).
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from datetime import datetime

router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """
    Obsługuje połączenie WebSocket.
    Wysyła aktualny czas i status serwera w pętli.
    """
    await websocket.accept()
    try:
        while True:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            await websocket.send_json({
                "status": "Online",
                "timestamp": now
            })
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass