# ======================================================
# IMPORTS
# ======================================================
import json
import asyncio
import time
import datetime
import threading
import os
from typing import List, Optional, Dict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi import HTTPException, Depends
from paho.mqtt.client import Client as MQTTClient, CallbackAPIVersion

from sqlalchemy import (
    create_engine, Column, Integer, String, Date, Text, ForeignKey,
    TIMESTAMP, Numeric, ARRAY, CheckConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.sql import func

from fastapi.middleware.cors import CORSMiddleware

import numpy as np
from scipy.signal import butter, lfilter, iirnotch

# ======================================================
# CONFIGURACIÓN
# ======================================================
DB_URL = "postgresql+psycopg2://postgres:12345678@localhost:5432/tu_basededatos"

MQTT_BROKER = os.getenv("MQTT_BROKER", "161.35.100.210")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1884))
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "salva")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "Urbepalacio8")
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "datos/sensores/#")

Base = declarative_base()
engine = create_engine(DB_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

app = FastAPI(
    title="API de Monitoreo de Signos Vitales",
    description="API para gestionar pacientes, dispositivos, lecturas y alertas."
)

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
# FILTRO ECG SCIPY (STATEFUL & MULTI-DISPOSITIVO)
# ======================================================

ecg_states: Dict[str, dict] = {}

def ecg_filter_realtime(raw_values: List[float], fs: int, uid_equipo: str):
    """Filtro ECG profesional tiempo real usando SciPy."""
    try:
        ecg = np.asarray(raw_values, dtype=float)

        if len(ecg) < 3:
            return ecg

        if uid_equipo not in ecg_states:
            ecg_states[uid_equipo] = {"zi_bp": None, "zi_notch": None}

        state = ecg_states[uid_equipo]

        # Bandpass 0.5–40 Hz
        low, high = 0.5, 40
        b_bp, a_bp = butter(4, [low/(fs/2), high/(fs/2)], btype='band')

        if state["zi_bp"] is None:
            zi_init = np.zeros(max(len(a_bp), len(b_bp)) - 1)
            state["zi_bp"] = zi_init * ecg[0]

        ecg_bp, state["zi_bp"] = lfilter(b_bp, a_bp, ecg, zi=state["zi_bp"])

        # Notch 50 Hz
        f0 = 50
        Q = 25
        b_no, a_no = iirnotch(f0, Q, fs)

        if state["zi_notch"] is None:
            zi_init = np.zeros(max(len(a_no), len(b_no)) - 1)
            state["zi_notch"] = zi_init * ecg_bp[0]

        ecg_notch, state["zi_notch"] = lfilter(b_no, a_no, ecg_bp, zi=state["zi_notch"])

        # Suavizado
        ecg_smooth = np.convolve(ecg_notch, np.ones(3)/3, mode="same")

        ecg_states[uid_equipo] = state
        return ecg_smooth

    except Exception as e:
        print(f"❌ Error filtrando ECG {uid_equipo}: {e}")
        return np.asarray(raw_values, dtype=float)

# ======================================================
# DB DEPENDENCY
# ======================================================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ======================================================
# MODELOS BD
# ======================================================
class Paciente(Base):
    __tablename__ = "paciente"
    id_paciente = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    apellido = Column(String(100), nullable=False)
    fecha_nacimiento = Column(Date)
    direccion = Column(Text)
    sexo = Column(String(1), CheckConstraint("sexo IN ('M', 'F')"))
    diagnostico = Column(Text)
    tipo = Column(String(50))
    creado_en = Column(TIMESTAMP(timezone=True), default=func.now())
    actualizado_en = Column(TIMESTAMP(timezone=True), default=func.now(), onupdate=func.now())

    dispositivos = relationship("PacienteDispositivo", back_populates="paciente")
    lecturas_generales = relationship("LecturaGeneral", back_populates="paciente_rel")
    ecg_bloques = relationship("ECG", back_populates="paciente_rel")
    lecturas_pni = relationship("LecturaPNI", back_populates="paciente_rel")
    rangos_signos_vitales = relationship("RangoSignoVital", back_populates="paciente_rel")
    alertas = relationship("Alerta", back_populates="paciente_rel")


class Dispositivo(Base):
    __tablename__ = "dispositivo"
    id_dispositivo = Column(Integer, primary_key=True, index=True)
    uid_equipo = Column(String(100), nullable=False, unique=True, index=True)
    estado = Column(String(50), default="Activo")
    creado_en = Column(TIMESTAMP(timezone=True), default=func.now())
    actualizado_en = Column(TIMESTAMP(timezone=True), default=func.now(), onupdate=func.now())

    pacientes_asociados = relationship("PacienteDispositivo", back_populates="dispositivo")
    sensores = relationship("Sensor", back_populates="dispositivo_rel")
    lecturas_generales = relationship("LecturaGeneral", back_populates="dispositivo_rel")
    ecg_bloques = relationship("ECG", back_populates="dispositivo_rel")
    lecturas_pni = relationship("LecturaPNI", back_populates="dispositivo_rel")
    alertas = relationship("Alerta", back_populates="dispositivo_rel")


class PacienteDispositivo(Base):
    __tablename__ = "paciente_dispositivo"
    id_paciente = Column(Integer, ForeignKey("paciente.id_paciente"), primary_key=True)
    id_dispositivo = Column(Integer, ForeignKey("dispositivo.id_dispositivo"), primary_key=True)
    fecha_hora_asoc = Column(TIMESTAMP(timezone=True), default=func.now())
    fecha_hora_disoc = Column(TIMESTAMP(timezone=True))

    paciente = relationship("Paciente", back_populates="dispositivos")
    dispositivo = relationship("Dispositivo", back_populates="pacientes_asociados")


class Sensor(Base):
    __tablename__ = "sensor"
    id_sensor = Column(Integer, primary_key=True, index=True)
    id_dispositivo = Column(Integer, ForeignKey("dispositivo.id_dispositivo"))
    tipo = Column(String(50), nullable=False)
    estado = Column(String(50), default="Activo")
    creado_en = Column(TIMESTAMP(timezone=True), default=func.now())
    actualizado_en = Column(TIMESTAMP(timezone=True), default=func.now(), onupdate=func.now())

    dispositivo_rel = relationship("Dispositivo", back_populates="sensores")


class LecturaGeneral(Base):
    __tablename__ = "lecturas_generales"
    id_lectura = Column(Integer, primary_key=True)
    id_dispositivo = Column(Integer, ForeignKey("dispositivo.id_dispositivo"))
    id_paciente = Column(Integer, ForeignKey("paciente.id_paciente"))
    tipo_sensor = Column(String(50), nullable=False)
    fecha_hora = Column(TIMESTAMP(timezone=True), nullable=False)
    valor_numerico = Column(Numeric)
    modo = Column(String(50))
    creado_en = Column(TIMESTAMP(timezone=True), default=func.now())

    dispositivo_rel = relationship("Dispositivo", back_populates="lecturas_generales")
    paciente_rel = relationship("Paciente", back_populates="lecturas_generales")


class ECG(Base):
    __tablename__ = "ecg_bloque"
    id = Column(Integer, primary_key=True)
    id_dispositivo = Column(Integer, ForeignKey("dispositivo.id_dispositivo"))
    id_paciente = Column(Integer, ForeignKey("paciente.id_paciente"))
    fecha_inicio = Column(TIMESTAMP(timezone=True), nullable=False)
    frecuencia_muestreo = Column(Integer, nullable=False)
    sample_number = Column(Integer, nullable=False)
    valor = Column(ARRAY(Numeric), nullable=False)
    modo = Column(Text)
    creado_en = Column(TIMESTAMP(timezone=True), default=func.now())

    dispositivo_rel = relationship("Dispositivo", back_populates="ecg_bloques")
    paciente_rel = relationship("Paciente", back_populates="ecg_bloques")


class LecturaPNI(Base):
    __tablename__ = "lectura_pni"
    id_lectura = Column(Integer, primary_key=True)
    id_dispositivo = Column(Integer, ForeignKey("dispositivo.id_dispositivo"))
    id_paciente = Column(Integer, ForeignKey("paciente.id_paciente"))
    fecha_hora = Column(TIMESTAMP(timezone=True), nullable=False)
    presion_sistolica = Column(Integer, nullable=False)
    presion_diastolica = Column(Integer, nullable=False)
    modo = Column(Text)
    creado_en = Column(TIMESTAMP(timezone=True), default=func.now())

    dispositivo_rel = relationship("Dispositivo", back_populates="lecturas_pni")
    paciente_rel = relationship("Paciente", back_populates="lecturas_pni")


class RangoSignoVital(Base):
    __tablename__ = "rango_signo_vital"
    id_rango = Column(Integer, primary_key=True)
    id_paciente = Column(Integer, ForeignKey("paciente.id_paciente"))
    tipo_signo = Column(String(50), nullable=False)
    valor_minimo = Column(Numeric, nullable=False)
    valor_maximo = Column(Numeric, nullable=False)
    unidad = Column(String(50))
    creado_en = Column(TIMESTAMP(timezone=True), default=func.now())
    actualizado_en = Column(TIMESTAMP(timezone=True), default=func.now(), onupdate=func.now())

    paciente_rel = relationship("Paciente", back_populates="rangos_signos_vitales")


class Alerta(Base):
    __tablename__ = "alerta"
    id_alerta = Column(Integer, primary_key=True)
    id_paciente = Column(Integer, ForeignKey("paciente.id_paciente"))
    id_dispositivo = Column(Integer, ForeignKey("dispositivo.id_dispositivo"))
    fecha_hora = Column(TIMESTAMP(timezone=True), default=func.now())
    descripcion = Column(Text, nullable=False)
    estado = Column(String(50), default="ACTIVA")
    resuelta_en = Column(TIMESTAMP(timezone=True))
    creado_en = Column(TIMESTAMP(timezone=True), default=func.now())
    actualizado_en = Column(TIMESTAMP(timezone=True), default=func.now(), onupdate=func.now())

    paciente_rel = relationship("Paciente", back_populates="alertas")
    dispositivo_rel = relationship("Dispositivo", back_populates="alertas")

# ======================================================
# WEBSOCKET
# ======================================================

clientes_websocket: List[WebSocket] = []
websocket_loop = None

def iniciar_event_loop():
    global websocket_loop
    websocket_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(websocket_loop)
    websocket_loop.run_forever()

threading.Thread(target=iniciar_event_loop, daemon=True).start()

@app.websocket("/ws/datos")
async def websocket_datos(websocket: WebSocket):
    await websocket.accept()
    clientes_websocket.append(websocket)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in clientes_websocket:
            clientes_websocket.remove(websocket)

def emitir_a_websockets(sensor: str, payload: dict):
    if websocket_loop is None:
        return

    msg = json.dumps({"sensor": sensor, "payload": payload})

    for ws in clientes_websocket[:]:
        try:
            asyncio.run_coroutine_threadsafe(ws.send_text(msg), websocket_loop)
        except:
            try:
                clientes_websocket.remove(ws)
            except:
                pass

# ======================================================
# MQTT
# ======================================================

mqtt_client: Optional[MQTTClient] = None

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("MQTT conectado")
        client.subscribe(MQTT_TOPIC)
    else:
        print("Error MQTT:", rc)

def on_disconnect(client, userdata, rc):
    print("MQTT desconectado", rc)

def on_message(client, userdata, msg):
    session = SessionLocal()
    try:
        payload = json.loads(msg.payload.decode())
        uid_equipo = payload.get("Uid_Equipo")
        if not uid_equipo:
            return

        timestamp = datetime.datetime.fromtimestamp(
            payload.get("Date", time.time()),
            tz=datetime.timezone.utc
        )

        dispositivo = session.query(Dispositivo).filter_by(uid_equipo=uid_equipo).first()
        if not dispositivo:
            dispositivo = Dispositivo(uid_equipo=uid_equipo)
            session.add(dispositivo)
            session.commit()
            session.refresh(dispositivo)

        id_dispositivo = dispositivo.id_dispositivo

        assoc = session.query(PacienteDispositivo).filter_by(
            id_dispositivo=id_dispositivo,
            fecha_hora_disoc=None
        ).first()

        id_paciente = assoc.id_paciente if assoc else None
        sensor_tipo = msg.topic.split("/")[-1].lower()

        # ============================
        # ECG
        # ============================
        if sensor_tipo == "ecg":
            raw_values = payload.get("raw_values", [])

            nuevo = ECG(
                id_dispositivo=id_dispositivo,
                id_paciente=id_paciente,
                fecha_inicio=timestamp,
                frecuencia_muestreo=payload.get("FS", 360),
                sample_number=payload.get("sample_number", len(raw_values)),
                valor=[float(x) for x in raw_values],
                modo=payload.get("mode")        # <--- CORREGIDO
            )
            session.add(nuevo)

            if raw_values:
                try:
                    fs = payload.get("FS", 360)
                    filtered = ecg_filter_realtime(raw_values, fs, uid_equipo)
                    payload["raw_values"] = filtered.tolist()
                except:
                    payload["raw_values"] = raw_values

        # ============================
        # PNI
        # ============================
        elif sensor_tipo == "pni":
            try:
                sist, diast = map(int, payload.get("value", "0/0").split("/"))
            except:
                return

            nuevo = LecturaPNI(
                id_dispositivo=id_dispositivo,
                id_paciente=id_paciente,
                fecha_hora=timestamp,
                presion_sistolica=sist,
                presion_diastolica=diast,
                modo=payload.get("mode")
            )
            session.add(nuevo)

        # ============================
        # VALORES GENERALES
        # ============================
        else:
            valor = payload.get("value")
            if valor is None:
                return

            nuevo = LecturaGeneral(
                id_dispositivo=id_dispositivo,
                id_paciente=id_paciente,
                tipo_sensor=sensor_tipo,
                fecha_hora=timestamp,
                valor_numerico=float(valor),
                modo=payload.get("mode")
            )
            session.add(nuevo)

        session.commit()
        emitir_a_websockets(sensor_tipo, payload)

    except Exception as e:
        print("[ERROR MQTT]", e)
        session.rollback()
    finally:
        session.close()

def start_mqtt_thread():
    global mqtt_client
    mqtt_client = MQTTClient(
        client_id="fastapi_api_listener",
        callback_api_version=CallbackAPIVersion.VERSION2
    )
    mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_disconnect = on_disconnect
    mqtt_client.on_message = on_message
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    mqtt_client.loop_forever()

# ======================================================
# STARTUP
# ======================================================

@app.on_event("startup")
async def startup_event():
    Base.metadata.create_all(bind=engine)
    threading.Thread(target=start_mqtt_thread, daemon=True).start()

@app.on_event("shutdown")
async def shutdown_event():
    if mqtt_client:
        mqtt_client.disconnect()

# ======================================================
# ENDPOINTS
# ======================================================

@app.get("/")
async def root():
    return {"message": "API funcionando correctamente"}

@app.get("/pacientes_por_dispositivo_uid/{uid}")
def get_paciente_por_uid(uid: str, db: Session = Depends(get_db)):
    disp = db.query(Dispositivo).filter(Dispositivo.uid_equipo == uid).first()
    if not disp:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")

    asociacion = db.query(PacienteDispositivo).filter(
        PacienteDispositivo.id_dispositivo == disp.id_dispositivo,
        PacienteDispositivo.fecha_hora_disoc == None
    ).first()

    if not asociacion:
        raise HTTPException(status_code=404, detail="Paciente no asociado")

    paciente = db.query(Paciente).filter(
        Paciente.id_paciente == asociacion.id_paciente
    ).first()

    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    return {
        "id_paciente": paciente.id_paciente,
        "nombre": paciente.nombre,
        "apellido": paciente.apellido,
        "sexo": paciente.sexo,
        "diagnostico": paciente.diagnostico,
    }

# ======================================================
# ENDPOINTS HISTÓRICOS PARA FRONTEND   de aca para abajo falta el front para probar solo lo hice para ir probando en forma aislada
# ======================================================

from fastapi import Query

# --------- HISTORICO SENSORES GENERALES (SpO2, Temp, Pulso, PNI) ---------
@app.get("/historico/{uid_equipo}/{sensor}")
def historico_sensor(
    uid_equipo: str,
    sensor: str,
    fecha: Optional[str] = Query(None, description="Formato YYYY-MM-DD"),
    db: Session = Depends(get_db)
):
    """
    Devuelve valores históricos de un sensor (spo2, temp, pulso, pni)
    Puede filtrar por día.
    """
    disp = db.query(Dispositivo).filter(Dispositivo.uid_equipo == uid_equipo).first()
    if not disp:
        raise HTTPException(status_code=404, detail="Dispositivo no existe")

    q = db.query(LecturaGeneral).filter(
        LecturaGeneral.id_dispositivo == disp.id_dispositivo,
        LecturaGeneral.tipo_sensor == sensor
    )

    if fecha:
        inicio = datetime.datetime.fromisoformat(fecha)
        fin = inicio + datetime.timedelta(days=1)
        q = q.filter(LecturaGeneral.fecha_hora >= inicio,
                     LecturaGeneral.fecha_hora < fin)

    datos = [{
        "timestamp": lec.fecha_hora.isoformat(),
        "valor": float(lec.valor_numerico)
    } for lec in q.order_by(LecturaGeneral.fecha_hora.asc()).all()]

    return {"uid": uid_equipo, "sensor": sensor, "datos": datos}


# --------- HISTÓRICO ECG (CRUDO Y FILTRADO) ---------
from fastapi.responses import StreamingResponse
import io
import matplotlib.pyplot as plt

@app.get("/ecg/imagen_10s/{uid}")
def ecg_10s_imagen(uid: str, db: Session = Depends(get_db)):

    # Buscar últimos 10 segundos (asumo bloques de ECG continuos)
    ecg_blocks = (
        db.query(ECG)
        .join(Dispositivo, Dispositivo.id_dispositivo == ECG.id_dispositivo)
        .filter(Dispositivo.uid_equipo == uid)
        .order_by(ECG.fecha_inicio.desc())
        .limit(1)
        .all()
    )

    if not ecg_blocks:
        raise HTTPException(status_code=404, detail="No hay datos ECG")

    ecg = ecg_blocks[0]
    data = np.array(ecg.valor, dtype=float)  # señal cruda
    fs = ecg.frecuencia_muestreo

    # Crear figura
    plt.figure(figsize=(10, 3))   # más chica y liviana
    t = np.arange(len(data)) / fs

    plt.plot(t, data, linewidth=0.8)
    plt.title("ECG - Últimos 10 segundos")
    plt.xlabel("Tiempo (s)")
    plt.ylabel("mV")
    plt.grid(True)

    # Convertir a PNG
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=100)
    plt.close()
    buf.seek(0)

    return StreamingResponse(buf, media_type="image/png")

@app.get("/historico_ecg/{uid_equipo}")
def historico_ecg(
    uid_equipo: str,
    fecha: Optional[str] = Query(None, description="YYYY-MM-DD"),
    db: Session = Depends(get_db)
):
    disp = db.query(Dispositivo).filter(Dispositivo.uid_equipo == uid_equipo).first()
    if not disp:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")

    q = db.query(ECG).filter(ECG.id_dispositivo == disp.id_dispositivo)

    if fecha:
        inicio = datetime.datetime.fromisoformat(fecha)
        fin = inicio + datetime.timedelta(days=1)
        q = q.filter(ECG.fecha_inicio >= inicio, ECG.fecha_inicio < fin)

    bloques = q.order_by(ECG.fecha_inicio.asc()).all()

    respuesta = []
    for b in bloques:
        raw = [float(x) for x in b.valor]
        fs = b.frecuencia_muestreo
        filtrada = ecg_filter_realtime(raw, fs, uid_equipo).tolist()

        respuesta.append({
            "timestamp": b.fecha_inicio.isoformat(),
            "fs": fs,
            "sample_number": b.sample_number,
            "raw": raw,
            "filtered": filtrada
        })

    return {"uid": uid_equipo, "ecg": respuesta}
@app.get("/historico_ecg_segmentado/{uid}")
def historico_ecg_segmentado(uid: str, t0: float, t1: float, db: Session = Depends(get_db)):
    """
    Devuelve solo un segmento de ECG entre timestamps t0 y t1.
    t0 y t1 son tiempos UNIX en segundos.
    """

    disp = db.query(Dispositivo).filter_by(uid_equipo=uid).first()
    if not disp:
        return {"ecg": []}

    q = db.query(ECG).filter(
        ECG.id_dispositivo == disp.id_dispositivo,
        ECG.fecha_inicio >= datetime.datetime.fromtimestamp(t0),
        ECG.fecha_inicio <= datetime.datetime.fromtimestamp(t1)
    ).order_by(ECG.fecha_inicio.asc())

    bloques = q.all()

    datos = []
    for b in bloques:
        datos.extend([float(x) for x in b.valor])  # Señal cruda únicamente

    return {
        "t0": t0,
        "t1": t1,
        "values": datos
    }

