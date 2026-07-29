# routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models import Usuario
from schemas.usuario import UsuarioCrear, UsuarioLogin, TokenResponse
from services.auth_service import (
    hashear_password,
    verificar_password,
    crear_token_acceso,
    obtener_usuario_actual,
    oauth2_scheme,
)
from services.permissions import ROLES_VALIDOS

router = APIRouter(prefix="/auth", tags=["Autenticación"])


def _autorizar_registro(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> bool:
    """Registro público SOLO para crear el primer usuario del sistema (bootstrap).
    En cuanto exista al menos un usuario, /auth/registro exige un admin autenticado
    (así se evita que cualquiera pueda auto-asignarse rol admin). Devuelve True si
    esta llamada corresponde al bootstrap (base de usuarios vacía).
    """
    if db.query(Usuario).count() == 0:
        return True

    usuario = obtener_usuario_actual(token=token, db=db)
    if usuario.rol != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tenés permisos para realizar esta acción",
        )
    return False


@router.post("/registro", status_code=status.HTTP_201_CREATED)
def registrar_usuario(
    user_in: UsuarioCrear,
    db: Session = Depends(get_db),
    es_bootstrap: bool = Depends(_autorizar_registro),
):
    # Verificamos si el email ya existe
    existe = db.query(Usuario).filter(Usuario.email == user_in.email).first()
    if existe:
        raise HTTPException(status_code=400, detail="El email ya está registrado")

    if user_in.rol not in ROLES_VALIDOS:
        raise HTTPException(status_code=400, detail="Rol inválido")

    if es_bootstrap and user_in.rol != "admin":
        raise HTTPException(
            status_code=400,
            detail="El primer usuario del sistema debe registrarse con rol 'admin'",
        )

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