from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.sql import func  # <-- Importamos func para la hora
from database import get_db
from models import Alerta, Dispositivo, PacienteDispositivo
from pydantic import BaseModel

router = APIRouter(prefix="/alertas", tags=["Alertas"])

class AlertaCreate(BaseModel):
    uid_equipo: str
    sensor: str
    valor: str
    
# POST: Registrar nueva alarma desde el monitor
@router.post("/")
def registrar_alerta(alerta_in: AlertaCreate, db: Session = Depends(get_db)):
    disp = db.query(Dispositivo).filter(Dispositivo.uid_equipo == alerta_in.uid_equipo).first()
    if not disp:
        return {"error": "Equipo no encontrado"}

    asoc = db.query(PacienteDispositivo).filter_by(
        id_dispositivo=disp.id_dispositivo, 
        fecha_hora_disoc=None
    ).first()

    nueva_alerta = Alerta(
        id_dispositivo=disp.id_dispositivo,
        id_paciente=asoc.id_paciente if asoc else None,
        descripcion=f"Alarma de {alerta_in.sensor.upper()}: Valor detectado {alerta_in.valor}",
        estado="ACTIVA"
    )
    db.add(nueva_alerta)
    db.commit()
    return {"mensaje": "Alerta registrada"}
# ======================================================
# GET: Obtener el historial de alarmas
# ======================================================
@router.get("/")
def listar_alertas(db: Session = Depends(get_db)):
    # Traemos las últimas 50 alarmas, ordenadas por la fecha_hora
    alertas_db = db.query(Alerta).order_by(Alerta.fecha_hora.desc()).limit(50).all()
    
    resultado = []
    for a in alertas_db:
        # Buscamos el nombre del paciente asociado (si lo hay)
        paciente_nombre = "Desconocido"
        if a.paciente_rel:
            paciente_nombre = f"{a.paciente_rel.nombre} {a.paciente_rel.apellido}"
            
        resultado.append({
            "id": a.id_alerta,
            "paciente": paciente_nombre,
            # Como la info está junta en 'descripcion', la acomodamos así para el frontend:
            "sensor": "Sistema", 
            "valor": a.descripcion, 
            "estado": a.estado,
            "fecha": a.fecha_hora.strftime("%H:%M:%S - %d/%m/%Y") if a.fecha_hora else "Sin fecha"
        })
        
    return resultado

# ======================================================
# PATCH: Marcar una alarma como RESUELTA
# ======================================================
@router.patch("/{id_alerta}/resolver")
def resolver_alarma(id_alerta: int, db: Session = Depends(get_db)):
    alarma = db.query(Alerta).filter(Alerta.id_alerta == id_alerta).first()
    
    if not alarma:
        raise HTTPException(status_code=404, detail="Alarma no encontrada")
        
    # Actualizamos el estado y marcamos la hora exacta en que se resolvió
    alarma.estado = "RESUELTA"
    alarma.resuelta_en = func.now() 
    
    db.commit()
    
    return {"mensaje": "Alarma marcada como resuelta"}