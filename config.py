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
# JWT
# ======================================================
# Sin fallback a propósito: el criterio 4 del plan pide que las credenciales
# vivan en el .env y no hardcodeadas. Además, un default silencioso hace que un
# .env mal armado firme los tokens con otra clave sin que nada avise.
SECRET_KEY = os.getenv("SECRET_KEY")

if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY no está definida. "
        "Copiá .env.example a .env y completá la clave, o exportá la variable de entorno. "
        'Podés generar una con: python -c "import secrets; print(secrets.token_hex(32))"'
    )

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

# ======================================================
# CORS
# ======================================================
# Orígenes que pueden consumir la API desde el navegador, separados por coma.
# El default cubre el frontend abierto en local (con y sin servidor estático).
# En producción se define CORS_ORIGINS en el .env con el dominio real.
#
# No usamos "*": combinado con allow_credentials=True la spec de CORS lo prohíbe
# y los navegadores terminan rechazando la respuesta.
CORS_ORIGINS = [
    origen.strip()
    for origen in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:8000,http://127.0.0.1:8000,"
        "http://localhost:5500,http://127.0.0.1:5500,"
        "null",  # archivos HTML abiertos directo con file://
    ).split(",")
    if origen.strip()
]