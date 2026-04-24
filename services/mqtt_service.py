# services/mqtt_service.py
import json
import datetime
import time
from typing import Optional
from paho.mqtt.client import Client as MQTTClient, CallbackAPIVersion

# Importamos todo desde nuestros nuevos módulos
from config import MQTT_BROKER, MQTT_PORT, MQTT_USERNAME, MQTT_PASSWORD, MQTT_TOPIC
from database import SessionLocal
from models import Dispositivo, PacienteDispositivo, ECG, LecturaPNI, LecturaGeneral
from services.signal_processor import ecg_filter_realtime
from services.websocket_manager import ws_manager

mqtt_client: Optional[MQTTClient] = None

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("✅ MQTT conectado exitosamente")
        client.subscribe(MQTT_TOPIC)
    else:
        print(f"❌ Error de conexión MQTT. Código: {rc}")

def on_disconnect(client, userdata, rc):
    print("⚠️ MQTT desconectado", rc)

def on_message(client, userdata, msg):
    session = SessionLocal()
    try:
        payload = json.loads(msg.payload.decode())
        uid_equipo = payload.get("Uid_Equipo")
        if not uid_equipo:
            return

        timestamp = datetime.datetime.fromtimestamp(
            payload.get("Date", time.time()),
            tz=datetime.timezone.utc
        )

        # 1. Búsqueda o creación del dispositivo
        dispositivo = session.query(Dispositivo).filter_by(uid_equipo=uid_equipo).first()
        if not dispositivo:
            dispositivo = Dispositivo(uid_equipo=uid_equipo)
            session.add(dispositivo)
            session.commit()
            session.refresh(dispositivo)

        id_dispositivo = dispositivo.id_dispositivo

        # 2. Búsqueda del paciente asociado
        assoc = session.query(PacienteDispositivo).filter_by(
            id_dispositivo=id_dispositivo,
            fecha_hora_disoc=None
        ).first()

        id_paciente = assoc.id_paciente if assoc else None
        sensor_tipo = msg.topic.split("/")[-1].lower()

        # 3. Procesamiento según el tipo de sensor
        if sensor_tipo == "ecg":
            raw_values = payload.get("raw_values", [])
            nuevo = ECG(
                id_dispositivo=id_dispositivo,
                id_paciente=id_paciente,
                fecha_inicio=timestamp,
                frecuencia_muestreo=payload.get("FS", 360),
                sample_number=payload.get("sample_number", len(raw_values)),
                valor=[float(x) for x in raw_values],
                modo=payload.get("mode")
            )
            session.add(nuevo)

            # Usamos nuestro nuevo procesador de señales importado
            if raw_values:
                try:
                    fs = payload.get("FS", 360)
                    filtered = ecg_filter_realtime(raw_values, fs, uid_equipo)
                    payload["raw_values"] = filtered.tolist()
                except:
                    payload["raw_values"] = raw_values

        elif sensor_tipo == "pni":
            try:
                sist, diast = map(int, payload.get("value", "0/0").split("/"))
            except:
                return
            nuevo = LecturaPNI(
                id_dispositivo=id_dispositivo,
                id_paciente=id_paciente,
                fecha_hora=timestamp,
                presion_sistolica=sist,
                presion_diastolica=diast,
                modo=payload.get("mode")
            )
            session.add(nuevo)

        else:
            valor = payload.get("value")
            if valor is None:
                return
            nuevo = LecturaGeneral(
                id_dispositivo=id_dispositivo,
                id_paciente=id_paciente,
                tipo_sensor=sensor_tipo,
                fecha_hora=timestamp,
                valor_numerico=float(valor),
                modo=payload.get("mode")
            )
            session.add(nuevo)

        session.commit()
        
        # 4. Usamos nuestro nuevo gestor de WebSockets para emitir el dato
        ws_manager.broadcast_sync(sensor_tipo, payload)

    except Exception as e:
        print("[ERROR MQTT]", e)
        session.rollback()
    finally:
        session.close()

def iniciar_mqtt():
    """Configura y arranca el cliente MQTT en segundo plano."""
    global mqtt_client
    mqtt_client = MQTTClient(
        client_id="fastapi_api_listener",
        callback_api_version=CallbackAPIVersion.VERSION2
    )
    mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_disconnect = on_disconnect
    mqtt_client.on_message = on_message
    
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    # loop_start() arranca un hilo automáticamente, no bloquea FastAPI
    mqtt_client.loop_start() 

def detener_mqtt():
    """Apaga el cliente de forma limpia."""
    if mqtt_client:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()