# 🐳 Levantar el proyecto con Docker

Guía para correr el **Sistema de Monitoreo de Signos Vitales IoT** completo (API + PostgreSQL) usando Docker, sin instalar Python ni Postgres en tu máquina.

---

## Requisitos

- **Docker Desktop** (Windows/Mac) o **Docker Engine + Compose v2** (Linux).
- Verificá que funciona con:

```bash
docker --version
docker compose version
```

---

## Archivos que intervienen

| Archivo | Qué hace |
|---|---|
| `Dockerfile` | Define la imagen de la API (Python 3.12 slim + dependencias + código). |
| `docker-compose.yml` | Orquesta los dos servicios: `db` (PostgreSQL 16) y `api` (FastAPI). |
| `.env.example` | Plantilla de variables de entorno. Se copia como `.env`. |
| `.dockerignore` | Lo que NO entra a la imagen (`.env`, venv, docs, simuladores, etc.). |
| `db/init/01-crear-bd-test.sql` | Corre solo la primera vez: crea la BD `monitor_test` para pytest. |

Dentro de la red de Docker, la API se conecta a Postgres usando el hostname `db` (no `localhost`). Eso ya está resuelto en el `docker-compose.yml`: las variables `DATABASE_URL` y `TEST_DATABASE_URL` se inyectan ahí y **pisan** lo que diga tu `.env`, así que el mismo `.env` te sirve para correr con y sin Docker.

---

## Paso a paso

### 1. Crear el archivo de configuración

```bash
cp .env.example .env
```

Abrí `.env` y completá al menos:

- `SECRET_KEY`: una clave larga y aleatoria para firmar los JWT. Podés generarla con:
  ```bash
  python -c "import secrets; print(secrets.token_hex(32))"
  ```
- `MQTT_BROKER`, `MQTT_PORT`, `MQTT_USERNAME`, `MQTT_PASSWORD`: los datos del broker donde publican los ESP32. **Si los dejás vacíos, la API arranca igual** pero sin recibir telemetría (útil para desarrollo o para probar solo los endpoints REST).

> ⚠️ El `.env` está en `.gitignore` y `.dockerignore` a propósito: nunca lo subas al repo ni lo metas dentro de la imagen.

### 2. Construir y levantar el stack

```bash
docker compose up --build -d
```

La primera vez tarda unos minutos (descarga las imágenes base e instala dependencias). El flag `-d` lo deja corriendo en segundo plano.

Qué pasa por atrás:

1. Se levanta `db` (PostgreSQL) con las bases `monitor` (app) y `monitor_test` (pytest).
2. El healthcheck espera a que Postgres acepte conexiones de verdad.
3. Recién ahí arranca `api`, que crea las tablas automáticamente al iniciar.

### 3. Verificar que anda

```bash
docker compose ps            # ambos servicios deben decir "running" / "healthy"
docker compose logs -f api   # logs de la API en vivo (Ctrl+C para salir)
```

Y en el navegador:

- **http://localhost:8000/** → `{"message": "API funcionando correctamente"}`
- **http://localhost:8000/docs** → Swagger UI con todos los endpoints

En los logs de la API vas a ver el estado del MQTT: `✅ MQTT conectado exitosamente` si el broker respondió, o una advertencia si no está configurado/disponible (la API sigue funcionando igual).

### 4. Usar el frontend

El frontend es estático (`login.html`, `admin/*.html`) y ya apunta a `http://localhost:8000`, así que basta con abrir `login.html` en el navegador con la API dockerizada corriendo.

Para crear el primer usuario podés usar Swagger (`POST /auth/registro`) o:

```bash
curl -X POST http://localhost:8000/auth/registro \
  -H "Content-Type: application/json" \
  -d '{"nombre": "Admin", "email": "admin@demo.com", "password": "admin123", "rol": "admin"}'
```

---

## Correr los tests dentro del contenedor

La imagen ya incluye pytest (viene de `requirements-dev.txt`), y la suite usa la base `monitor_test` — **nunca toca los datos reales** de `monitor`.

```bash
# Suite completa
docker compose exec api pytest

# Con reporte de cobertura (el plan de trabajo pide >= 70%)
docker compose exec api pytest --cov=. --cov-report=term-missing
```

Más detalle sobre la suite en [`tests/README.md`](tests/README.md).

---

## Comandos útiles del día a día

```bash
docker compose stop            # pausar sin borrar nada
docker compose start           # retomar
docker compose down            # bajar contenedores (los datos de la BD se conservan)
docker compose down -v         # ⚠️ bajar TODO incluyendo la base de datos (borrón y cuenta nueva)
docker compose up --build -d   # reconstruir tras cambiar código o requirements
docker compose logs -f db      # logs de Postgres
```

Para entrar a la base de datos:

```bash
docker compose exec db psql -U monitor -d monitor
```

(Consultas útiles: `\dt` lista las tablas, `SELECT * FROM paciente;`, `\q` para salir.)

También podés conectarte con pgAdmin/DBeaver desde tu máquina a `localhost:5432`, usuario `monitor`, contraseña `monitor`.

---

## Problemas comunes

**"port is already allocated" (8000 o 5432)**
Ya tenés algo usando ese puerto (por ejemplo un Postgres local). Opciones: frenar el servicio local, o cambiar el mapeo en `docker-compose.yml` (ej: `"8001:8000"` y entrar por `localhost:8001`).

**La API no conecta a la base / se reinicia en loop**
Mirá `docker compose logs api`. Si el healthcheck de `db` no pasa, revisá `docker compose logs db`. Un `docker compose down -v && docker compose up --build -d` resuelve la mayoría de los estados raros (a costa de borrar los datos).

**Cambié `requirements.txt` y no toma los paquetes nuevos**
Las dependencias se instalan en build, no en runtime: `docker compose up --build -d`.

**Creé el volumen antes de que existiera `db/init/`**
Los scripts de `docker-entrypoint-initdb.d` corren solo con el volumen vacío. Si falta `monitor_test`, creala a mano:
```bash
docker compose exec db psql -U monitor -d postgres -c "CREATE DATABASE monitor_test OWNER monitor;"
```

**Windows: error de fin de línea o "exec format error"**
Cloná/descomprimí el proyecto con Git configurado en `core.autocrlf=input`, o asegurate de que `Dockerfile` y los `.sql` queden con fin de línea LF.

---

## Notas de diseño

- **MQTT es opcional al arrancar**: `services/mqtt_service.py` fue ajustado para que un broker ausente o caído no impida levantar la API (antes, un fallo de conexión tiraba abajo todo el arranque). Esto es clave en Docker, donde el contenedor puede no tener salida de red hacia el broker.
- **Producción**: para una imagen más liviana podés instalar solo `requirements.txt` en el `Dockerfile` (sacando `requirements-dev.txt`); acá se incluyen las herramientas de test porque el plan de trabajo pide correr pytest como criterio de evaluación.
- **Persistencia**: los datos viven en el volumen `pgdata`. Sobreviven a `down`, `stop` y rebuilds; solo mueren con `down -v`.
