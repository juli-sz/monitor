# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

FastAPI backend for an IoT vital-signs monitoring system (SpO2, blood pressure, ECG, temperature) for hospital patients. ESP32 devices publish readings over MQTT; the API ingests them, stores them in PostgreSQL, and pushes live updates to a static HTML/JS frontend over WebSockets. Spanish is the language of the domain: models, routes, and variables use Spanish names (paciente, dispositivo, alerta, rango_signo_vital, etc.) — keep new code consistent with this.

## Commands

Run everything from the repo root (this directory).

**Local setup (no Docker):**
```bash
python -m venv venv && venv\Scripts\activate      # Windows
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env   # then fill in SECRET_KEY at minimum
uvicorn mainf:app --reload --port 8000
```
Swagger UI at `http://localhost:8000/docs`.

**Tests** (needs a real PostgreSQL — the `ECG` model uses a Postgres `ARRAY` column, so SQLite/mocks won't work):
```bash
pytest                                              # full suite
pytest --cov=. --cov-report=term-missing            # with coverage (target: >=70%, currently ~97%)
pytest tests/test_auth.py                           # single file
pytest tests/test_auth.py::test_login_ok            # single test
```
Test DB defaults to `postgresql://monitor:monitor@localhost:5432/monitor_test`; override with `TEST_DATABASE_URL`. `tests/conftest.py` **refuses to run** unless `"test"` appears in the DB name (every test truncates all tables via the autouse `bd_limpia` fixture) — never point `TEST_DATABASE_URL` at the real database.

**Docker (full stack: API + Postgres, zero local install):**
```bash
docker compose up --build -d
docker compose exec api pytest --cov=. --cov-report=term-missing
docker compose logs -f api
```
Inside Docker, `DATABASE_URL`/`TEST_DATABASE_URL` are forced to point at the `db` service host regardless of `.env`. See `DOCKER.md` for troubleshooting (port conflicts, `db/init/` only runs against a fresh volume, etc.).

## Architecture

**Layering:** `mainf.py` (FastAPI app + lifespan) → `routes/*.py` (APIRouters, one per resource) → `services/*.py` (business logic) → `models.py` (SQLAlchemy ORM, single `Base` shared by everything) / `schemas/*.py` (Pydantic request/response models, one per resource, separate from `models.py`).

**Two independent runtime entry points feed the same database:**
1. HTTP/WebSocket requests through FastAPI routes (normal request/response cycle, session via `Depends(get_db)`).
2. `services/mqtt_service.py`'s `on_message` callback, invoked on a paho-mqtt background thread started in `mainf.py`'s `lifespan`. It opens its own `SessionLocal()` (does not use `get_db`), auto-creates a `Dispositivo` row on first sighting of a UID, resolves the currently-associated `Paciente` via `PacienteDispositivo` (association row with `fecha_hora_disoc IS NULL` = active), branches on topic suffix (`ecg` / `pni` / anything else → `LecturaGeneral`), and finally calls `ws_manager.broadcast_sync(...)` to fan the reading out over WebSockets. A missing/unreachable MQTT broker is non-fatal — `iniciar_mqtt()` catches connection errors so the API still starts and serves REST traffic (this matters for Docker/dev environments without network access to the broker).
3. The MQTT thread is synchronous but needs to push into the asyncio WebSocket loop; `ConnectionManager.broadcast_sync` (in `services/websocket_manager.py`) bridges this via `asyncio.run_coroutine_threadsafe` against `ws_manager.main_loop`, which is captured from the running loop during `lifespan` startup.

**Patient/device association model:** patients and devices are linked (and re-linked) over time through `PacienteDispositivo` rows rather than a foreign key on either side. An open association has `fecha_hora_disoc = NULL`; reassigning a device closes the old row and opens a new one. Always check for the active association (not just "any association") when resolving "which patient is this device currently reporting for."

**ECG signal processing** (`services/signal_processor.py`) keeps per-device filter state (`ecg_states` dict, keyed by `uid_equipo`) across calls so the bandpass/notch filters have continuous state for streaming chunks rather than re-initializing per message — don't treat `ecg_filter_realtime` as a pure function.

**Auth/RBAC enforcement.** `services/auth_service.py` issues/hashes tokens (bcrypt + PyJWT, `SECRET_KEY` from env) and exposes `obtener_usuario_actual` — a FastAPI dependency that reads the `Authorization: Bearer <token>` header, decodes/validates the JWT, loads the `Usuario` row, and rejects (401) if the token is missing/invalid/expired or the user is inactive. `services/permissions.py` builds on it with `requiere_rol(*roles)`, a dependency factory that requires login AND membership in an allowed-roles set (403 otherwise). Every resource router now depends on one of these — role assignment follows the README's matrix:
- `routes/usuarios.py`: whole router is `admin`-only (router-level `dependencies=[Depends(requiere_rol("admin"))]`).
- `routes/pacientes.py`, `routes/dispositivos.py`, `routes/sensores.py`, `routes/historico.py`, `routes/alertas.py` GETs, `mainf.py`'s `/pacientes_por_dispositivo_uid/{uid}`: any logged-in role can read (`Depends(obtener_usuario_actual)`).
- Writes are role-gated per-route: `pacientes` POST/PATCH and `alertas` POST → `admin`+`medico`; `pacientes` DELETE and all of `dispositivos` POST/PATCH/DELETE → `admin` only; `sensores` POST (umbrales) → `admin`+`medico`; `alertas` PATCH resolver → `admin`+`medico`+`enfermero`.
- `mainf.py`'s `/` root stays fully public (health check). `routes/auth.py`'s `/auth/login` is public (that's the point). `/auth/registro` is bootstrap-gated (see below).

**`/auth/registro` bootstrap rule:** it's public and unauthenticated ONLY while the `usuario` table is empty, and in that case the requested `rol` must be `"admin"` (400 otherwise) — this is how the very first admin gets created. Once at least one `Usuario` row exists, the same endpoint requires an authenticated `admin` caller (401 with no/invalid token, 403 if authenticated but not admin) — otherwise anyone could self-register as `admin`. The check lives in `routes/auth.py`'s `_autorizar_registro` dependency, which re-queries `Usuario` count rather than trusting client input.

**WebSocket auth (`/ws/datos`):** browsers can't attach custom headers to a WebSocket handshake, so the token travels as a query param: `ws://host/ws/datos?token=<jwt>`. `routes/websockets.py` validates it via `obtener_usuario_actual` before calling `ws_manager.connect()`/`websocket.accept()`; on missing/invalid/expired token it calls `websocket.close(code=1008)` and returns, which surfaces to any WebSocket client (including `TestClient.websocket_connect`) as a rejected handshake rather than a message on an open socket. `app.js`'s `conectarWebSocket()` appends `?token=${token}` (the same token stored in `localStorage` for REST calls) to `CONFIG.WS_URL` when opening the socket.

**Testing conventions** (see `tests/README.md` for full details): every test gets a truncated DB via the autouse `bd_limpia` fixture; use the `conftest.py` factory fixtures (`crear_paciente`, `crear_dispositivo`, `asociar`, `crear_usuario`, `crear_lectura`, `crear_bloque_ecg`) instead of constructing model instances by hand; MQTT ingestion is tested by calling `on_message` directly with a fabricated `msg` object, no broker needed; the `client` fixture builds `TestClient(mainf.app)` without `with`, so the FastAPI `lifespan` (and therefore MQTT connect) never runs during tests. For endpoints behind auth, use the `admin_headers`/`medico_headers`/`enfermero_headers`/`visor_headers` fixtures (or the underlying `headers_para_rol(rol)` factory) from `conftest.py` — each creates a real `Usuario` of that role and returns a ready-to-use `{"Authorization": "Bearer ..."}` dict; pass it as `headers=` on the `client` call.

**Frontend** is static HTML/Bootstrap/vanilla JS (`login.html`, `admin/*.html`, `app.js`, `styles.css`) served independently of the API and pointed at `http://localhost:8000` — there's no build step, just open the HTML files in a browser against a running API.
