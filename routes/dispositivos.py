from fastapi import APIRouter, HTTPException, Depends, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from typing import List, Optional

from database import get_db
from models import Dispositivo, PacienteDispositivo
from schemas.dispositivo import DispositivoCreate, DispositivoUpdate, DispositivoResponse

router = APIRouter(prefix="/dispositivos", tags=["Dispositivos"])

# ======================================================
# POST: Crear un nuevo dispositivo
# ======================================================
@router.post("/", response_model=DispositivoResponse, status_code=status.HTTP_201_CREATED)
def crear_dispositivo(dispositivo_in: DispositivoCreate, db: Session = Depends(get_db)):
    # Validación extra: El uid_equipo debe ser único
    existe = db.query(Dispositivo).filter(Dispositivo.uid_equipo == dispositivo_in.uid_equipo).first()
    if existe:
        raise HTTPException(status_code=400, detail="Ya existe un dispositivo con ese UID")

    nuevo_dispositivo = Dispositivo(**dispositivo_in.model_dump())
    db.add(nuevo_dispositivo)
    db.commit()
    db.refresh(nuevo_dispositivo)
    return nuevo_dispositivo

# ======================================================
# GET: Obtener lista con FILTROS, BÚSQUEDA y PAGINACIÓN
# ======================================================
@router.get("/", response_model=List[DispositivoResponse])
def listar_dispositivos(
    skip: int = Query(0, ge=0, description="Registros a omitir"),
    limit: int = Query(100, le=1000, description="Límite de registros a devolver"),
    estado: Optional[str] = Query(None, description="Filtrar por estado exacto (ej: Activo)"),
    uid_equipo: Optional[str] = Query(None, description="Búsqueda parcial del UID"),
    db: Session = Depends(get_db)
):
    # 1. Iniciamos la consulta base con tus filtros
    query = db.query(Dispositivo)
    if estado:
        query = query.filter(Dispositivo.estado == estado)
    if uid_equipo:
        query = query.filter(Dispositivo.uid_equipo.ilike(f"%{uid_equipo}%"))

    # Aplicamos paginación
    dispositivos_db = query.offset(skip).limit(limit).all()
    resultado = []

    # 2. Le adjuntamos el paciente activo a cada dispositivo
    for disp in dispositivos_db:
        asoc_activa = db.query(PacienteDispositivo).filter(
            PacienteDispositivo.id_dispositivo == disp.id_dispositivo,
            PacienteDispositivo.fecha_hora_disoc == None
        ).first()

        disp_dict = {
            "id_dispositivo": disp.id_dispositivo,
            "uid_equipo": disp.uid_equipo,
            "estado": disp.estado,
            "creado_en": disp.creado_en,           # <-- AGREGAR ESTO
            "actualizado_en": disp.actualizado_en, # <-- AGREGAR ESTO
            "id_paciente": None,
            "paciente": None
        }

        if asoc_activa and asoc_activa.paciente:
            disp_dict["id_paciente"] = asoc_activa.id_paciente
            disp_dict["paciente"] = {
                "id_paciente": asoc_activa.paciente.id_paciente,
                "nombre": asoc_activa.paciente.nombre,
                "apellido": asoc_activa.paciente.apellido,
                # "dni": asoc_activa.paciente.dni
            }
            
        resultado.append(disp_dict)

    return resultado

# ======================================================
# GET: Obtener detalle de un dispositivo específico
# ======================================================
@router.get("/{id_dispositivo}", response_model=DispositivoResponse)
def obtener_dispositivo(id_dispositivo: int, db: Session = Depends(get_db)):
    dispositivo = db.query(Dispositivo).filter(Dispositivo.id_dispositivo == id_dispositivo).first()
    if not dispositivo:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    return dispositivo

# ======================================================
# PUT: Reemplazar un dispositivo completo
# ======================================================
@router.put("/{id_dispositivo}", response_model=DispositivoResponse)
def actualizar_dispositivo_completo(id_dispositivo: int, dispositivo_in: DispositivoCreate, db: Session = Depends(get_db)):
    dispositivo = db.query(Dispositivo).filter(Dispositivo.id_dispositivo == id_dispositivo).first()
    if not dispositivo:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")

    # Chequear que si cambió el UID, no pise uno existente
    if dispositivo.uid_equipo != dispositivo_in.uid_equipo:
        existe = db.query(Dispositivo).filter(Dispositivo.uid_equipo == dispositivo_in.uid_equipo).first()
        if existe:
            raise HTTPException(status_code=400, detail="El nuevo UID ya está en uso")

    for field, value in dispositivo_in.model_dump().items():
        setattr(dispositivo, field, value)

    db.commit()
    db.refresh(dispositivo)
    return dispositivo

# ======================================================
# PATCH: Actualizar parcialmente (Ideal para cambiar solo el estado)
# ======================================================
@router.patch("/{id_dispositivo}")
def actualizar_dispositivo_parcial(id_dispositivo: int, dispositivo_in: DispositivoUpdate, db: Session = Depends(get_db)):
    dispositivo = db.query(Dispositivo).filter(Dispositivo.id_dispositivo == id_dispositivo).first()
    if not dispositivo:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")

    update_data = dispositivo_in.model_dump(exclude_unset=True)
    
    # 1. Validación de UID (Tu lógica original)
    if "uid_equipo" in update_data and update_data["uid_equipo"] != dispositivo.uid_equipo:
        existe = db.query(Dispositivo).filter(Dispositivo.uid_equipo == update_data["uid_equipo"]).first()
        if existe:
            raise HTTPException(status_code=400, detail="El nuevo UID ya está en uso")

    # 2. Actualizar campos básicos
    if "uid_equipo" in update_data:
        dispositivo.uid_equipo = update_data["uid_equipo"]
    if "estado" in update_data:
        dispositivo.estado = update_data["estado"]

    # 3. Lógica de asociación con la tabla PacienteDispositivo
    if "id_paciente" in update_data:
        nuevo_id_paciente = update_data["id_paciente"]

        # Buscar si hay alguna asociación ACTIVA y cerrarla
        asociacion_activa = db.query(PacienteDispositivo).filter(
            PacienteDispositivo.id_dispositivo == id_dispositivo,
            PacienteDispositivo.fecha_hora_disoc == None
        ).first()

        if asociacion_activa and asociacion_activa.id_paciente != nuevo_id_paciente:
            asociacion_activa.fecha_hora_disoc = func.now()

        # Crear o reactivar la nueva asociación
        if nuevo_id_paciente is not None:
            asoc_historica = db.query(PacienteDispositivo).filter_by(
                id_paciente=nuevo_id_paciente, 
                id_dispositivo=id_dispositivo
            ).first()

            if asoc_historica:
                asoc_historica.fecha_hora_disoc = None
                asoc_historica.fecha_hora_asoc = func.now()
            else:
                nueva_asociacion = PacienteDispositivo(
                    id_paciente=nuevo_id_paciente,
                    id_dispositivo=id_dispositivo
                )
                db.add(nueva_asociacion)

    db.commit()
    return {"mensaje": "Dispositivo actualizado con éxito"}

# ======================================================
# DELETE: Eliminar un dispositivo
# ======================================================
@router.delete("/{id_dispositivo}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_dispositivo(id_dispositivo: int, db: Session = Depends(get_db)):
    dispositivo = db.query(Dispositivo).filter(Dispositivo.id_dispositivo == id_dispositivo).first()
    if not dispositivo:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")

    db.delete(dispositivo)
    db.commit()
    return None