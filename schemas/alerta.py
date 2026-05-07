from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class AlertaBase(BaseModel):
    descripcion: str
    estado: str = "ACTIVA"

class AlertaCreate(BaseModel):
    uid_equipo: str
    sensor: str
    valor: str

class AlertaResponse(AlertaBase):
    id_alerta: int
    id_paciente: Optional[int]
    id_dispositivo: Optional[int]
    fecha_hora: datetime
    resuelta_en: Optional[datetime]

    class Config:
        from_attributes = True