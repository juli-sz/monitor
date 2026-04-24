# ======================================================
# IMPORTS
# ======================================================
from contextlib import asynccontextmanager
import datetime
from typing import Optional
import asyncio

from fastapi.middleware.cors import CORSMiddleware
from fastapi import HTTPException, Depends
from paho.mqtt.client import Client as MQTTClient, CallbackAPIVersion
from fastapi import FastAPI
from sqlalchemy.orm import Session

from services.signal_processor import ecg_filter_realtime
from database import Base, engine, get_db

# Importamos nuestras rutas y el manager
from routes.websockets import router as ws_router
from routes.pacientes import router as pacientes_router
from routes.historico import router as historico_router
from services.websocket_manager import ws_manager
from services.mqtt_service import iniciar_mqtt, detener_mqtt


@asynccontextmanager
async def lifespan(app: FastAPI):
    
    print("Sincronizando Base de Datos...")
    Base.metadata.create_all(bind=engine)
    
    # Cuando arranca el servidor, capturamos el bucle asíncrono principal para WebSockets
    ws_manager.main_loop = asyncio.get_running_loop()
    
    # 2. Arrancamos el cliente MQTT
    print("Iniciando servicio MQTT...")
    iniciar_mqtt()
    
    yield # Aquí el servidor se queda corriendo
    
    # 3. Al apagar el servidor, cerramos MQTT limpiamente
    print("Apagando servicios limpiamente...")
    detener_mqtt()

app = FastAPI(title="API de Monitoreo de Signos Vitales", lifespan=lifespan)
# ======================================================
# CORS
# ======================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ws_router)


# ======================================================
# ENDPOINTS
# ======================================================

@app.get("/")
async def root():
    return {"message": "API funcionando correctamente"}

# Registramos las rutas
app.include_router(ws_router)
app.include_router(pacientes_router)
app.include_router(historico_router)

