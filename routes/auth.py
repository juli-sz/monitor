# routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models import Usuario
from schemas.usuario import UsuarioCrear, UsuarioLogin, TokenResponse
from services.auth_service import hashear_password, verificar_password, crear_token_acceso

router = APIRouter(prefix="/auth", tags=["Autenticación"])

@router.post("/registro", status_code=status.HTTP_201_CREATED)
def registrar_usuario(user_in: UsuarioCrear, db: Session = Depends(get_db)):
    # Verificamos si el email ya existe
    existe = db.query(Usuario).filter(Usuario.email == user_in.email).first()
    if existe:
        raise HTTPException(status_code=400, detail="El email ya está registrado")

    nuevo_usuario = Usuario(
        email=user_in.email,
        password_hash=hashear_password(user_in.password),
        nombre=user_in.nombre,
        rol=user_in.rol
    )
    db.add(nuevo_usuario)
    db.commit()
    return {"mensaje": "Usuario creado exitosamente"}

@router.post("/login", response_model=TokenResponse)
def iniciar_sesion(credenciales: UsuarioLogin, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.email == credenciales.email).first()
    
    # Validamos que el usuario exista, que la contraseña coincida y que esté activo
    if not usuario or not verificar_password(credenciales.password, usuario.password_hash):
        raise HTTPException(status_code=401, detail="Email o contraseña incorrectos")
    
    if not usuario.activo:
        raise HTTPException(status_code=403, detail="Usuario inactivo. Contacte al administrador.")

    # Generamos el pase de acceso incluyendo su ID y su Rol
    token_data = {"sub": str(usuario.id_usuario), "rol": usuario.rol}
    token = crear_token_acceso(data=token_data)

    return {
        "access_token": token,
        "token_type": "bearer",
        "rol": usuario.rol,
        "nombre": usuario.nombre
    }