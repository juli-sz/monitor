# schemas/usuario.py
from pydantic import BaseModel, EmailStr, Field

class UsuarioCrear(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    nombre: str
    rol: str = Field(..., pattern="^(admin|medico|enfermero|visor)$")

class UsuarioLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    rol: str
    nombre: str