from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import date, datetime

# 1. Esquema Base: Los campos comunes
class PacienteBase(BaseModel):
    nombre: str = Field(..., max_length=100)
    apellido: str = Field(..., max_length=100)
    dni: Optional[str] = None
    fecha_nacimiento: Optional[date] = None
    direccion: Optional[str] = None
    sexo: Optional[str] = Field(None, pattern="^[MF]$", description="Debe ser 'M' o 'F'")
    diagnostico: Optional[str] = None
    tipo: Optional[str] = Field(None, max_length=50)

# 2. Esquema para CREAR (POST y PUT)
class PacienteCreate(PacienteBase):
    pass # Exige nombre y apellido obligatorios, el resto opcional

# 3. Esquema para ACTUALIZAR PARCIALMENTE (PATCH)
class PacienteUpdate(BaseModel):
    nombre: Optional[str] = Field(None, max_length=100)
    apellido: Optional[str] = Field(None, max_length=100)
    fecha_nacimiento: Optional[date] = None
    direccion: Optional[str] = None
    sexo: Optional[str] = Field(None, pattern="^[MF]$")
    diagnostico: Optional[str] = None
    tipo: Optional[str] = Field(None, max_length=50)

# 4. Esquema de RESPUESTA (Lo que le enviamos al Frontend)
class PacienteResponse(PacienteBase):
    id_paciente: int
    
    creado_en: Optional[datetime]
    actualizado_en: Optional[datetime]

    # Esto le dice a Pydantic que lea desde objetos de SQLAlchemy
    model_config = ConfigDict(from_attributes=True)