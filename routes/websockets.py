# routers/websockets.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from services.websocket_manager import ws_manager

# Usamos APIRouter en lugar de app directamente
router = APIRouter()

@router.websocket("/ws/datos")
async def websocket_datos(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            # Mantenemos la conexión viva escuchando (aunque solo enviemos)
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)