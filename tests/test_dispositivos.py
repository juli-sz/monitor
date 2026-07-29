# tests/test_dispositivos.py
# CRUD de /dispositivos + lógica de asociación paciente-dispositivo
# Permisos: GET = cualquier rol logueado; POST/PATCH/DELETE = admin

import models


# ------------------------- POST -------------------------

def test_crear_dispositivo_simple(client, admin_headers):
    resp = client.post("/dispositivos/", headers=admin_headers, json={"uid_equipo": "ESP32-NUEVO"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["uid_equipo"] == "ESP32-NUEVO"
    assert data["estado"] == "Activo"  # default del schema
    assert data["id_paciente"] is None


def test_crear_dispositivo_medico_403(client, medico_headers):
    """Médico puede leer dispositivos pero no crearlos (solo admin, CRUD total)."""
    resp = client.post("/dispositivos/", headers=medico_headers, json={"uid_equipo": "ESP32-X"})
    assert resp.status_code == 403


def test_crear_dispositivo_sin_uid_devuelve_422(client, admin_headers):
    resp = client.post("/dispositivos/", headers=admin_headers, json={"estado": "Activo"})
    assert resp.status_code == 422


def test_crear_dispositivo_con_paciente_crea_asociacion(client, crear_paciente, db, admin_headers):
    paciente = crear_paciente()
    resp = client.post(
        "/dispositivos/",
        headers=admin_headers,
        json={"uid_equipo": "ESP32-ASOC", "id_paciente": paciente.id_paciente},
    )
    assert resp.status_code == 200
    assert resp.json()["id_paciente"] == paciente.id_paciente

    asoc = db.query(models.PacienteDispositivo).one()
    assert asoc.id_paciente == paciente.id_paciente
    assert asoc.fecha_hora_disoc is None  # asociación activa


# ------------------------- GET -------------------------

def test_listar_dispositivos_sin_asignar(client, crear_dispositivo, visor_headers):
    crear_dispositivo(uid_equipo="ESP32-SOLO")
    resp = client.get("/dispositivos/", headers=visor_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["paciente_asignado"] == "Sin asignar"
    assert data[0]["id_paciente"] is None


def test_listar_dispositivos_muestra_paciente_asignado(
    client, crear_paciente, crear_dispositivo, asociar, visor_headers
):
    paciente = crear_paciente(nombre="Laura", apellido="Núñez")
    disp = crear_dispositivo(uid_equipo="ESP32-LAURA")
    asociar(paciente, disp)

    resp = client.get("/dispositivos/", headers=visor_headers)
    data = resp.json()
    assert data[0]["paciente_asignado"] == "Laura Núñez"
    assert data[0]["id_paciente"] == paciente.id_paciente


def test_listar_dispositivos_sin_token_401(client):
    resp = client.get("/dispositivos/")
    assert resp.status_code == 401


# ------------------------- PATCH -------------------------

def test_actualizar_estado_dispositivo(client, crear_dispositivo, db, admin_headers):
    disp = crear_dispositivo()
    resp = client.patch(
        f"/dispositivos/{disp.id_dispositivo}",
        headers=admin_headers,
        json={"estado": "Mantenimiento"},
    )
    assert resp.status_code == 200

    db.refresh(disp)
    assert disp.estado == "Mantenimiento"


def test_asignar_paciente_a_dispositivo_libre(client, crear_paciente, crear_dispositivo, db, admin_headers):
    paciente = crear_paciente()
    disp = crear_dispositivo()

    resp = client.patch(
        f"/dispositivos/{disp.id_dispositivo}",
        headers=admin_headers,
        json={"id_paciente": paciente.id_paciente},
    )
    assert resp.status_code == 200

    asoc = db.query(models.PacienteDispositivo).one()
    assert asoc.id_paciente == paciente.id_paciente
    assert asoc.fecha_hora_disoc is None


def test_reasignar_paciente_cierra_asociacion_anterior(
    client, crear_paciente, crear_dispositivo, asociar, db, admin_headers
):
    """Al cambiar de paciente: la sesión vieja se cierra (fecha_hora_disoc) y se abre una nueva."""
    paciente_viejo = crear_paciente(nombre="Viejo")
    paciente_nuevo = crear_paciente(nombre="Nuevo")
    disp = crear_dispositivo()
    asociar(paciente_viejo, disp)

    resp = client.patch(
        f"/dispositivos/{disp.id_dispositivo}",
        headers=admin_headers,
        json={"id_paciente": paciente_nuevo.id_paciente},
    )
    assert resp.status_code == 200

    asocs = (
        db.query(models.PacienteDispositivo)
        .order_by(models.PacienteDispositivo.id)
        .all()
    )
    assert len(asocs) == 2
    vieja, nueva = asocs
    assert vieja.id_paciente == paciente_viejo.id_paciente
    assert vieja.fecha_hora_disoc is not None  # sesión cerrada
    assert nueva.id_paciente == paciente_nuevo.id_paciente
    assert nueva.fecha_hora_disoc is None  # sesión activa


def test_desvincular_paciente_de_dispositivo(
    client, crear_paciente, crear_dispositivo, asociar, db, admin_headers
):
    """Mandar id_paciente = null desconecta al paciente sin crear una asociación nueva."""
    paciente = crear_paciente()
    disp = crear_dispositivo()
    asociar(paciente, disp)

    resp = client.patch(
        f"/dispositivos/{disp.id_dispositivo}",
        headers=admin_headers,
        json={"id_paciente": None},
    )
    assert resp.status_code == 200

    asocs = db.query(models.PacienteDispositivo).all()
    assert len(asocs) == 1
    assert asocs[0].fecha_hora_disoc is not None


def test_actualizar_dispositivo_inexistente_404(client, admin_headers):
    resp = client.patch("/dispositivos/9999", headers=admin_headers, json={"estado": "X"})
    assert resp.status_code == 404


# ------------------------- DELETE -------------------------

def test_eliminar_dispositivo_ok(client, crear_dispositivo, db, admin_headers):
    disp = crear_dispositivo()
    resp = client.delete(f"/dispositivos/{disp.id_dispositivo}", headers=admin_headers)
    assert resp.status_code == 200
    assert db.query(models.Dispositivo).count() == 0


def test_eliminar_dispositivo_borra_sensores_en_cascada(client, crear_dispositivo, db, admin_headers):
    disp = crear_dispositivo()
    db.add(models.Sensor(id_dispositivo=disp.id_dispositivo, tipo="spo2"))
    db.commit()

    resp = client.delete(f"/dispositivos/{disp.id_dispositivo}", headers=admin_headers)
    assert resp.status_code == 200
    assert db.query(models.Sensor).count() == 0


def test_eliminar_dispositivo_inexistente_404(client, admin_headers):
    resp = client.delete("/dispositivos/9999", headers=admin_headers)
    assert resp.status_code == 404
