from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from database import get_db
from models import RangoSignoVital

router = APIRouter(prefix="/sensores", tags=["Sensores"])

class RangoCreate(BaseModel):
    tipo_signo: str
    valor_minimo: float
    valor_maximo: float
    unidad: str

# ======================================================
# GET: Obtener umbrales globales (id_paciente = None)
# ======================================================
@router.get("/")
def obtener_umbrales_globales(db: Session = Depends(get_db)):
    return db.query(RangoSignoVital).filter(RangoSignoVital.id_paciente == None).all()

# ======================================================
# POST: Guardar o actualizar un umbral global
# ======================================================
@router.post("/")
def configurar_umbral_global(rango_in: RangoCreate, db: Session = Depends(get_db)):
    # Buscamos si ya existe ese sensor a nivel global
    rango = db.query(RangoSignoVital).filter(
        RangoSignoVital.id_paciente == None,
        RangoSignoVital.tipo_signo == rango_in.tipo_signo.lower()
    ).first()

    if rango:
        # Lo actualizamos
        rango.valor_minimo = rango_in.valor_minimo
        rango.valor_maximo = rango_in.valor_maximo
        rango.unidad = rango_in.unidad
    else:
        # Lo creamos
        nuevo_rango = RangoSignoVital(
            id_paciente=None,
            tipo_signo=rango_in.tipo_signo.lower(),
            valor_minimo=rango_in.valor_minimo,
            valor_maximo=rango_in.valor_maximo,
            unidad=rango_in.unidad
        )
        db.add(nuevo_rango)
        
    db.commit()
    return {"mensaje": "Configuración guardada"}