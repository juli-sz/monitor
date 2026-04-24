import paho.mqtt.client as mqtt
import json
import time
import random
import math
from datetime import datetime

# --- Configuración del broker MQTT ---
BROKER = "127.0.0.1"
PORT = 1883
TOPICO_BASE = "datos/sensores"
USUARIO = "juli"
CONTRASENA = "juliBAR"

# --- Callbacks MQTT ---
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Conectado exitosamente al broker MQTT.")
    else:
        print(f"❌ Error de conexión. Código de retorno: {rc}")

def on_disconnect(client, userdata, rc):
    print("⚠️ Desconectado del broker.")

# --- Cliente MQTT ---
client = mqtt.Client()
client.username_pw_set(USUARIO, CONTRASENA)
client.on_connect = on_connect
client.on_disconnect = on_disconnect

# --- Función para simular onda ECG ---
def generate_ecg_wave(num_samples, heart_rate_bpm=70, amplitude=1.0, noise_level=0.05):
    ecg_data = []
    time_per_beat = 60 / heart_rate_bpm
    num_beats_in_segment = 1 / time_per_beat
    samples_per_beat = num_samples / num_beats_in_segment
    if samples_per_beat < 100:
        samples_per_beat = 100
        num_beats_in_segment = num_samples / samples_per_beat

    current_sample = 0
    while current_sample < num_samples:
        for i in range(int(samples_per_beat)):
            if current_sample >= num_samples:
                break
            if 0 <= i < samples_per_beat * 0.1:
                val = amplitude * 0.1 * math.sin(math.pi * i / (samples_per_beat * 0.1))
            elif samples_per_beat * 0.1 <= i < samples_per_beat * 0.2:
                if i < samples_per_beat * 0.15:
                    val = -amplitude * 0.3 * math.sin(math.pi * (i - samples_per_beat * 0.1) / (samples_per_beat * 0.05))
                elif i < samples_per_beat * 0.175:
                    val = amplitude * 1.0 * math.sin(math.pi * (i - samples_per_beat * 0.15) / (samples_per_beat * 0.025))
                else:
                    val = -amplitude * 0.5 * math.sin(math.pi * (i - samples_per_beat * 0.175) / (samples_per_beat * 0.025))
            elif samples_per_beat * 0.3 <= i < samples_per_beat * 0.5:
                val = amplitude * 0.2 * math.sin(math.pi * (i - samples_per_beat * 0.3) / (samples_per_beat * 0.2))
            else:
                val = 0
            val += random.uniform(-noise_level, noise_level)
            ecg_data.append(round(val, 3))
            current_sample += 1
    while len(ecg_data) < num_samples:
        ecg_data.append(ecg_data[-1] if ecg_data else 0)
    return ecg_data[:num_samples]

# --- Función para simular PPG de canal rojo e infrarrojo ---
def generate_ppg_wave(num_samples=100, heart_rate_bpm=75, noise_level=0.01):
    ppg_r, ppg_ir = [], []
    t = 0
    fs = num_samples  # muestreo en 1 segundo
    for i in range(num_samples):
        base_wave = math.sin(2 * math.pi * heart_rate_bpm * (t / 60)) ** 2
        ir_val = 0.8 + 0.2 * base_wave + random.uniform(-noise_level, noise_level)
        r_val = 0.6 + 0.25 * base_wave + random.uniform(-noise_level * 2, noise_level * 2)
        ppg_ir.append(round(ir_val, 4))
        ppg_r.append(round(r_val, 4))
        t += 1 / fs
    return ppg_r, ppg_ir

# --- Cálculo de SpO₂ ---
def calculate_spo2(ppg_r, ppg_ir):
    ac_r = max(ppg_r) - min(ppg_r)
    dc_r = sum(ppg_r) / len(ppg_r)
    ac_ir = max(ppg_ir) - min(ppg_ir)
    dc_ir = sum(ppg_ir) / len(ppg_ir)
    ratio = (ac_r / dc_r) / (ac_ir / dc_ir)
    spo2 = 110 - 25 * ratio
    return max(0, min(100, round(spo2, 1)))

# --- Publicación de datos ---
def publicar_datos_sensores():
    timestamp = int(time.time())
    uid_equipo = "rtrt-rtrtr-rtrtr2"

    # ECG
    ecg_values = generate_ecg_wave(num_samples=500, heart_rate_bpm=random.randint(60, 100))
    payload_ecg = {
        "Uid_Equipo": uid_equipo,
        "Date": timestamp,
        "raw_values": ecg_values,
        "sample_number": 500,
        "FS": 500,
        "mode": "active"
    }
    client.publish(f"{TOPICO_BASE}/ecg", json.dumps(payload_ecg))
    print(f"📤 ECG publicado en {TOPICO_BASE}/ecg")

    # SpO₂
    spo2_r, spo2_ir = generate_ppg_wave(num_samples=100, heart_rate_bpm=random.randint(60, 100))
    spo2_value = calculate_spo2(spo2_r, spo2_ir)
    payload_spo2 = {
        "Uid_Equipo": uid_equipo,
        "Date": timestamp,
        "value": spo2_value,
        "SPO2_R": spo2_r,
        "SPO2_IR": spo2_ir,
        "mode": "active"
    }
    client.publish(f"{TOPICO_BASE}/spo2", json.dumps(payload_spo2))
    print(f"📤 SpO₂ publicado ({spo2_value}%) en {TOPICO_BASE}/spo2")

    # PNI
    sys_val = random.randint(90, 130)
    dia_val = random.randint(60, 90)
    payload_pni = {
        "Uid_Equipo": uid_equipo,
        "Date": timestamp,
        "systolic": sys_val,
        "diastolic": dia_val,
        "value": f"{sys_val}/{dia_val}",
        "mode": "active"
    }
    client.publish(f"{TOPICO_BASE}/pni", json.dumps(payload_pni))
    print(f"📤 PNI publicado en {TOPICO_BASE}/pni")

    # Temperatura
    temp_value = round(random.uniform(35.5, 37.5), 1)
    payload_temp = {
        "Uid_Equipo": uid_equipo,
        "Date": timestamp,
        "value": temp_value,
        "mode": "active"
    }
    client.publish(f"{TOPICO_BASE}/temperatura_piel", json.dumps(payload_temp))
    print(f"📤 Temperatura publicada ({temp_value} °C) en {TOPICO_BASE}/temperatura_piel")

# --- Main ---
def main():
    print(f"🔌 Conectando a {BROKER}:{PORT} como {USUARIO}...")
    try:
        client.connect(BROKER, PORT, keepalive=60)
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return

    client.loop_start()
    try:
        while True:
            publicar_datos_sensores()
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Publicación detenida por el usuario.")
    finally:
        client.loop_stop()
        client.disconnect()
        print("👋 Cliente MQTT desconectado.")

if __name__ == "__main__":
    main()
