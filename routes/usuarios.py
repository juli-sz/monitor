from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, ConfigDict
from database import get_db
from models import Usuario
from services.auth_service import hashear_password
from services.permissions import requiere_rol, ROLES_VALIDOS

# Gestión de usuarios: solo admin (ver README, "Admin: CRUD total (usuarios, ...)").
router = APIRouter(
    prefix="/usuarios",
    tags=["Usuarios"],
    dependencies=[Depends(requiere_rol("admin"))],
)

# ======================================================
# ESQUEMAS (PYDANTIC)
# ======================================================
class UsuarioCreate(BaseModel):
    nombre: str
    email: EmailStr
    password: str
    rol: str # 'admin', 'medico', 'enfermero', 'visor'

class UsuarioResponse(BaseModel):
    id_usuario: int
    nombre: str
    email: str
    rol: str
    activo: bool

    model_config = ConfigDict(from_attributes=True)

# ======================================================
# GET: Listar todos los usuarios
# ======================================================
@router.get("/", response_model=list[UsuarioResponse])
def listar_usuarios(db: Session = Depends(get_db)):
    return db.query(Usuario).order_by(Usuario.id_usuario.desc()).all()

# ======================================================
# POST: Crear un nuevo usuario
# ======================================================
@router.post("/", response_model=UsuarioResponse)
def crear_usuario(usuario_in: UsuarioCreate, db: Session = Depends(get_db)):
    # 1. Verificamos que el email no esté repetido
    existe = db.query(Usuario).filter(Usuario.email == usuario_in.email).first()
    if existe:
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    
    # 2. Validamos que el rol sea uno de los permitidos por tu base de datos
    if usuario_in.rol not in ROLES_VALIDOS:
        raise HTTPException(status_code=400, detail="Rol inválido")

    # 3. Encriptamos la contraseña
    hashed_password = hashear_password(usuario_in.password)
    
    # 4. Guardamos en la base
    nuevo_usuario = Usuario(
        nombre=usuario_in.nombre,
        email=usuario_in.email,
        password_hash=hashed_password,
        rol=usuario_in.rol
    )
    
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    
    return nuevo_usuario

# ======================================================
# PATCH: Dar de baja/alta un usuario (Toggle Activo)
# ======================================================
@router.patch("/{id_usuario}/estado")
def cambiar_estado_usuario(id_usuario: int, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.id_usuario == id_usuario).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Invertimos el estado actual (Si era True pasa a False, y viceversa)
    usuario.activo = not usuario.activo 
    db.commit()
    
    estado_texto = "Activo" if usuario.activo else "Inactivo (Baja)"
    return {"mensaje": f"El estado del usuario ahora es: {estado_texto}"}