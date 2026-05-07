from pydantic import BaseModel
from typing import Optional

class RangoBase(BaseModel):
    tipo_signo: str
    valor_minimo: float
    valor_maximo: float
    unidad: str

class RangoCreate(RangoBase):
    id_paciente: Optional[int] = None

class RangoResponse(RangoBase):
    id_rango: int
    id_paciente: Optional[int]

    class Config:
        from_attributes = True