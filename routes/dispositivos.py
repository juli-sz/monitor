from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from database import get_db
from typing import List

# Modelos (Base de datos)
from models import Dispositivo, Paciente, PacienteDispositivo

# Schemas (Validación)
from schemas.dispositivo import DispositivoCreate, DispositivoUpdate, DispositivoResponse

router = APIRouter(prefix="/dispositivos", tags=["Dispositivos"])

# ======================================================
# GET: Listar todos los dispositivos y a quién están conectados
# ======================================================
@router.get("/", response_model=List[DispositivoResponse])
def listar_dispositivos(db: Session = Depends(get_db)):
    dispositivos = db.query(Dispositivo).all()
    resultado = []
    
    for disp in dispositivos:
        # Buscamos si el equipo está conectado a alguien ahora mismo
        asoc_activa = db.query(PacienteDispositivo).filter(
            PacienteDispositivo.id_dispositivo == disp.id_dispositivo,
            PacienteDispositivo.fecha_hora_disoc == None
        ).first()
        
        nombre_paciente = "Sin asignar"
        
        # Si está conectado, buscamos el nombre del paciente por su ID
        if asoc_activa:
            paciente = db.query(Paciente).filter(Paciente.id_paciente == asoc_activa.id_paciente).first()
            if paciente:
                nombre_paciente = f"{paciente.nombre} {paciente.apellido}"
        
        # Armamos la respuesta para la tabla (SIN nombre_dispositivo)
        resultado.append({
            "id_dispositivo": disp.id_dispositivo,
            "uid_equipo": disp.uid_equipo,
            "estado": disp.estado,
            "paciente_asignado": nombre_paciente,
            "id_paciente": asoc_activa.id_paciente if asoc_activa else None
        })
        
    return resultado

# ======================================================
# POST: Crear Dispositivo (y asociarlo si viene con paciente)
# ======================================================
@router.post("/", response_model=DispositivoResponse)
def crear_dispositivo(disp_in: DispositivoCreate, db: Session = Depends(get_db)):
    nuevo_disp = Dispositivo(
        uid_equipo=disp_in.uid_equipo,
        estado=disp_in.estado
    )
    db.add(nuevo_disp)
    db.commit()
    db.refresh(nuevo_disp)

    id_paciente_asignado = None

    # Si nos mandaron un paciente desde el modal, creamos el vínculo
    if getattr(disp_in, 'id_paciente', None):
        nueva_asoc = PacienteDispositivo(id_paciente=disp_in.id_paciente, id_dispositivo=nuevo_disp.id_dispositivo)
        db.add(nueva_asoc)
        db.commit()
        id_paciente_asignado = disp_in.id_paciente

    return {
        "id_dispositivo": nuevo_disp.id_dispositivo, 
        "uid_equipo": nuevo_disp.uid_equipo, 
        "estado": nuevo_disp.estado,
        "id_paciente": id_paciente_asignado,
        "paciente_asignado": "Sin asignar" # Visualmente, al crearlo recién, delegamos el nombre hasta recargar
    }

# ======================================================
# PATCH: Actualizar Dispositivo y Vínculo con Paciente
# ======================================================
@router.patch("/{id_dispositivo}")
def actualizar_dispositivo(id_dispositivo: int, disp_in: DispositivoUpdate, db: Session = Depends(get_db)):
    db_disp = db.query(Dispositivo).filter(Dispositivo.id_dispositivo == id_dispositivo).first()
    if not db_disp:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")

    update_data = disp_in.model_dump(exclude_unset=True)
    
    # Separamos el id_paciente porque no va en la tabla base 'Dispositivo'
    nuevo_id_paciente = update_data.pop("id_paciente", -1) 
    
    # Por las dudas, si el frontend manda un "nombre_dispositivo" fantasma, lo borramos antes de actualizar
    update_data.pop("nombre_dispositivo", None)

    # Actualizamos los datos físicos del equipo (ej: su estado o UID)
    for key, value in update_data.items():
        setattr(db_disp, key, value)

    # Lógica del historial de conexión a pacientes
    if nuevo_id_paciente != -1:
        # Buscamos a quién está conectado AHORA MISMO
        asoc_activa = db.query(PacienteDispositivo).filter(
            PacienteDispositivo.id_dispositivo == id_dispositivo,
            PacienteDispositivo.fecha_hora_disoc == None
        ).first()

        if asoc_activa:
            # Si el paciente cambió o lo desvincularon (nuevo_id_paciente = None)
            if asoc_activa.id_paciente != nuevo_id_paciente:
                asoc_activa.fecha_hora_disoc = func.now() # "Cerramos" la sesión vieja poniendo fecha de fin
                
                # Si seleccionaron un paciente nuevo, creamos la sesión nueva
                if nuevo_id_paciente is not None:
                    nueva_asoc = PacienteDispositivo(id_paciente=nuevo_id_paciente, id_dispositivo=id_dispositivo)
                    db.add(nueva_asoc)
        else:
            # Si estaba suelto (no asociado a nadie) y le asignaron un paciente
            if nuevo_id_paciente is not None:
                nueva_asoc = PacienteDispositivo(id_paciente=nuevo_id_paciente, id_dispositivo=id_dispositivo)
                db.add(nueva_asoc)

    db.commit()
    return {"mensaje": "Equipo y conexión actualizados correctamente"}

# ======================================================
# DELETE: Eliminar Dispositivo
# ======================================================
@router.delete("/{id_dispositivo}")
def eliminar_dispositivo(id_dispositivo: int, db: Session = Depends(get_db)):
    db_disp = db.query(Dispositivo).filter(Dispositivo.id_dispositivo == id_dispositivo).first()
    if not db_disp:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    
    # Si borramos el dispositivo, los registros de 'paciente_dispositivo' 
    # se borran solos si pusimos cascade="all, delete" en los models.
    db.delete(db_disp)
    db.commit()
    return {"mensaje": "Dispositivo eliminado correctamente"}