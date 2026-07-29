# routers/websockets.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from services.websocket_manager import ws_manager
from services.auth_service import obtener_usuario_actual

# Usamos APIRouter en lugar de app directamente
router = APIRouter()


@router.websocket("/ws/datos")
async def websocket_datos(
    websocket: WebSocket,
    token: str = Query(None),
    db: Session = Depends(get_db),
):
    # Los navegadores no pueden mandar headers en el handshake de un WebSocket,
    # así que el token viaja como query param: ws://host/ws/datos?token=<jwt>.
    try:
        obtener_usuario_actual(token=token, db=db)
    except HTTPException:
        await websocket.close(code=1008)  # 1008 = Policy Violation
        return

    await ws_manager.connect(websocket)
    try:
        while True:
            # Mantenemos la conexión viva escuchando (aunque solo enviemos)
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
