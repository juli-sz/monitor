# tests/test_servicios.py
# Servicios internos: ingesta MQTT (on_message), filtro ECG y WebSocket manager

import json
import time

import numpy as np
import pytest

import models
from services import mqtt_service
from services.signal_processor import ecg_filter_realtime, ecg_states
from services.websocket_manager import ConnectionManager


# ======================================================
# INGESTA MQTT (services/mqtt_service.py)
# ======================================================

class MensajeFalso:
    """Simula el objeto msg que paho-mqtt le pasa a on_message."""

    def __init__(self, topic: str, payload: dict):
        self.topic = topic
        self.payload = json.dumps(payload).encode()


def test_on_message_crea_dispositivo_y_lectura_general(db):
    msg = MensajeFalso("datos/sensores/ESP32-MQTT-1/temperatura", {
        "Uid_Equipo": "ESP32-MQTT-1",
        "Date": time.time(),
        "value": 36.8,
    })
    mqtt_service.on_message(None, None, msg)

    # El dispositivo se auto-registra si no existía
    disp = db.query(models.Dispositivo).filter_by(uid_equipo="ESP32-MQTT-1").one()
    lectura = db.query(models.LecturaGeneral).one()
    assert lectura.id_dispositivo == disp.id_dispositivo
    assert lectura.tipo_sensor == "temperatura"
    assert float(lectura.valor_numerico) == 36.8
    assert lectura.id_paciente is None  # nadie asociado todavía


def test_on_message_asocia_lectura_al_paciente_conectado(
    db, crear_paciente, crear_dispositivo, asociar
):
    paciente = crear_paciente()
    disp = crear_dispositivo(uid_equipo="ESP32-MQTT-PAC")
    asociar(paciente, disp)

    msg = MensajeFalso("datos/sensores/ESP32-MQTT-PAC/spo2", {
        "Uid_Equipo": "ESP32-MQTT-PAC",
        "Date": time.time(),
        "value": 97,
    })
    mqtt_service.on_message(None, None, msg)

    lectura = db.query(models.LecturaGeneral).one()
    assert lectura.id_paciente == paciente.id_paciente


def test_on_message_ecg_guarda_bloque(db):
    valores = [0.1, 0.4, 0.9, 0.4, 0.1, 0.0]
    msg = MensajeFalso("datos/sensores/ESP32-MQTT-ECG/ecg", {
        "Uid_Equipo": "ESP32-MQTT-ECG",
        "Date": time.time(),
        "FS": 250,
        "sample_number": len(valores),
        "raw_values": valores,
    })
    mqtt_service.on_message(None, None, msg)

    bloque = db.query(models.ECG).one()
    assert bloque.frecuencia_muestreo == 250
    assert bloque.sample_number == len(valores)
    assert [float(v) for v in bloque.valor] == valores


def test_on_message_pni_guarda_presiones(db):
    msg = MensajeFalso("datos/sensores/ESP32-MQTT-PNI/pni", {
        "Uid_Equipo": "ESP32-MQTT-PNI",
        "Date": time.time(),
        "value": "120/80",
    })
    mqtt_service.on_message(None, None, msg)

    lectura = db.query(models.LecturaPNI).one()
    assert lectura.presion_sistolica == 120
    assert lectura.presion_diastolica == 80


def test_on_message_pni_malformada_no_guarda_nada(db):
    msg = MensajeFalso("datos/sensores/ESP32-MQTT-PNI2/pni", {
        "Uid_Equipo": "ESP32-MQTT-PNI2",
        "value": "no-es-presion",
    })
    mqtt_service.on_message(None, None, msg)
    assert db.query(models.LecturaPNI).count() == 0


def test_on_message_sin_uid_se_ignora(db):
    msg = MensajeFalso("datos/sensores/X/temperatura", {"value": 36.5})
    mqtt_service.on_message(None, None, msg)
    assert db.query(models.LecturaGeneral).count() == 0
    assert db.query(models.Dispositivo).count() == 0


def test_on_message_payload_invalido_no_explota(db):
    """Un JSON roto debe capturarse sin tirar la ingesta abajo."""
    msg = MensajeFalso("datos/sensores/X/temperatura", {})
    msg.payload = b"esto no es json {"
    mqtt_service.on_message(None, None, msg)  # no debe lanzar excepción
    assert db.query(models.LecturaGeneral).count() == 0


def test_iniciar_mqtt_sin_broker_no_arranca(monkeypatch):
    """Sin MQTT_BROKER configurado la API debe seguir andando sin cliente MQTT."""
    monkeypatch.setattr(mqtt_service, "MQTT_BROKER", None)
    monkeypatch.setattr(mqtt_service, "mqtt_client", None)
    mqtt_service.iniciar_mqtt()
    assert mqtt_service.mqtt_client is None


def test_iniciar_mqtt_broker_caido_no_explota(monkeypatch):
    """Si el broker no responde, la API arranca igual (clave para Docker)."""
    monkeypatch.setattr(mqtt_service, "MQTT_BROKER", "127.0.0.1")
    monkeypatch.setattr(mqtt_service, "MQTT_PORT", 1)  # puerto sin nada escuchando
    mqtt_service.iniciar_mqtt()  # no debe lanzar excepción
    assert mqtt_service.mqtt_client is None


def test_detener_mqtt_sin_cliente_no_falla(monkeypatch):
    monkeypatch.setattr(mqtt_service, "mqtt_client", None)
    mqtt_service.detener_mqtt()  # no debe lanzar excepción


def test_callbacks_de_conexion_no_fallan(capsys):
    mqtt_service.on_disconnect(None, None, 0)
    salida = capsys.readouterr().out
    assert "desconectado" in salida.lower()


# ======================================================
# FILTRO ECG (services/signal_processor.py)
# ======================================================

def test_filtro_ecg_conserva_cantidad_de_muestras():
    ecg_states.clear()
    senal = list(np.sin(np.linspace(0, 8 * np.pi, 400)))
    filtrada = ecg_filter_realtime(senal, fs=360, uid_equipo="UID-FILTRO-1")
    assert isinstance(filtrada, np.ndarray)
    assert len(filtrada) == len(senal)


def test_filtro_ecg_senal_corta_pasa_sin_filtrar():
    resultado = ecg_filter_realtime([0.5, 0.7], fs=360, uid_equipo="UID-CORTO")
    assert list(resultado) == [0.5, 0.7]


def test_filtro_ecg_mantiene_estado_por_dispositivo():
    """El estado del filtro (zi) se guarda por uid para procesar en tiempo real."""
    ecg_states.clear()
    senal = list(np.random.default_rng(42).normal(0, 1, 200))
    ecg_filter_realtime(senal, fs=360, uid_equipo="UID-ESTADO")
    assert "UID-ESTADO" in ecg_states
    assert ecg_states["UID-ESTADO"]["zi_bp"] is not None

    # Segunda pasada con estado previo: no debe fallar
    filtrada2 = ecg_filter_realtime(senal, fs=360, uid_equipo="UID-ESTADO")
    assert len(filtrada2) == len(senal)


def test_filtro_ecg_estados_independientes_entre_dispositivos():
    ecg_states.clear()
    senal = [0.1] * 50
    ecg_filter_realtime(senal, fs=360, uid_equipo="UID-A")
    ecg_filter_realtime(senal, fs=360, uid_equipo="UID-B")
    assert set(ecg_states.keys()) >= {"UID-A", "UID-B"}


# ======================================================
# WEBSOCKETS (services/websocket_manager.py + routes/websockets.py)
# ======================================================

class WebSocketFalso:
    def __init__(self):
        self.mensajes = []

    async def send_text(self, mensaje):
        self.mensajes.append(mensaje)


class WebSocketRoto:
    async def send_text(self, mensaje):
        raise RuntimeError("conexión caída")


@pytest.mark.asyncio
async def test_broadcast_envia_a_todos_los_conectados():
    manager = ConnectionManager()
    ws1, ws2 = WebSocketFalso(), WebSocketFalso()
    manager.active_connections = [ws1, ws2]

    await manager._broadcast_async("spo2", {"value": 97})

    for ws in (ws1, ws2):
        assert len(ws.mensajes) == 1
        mensaje = json.loads(ws.mensajes[0])
        assert mensaje["sensor"] == "spo2"
        assert mensaje["payload"] == {"value": 97}


@pytest.mark.asyncio
async def test_broadcast_desconecta_clientes_rotos():
    manager = ConnectionManager()
    sano, roto = WebSocketFalso(), WebSocketRoto()
    manager.active_connections = [roto, sano]

    await manager._broadcast_async("ecg", {"raw_values": [1, 2]})

    assert roto not in manager.active_connections
    assert sano in manager.active_connections
    assert len(sano.mensajes) == 1


def test_broadcast_sync_sin_loop_no_falla():
    """El puente MQTT->WS no debe explotar si el loop principal aún no arrancó."""
    manager = ConnectionManager()
    manager.broadcast_sync("spo2", {"value": 95})  # main_loop es None: no-op


def test_endpoint_websocket_requiere_token(client):
    """Sin token (o inválido) el handshake se rechaza antes de aceptar la conexión."""
    from starlette.websockets import WebSocketDisconnect
    from services.websocket_manager import ws_manager

    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws/datos"):
            pass
    assert exc_info.value.code == 1008
    assert len(ws_manager.active_connections) == 0


def test_endpoint_websocket_acepta_conexiones(client, crear_usuario):
    from services.websocket_manager import ws_manager
    from services.auth_service import crear_token_acceso

    usuario = crear_usuario(email="ws@test.com", rol="visor")
    token = crear_token_acceso({"sub": str(usuario.id_usuario), "rol": usuario.rol})

    with client.websocket_connect(f"/ws/datos?token={token}"):
        assert len(ws_manager.active_connections) == 1
    # Al salir del with, el cliente se desconecta y se limpia la lista
    assert len(ws_manager.active_connections) == 0
