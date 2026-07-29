from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional

class UsuarioCrear(BaseModel):
    nombre: str
    email: EmailStr
    password: str
    rol: str

class UsuarioLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    rol: str
    nombre: str  # login.html guarda data.nombre en localStorage; sin este campo response_model lo filtraba

class UsuarioResponse(BaseModel):
    id_usuario: int
    nombre: str
    email: str
    rol: str
    activo: bool

    model_config = ConfigDict(from_attributes=True)