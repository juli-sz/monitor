import os

# Base de Datos
# Usamos os.getenv para no dejar contraseñas a la vista. 
# Si no encuentra la variable, usa la cadena por defecto (ideal para desarrollo local).
DB_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:admin@localhost:5432/tu_basededatos")

# MQTT Broker
MQTT_BROKER = os.getenv("MQTT_BROKER", "127.0.0.1")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "juli")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "juliBAR")
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "datos/sensores/#")