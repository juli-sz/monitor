# tests/test_usuarios.py
# Gestión de usuarios: /usuarios (todo el router exige rol admin)

import models
from services.auth_service import verificar_password


def test_listar_usuarios_vacio(client, admin_headers):
    # "Vacío" salvo el propio usuario admin usado para autenticar la request
    resp = client.get("/usuarios/", headers=admin_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_listar_usuarios_no_expone_password(client, crear_usuario, admin_headers):
    crear_usuario(email="lista@test.com")
    resp = client.get("/usuarios/", headers=admin_headers)
    data = resp.json()
    # El admin de la fixture también aparece en el listado
    creado = next(u for u in data if u["email"] == "lista@test.com")
    assert "password" not in creado
    assert "password_hash" not in creado


def test_crear_usuario_ok(client, db, admin_headers):
    resp = client.post("/usuarios/", headers=admin_headers, json={
        "nombre": "Enfermero Uno",
        "email": "enf1@test.com",
        "password": "clave123",
        "rol": "enfermero",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "enf1@test.com"
    assert data["activo"] is True
    assert "password" not in data

    usuario = db.query(models.Usuario).filter(models.Usuario.email == "enf1@test.com").one()
    # El hash guardado es compatible con el login (services/auth_service)
    assert verificar_password("clave123", usuario.password_hash)


def test_crear_usuario_email_duplicado_400(client, crear_usuario, admin_headers):
    crear_usuario(email="dup@test.com")
    resp = client.post("/usuarios/", headers=admin_headers, json={
        "nombre": "Dup",
        "email": "dup@test.com",
        "password": "clave123",
        "rol": "visor",
    })
    assert resp.status_code == 400


def test_crear_usuario_rol_invalido_400(client, admin_headers):
    resp = client.post("/usuarios/", headers=admin_headers, json={
        "nombre": "Hacker",
        "email": "hacker@test.com",
        "password": "clave123",
        "rol": "superadmin",  # no está en la lista permitida
    })
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Rol inválido"


def test_crear_usuario_email_invalido_422(client, admin_headers):
    resp = client.post("/usuarios/", headers=admin_headers, json={
        "nombre": "X",
        "email": "no-es-email",
        "password": "clave123",
        "rol": "visor",
    })
    assert resp.status_code == 422


def test_toggle_estado_usuario(client, crear_usuario, db, admin_headers):
    usuario = crear_usuario(email="toggle@test.com", activo=True)

    # Baja
    resp = client.patch(f"/usuarios/{usuario.id_usuario}/estado", headers=admin_headers)
    assert resp.status_code == 200
    db.refresh(usuario)
    assert usuario.activo is False

    # Alta de nuevo
    resp = client.patch(f"/usuarios/{usuario.id_usuario}/estado", headers=admin_headers)
    assert resp.status_code == 200
    db.refresh(usuario)
    assert usuario.activo is True


def test_toggle_estado_usuario_inexistente_404(client, admin_headers):
    resp = client.patch("/usuarios/9999/estado", headers=admin_headers)
    assert resp.status_code == 404
