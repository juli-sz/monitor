# services/websocket_manager.py
import asyncio
import json
from typing import List
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        # Aquí guardaremos el bucle de eventos principal de FastAPI
        self.main_loop = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def _broadcast_async(self, sensor: str, payload: dict):
        """Método interno asíncrono para enviar a todos."""
        message = json.dumps({"sensor": sensor, "payload": payload})
        for connection in self.active_connections[:]:
            try:
                await connection.send_text(message)
            except Exception:
                self.disconnect(connection)

    def broadcast_sync(self, sensor: str, payload: dict):
        """
        ¡Este es el puente! 
        El cliente MQTT (que es síncrono) debe llamar a esta función.
        """
        if self.main_loop and self.main_loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self._broadcast_async(sensor, payload), 
                self.main_loop
            )

# Instanciamos el manager para importarlo desde cualquier parte del proyecto
ws_manager = ConnectionManager()