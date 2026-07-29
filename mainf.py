# ======================================================
# IMPORTS
# ======================================================
from contextlib import asynccontextmanager
import datetime
from typing import Optional
import asyncio
from routes.alertas import router as alertas_router
from routes.dispositivos import router as dispositivos_router
from routes.sensores import router as sensores_router
from routes.usuarios import router as usuarios_router
from fastapi.middleware.cors import CORSMiddleware
from fastapi import HTTPException, Depends
from paho.mqtt.client import Client as MQTTClient, CallbackAPIVersion
from fastapi import FastAPI
from sqlalchemy.orm import Session

import models
from models import Dispositivo, Paciente, PacienteDispositivo, ECG, LecturaPNI, LecturaGeneral
from services.signal_processor import ecg_filter_realtime
from services.auth_service import obtener_usuario_actual
from database import Base, engine, get_db

# Importamos nuestras rutas y el manager
from routes.websockets import router as ws_router
from routes.pacientes import router as pacientes_router
from routes.historico import router as historico_router
from routes.auth import router as auth_router
from services.websocket_manager import ws_manager
from services.mqtt_service import iniciar_mqtt, detener_mqtt

# Revisa todos los modelos y crea las tablas que falten en PostgreSQL
models.Base.metadata.create_all(bind=engine)

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

# ======================================================
# ENDPOINTS
# ======================================================

@app.get("/pacientes_por_dispositivo_uid/{uid_equipo}")
def obtener_paciente_por_uid(
    uid_equipo: str,
    db: Session = Depends(get_db),
    _=Depends(obtener_usuario_actual),
):
    # 1. Buscamos el dispositivo
    disp = db.query(Dispositivo).filter(Dispositivo.uid_equipo == uid_equipo).first()
    if not disp:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    
    # 2. Buscamos la asociación activa (fecha de disociación es nula)
    asoc_activa = db.query(PacienteDispositivo).filter(
        PacienteDispositivo.id_dispositivo == disp.id_dispositivo,
        PacienteDispositivo.fecha_hora_disoc == None
    ).first()
    
    if not asoc_activa:
        raise HTTPException(status_code=404, detail="No hay paciente asociado a este equipo")

    # 3. BUSCAMOS AL PACIENTE MANUALMENTE (Esto soluciona el AttributeError)
    paciente = db.query(Paciente).filter(Paciente.id_paciente == asoc_activa.id_paciente).first()
    
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado en la base de datos")
        
    return paciente

@app.get("/")
async def root():
    return {"message": "API funcionando correctamente"}

# Registramos las rutas
app.include_router(ws_router)
app.include_router(pacientes_router)
app.include_router(historico_router)
app.include_router(dispositivos_router)
app.include_router(auth_router)
app.include_router(alertas_router)
app.include_router(sensores_router)
app.include_router(usuarios_router)

