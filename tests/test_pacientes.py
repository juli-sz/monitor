# tests/test_pacientes.py
# CRUD completo de /pacientes
# Permisos: GET = cualquier rol logueado; POST/PATCH = admin+medico; DELETE = admin

import models

PACIENTE_VALIDO = {
    "nombre": "María",
    "apellido": "López",
    "dni": "28999888",
    "fecha_nacimiento": "1985-04-12",
    "sexo": "F",
    "direccion": "Av. Siempreviva 742",
    "tipo": "Ambulatorio",
    "diagnostico": "Hipertensión",
}


# ------------------------- POST -------------------------

def test_crear_paciente_ok(client, medico_headers):
    resp = client.post("/pacientes/", headers=medico_headers, json=PACIENTE_VALIDO)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id_paciente"] >= 1
    assert data["nombre"] == "María"
    assert data["apellido"] == "López"
    assert data["fecha_egreso"] is None
    assert data["creado_en"] is not None


def test_crear_paciente_datos_invalidos_devuelve_422(client, medico_headers):
    # Falta "apellido" (obligatorio en PacienteCreate)
    resp = client.post("/pacientes/", headers=medico_headers, json={"nombre": "SinApellido"})
    assert resp.status_code == 422


def test_crear_paciente_fecha_invalida_devuelve_422(client, medico_headers):
    datos = dict(PACIENTE_VALIDO, fecha_nacimiento="no-es-fecha")
    resp = client.post("/pacientes/", headers=medico_headers, json=datos)
    assert resp.status_code == 422


def test_crear_paciente_enfermero_403(client, enfermero_headers):
    """Enfermero puede leer pacientes pero no crearlos."""
    resp = client.post("/pacientes/", headers=enfermero_headers, json=PACIENTE_VALIDO)
    assert resp.status_code == 403


# ------------------------- GET -------------------------

def test_listar_pacientes_vacio(client, visor_headers):
    resp = client.get("/pacientes/", headers=visor_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_listar_pacientes_orden_descendente(client, crear_paciente, visor_headers):
    p1 = crear_paciente(nombre="Primero")
    p2 = crear_paciente(nombre="Segundo")

    resp = client.get("/pacientes/", headers=visor_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    # Los más nuevos primero
    assert data[0]["id_paciente"] == p2.id_paciente
    assert data[1]["id_paciente"] == p1.id_paciente


def test_obtener_paciente_por_id(client, crear_paciente, visor_headers):
    paciente = crear_paciente(nombre="Carlos")
    resp = client.get(f"/pacientes/{paciente.id_paciente}", headers=visor_headers)
    assert resp.status_code == 200
    assert resp.json()["nombre"] == "Carlos"


def test_obtener_paciente_inexistente_404(client, visor_headers):
    resp = client.get("/pacientes/9999", headers=visor_headers)
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Paciente no encontrado"


def test_listar_pacientes_sin_token_401(client):
    resp = client.get("/pacientes/")
    assert resp.status_code == 401


# ------------------------- PATCH -------------------------

def test_actualizar_paciente_parcial(client, crear_paciente, medico_headers):
    paciente = crear_paciente(diagnostico="Inicial")

    resp = client.patch(
        f"/pacientes/{paciente.id_paciente}",
        headers=medico_headers,
        json={"diagnostico": "Actualizado"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["diagnostico"] == "Actualizado"
    # Los campos no enviados no se tocan
    assert data["nombre"] == paciente.nombre


def test_dar_de_alta_paciente_con_fecha_egreso(client, crear_paciente, medico_headers):
    paciente = crear_paciente()
    resp = client.patch(
        f"/pacientes/{paciente.id_paciente}",
        headers=medico_headers,
        json={"fecha_egreso": "2026-07-01"},
    )
    assert resp.status_code == 200
    assert resp.json()["fecha_egreso"] == "2026-07-01"


def test_actualizar_paciente_inexistente_404(client, medico_headers):
    resp = client.patch("/pacientes/9999", headers=medico_headers, json={"nombre": "Nadie"})
    assert resp.status_code == 404


# ------------------------- DELETE -------------------------

def test_eliminar_paciente_ok(client, crear_paciente, db, admin_headers):
    paciente = crear_paciente()
    resp = client.delete(f"/pacientes/{paciente.id_paciente}", headers=admin_headers)
    assert resp.status_code == 200

    assert db.query(models.Paciente).count() == 0


def test_eliminar_paciente_medico_403(client, crear_paciente, medico_headers):
    """Solo admin puede borrar pacientes; médico no."""
    paciente = crear_paciente()
    resp = client.delete(f"/pacientes/{paciente.id_paciente}", headers=medico_headers)
    assert resp.status_code == 403


def test_eliminar_paciente_borra_datos_relacionados(
    client, db, crear_paciente, crear_dispositivo, asociar, admin_headers
):
    """Al borrar un paciente deben desaparecer sus asociaciones, rangos y alertas."""
    paciente = crear_paciente()
    disp = crear_dispositivo()
    asociar(paciente, disp)

    db.add(models.RangoSignoVital(
        id_paciente=paciente.id_paciente,
        tipo_signo="spo2", valor_minimo=90, valor_maximo=100, unidad="%",
    ))
    db.add(models.Alerta(
        id_dispositivo=disp.id_dispositivo,
        id_paciente=paciente.id_paciente,
        descripcion="Alerta de prueba",
    ))
    db.commit()

    resp = client.delete(f"/pacientes/{paciente.id_paciente}", headers=admin_headers)
    assert resp.status_code == 200

    assert db.query(models.Paciente).count() == 0
    assert db.query(models.PacienteDispositivo).count() == 0
    assert db.query(models.RangoSignoVital).count() == 0
    assert db.query(models.Alerta).count() == 0
    # El dispositivo NO se borra, solo el vínculo
    assert db.query(models.Dispositivo).count() == 1


def test_eliminar_paciente_inexistente_404(client, admin_headers):
    resp = client.delete("/pacientes/9999", headers=admin_headers)
    assert resp.status_code == 404
