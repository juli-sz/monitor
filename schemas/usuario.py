from pydantic import BaseModel, EmailStr
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

class UsuarioResponse(BaseModel):
    id_usuario: int
    nombre: str
    email: str
    rol: str
    activo: bool

    class Config:
        from_attributes = True