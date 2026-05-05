# routers/pacientes.py
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import Dispositivo, PacienteDispositivo, Paciente
from schemas.paciente import PacienteCreate, PacienteUpdate, PacienteResponse

# Creamos el router. Le podemos poner un "tag" para que en la doc de Swagger se vea ordenado.
router = APIRouter(prefix="/pacientes", tags=["Pacientes"])

# ======================================================
# POST: Crear un nuevo paciente
# ======================================================
@router.post("/", response_model=PacienteResponse, status_code=status.HTTP_201_CREATED)
def crear_paciente(paciente_in: PacienteCreate, db: Session = Depends(get_db)):
    # Desempaquetamos el diccionario validado por Pydantic
    nuevo_paciente = Paciente(**paciente_in.model_dump())
    db.add(nuevo_paciente)
    db.commit()
    db.refresh(nuevo_paciente)
    return nuevo_paciente

# ======================================================
# GET: Obtener lista de pacientes (con paginación básica)
# ======================================================
@router.get("/", response_model=List[PacienteResponse])
def listar_pacientes(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    pacientes = db.query(Paciente).offset(skip).limit(limit).all()
    return pacientes

# ======================================================
# GET: Obtener detalle de un paciente específico
# ======================================================
@router.get("/{id_paciente}", response_model=PacienteResponse)
def obtener_paciente(id_paciente: int, db: Session = Depends(get_db)):
    paciente = db.query(Paciente).filter(Paciente.id_paciente == id_paciente).first()
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    return paciente

# ======================================================
# PUT: Reemplazar un paciente completo
# ======================================================
@router.put("/{id_paciente}", response_model=PacienteResponse)
def actualizar_paciente_completo(id_paciente: int, paciente_in: PacienteCreate, db: Session = Depends(get_db)):
    paciente = db.query(Paciente).filter(Paciente.id_paciente == id_paciente).first()
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    # Actualizamos todos los campos
    for field, value in paciente_in.model_dump().items():
        setattr(paciente, field, value)

    db.commit()
    db.refresh(paciente)
    return paciente

# ======================================================
# PATCH: Actualizar parcialmente un paciente
# ======================================================
@router.patch("/{id_paciente}", response_model=PacienteResponse)
def actualizar_paciente_parcial(id_paciente: int, paciente_in: PacienteUpdate, db: Session = Depends(get_db)):
    paciente = db.query(Paciente).filter(Paciente.id_paciente == id_paciente).first()
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    # exclude_unset=True ignora los campos que el frontend no envió en la petición
    update_data = paciente_in.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(paciente, field, value)

    db.commit()
    db.refresh(paciente)
    return paciente

# ======================================================
# DELETE: Eliminar un paciente
# ======================================================
@router.delete("/{id_paciente}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_paciente(id_paciente: int, db: Session = Depends(get_db)):
    paciente = db.query(Paciente).filter(Paciente.id_paciente == id_paciente).first()
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    # Opcional: Podrías validar si tiene dispositivos o alertas antes de borrarlo
    db.delete(paciente)
    db.commit()
    return None

# ======================================================
# (Acá abajo dejás el que ya tenías: get_paciente_por_uid)
# Solo recordá actualizar la ruta si le pusiste el prefix al router
# ======================================================
@router.get("/por_dispositivo/{uid}") # Acorté la ruta ya que el prefix es /pacientes
def get_paciente_por_uid(uid: str, db: Session = Depends(get_db)):
    disp = db.query(Dispositivo).filter(Dispositivo.uid_equipo == uid).first()
    if not disp:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")

    asociacion = db.query(PacienteDispositivo).filter(
        PacienteDispositivo.id_dispositivo == disp.id_dispositivo,
        PacienteDispositivo.fecha_hora_disoc == None
    ).first()

    if not asociacion:
        raise HTTPException(status_code=404, detail="Dispositivo sin paciente")

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
    
