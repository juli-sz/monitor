from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from database import get_db
from models import RangoSignoVital

from services.auth_service import obtener_usuario_actual
from services.permissions import requiere_rol

router = APIRouter(prefix="/sensores", tags=["Sensores"])

class RangoCreate(BaseModel):
    id_paciente: Optional[int] = None  # <-- AGREGAMOS ESTO
    tipo_signo: str
    valor_minimo: float
    valor_maximo: float
    unidad: str

# ======================================================
# GET: Obtener umbrales globales (id_paciente = None)
# ======================================================
@router.get("/")
def obtener_umbrales_globales(db: Session = Depends(get_db), _=Depends(obtener_usuario_actual)):
    return db.query(RangoSignoVital).filter(RangoSignoVital.id_paciente == None).all()

# ======================================================
# POST: Guardar o actualizar un umbral global (Admin y Médico)
# ======================================================
@router.post("/")
def configurar_umbral(
    rango_in: RangoCreate,
    db: Session = Depends(get_db),
    _=Depends(requiere_rol("admin", "medico")),
):
    # Buscamos si ya existe ese sensor para ESTE paciente (o a nivel global si es None)
    rango = db.query(RangoSignoVital).filter(
        RangoSignoVital.id_paciente == rango_in.id_paciente,
        RangoSignoVital.tipo_signo == rango_in.tipo_signo.lower()
    ).first()

    if rango:
        rango.valor_minimo = rango_in.valor_minimo
        rango.valor_maximo = rango_in.valor_maximo
        rango.unidad = rango_in.unidad
    else:
        nuevo_rango = RangoSignoVital(
            id_paciente=rango_in.id_paciente, # <-- Usamos el ID que manda el frontend
            tipo_signo=rango_in.tipo_signo.lower(),
            valor_minimo=rango_in.valor_minimo,
            valor_maximo=rango_in.valor_maximo,
            unidad=rango_in.unidad
        )
        db.add(nuevo_rango)
        
    db.commit()
    return {"mensaje": "Configuración guardada"}

# ======================================================
# GET: Obtener umbrales específicos de un paciente
# ======================================================
@router.get("/paciente/{id_paciente}")
def obtener_umbrales_paciente(
    id_paciente: int,
    db: Session = Depends(get_db),
    _=Depends(obtener_usuario_actual),
):
    return db.query(RangoSignoVital).filter(RangoSignoVital.id_paciente == id_paciente).all()