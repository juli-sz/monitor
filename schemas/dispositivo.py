from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime

# --- ESQUEMA AUXILIAR ---
# Creamos este esquema chiquito acá para evitar errores de importación cruzada 
# con tu archivo de schemas/paciente.py. Esto define qué datos del paciente viajarán.
class PacienteBasico(BaseModel):
    id_paciente: int
    nombre: str
    apellido: str
    # dni: str

    model_config = ConfigDict(from_attributes=True)

# 1. Esquema Base
class DispositivoBase(BaseModel):
    uid_equipo: str = Field(..., max_length=100, description="Identificador único del hardware")
    estado: Optional[str] = Field("Activo", max_length=50)

# 2. Esquema para CREAR (POST)
class DispositivoCreate(DispositivoBase):
    pass # Exige uid_equipo, el estado es opcional (por defecto "Activo")

# 3. Esquema para ACTUALIZAR (PATCH / PUT)
class DispositivoUpdate(BaseModel):
    uid_equipo: Optional[str] = Field(None, max_length=100)
    estado: Optional[str] = Field(None, max_length=50)
    # Agregamos este campo para que FastAPI permita recibir el ID desde el frontend
    id_paciente: Optional[int] = None 

# 4. Esquema de RESPUESTA
class DispositivoResponse(DispositivoBase):
    id_dispositivo: int
    id_paciente: Optional[int] = None
    # Agregamos esta relación para que viaje el nombre y apellido al frontend
    paciente: Optional[PacienteBasico] = None
    
    creado_en: Optional[datetime]
    actualizado_en: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)