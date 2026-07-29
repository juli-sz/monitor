# tests/test_permisos.py
# Mecánica de autenticación/autorización (services/auth_service.obtener_usuario_actual
# y services/permissions.requiere_rol), independiente de cada recurso puntual.
#
# Las pruebas de "quién puede hacer qué" en cada endpoint viven junto a cada
# recurso (test_pacientes.py, test_dispositivos.py, etc.). Acá solo se cubren
# los casos transversales: sin token, token roto/expirado/de otra clave,
# usuario inactivo, y el router /usuarios (admin-only en su totalidad).

import datetime

import jwt

from services import auth_service


def test_sin_token_devuelve_401(client):
    resp = client.get("/pacientes/")
    assert resp.status_code == 401


def test_token_con_firma_invalida_devuelve_401(client):
    token = jwt.encode({"sub": "1", "exp": _exp_futuro()}, "otra-clave-distinta", algorithm=auth_service.ALGORITHM)
    resp = client.get("/pacientes/", headers=_bearer(token))
    assert resp.status_code == 401


def test_token_expirado_devuelve_401(client, crear_usuario):
    usuario = crear_usuario(email="expirado@test.com")
    token = auth_service.crear_token_acceso(
        {"sub": str(usuario.id_usuario), "rol": usuario.rol}, expira_en_minutos=-5
    )
    resp = client.get("/pacientes/", headers=_bearer(token))
    assert resp.status_code == 401


def test_token_de_usuario_inexistente_devuelve_401(client):
    token = auth_service.crear_token_acceso({"sub": "999999", "rol": "admin"})
    resp = client.get("/pacientes/", headers=_bearer(token))
    assert resp.status_code == 401


def test_token_de_usuario_inactivo_devuelve_401(client, crear_usuario):
    usuario = crear_usuario(email="inactivo@test.com", activo=False)
    token = auth_service.crear_token_acceso({"sub": str(usuario.id_usuario), "rol": usuario.rol})
    resp = client.get("/pacientes/", headers=_bearer(token))
    assert resp.status_code == 401


def test_token_malformado_devuelve_401(client):
    resp = client.get("/pacientes/", headers=_bearer("esto-no-es-un-jwt"))
    assert resp.status_code == 401


# ------------------------- /usuarios (admin-only en su totalidad) -------------------------

def test_usuarios_sin_token_401(client):
    resp = client.get("/usuarios/")
    assert resp.status_code == 401


def test_usuarios_medico_403(client, medico_headers):
    resp = client.get("/usuarios/", headers=medico_headers)
    assert resp.status_code == 403


def test_usuarios_enfermero_403(client, enfermero_headers):
    resp = client.get("/usuarios/", headers=enfermero_headers)
    assert resp.status_code == 403


def test_usuarios_visor_403(client, visor_headers):
    resp = client.get("/usuarios/", headers=visor_headers)
    assert resp.status_code == 403


def test_usuarios_admin_200(client, admin_headers):
    resp = client.get("/usuarios/", headers=admin_headers)
    assert resp.status_code == 200


# ------------------------- helpers -------------------------

def _bearer(token):
    return {"Authorization": f"Bearer {token}"}


def _exp_futuro():
    return datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)
