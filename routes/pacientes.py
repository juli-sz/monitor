from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db

# Modelos (Base de datos)
from models import Paciente, RangoSignoVital, PacienteDispositivo

# Schemas (Validación)
from schemas.paciente import PacienteCreate, PacienteUpdate, PacienteResponse

from services.auth_service import obtener_usuario_actual
from services.permissions import requiere_rol

router = APIRouter(prefix="/pacientes", tags=["Pacientes"])

# ======================================================
# GET: Listar TODOS los pacientes (Activos e Históricos)
# ======================================================
@router.get("/", response_model=list[PacienteResponse])
def listar_pacientes(db: Session = Depends(get_db), _=Depends(obtener_usuario_actual)):
    # Los ordenamos para que los más nuevos salgan arriba
    return db.query(Paciente).order_by(Paciente.id_paciente.desc()).all()

# ======================================================
# GET: Obtener un paciente específico por ID
# ======================================================
@router.get("/{id_paciente}", response_model=PacienteResponse)
def obtener_paciente(id_paciente: int, db: Session = Depends(get_db), _=Depends(obtener_usuario_actual)):
    paciente = db.query(Paciente).filter(Paciente.id_paciente == id_paciente).first()
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    return paciente

# ======================================================
# POST: Crear un nuevo paciente (Solo Admin y Médico)
# ======================================================
@router.post("/", response_model=PacienteResponse)
def crear_paciente(
    paciente_in: PacienteCreate,
    db: Session = Depends(get_db),
    _=Depends(requiere_rol("admin", "medico")),
):
    # .model_dump() convierte el schema de pydantic en un diccionario compatible
    nuevo_paciente = Paciente(**paciente_in.model_dump())
    db.add(nuevo_paciente)
    db.commit()
    db.refresh(nuevo_paciente)
    return nuevo_paciente

# ======================================================
# PATCH: Actualizar datos de un paciente (o darle el alta) (Solo Admin y Médico)
# ======================================================
@router.patch("/{id_paciente}", response_model=PacienteResponse)
def actualizar_paciente(
    id_paciente: int,
    paciente_in: PacienteUpdate,
    db: Session = Depends(get_db),
    _=Depends(requiere_rol("admin", "medico")),
):
    db_paciente = db.query(Paciente).filter(Paciente.id_paciente == id_paciente).first()
    if not db_paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    # Solo actualizamos los campos que el frontend nos haya enviado
    update_data = paciente_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_paciente, key, value)
    
    db.commit()
    db.refresh(db_paciente)
    return db_paciente

# ======================================================
# DELETE: Eliminar un paciente y sus alarmas (Solo Admin)
# ======================================================
@router.delete("/{id_paciente}")
def eliminar_paciente(
    id_paciente: int,
    db: Session = Depends(get_db),
    _=Depends(requiere_rol("admin")),
):
    paciente = db.query(Paciente).filter(Paciente.id_paciente == id_paciente).first()
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    # 1. Borramos el historial de conexión a los monitores
    db.query(PacienteDispositivo).filter(PacienteDispositivo.id_paciente == id_paciente).delete()

    # 2. Borramos sus umbrales personalizados 
    db.query(RangoSignoVital).filter(RangoSignoVital.id_paciente == id_paciente).delete()
    
    # 3. Borramos al paciente
    db.delete(paciente)
    db.commit()
    
    return {"mensaje": "Paciente y sus configuraciones eliminados correctamente"}
