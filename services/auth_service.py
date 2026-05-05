import bcrypt
import jwt
import datetime
import os

# Clave secreta para firmar los tokens
SECRET_KEY = os.getenv("SECRET_KEY", "super_secreto_desarrollo") 
ALGORITHM = "HS256"

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