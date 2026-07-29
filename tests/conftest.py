# tests/conftest.py
# ======================================================
# CONFIGURACIÓN GLOBAL DE LOS TESTS
# ======================================================
# ⚠️ El orden importa: hay que definir DATABASE_URL *antes* de importar
# cualquier módulo del proyecto, porque database.py crea el engine al importarse.

import os
import datetime

# 1. Base de datos de TEST (nunca la de producción/desarrollo)
TEST_DB_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://monitor:monitor@localhost:5432/monitor_test",
)

# Red de seguridad: los tests TRUNCAN todas las tablas, así que nos negamos
# a correr contra una base que no tenga "test" en el nombre.
if "test" not in TEST_DB_URL.rsplit("/", 1)[-1]:
    raise RuntimeError(
        f"La base de datos de tests debe contener 'test' en su nombre: {TEST_DB_URL!r}. "
        "Configurá TEST_DATABASE_URL correctamente."
    )

os.environ["DATABASE_URL"] = TEST_DB_URL
os.environ.setdefault("SECRET_KEY", "clave_secreta_solo_para_tests")
# Nos aseguramos de que ningún test intente conectarse a un broker MQTT real
os.environ.pop("MQTT_BROKER", None)


def _asegurar_bd_de_test(url_str: str) -> None:
    """Crea la base de datos de test si no existe (conectándose a la BD 'postgres')."""
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
    from sqlalchemy.engine import make_url

    url = make_url(url_str)
    try:
        conn = psycopg2.connect(
            dbname="postgres",
            user=url.username,
            password=url.password,
            host=url.host or "localhost",
            port=url.port or 5432,
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (url.database,))
            if not cur.fetchone():
                cur.execute(f'CREATE DATABASE "{url.database}"')
        conn.close()
    except Exception:
        # Si no tenemos permisos para crearla, asumimos que ya existe
        # (en docker-compose la crea el script db/init/01-crear-bd-test.sql).
        pass


_asegurar_bd_de_test(TEST_DB_URL)

# 2. Recién ahora importamos el proyecto (esto crea el engine contra la BD de test)
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

import mainf  # noqa: E402  (registra la app, los routers y crea las tablas)
import models  # noqa: E402
from database import SessionLocal, engine  # noqa: E402
from services.auth_service import hashear_password, crear_token_acceso  # noqa: E402

# Por las dudas (mainf ya lo hace al importarse, es idempotente)
models.Base.metadata.create_all(bind=engine)


# ======================================================
# FIXTURES BASE
# ======================================================

@pytest.fixture(autouse=True)
def bd_limpia():
    """Trunca todas las tablas antes de cada test para que sean independientes."""
    tablas = ", ".join(
        f'"{t.name}"' for t in reversed(models.Base.metadata.sorted_tables)
    )
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE TABLE {tablas} RESTART IDENTITY CASCADE"))
    yield


@pytest.fixture
def client():
    # OJO: sin "with" no se ejecuta el lifespan => no se intenta conectar MQTT.
    return TestClient(mainf.app)


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()


# ======================================================
# FÁBRICAS DE DATOS (factories)
# ======================================================

@pytest.fixture
def crear_paciente(db):
    def _crear(**kwargs):
        datos = {
            "nombre": "Juan",
            "apellido": "Pérez",
            "dni": "30123456",
            "sexo": "M",
            "tipo": "Internado",
            "diagnostico": "Observación",
        }
        datos.update(kwargs)
        paciente = models.Paciente(**datos)
        db.add(paciente)
        db.commit()
        db.refresh(paciente)
        return paciente

    return _crear


@pytest.fixture
def crear_dispositivo(db):
    def _crear(**kwargs):
        datos = {"uid_equipo": "ESP32-TEST-01", "estado": "Activo"}
        datos.update(kwargs)
        disp = models.Dispositivo(**datos)
        db.add(disp)
        db.commit()
        db.refresh(disp)
        return disp

    return _crear


@pytest.fixture
def asociar(db):
    """Crea el vínculo paciente-dispositivo (asociación activa por defecto)."""

    def _asociar(paciente, dispositivo, disociado=False):
        asoc = models.PacienteDispositivo(
            id_paciente=paciente.id_paciente,
            id_dispositivo=dispositivo.id_dispositivo,
            fecha_hora_disoc=(
                datetime.datetime.now(datetime.timezone.utc) if disociado else None
            ),
        )
        db.add(asoc)
        db.commit()
        db.refresh(asoc)
        return asoc

    return _asociar


@pytest.fixture
def crear_usuario(db):
    def _crear(email="admin@test.com", password="secreto123", rol="admin",
               nombre="Admin Test", activo=True):
        usuario = models.Usuario(
            email=email,
            password_hash=hashear_password(password),
            nombre=nombre,
            rol=rol,
            activo=activo,
        )
        db.add(usuario)
        db.commit()
        db.refresh(usuario)
        return usuario

    return _crear


@pytest.fixture
def headers_para_rol(crear_usuario):
    """Crea un usuario con el rol dado y devuelve headers Authorization listos
    para pasarle a client.get/post/... . Ej: client.get("/pacientes/", headers=headers_para_rol("medico"))
    """
    contador = {"n": 0}

    def _headers(rol="admin"):
        contador["n"] += 1
        usuario = crear_usuario(email=f"auth-{rol}-{contador['n']}@test.com", rol=rol)
        token = crear_token_acceso({"sub": str(usuario.id_usuario), "rol": usuario.rol})
        return {"Authorization": f"Bearer {token}"}

    return _headers


@pytest.fixture
def admin_headers(headers_para_rol):
    return headers_para_rol("admin")


@pytest.fixture
def medico_headers(headers_para_rol):
    return headers_para_rol("medico")


@pytest.fixture
def enfermero_headers(headers_para_rol):
    return headers_para_rol("enfermero")


@pytest.fixture
def visor_headers(headers_para_rol):
    return headers_para_rol("visor")


@pytest.fixture
def crear_lectura(db):
    def _crear(dispositivo, tipo_sensor="temperatura", valor=36.5,
               fecha_hora=None, paciente=None):
        lectura = models.LecturaGeneral(
            id_dispositivo=dispositivo.id_dispositivo,
            id_paciente=paciente.id_paciente if paciente else None,
            tipo_sensor=tipo_sensor,
            fecha_hora=fecha_hora or datetime.datetime.now(datetime.timezone.utc),
            valor_numerico=valor,
        )
        db.add(lectura)
        db.commit()
        db.refresh(lectura)
        return lectura

    return _crear


@pytest.fixture
def crear_bloque_ecg(db):
    def _crear(dispositivo, valores=None, fs=360, fecha_inicio=None, paciente=None):
        valores = valores if valores is not None else [0.1, 0.2, 0.3, 0.5, 0.2, 0.1]
        bloque = models.ECG(
            id_dispositivo=dispositivo.id_dispositivo,
            id_paciente=paciente.id_paciente if paciente else None,
            fecha_inicio=fecha_inicio or datetime.datetime.now(datetime.timezone.utc),
            frecuencia_muestreo=fs,
            sample_number=len(valores),
            valor=valores,
        )
        db.add(bloque)
        db.commit()
        db.refresh(bloque)
        return bloque

    return _crear
