from pydantic import BaseModel
from typing import Optional

class DispositivoBase(BaseModel):
    uid_equipo: str
    nombre_dispositivo: Optional[str] = None
    estado: str = "Activo"

class DispositivoCreate(DispositivoBase):
    id_paciente: Optional[int] = None  # Agregado para recibir el paciente

class DispositivoUpdate(BaseModel):
    uid_equipo: Optional[str] = None
    nombre_dispositivo: Optional[str] = None
    estado: Optional[str] = None
    id_paciente: Optional[int] = None  # Agregado para recibir el paciente

class DispositivoResponse(DispositivoBase):
    id_dispositivo: int
    paciente_asignado: Optional[str] = "Sin asignar"
    id_paciente: Optional[int] = None  # Agregado para que el modal sepa quién está seleccionado

    class Config:
        from_attributes = True