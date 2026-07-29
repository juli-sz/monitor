# Sistema de Monitoreo de Signos Vitales IoT

Plataforma de telemetría médica para el monitoreo remoto y en tiempo real de pacientes, con ingesta de datos vía MQTT desde dispositivos ESP32, autenticación JWT y control de acceso por roles.

## Contenido

- [Descripción](#descripción)
- [Arquitectura](#arquitectura)
- [Stack tecnológico](#stack-tecnológico)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Puesta en marcha](#puesta-en-marcha)
- [Uso de la API](#uso-de-la-api)
- [Roles y permisos](#roles-y-permisos)
- [Modelo de datos](#modelo-de-datos)
- [Testing](#testing)
- [Documentación adicional](#documentación-adicional)
- [Seguridad](#seguridad)
- [Estado del proyecto](#estado-del-proyecto)

## Descripción

El sistema recibe telemetría (SpO2, ECG, presión arterial, temperatura) de múltiples dispositivos ESP32 vía MQTT, la procesa y persiste en PostgreSQL, evalúa un motor de alertas contra rangos configurables por paciente, y transmite eventos en tiempo real al frontend mediante WebSockets. El acceso a la API está protegido con JWT y un esquema de roles (admin, médico, enfermero, visor).

Proyecto desarrollado como parte de un plan de trabajo anual (becario junior), actualmente en la etapa de testing y contenerización.

## Arquitectura

```
Dispositivo ESP32
      │  MQTT (paho-mqtt)
      ▼
services/mqtt_service.py  ──▶  PostgreSQL (SQLAlchemy)
      │
      ▼
Motor de alertas  ──▶  services/websocket_manager.py
                              │
                              ▼
                        Frontend (WebSocket, tiempo real)
```

La API expone además endpoints REST (FastAPI) para CRUD de pacientes, dispositivos, usuarios, alertas e histórico, todos detrás de autenticación JWT y validación de rol.

## Stack tecnológico

**Backend**

| Componente | Tecnología |
|---|---|
| Framework | FastAPI 0.135 |
| ORM | SQLAlchemy 2.0 |
| Base de datos | PostgreSQL 16 |
| Autenticación | JWT (PyJWT) + bcrypt |
| Validación | Pydantic v2 |
| Mensajería IoT | MQTT (paho-mqtt) |
| Tiempo real | WebSockets (asyncio) |
| Procesamiento de señal | NumPy, SciPy |
| Gráficos ECG | Matplotlib |
| Testing | pytest, pytest-asyncio, pytest-cov |

**Frontend**

HTML5 + Bootstrap 5, JavaScript vanilla, uPlot para gráficos ECG en tiempo real.

**Infraestructura**

Uvicorn (ASGI), Docker + Docker Compose (API + PostgreSQL), Git.

## Estructura del proyecto

```
monitor/
├── mainf.py                    # Punto de entrada FastAPI
├── models.py                   # Modelos SQLAlchemy (10 entidades)
├── config.py                   # Configuración / variables de entorno
├── database.py                 # Engine y sesión de PostgreSQL
│
├── routes/                     # Endpoints REST
│   ├── auth.py                 # Login, registro, refresh, logout
│   ├── pacientes.py            # CRUD de pacientes
│   ├── dispositivos.py         # CRUD de dispositivos
│   ├── usuarios.py             # Gestión de usuarios (solo admin)
│   ├── alertas.py               # Alertas y resolución
│   ├── sensores.py             # Rangos de signos vitales
│   ├── historico.py            # Consultas históricas y ECG
│   └── websockets.py           # Conexiones WebSocket
│
├── services/                   # Lógica de negocio
│   ├── auth_service.py         # JWT, hashing de contraseñas
│   ├── permissions.py          # Dependencia de control de acceso por rol
│   ├── mqtt_service.py         # Cliente MQTT / ingesta de telemetría
│   ├── websocket_manager.py    # Gestión de conexiones WebSocket
│   └── signal_processor.py     # Filtros y procesamiento de ECG
│
├── schemas/                     # Esquemas Pydantic
├── admin/                       # Frontend (dashboard, gestión, monitor)
├── docs/                        # Diagramas de entidad-relación y de flujo
├── pruebas_sensores/            # Simuladores de dispositivos IoT (MQTT)
├── tests/                       # Suite de tests (pytest)
├── db/init/                     # Scripts de inicialización de BD (Docker)
│
├── Dockerfile
├── docker-compose.yml
├── requirements.txt              # Dependencias de producción
├── requirements-dev.txt          # Dependencias de testing
└── .env.example                  # Plantilla de variables de entorno
```

## Puesta en marcha

Dos caminos: **Docker** (base de datos incluida, cero instalación local) o **entorno local** (requiere PostgreSQL instalado). Los pasos de configuración de `.env` y de MQTT son los mismos en ambos casos.

### 1. Clonar el repo y configurar variables de entorno

```bash
git clone <url-del-repo> monitor
cd monitor
cp .env.example .env
```

Editá `.env`:

```bash
# Generá una clave propia para firmar los JWT (no usar la de ejemplo)
python -c "import secrets; print(secrets.token_hex(32))"
```

Pegá el resultado en `SECRET_KEY`. El resto de las variables (`DATABASE_URL`, `MQTT_*`) se explican en los pasos siguientes.

### 2. Base de datos

**Con Docker:** no requiere ningún paso manual. `docker-compose.yml` levanta un contenedor PostgreSQL 16 con las bases `monitor` (datos de la app) y `monitor_test` (para pytest), usando las credenciales que definas en `.env`. Al arrancar la API, `mainf.py` ejecuta `Base.metadata.create_all(bind=engine)`, que crea automáticamente todas las tablas si no existen — no hay que correr migraciones a mano.

**Sin Docker (PostgreSQL local):**

1. Instalá PostgreSQL 16 y asegurate de que el servicio esté corriendo.
2. Creá la base y el usuario de la app:
   ```bash
   psql -U postgres -c "CREATE USER monitor WITH PASSWORD 'monitor';"
   psql -U postgres -c "CREATE DATABASE monitor OWNER monitor;"
   ```
3. (Opcional, solo si vas a correr los tests) creá también la base de test:
   ```bash
   psql -U postgres -c "CREATE DATABASE monitor_test OWNER monitor;"
   ```
4. En `.env`, apuntá `DATABASE_URL` a esa base:
   ```
   DATABASE_URL=postgresql://monitor:monitor@localhost:5432/monitor
   ```
5. Las tablas se crean solas la primera vez que arranca la API (paso 4 de esta guía) — no hace falta ejecutar ningún script de creación de esquema.

### 3. Conexión MQTT

La API solo **suscribe** telemetría; no necesita un broker propio para arrancar. Si `MQTT_BROKER` queda vacío en `.env`, el servidor levanta igual sin ingesta de datos (útil para trabajar solo sobre los endpoints REST).

**Opción A — Usar un broker existente**

Completá en `.env`:

```
MQTT_BROKER=<host-del-broker>
MQTT_PORT=1883
MQTT_USERNAME=<usuario>
MQTT_PASSWORD=<contraseña>
MQTT_TOPIC=datos/sensores/#
```

`services/mqtt_service.py` se conecta a ese broker al iniciar la API y se suscribe a `MQTT_TOPIC`. El tipo de sensor se infiere del último segmento del topic (`datos/sensores/ecg`, `datos/sensores/spo2`, `datos/sensores/bpm`, `datos/sensores/pni`, `datos/sensores/temperatura_piel`, etc.), así que cualquier publicador que respete ese formato de topic y payload JSON es compatible.

**Opción B — Broker local para desarrollo/pruebas (recomendado si no tenés uno)**

1. Instalá y arrancá Mosquitto (o cualquier broker MQTT) en tu máquina, escuchando en `localhost:1883`.
2. En `.env`:
   ```
   MQTT_BROKER=localhost
   MQTT_PORT=1883
   MQTT_USERNAME=
   MQTT_PASSWORD=
   MQTT_TOPIC=datos/sensores/#
   ```
3. Simulá dispositivos ESP32 con los scripts de `pruebas_sensores/` (`p1.py` … `p13.py`), que publican payloads de ejemplo (ECG, SpO2, PNI, temperatura, etc.) en `datos/sensores/<tipo>`:
   ```bash
   pip install paho-mqtt
   python pruebas_sensores/p1.py
   ```
   Antes de correrlo, revisá el `BROKER`/`USUARIO`/`CONTRASENA` hardcodeados al inicio del script y ajustalos a tu broker local.
4. Con la API corriendo, deberías ver en sus logs `MQTT conectado exitosamente` y, al publicar, los datos llegando a la base y propagándose por WebSocket al frontend en tiempo real.

### 4. Levantar el servidor

**Con Docker:**

```bash
docker compose up --build -d
docker compose logs -f api      # verificar arranque y conexión MQTT
```

Guía extendida (troubleshooting, comandos del día a día) en [DOCKER.md](./DOCKER.md).

**Local:**

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
uvicorn mainf:app --reload --port 8000
```

### 5. Verificar la instalación

- `http://localhost:8000/` → `{"message": "API funcionando correctamente"}`
- `http://localhost:8000/docs` → Swagger UI con todos los endpoints
- Frontend: abrí `login.html` en el navegador (ya apunta a `http://localhost:8000`)

## Uso de la API

```bash
# 1. Registrar usuario
curl -X POST http://localhost:8000/auth/registro \
  -H "Content-Type: application/json" \
  -d '{"nombre":"Admin","email":"admin@test.com","password":"123456","rol":"admin"}'

# 2. Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@test.com","password":"123456"}'
# → { "access_token": "...", "refresh_token": "...", "token_type": "bearer", "rol": "admin" }

# 3. Consumir un endpoint protegido
curl -X GET http://localhost:8000/pacientes/ \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

## Roles y permisos

Cada endpoint declara los roles habilitados mediante la dependencia `requiere_rol(...)` (`services/permissions.py`).

| Rol | Alcance |
|---|---|
| **Admin** | Acceso total: usuarios, pacientes, dispositivos, alertas |
| **Médico** | CRUD de pacientes, lectura de dispositivos, gestión de alertas, histórico completo |
| **Enfermero** | Lectura de pacientes/dispositivos, resolución de alertas, histórico |
| **Visor** | Solo lectura: pacientes, alertas, histórico |

## Modelo de datos

10 entidades principales (`models.py`): `Usuario`, `Paciente`, `Dispositivo`, `Sensor`, `LecturaGeneral`, `ECG`, `LecturaPNI`, `RangoSignoVital`, `Alerta`, `PacienteDispositivo`. Diagrama entidad-relación en [`docs/MER_telemetria.html`](./docs/MER_telemetria.html) y descripción en [`docs/estructura.md`](./docs/estructura.md).

## Testing

Suite de 91 tests con ~97% de cobertura, corridos contra una base PostgreSQL de test dedicada (nunca contra los datos reales).

```bash
# Con Docker
docker compose exec api pytest --cov=. --cov-report=term-missing

# Local
pip install -r requirements.txt -r requirements-dev.txt
pytest --cov=. --cov-report=term-missing
```

Detalle de qué cubre cada archivo de test en [`tests/README.md`](./tests/README.md).

## Documentación adicional

| Documento | Contenido |
|---|---|
| [DOCKER.md](./DOCKER.md) | Guía completa de contenerización (setup, troubleshooting, comandos) |
| [tests/README.md](./tests/README.md) | Estructura y alcance de la suite de tests |
| [docs/estructura.md](./docs/estructura.md) | Descripción del modelo de entidades |
| [docs/MER_telemetria.html](./docs/MER_telemetria.html) | Diagrama entidad-relación |

## Seguridad

- JWT con expiración (access / refresh token) y hashing de contraseñas con bcrypt
- Control de acceso por rol en cada endpoint protegido
- Validación de entrada con Pydantic en todos los inputs
- Variables sensibles fuera del código, vía `.env` (excluido de git)

> `.env` nunca debe commitearse. Usá `.env.example` como plantilla y generá un `SECRET_KEY` propio con `python -c "import secrets; print(secrets.token_hex(32))"`.

## Estado del proyecto

En desarrollo activo — etapa de testing, alertas automáticas y contenerización.

- Fundamentos y CRUD — completo
- Autenticación y RBAC — completo
- Testing y alertas automáticas — en curso
- Documentación y deploy — pendiente

**Licencia**: proyecto académico.
