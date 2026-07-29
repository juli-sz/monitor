# tests/test_general.py
# Tests de los endpoints definidos directamente en mainf.py


def test_root_responde(client):
    """El healthcheck raíz sigue siendo público, sin autenticación."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json() == {"message": "API funcionando correctamente"}


def test_paciente_por_uid_sin_token_401(client):
    resp = client.get("/pacientes_por_dispositivo_uid/NO-EXISTE")
    assert resp.status_code == 401


def test_paciente_por_uid_dispositivo_inexistente(client, visor_headers):
    resp = client.get("/pacientes_por_dispositivo_uid/NO-EXISTE", headers=visor_headers)
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Dispositivo no encontrado"


def test_paciente_por_uid_sin_asociacion(client, crear_dispositivo, visor_headers):
    disp = crear_dispositivo(uid_equipo="ESP32-LIBRE")
    resp = client.get(f"/pacientes_por_dispositivo_uid/{disp.uid_equipo}", headers=visor_headers)
    assert resp.status_code == 404
    assert "No hay paciente asociado" in resp.json()["detail"]


def test_paciente_por_uid_asociacion_cerrada_no_cuenta(
    client, crear_paciente, crear_dispositivo, asociar, visor_headers
):
    """Una asociación con fecha_hora_disoc NO es una asociación activa."""
    paciente = crear_paciente()
    disp = crear_dispositivo(uid_equipo="ESP32-HISTORICO")
    asociar(paciente, disp, disociado=True)

    resp = client.get(f"/pacientes_por_dispositivo_uid/{disp.uid_equipo}", headers=visor_headers)
    assert resp.status_code == 404


def test_paciente_por_uid_ok(client, crear_paciente, crear_dispositivo, asociar, visor_headers):
    paciente = crear_paciente(nombre="Ana", apellido="Gómez")
    disp = crear_dispositivo(uid_equipo="ESP32-ANA")
    asociar(paciente, disp)

    resp = client.get(f"/pacientes_por_dispositivo_uid/{disp.uid_equipo}", headers=visor_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id_paciente"] == paciente.id_paciente
    assert data["nombre"] == "Ana"
    assert data["apellido"] == "Gómez"
