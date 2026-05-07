from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.sql import func  # <-- Importamos func para la hora
from database import get_db
from models import Alerta, Dispositivo, PacienteDispositivo
from schemas.alerta import AlertaCreate
from typing import Optional

router = APIRouter(prefix="/alertas", tags=["Alertas"])
    
# ======================================================
# POST: Registrar nueva alarma desde el monitor (MQTT)
# ======================================================
@router.post("/")
def registrar_alerta(alerta_in: AlertaCreate, db: Session = Depends(get_db)):
    disp = db.query(Dispositivo).filter(Dispositivo.uid_equipo == alerta_in.uid_equipo).first()
    if not disp:
        return {"error": "Equipo no encontrado"}

    # Buscamos si alguien está conectado a ese equipo AHORA MISMO
    asoc_activa = db.query(PacienteDispositivo).filter(
        PacienteDispositivo.id_dispositivo == disp.id_dispositivo,
        PacienteDispositivo.fecha_hora_disoc == None
    ).first()
    
    # Extraemos el ID del paciente (si es que hay uno conectado)
    id_paciente_actual = asoc_activa.id_paciente if asoc_activa else None

    nueva_alerta = Alerta(
        id_dispositivo=disp.id_dispositivo,
        id_paciente=id_paciente_actual,
        descripcion=f"Alarma de {alerta_in.sensor.upper()}: Valor detectado {alerta_in.valor}",
        estado="ACTIVA"
    )
    
    db.add(nueva_alerta)
    db.commit()
    
    return {"mensaje": "Alerta registrada"}

# ======================================================
# GET: Obtener todas las alertas (con filtro opcional por estado)
# ======================================================
@router.get("/")
def obtener_todas_las_alertas(estado: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Alerta)
    
    if estado:
        query = query.filter(Alerta.estado == estado)
        
    # Las ordenamos de más recientes a más antiguas
    alertas_db = query.order_by(Alerta.fecha_hora.desc()).all()
    
    # Devolvemos los datos en un formato diccionario limpio que el frontend pueda leer bien
    resultado = []
    for a in alertas_db:
        resultado.append({
            "id_alerta": a.id_alerta,
            "id_dispositivo": a.id_dispositivo,
            "id_paciente": a.id_paciente,
            "descripcion": a.descripcion,
            "estado": a.estado,
            "fecha_hora": a.fecha_hora.isoformat() if a.fecha_hora else None
        })
        
    return resultado


# ======================================================
# PATCH: Resolver todas las alarmas de un paciente manualmente
# ======================================================
# Buscá esta función en routes/alertas.py y dejala así:

@router.patch("/resolver/paciente/{id_paciente}")
def resolver_alarmas_paciente(id_paciente: int, db: Session = Depends(get_db)):
    alertas = db.query(Alerta).filter(
        Alerta.id_paciente == id_paciente, 
        Alerta.estado == "ACTIVA"
    ).all()
    
    for a in alertas:
        a.estado = "RESUELTA"
        a.resuelta_en = func.now()
        
    db.commit()
    return {"mensaje": f"{len(alertas)} alarmas resueltas"}
# ======================================================
# GET: Obtener historial de alertas de un paciente
# ======================================================
@router.get("/paciente/{id_paciente}")
def obtener_alertas_paciente(id_paciente: int, db: Session = Depends(get_db)):
    alertas_db = db.query(Alerta).filter(
        Alerta.id_paciente == id_paciente
    ).order_by(Alerta.fecha_hora.desc()).all()

    resultado = []
    for a in alertas_db:
        resultado.append({
            "id_alerta": a.id_alerta,
            "id_dispositivo": a.id_dispositivo,
            "id_paciente": a.id_paciente,
            "descripcion": a.descripcion,
            "estado": a.estado,
            "fecha_hora": a.fecha_hora.isoformat() if a.fecha_hora else None,
            "resuelta_en": a.resuelta_en.isoformat() if a.resuelta_en else None
        })

    return resultado