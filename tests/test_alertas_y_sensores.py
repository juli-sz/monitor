# tests/test_alertas_y_sensores.py
# Alertas (/alertas) y umbrales de signos vitales (/sensores)
# Permisos alertas: POST = admin+medico; GET = cualquier rol; PATCH resolver = admin+medico+enfermero
# Permisos sensores: GET = cualquier rol; POST = admin+medico

import models


# ======================================================
# ALERTAS
# ======================================================

def test_registrar_alerta_equipo_inexistente(client, medico_headers):
    resp = client.post("/alertas/", headers=medico_headers, json={
        "uid_equipo": "NO-EXISTE", "sensor": "spo2", "valor": "82",
    })
    assert resp.status_code == 200
    assert resp.json() == {"error": "Equipo no encontrado"}


def test_registrar_alerta_enfermero_403(client, crear_dispositivo, enfermero_headers):
    """Enfermero puede resolver alertas pero no crearlas."""
    disp = crear_dispositivo(uid_equipo="ESP32-SUELTO-403")
    resp = client.post("/alertas/", headers=enfermero_headers, json={
        "uid_equipo": disp.uid_equipo, "sensor": "spo2", "valor": "82",
    })
    assert resp.status_code == 403


def test_registrar_alerta_sin_paciente_asociado(client, crear_dispositivo, db, medico_headers):
    disp = crear_dispositivo(uid_equipo="ESP32-SUELTO")
    resp = client.post("/alertas/", headers=medico_headers, json={
        "uid_equipo": disp.uid_equipo, "sensor": "spo2", "valor": "82",
    })
    assert resp.status_code == 200

    alerta = db.query(models.Alerta).one()
    assert alerta.id_dispositivo == disp.id_dispositivo
    assert alerta.id_paciente is None
    assert alerta.estado == "ACTIVA"


def test_registrar_alerta_con_paciente_asociado(
    client, crear_paciente, crear_dispositivo, asociar, db, medico_headers
):
    paciente = crear_paciente()
    disp = crear_dispositivo(uid_equipo="ESP32-CON-PAC")
    asociar(paciente, disp)

    resp = client.post("/alertas/", headers=medico_headers, json={
        "uid_equipo": disp.uid_equipo, "sensor": "temperatura", "valor": "39.5",
    })
    assert resp.status_code == 200

    alerta = db.query(models.Alerta).one()
    assert alerta.id_paciente == paciente.id_paciente
    assert "TEMPERATURA" in alerta.descripcion
    assert "39.5" in alerta.descripcion


def test_listar_alertas_con_filtro_por_estado(
    client, crear_paciente, crear_dispositivo, db, visor_headers
):
    paciente = crear_paciente()
    disp = crear_dispositivo()
    db.add(models.Alerta(id_dispositivo=disp.id_dispositivo,
                         id_paciente=paciente.id_paciente,
                         descripcion="Activa 1", estado="ACTIVA"))
    db.add(models.Alerta(id_dispositivo=disp.id_dispositivo,
                         id_paciente=paciente.id_paciente,
                         descripcion="Resuelta 1", estado="RESUELTA"))
    db.commit()

    # Sin filtro: todas
    resp = client.get("/alertas/", headers=visor_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    # Con filtro: solo las activas
    resp = client.get("/alertas/", headers=visor_headers, params={"estado": "ACTIVA"})
    data = resp.json()
    assert len(data) == 1
    assert data[0]["estado"] == "ACTIVA"
    assert data[0]["fecha_hora"] is not None


def test_resolver_alarmas_de_un_paciente(client, crear_paciente, crear_dispositivo, db, enfermero_headers):
    paciente = crear_paciente()
    otro = crear_paciente(nombre="Otro")
    disp = crear_dispositivo()
    for _ in range(3):
        db.add(models.Alerta(id_dispositivo=disp.id_dispositivo,
                             id_paciente=paciente.id_paciente,
                             descripcion="Alta", estado="ACTIVA"))
    db.add(models.Alerta(id_dispositivo=disp.id_dispositivo,
                         id_paciente=otro.id_paciente,
                         descripcion="Ajena", estado="ACTIVA"))
    db.commit()

    resp = client.patch(f"/alertas/resolver/paciente/{paciente.id_paciente}", headers=enfermero_headers)
    assert resp.status_code == 200
    assert "3 alarmas resueltas" in resp.json()["mensaje"]

    resueltas = db.query(models.Alerta).filter_by(estado="RESUELTA").all()
    assert len(resueltas) == 3
    assert all(a.resuelta_en is not None for a in resueltas)
    # La alerta del otro paciente sigue activa
    assert db.query(models.Alerta).filter_by(estado="ACTIVA").count() == 1


def test_resolver_alarmas_visor_403(client, crear_paciente, visor_headers):
    """Visor es solo lectura: no puede resolver alertas."""
    paciente = crear_paciente()
    resp = client.patch(f"/alertas/resolver/paciente/{paciente.id_paciente}", headers=visor_headers)
    assert resp.status_code == 403


def test_historial_alertas_por_paciente(client, crear_paciente, crear_dispositivo, db, visor_headers):
    paciente = crear_paciente()
    disp = crear_dispositivo()
    db.add(models.Alerta(id_dispositivo=disp.id_dispositivo,
                         id_paciente=paciente.id_paciente,
                         descripcion="Histórica", estado="RESUELTA"))
    db.commit()

    resp = client.get(f"/alertas/paciente/{paciente.id_paciente}", headers=visor_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["descripcion"] == "Histórica"
    assert "resuelta_en" in data[0]


# ======================================================
# SENSORES / RANGOS DE SIGNOS VITALES
# ======================================================

def test_umbrales_globales_vacios(client, visor_headers):
    resp = client.get("/sensores/", headers=visor_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_crear_umbral_global(client, db, medico_headers):
    resp = client.post("/sensores/", headers=medico_headers, json={
        "tipo_signo": "SPO2",  # se guarda en minúsculas
        "valor_minimo": 90,
        "valor_maximo": 100,
        "unidad": "%",
    })
    assert resp.status_code == 200

    rango = db.query(models.RangoSignoVital).one()
    assert rango.id_paciente is None  # global
    assert rango.tipo_signo == "spo2"
    assert float(rango.valor_minimo) == 90


def test_crear_umbral_enfermero_403(client, enfermero_headers):
    resp = client.post("/sensores/", headers=enfermero_headers, json={
        "tipo_signo": "spo2", "valor_minimo": 90, "valor_maximo": 100, "unidad": "%",
    })
    assert resp.status_code == 403


def test_actualizar_umbral_existente_no_duplica(client, db, medico_headers):
    """Postear dos veces el mismo tipo_signo debe actualizar, no crear otro registro."""
    payload = {"tipo_signo": "temperatura", "valor_minimo": 35.5,
               "valor_maximo": 37.5, "unidad": "°C"}
    client.post("/sensores/", headers=medico_headers, json=payload)

    payload["valor_maximo"] = 38.0
    resp = client.post("/sensores/", headers=medico_headers, json=payload)
    assert resp.status_code == 200

    rangos = db.query(models.RangoSignoVital).all()
    assert len(rangos) == 1
    assert float(rangos[0].valor_maximo) == 38.0


def test_umbral_por_paciente_y_consulta(client, crear_paciente, db, medico_headers, visor_headers):
    paciente = crear_paciente()
    resp = client.post("/sensores/", headers=medico_headers, json={
        "id_paciente": paciente.id_paciente,
        "tipo_signo": "pulso",
        "valor_minimo": 50,
        "valor_maximo": 110,
        "unidad": "lpm",
    })
    assert resp.status_code == 200

    # El umbral del paciente NO aparece entre los globales
    assert client.get("/sensores/", headers=visor_headers).json() == []

    resp = client.get(f"/sensores/paciente/{paciente.id_paciente}", headers=visor_headers)
    data = resp.json()
    assert len(data) == 1
    assert data[0]["tipo_signo"] == "pulso"


def test_crear_umbral_datos_invalidos_422(client, medico_headers):
    resp = client.post("/sensores/", headers=medico_headers, json={"tipo_signo": "spo2"})
    assert resp.status_code == 422
