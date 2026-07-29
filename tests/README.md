# 🧪 Suite de tests

Tests automatizados con **pytest** contra una base PostgreSQL de test real (necesaria porque el modelo `ECG` usa `ARRAY`, un tipo exclusivo de Postgres).

## Cómo correrlos

**Con Docker (recomendado, cero configuración):**

```bash
docker compose exec api pytest
docker compose exec api pytest --cov=. --cov-report=term-missing   # con cobertura
```

**Local (sin Docker):** necesitás un PostgreSQL corriendo y la base de test. Por defecto la suite usa `postgresql://monitor:monitor@localhost:5432/monitor_test`; para otra conexión, exportá `TEST_DATABASE_URL` (la crea sola si el usuario tiene permiso `CREATEDB`).

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest --cov=. --cov-report=term-missing
```

## Seguridad de los datos

- `conftest.py` **se niega a correr** si el nombre de la base no contiene `test`, porque cada test trunca todas las tablas. Imposible pisar la base real por accidente.
- El cliente de test **no ejecuta el lifespan** de FastAPI, así que nunca intenta conectarse al broker MQTT.

## Estructura

| Archivo | Qué cubre |
|---|---|
| `conftest.py` | Configuración de la BD de test, cliente HTTP y fábricas de datos (`crear_paciente`, `crear_dispositivo`, `asociar`, `crear_usuario`, `crear_lectura`, `crear_bloque_ecg`). |
| `test_general.py` | Endpoint raíz y `pacientes_por_dispositivo_uid` (asociación activa vs cerrada). |
| `test_pacientes.py` | CRUD completo de pacientes: validación 422, 404, alta con `fecha_egreso`, borrado en cascada de asociaciones/rangos/alertas. |
| `test_dispositivos.py` | CRUD de dispositivos + ciclo de vida de la asociación: asignar, reasignar (cierra la sesión vieja y abre la nueva), desvincular. |
| `test_auth.py` | Registro, login, hash bcrypt, contenido y expiración del JWT, usuario inactivo, firma inválida. |
| `test_usuarios.py` | Gestión de usuarios: no se expone el password, rol inválido, toggle activo/inactivo. |
| `test_alertas_y_sensores.py` | Registro de alertas (con y sin paciente asociado), filtros por estado, resolución masiva por paciente, umbrales globales y por paciente (upsert). |
| `test_historico.py` | Históricos con filtro por fecha y orden, imagen ECG (PNG real), ECG cruda + filtrada, segmentado por rango de tiempo. |
| `test_servicios.py` | Ingesta MQTT (`on_message` con mensajes simulados: general/ECG/PNI/payloads rotos), filtro ECG (SciPy) y WebSocket manager (broadcast, clientes caídos, endpoint `/ws/datos`). |

**Estado actual: 91 tests, ~97% de cobertura** (el plan de trabajo pide ≥ 70%).

## Convenciones

- Cada test es independiente: la fixture `bd_limpia` (autouse) trunca todas las tablas antes de cada uno.
- Los datos de prueba se crean con las fábricas del `conftest`, no a mano en cada test.
- Para probar la ingesta MQTT no hace falta broker: se invoca `on_message` directamente con un mensaje simulado.
