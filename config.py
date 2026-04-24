import os
from dotenv import load_dotenv

# Carga las variables desde el archivo .env a la memoria del sistema
load_dotenv()

# ======================================================
# BASE DE DATOS
# ======================================================
# Solo busca la variable. Si no la encuentra, devuelve None y fallará al conectar.
DB_URL = os.getenv("DATABASE_URL")

# ======================================================
# MQTT BROKER
# ======================================================
# El host y las credenciales son estrictamente secretas/dinámicas
MQTT_BROKER = os.getenv("MQTT_BROKER")
MQTT_USERNAME = os.getenv("MQTT_USERNAME")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")

# Para puertos o configuraciones genéricas, sí es válido dejar un fallback 
# porque no comprometen la seguridad si alguien lee este archivo.
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "datos/sensores/#")