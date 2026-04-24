# routers/pacientes.py
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import Dispositivo, PacienteDispositivo, Paciente

# Creamos el router. Le podemos poner un "tag" para que en la doc de Swagger se vea ordenado.
router = APIRouter(tags=["Pacientes"])

@router.get("/pacientes_por_dispositivo_uid/{uid}")
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