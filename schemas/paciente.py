from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime

class PacienteBase(BaseModel):
    nombre: str
    apellido: str
    dni: Optional[str] = None
    fecha_nacimiento: Optional[date] = None
    sexo: Optional[str] = None
    direccion: Optional[str] = None
    tipo: Optional[str] = None
    diagnostico: Optional[str] = None
    fecha_egreso: Optional[date] = None

class PacienteCreate(PacienteBase):
    pass 

class PacienteUpdate(BaseModel):
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    dni: Optional[str] = None
    fecha_nacimiento: Optional[date] = None
    fecha_egreso: Optional[date] = None
    sexo: Optional[str] = None
    direccion: Optional[str] = None
    tipo: Optional[str] = None
    diagnostico: Optional[str] = None

class PacienteResponse(PacienteBase):
    id_paciente: int
    creado_en: datetime
    # Eliminamos cualquier referencia a 'actualizado_en'

    class Config:
        from_attributes = True