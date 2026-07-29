import bcrypt
import jwt
import datetime
import os

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from database import get_db
from models import Usuario

# Clave secreta para firmar los tokens
SECRET_KEY = os.getenv("SECRET_KEY", "super_secreto_desarrollo")
ALGORITHM = "HS256"

# tokenUrl es solo informativo para el botón "Authorize" de Swagger;
# auto_error=False para poder devolver nuestro propio 401 con mensaje en español.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)

def hashear_password(password: str) -> str:
    # bcrypt requiere que la contraseña sea convertida a bytes antes de hashearla
    password_bytes = password.encode('utf-8')
    # Genera una "sal" aleatoria y hashea la contraseña
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password_bytes, salt)
    # Devuelve el hash como un string normal para guardarlo en la base de datos
    return hashed_password.decode('utf-8')

def verificar_password(plain_password: str, hashed_password: str) -> bool:
    # Convertimos ambos a bytes para que bcrypt pueda compararlos
    password_bytes = plain_password.encode('utf-8')
    hashed_password_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_password_bytes)

def crear_token_acceso(data: dict, expira_en_minutos: int = 1440): # 24 horas
    a_encriptar = data.copy()
    expiracion = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=expira_en_minutos)
    a_encriptar.update({"exp": expiracion})

    token_jwt = jwt.encode(a_encriptar, SECRET_KEY, algorithm=ALGORITHM)
    return token_jwt


def obtener_usuario_actual(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    """Dependencia FastAPI: valida el JWT del header Authorization y devuelve el Usuario logueado.

    Se usa como `Depends(obtener_usuario_actual)` en cualquier endpoint que deba
    exigir sesión iniciada (sin importar el rol). Para restringir por rol, ver
    `services.permissions.requiere_rol`.
    """
    error_credenciales = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No autenticado. Iniciá sesión nuevamente.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        raise error_credenciales

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        raise error_credenciales

    id_usuario = payload.get("sub")
    if id_usuario is None:
        raise error_credenciales

    try:
        id_usuario = int(id_usuario)
    except (TypeError, ValueError):
        raise error_credenciales

    usuario = db.query(Usuario).filter(Usuario.id_usuario == id_usuario).first()
    if not usuario or not usuario.activo:
        raise error_credenciales

    return usuario