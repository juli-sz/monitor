# tests/test_historico.py
# Endpoints de histórico y telemetría (routes/historico.py)
# Permisos: todos son de solo lectura, requieren cualquier rol logueado.

import datetime


UTC = datetime.timezone.utc


# ------------------------- /historico/{uid}/{sensor} -------------------------

def test_historico_dispositivo_inexistente_404(client, visor_headers):
    resp = client.get("/historico/NO-EXISTE/temperatura", headers=visor_headers)
    assert resp.status_code == 404


def test_historico_sin_token_401(client):
    resp = client.get("/historico/NO-EXISTE/temperatura")
    assert resp.status_code == 401


def test_historico_devuelve_lecturas_ordenadas(client, crear_dispositivo, crear_lectura, visor_headers):
    disp = crear_dispositivo(uid_equipo="ESP32-HIST")
    t1 = datetime.datetime(2026, 7, 1, 10, 0, tzinfo=UTC)
    t2 = datetime.datetime(2026, 7, 1, 12, 0, tzinfo=UTC)
    crear_lectura(disp, tipo_sensor="temperatura", valor=37.2, fecha_hora=t2)
    crear_lectura(disp, tipo_sensor="temperatura", valor=36.5, fecha_hora=t1)
    # Lectura de OTRO sensor: no debe aparecer
    crear_lectura(disp, tipo_sensor="spo2", valor=97, fecha_hora=t1)

    resp = client.get(f"/historico/{disp.uid_equipo}/temperatura", headers=visor_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["uid"] == disp.uid_equipo
    assert data["sensor"] == "temperatura"
    assert len(data["datos"]) == 2
    # Orden ascendente por fecha
    assert data["datos"][0]["valor"] == 36.5
    assert data["datos"][1]["valor"] == 37.2


def test_historico_filtra_por_fecha(client, crear_dispositivo, crear_lectura, visor_headers):
    disp = crear_dispositivo(uid_equipo="ESP32-FECHAS")
    dia1 = datetime.datetime(2026, 7, 1, 15, 0, tzinfo=UTC)
    dia2 = datetime.datetime(2026, 7, 2, 15, 0, tzinfo=UTC)
    crear_lectura(disp, valor=36.0, fecha_hora=dia1)
    crear_lectura(disp, valor=38.0, fecha_hora=dia2)

    resp = client.get(
        f"/historico/{disp.uid_equipo}/temperatura",
        headers=visor_headers,
        params={"fecha": "2026-07-01"},
    )
    data = resp.json()
    assert len(data["datos"]) == 1
    assert data["datos"][0]["valor"] == 36.0


# ------------------------- /ecg/imagen_10s/{uid} -------------------------

def test_imagen_ecg_sin_datos_404(client, crear_dispositivo, visor_headers):
    disp = crear_dispositivo(uid_equipo="ESP32-SIN-ECG")
    resp = client.get(f"/ecg/imagen_10s/{disp.uid_equipo}", headers=visor_headers)
    assert resp.status_code == 404


def test_imagen_ecg_devuelve_png(client, crear_dispositivo, crear_bloque_ecg, visor_headers):
    disp = crear_dispositivo(uid_equipo="ESP32-ECG-IMG")
    crear_bloque_ecg(disp, valores=[0.1, 0.5, 0.9, 0.5, 0.1] * 20, fs=100)

    resp = client.get(f"/ecg/imagen_10s/{disp.uid_equipo}", headers=visor_headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    # Firma de un archivo PNG real
    assert resp.content[:8] == b"\x89PNG\r\n\x1a\n"


# ------------------------- /historico_ecg/{uid} -------------------------

def test_historico_ecg_dispositivo_inexistente_404(client, visor_headers):
    resp = client.get("/historico_ecg/NO-EXISTE", headers=visor_headers)
    assert resp.status_code == 404


def test_historico_ecg_devuelve_cruda_y_filtrada(client, crear_dispositivo, crear_bloque_ecg, visor_headers):
    disp = crear_dispositivo(uid_equipo="ESP32-ECG-RAW")
    valores = [0.0, 0.2, 0.8, 1.2, 0.6, 0.1, -0.1, 0.0] * 10
    crear_bloque_ecg(disp, valores=valores, fs=360)

    resp = client.get(f"/historico_ecg/{disp.uid_equipo}", headers=visor_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["ecg"]) == 1
    bloque = data["ecg"][0]
    assert bloque["fs"] == 360
    assert len(bloque["raw"]) == len(valores)
    # La señal filtrada mantiene la misma cantidad de muestras
    assert len(bloque["filtered"]) == len(valores)


def test_historico_ecg_filtra_por_fecha(client, crear_dispositivo, crear_bloque_ecg, visor_headers):
    disp = crear_dispositivo(uid_equipo="ESP32-ECG-FECHA")
    crear_bloque_ecg(disp, fecha_inicio=datetime.datetime(2026, 7, 1, 8, 0, tzinfo=UTC))
    crear_bloque_ecg(disp, fecha_inicio=datetime.datetime(2026, 7, 3, 8, 0, tzinfo=UTC))

    resp = client.get(
        f"/historico_ecg/{disp.uid_equipo}", headers=visor_headers, params={"fecha": "2026-07-03"}
    )
    assert len(resp.json()["ecg"]) == 1


# ------------------------- /historico_ecg_segmentado/{uid} -------------------------

def test_ecg_segmentado_dispositivo_inexistente_devuelve_vacio(client, visor_headers):
    resp = client.get(
        "/historico_ecg_segmentado/NO-EXISTE", headers=visor_headers, params={"t0": 0, "t1": 1}
    )
    assert resp.status_code == 200
    assert resp.json() == {"ecg": []}


def test_ecg_segmentado_devuelve_solo_el_rango(client, crear_dispositivo, crear_bloque_ecg, visor_headers):
    disp = crear_dispositivo(uid_equipo="ESP32-ECG-SEG")
    ahora = datetime.datetime.now(UTC)
    dentro = crear_bloque_ecg(disp, valores=[1.0, 2.0, 3.0], fecha_inicio=ahora)
    # Bloque de hace 1 hora: queda fuera del rango pedido
    crear_bloque_ecg(
        disp, valores=[9.0, 9.0],
        fecha_inicio=ahora - datetime.timedelta(hours=1),
    )

    t0 = (ahora - datetime.timedelta(minutes=5)).timestamp()
    t1 = (ahora + datetime.timedelta(minutes=5)).timestamp()
    resp = client.get(
        f"/historico_ecg_segmentado/{disp.uid_equipo}",
        headers=visor_headers,
        params={"t0": t0, "t1": t1},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["values"] == [float(v) for v in dentro.valor]
