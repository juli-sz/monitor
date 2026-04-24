# routers/historico.py
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
import datetime
import io
import numpy as np

# Configuración segura para servidores sin pantalla
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt

from database import get_db
from models import Dispositivo, LecturaGeneral, ECG
from services.signal_processor import ecg_filter_realtime

router = APIRouter(tags=["Histórico y Telemetría"])

@router.get("/historico/{uid_equipo}/{sensor}")
def historico_sensor(
    uid_equipo: str, 
    sensor: str, 
    fecha: Optional[str] = Query(None, description="Formato YYYY-MM-DD"), 
    db: Session = Depends(get_db)
):
    # ... (Tu código exacto queda igual) ...
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
        q = q.filter(LecturaGeneral.fecha_hora >= inicio, LecturaGeneral.fecha_hora < fin)

    datos = [{
        "timestamp": lec.fecha_hora.isoformat(),
        "valor": float(lec.valor_numerico)
    } for lec in q.order_by(LecturaGeneral.fecha_hora.asc()).all()]

    return {"uid": uid_equipo, "sensor": sensor, "datos": datos}


@router.get("/ecg/imagen_10s/{uid}")
def ecg_10s_imagen(uid: str, db: Session = Depends(get_db)):
    # ... (Tu código exacto para generar el PNG, queda idéntico) ...
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
    data = np.array(ecg.valor, dtype=float)
    fs = ecg.frecuencia_muestreo

    plt.figure(figsize=(10, 3))
    t = np.arange(len(data)) / fs
    plt.plot(t, data, linewidth=0.8)
    plt.title("ECG - Últimos 10 segundos")
    plt.xlabel("Tiempo (s)")
    plt.ylabel("mV")
    plt.grid(True)

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=100)
    plt.close()
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")

# (Aquí abajo pegás también tus otras dos funciones: historico_ecg e historico_ecg_segmentado)
@router.get("/historico_ecg/{uid_equipo}")
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
@router.get("/historico_ecg_segmentado/{uid}")
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

