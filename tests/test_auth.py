# tests/test_auth.py
# Registro, login, contenido del JWT y helpers de services/auth_service.py

import datetime

import jwt
import pytest

import models
from services import auth_service


# ------------------------- /auth/registro -------------------------
# Bootstrap: con la base de usuarios vacía, el registro es público PERO
# solo puede crear un admin (el primer usuario del sistema). En cuanto existe
# al menos un usuario, /auth/registro exige un admin autenticado.

def test_registro_bootstrap_crea_primer_admin_sin_auth(client, db):
    resp = client.post("/auth/registro", json={
        "nombre": "Primer Admin",
        "email": "primeradmin@test.com",
        "password": "clave123",
        "rol": "admin",
    })
    assert resp.status_code == 201

    usuario = db.query(models.Usuario).one()
    assert usuario.email == "primeradmin@test.com"
    assert usuario.rol == "admin"
    # La contraseña NUNCA se guarda en texto plano
    assert usuario.password_hash != "clave123"
    assert usuario.password_hash.startswith("$2b$")


def test_registro_bootstrap_rechaza_rol_no_admin_400(client):
    """El primer usuario del sistema tiene que ser admin: no se puede
    bootstrapear directamente como medico/enfermero/visor."""
    resp = client.post("/auth/registro", json={
        "nombre": "Colado",
        "email": "colado@test.com",
        "password": "clave123",
        "rol": "medico",
    })
    assert resp.status_code == 400


def test_registro_luego_del_bootstrap_requiere_admin(client, db, admin_headers):
    """Ya con un usuario existente (el admin de la fixture), un admin autenticado
    puede seguir registrando gente con cualquier rol."""
    resp = client.post("/auth/registro", headers=admin_headers, json={
        "nombre": "Nueva Usuaria",
        "email": "nueva@test.com",
        "password": "clave123",
        "rol": "medico",
    })
    assert resp.status_code == 201

    usuario = db.query(models.Usuario).filter(models.Usuario.email == "nueva@test.com").one()
    assert usuario.rol == "medico"
    assert usuario.password_hash != "clave123"
    assert usuario.password_hash.startswith("$2b$")


def test_registro_sin_token_401_si_ya_hay_usuarios(client, crear_usuario):
    crear_usuario(email="existente@test.com")  # ya no es bootstrap
    resp = client.post("/auth/registro", json={
        "nombre": "Otra", "email": "otra@test.com", "password": "clave123", "rol": "visor",
    })
    assert resp.status_code == 401


def test_registro_no_admin_403_si_ya_hay_usuarios(client, medico_headers):
    resp = client.post("/auth/registro", headers=medico_headers, json={
        "nombre": "Otra", "email": "otra2@test.com", "password": "clave123", "rol": "visor",
    })
    assert resp.status_code == 403


def test_registro_email_duplicado_400(client, crear_usuario, admin_headers):
    crear_usuario(email="repetida@test.com")
    resp = client.post("/auth/registro", headers=admin_headers, json={
        "nombre": "Otra",
        "email": "repetida@test.com",
        "password": "clave123",
        "rol": "visor",
    })
    assert resp.status_code == 400
    assert "ya está registrado" in resp.json()["detail"]


def test_registro_email_invalido_422(client):
    """Con la base vacía (bootstrap), sigue sin hacer falta token: el 422
    de Pydantic por email inválido se dispara antes de tocar la lógica de roles."""
    resp = client.post("/auth/registro", json={
        "nombre": "X",
        "email": "esto-no-es-un-email",
        "password": "clave123",
        "rol": "admin",
    })
    assert resp.status_code == 422


# ------------------------- /auth/login -------------------------

def test_login_ok_devuelve_token_rol_y_nombre(client, crear_usuario):
    crear_usuario(email="medico@test.com", password="clave123",
                  rol="medico", nombre="Dra. Prueba")

    resp = client.post("/auth/login", json={
        "email": "medico@test.com",
        "password": "clave123",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["token_type"] == "bearer"
    assert data["rol"] == "medico"
    assert data["nombre"] == "Dra. Prueba"  # login.html lo guarda en localStorage
    assert len(data["access_token"]) > 20


def test_login_token_contiene_id_rol_y_expiracion(client, crear_usuario):
    usuario = crear_usuario(email="claims@test.com", password="clave123", rol="admin")

    resp = client.post("/auth/login", json={
        "email": "claims@test.com",
        "password": "clave123",
    })
    token = resp.json()["access_token"]

    payload = jwt.decode(
        token, auth_service.SECRET_KEY, algorithms=[auth_service.ALGORITHM]
    )
    assert payload["sub"] == str(usuario.id_usuario)
    assert payload["rol"] == "admin"

    # Expira ~24hs después de emitido
    exp = datetime.datetime.fromtimestamp(payload["exp"], tz=datetime.timezone.utc)
    ahora = datetime.datetime.now(datetime.timezone.utc)
    assert datetime.timedelta(hours=23) < (exp - ahora) <= datetime.timedelta(hours=24)


def test_login_password_incorrecta_401(client, crear_usuario):
    crear_usuario(email="user@test.com", password="correcta")
    resp = client.post("/auth/login", json={
        "email": "user@test.com",
        "password": "incorrecta",
    })
    assert resp.status_code == 401


def test_login_email_inexistente_401(client):
    resp = client.post("/auth/login", json={
        "email": "fantasma@test.com",
        "password": "loquesea",
    })
    assert resp.status_code == 401


def test_login_usuario_inactivo_403(client, crear_usuario):
    crear_usuario(email="baja@test.com", password="clave123", activo=False)
    resp = client.post("/auth/login", json={
        "email": "baja@test.com",
        "password": "clave123",
    })
    assert resp.status_code == 403
    assert "inactivo" in resp.json()["detail"].lower()


# ------------------------- auth_service (unitarios) -------------------------

def test_hashear_y_verificar_password():
    hash_ = auth_service.hashear_password("mi_clave")
    assert hash_ != "mi_clave"
    assert auth_service.verificar_password("mi_clave", hash_) is True
    assert auth_service.verificar_password("otra_clave", hash_) is False


def test_hashes_distintos_para_misma_password():
    """bcrypt usa sal aleatoria: dos hashes de la misma clave no coinciden."""
    h1 = auth_service.hashear_password("misma")
    h2 = auth_service.hashear_password("misma")
    assert h1 != h2


def test_token_expirado_es_rechazado():
    token = auth_service.crear_token_acceso({"sub": "1"}, expira_en_minutos=-5)
    with pytest.raises(jwt.ExpiredSignatureError):
        jwt.decode(token, auth_service.SECRET_KEY, algorithms=[auth_service.ALGORITHM])


def test_token_con_firma_invalida_es_rechazado():
    token = auth_service.crear_token_acceso({"sub": "1"})
    with pytest.raises(jwt.InvalidSignatureError):
        jwt.decode(token, "otra_clave_secreta", algorithms=[auth_service.ALGORITHM])
