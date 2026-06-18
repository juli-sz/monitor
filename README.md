# 🏥 Sistema de Monitoreo de Signos Vitales IoT

**Plataforma integral para monitoreo remoto de pacientes en tiempo real**

---

## 📋 Descripción

Sistema de telemetría médica basado en IoT que permite monitorear signos vitales (SpO2, presión arterial, ECG, temperatura) de múltiples pacientes simultáneamente. Integra dispositivos ESP32 conectados vía MQTT, procesa datos en tiempo real, genera alertas automáticas por valores anormales, y proporciona análisis histórico. Implementa autenticación JWT con control de acceso basado en roles (admin, médico, enfermero, visor) para garantizar privacidad. Diseñado para hospitales y centros de salud con escalabilidad y confiabilidad como prioridades.

---

## 🎯 Características Principales

### ✅ Telemetría en Tiempo Real
- Recepción de datos desde múltiples dispositivos ESP32 vía MQTT
- WebSockets para transmisión de alertas instantánea
- Procesamiento de ECG con filtros digitales (FFT, Butterworth)
- Rango dinámico de muestreo (100-500 Hz)

### 🔐 Seguridad & Autenticación
- JWT tokens con expiración (24h access, 7d refresh)
- Bcrypt hashing para contraseñas
- RBAC (4 roles con matriz de permisos)
- Endpoints protegidos por rol

### 🚨 Sistema de Alertas
- Motor de alertas automático (comparación contra rangos personalizados)
- Estados: ACTIVA / RESUELTA
- Historial completo de alertas por paciente/dispositivo

### 📊 Análisis & Visualización
- Histórico de lecturas con filtros temporales
- Generación de gráficos ECG (10s, segmentado)
- Dashboard con estado de dispositivos
- Exportación de datos

### 🏗️ Arquitectura Modular
- FastAPI (async, pydantic validation)
- SQLAlchemy ORM + PostgreSQL
- Servicios desacoplados (auth, MQTT, WebSockets, alertas)
- Clean code con separación de responsabilidades

---

## 🛠️ Stack Tecnológico

### Backend
| Capa | Tecnología |
|------|------------|
| Framework | FastAPI 0.135.2 |
| ORM | SQLAlchemy 2.0 |
| Base de Datos | PostgreSQL 12+ |
| Autenticación | JWT + bcrypt |
| Validación | Pydantic v2 |
| Mensajería | MQTT (paho-mqtt 2.1) |
| Tiempo Real | WebSockets + asyncio |
| Procesamiento | NumPy, SciPy |
| Graficación | Matplotlib |
| Testing | pytest, pytest-asyncio |

### Frontend
| Componente | Tecnología |
|-----------|------------|
| UI | HTML5 + Bootstrap 5 |
| Gráficas | uPlot (ECG real-time) |
| Interactividad | JavaScript vanilla |
| Estilos | CSS3 |

### Infraestructura
| Componente | Tecnología |
|-----------|------------|
| Servidor Web | Uvicorn |
| Producción | Gunicorn + Nginx |
| Containerización | Docker (opcional) |
| Control de Versiones | Git |

---

## 📦 Instalación Rápida

### Prerequisitos
- Python 3.9+
- PostgreSQL 12+
- MQTT Broker (Mosquitto)

### Setup
```bash
# Clonar proyecto
git clone <repo> && cd monitor-vitales

# Entorno virtual
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar .env
echo "DATABASE_URL=postgresql://user:pass@localhost/monitor_vitales" > .env
echo "SECRET_KEY=$(python -c 'import secrets; print(secrets.token_hex(32))')" >> .env

# Sincronizar BD
python -c "from models import Base; from database import engine; Base.metadata.create_all(bind=engine)"

# Ejecutar servidor
uvicorn mainf:app --reload --port 8000
```

**Swagger UI**: http://localhost:8000/docs

---

## 📚 Documentación

| Documento | Contenido |
|-----------|-----------|
| [DEPLOY_GUIDE.md](./DEPLOY_GUIDE.md) | Guía completa de deploy local y producción |
| [MANUAL_USUARIO.md](./MANUAL_USUARIO.md) | Funcionalidades por rol, flujos de uso |
| [TESTING_AUTENTICACION.md](./TESTING_AUTENTICACION.md) | JWT, validación de tokens, testing |
| [TESTING_RBAC.md](./TESTING_RBAC.md) | Matriz de permisos, escenarios RBAC |
| [TESTING_REFRESH_TOKEN.md](./TESTING_REFRESH_TOKEN.md) | Refresh token, renovación de sesión |
| [GUIA_MIGRACION.md](./GUIA_MIGRACION.md) | Migración desde versión anterior |

---

## 🗂️ Estructura del Proyecto

```
monitor-vitales/
├── mainf.py                 # Punto de entrada FastAPI
├── models.py                # Modelos SQLAlchemy (10 entidades)
├── config.py                # Configuración
├── database.py              # Session, engine PostgreSQL
│
├── routes/                  # Endpoints (21 protegidos)
│   ├── auth.py             # Login, registro, refresh, logout
│   ├── pacientes.py        # CRUD pacientes + RBAC
│   ├── dispositivos.py     # CRUD dispositivos + RBAC
│   ├── usuarios.py         # Gestión usuarios (admin only)
│   ├── alertas.py          # Alertas, resolución
│   ├── sensores.py         # Rangos vitales
│   ├── historico.py        # Consultas históricas, ECG
│   └── websockets.py       # Conexiones WS
│
├── services/               # Lógica de negocio
│   ├── auth_service.py    # JWT, bcrypt, hashing
│   ├── permissions.py     # RBAC matrix, validación roles
│   ├── mqtt_service.py    # Cliente MQTT, callback
│   ├── websocket_manager.py # Gestión conexiones WS
│   └── signal_processor.py # Filtros ECG, procesamiento
│
├── schemas/                # Validación Pydantic
│   ├── usuario.py
│   ├── paciente.py
│   ├── dispositivo.py
│   ├── alerta.py
│   └── sensores.py
│
├── admin/                  # Frontend
│   ├── index.html         # Dashboard principal
│   ├── pacientes.html     # Gestión pacientes
│   ├── usuarios.html      # Gestión usuarios
│   ├── equipos.html       # Dispositivos
│   ├── alarmas.html       # Alertas
│   ├── monitorU1.html     # Monitor individual
│   └── panel.html         # Panel de control
│
├── docs/                   # Documentación técnica
│   ├── estructura.md      # Diagrama entidades
│   ├── MER_telemetria.html # Entity-Relationship
│   └── *.svg              # Diagramas flujo
│
├── pruebas_sensores/      # Simuladores IoT
│   ├── p1.py - p13.py     # Scripts que generan datos MQTT
│
├── requirements.txt        # Dependencias Python
├── .env                    # Variables de entorno (no commitear)
└── README.md              # Este archivo

```

---

## 🔑 Entidades Principales

| Entidad | Descripción | Relaciones |
|---------|------------|-----------|
| **Usuario** | Credenciales + rol de acceso | Auth |
| **Paciente** | Datos demográficos, diagnóstico | Dispositivos, Alertas |
| **Dispositivo** | ESP32 identificado por UID | Sensores, Lecturas |
| **Sensor** | Tipo (SpO2, Temp, ECG, etc) | Dispositivo |
| **LecturaGeneral** | Valor + timestamp | Paciente, Dispositivo |
| **ECG** | Bloque de muestras + frecuencia | Paciente, Dispositivo |
| **LecturaPNI** | Presión sistólica/diastólica | Paciente, Dispositivo |
| **RangoSignoVital** | Umbrales normales personalizados | Paciente (opcional) |
| **Alerta** | Evento por valor fuera de rango | Paciente, Dispositivo |
| **PacienteDispositivo** | Histórico de asociaciones | Paciente, Dispositivo |

---

## 👥 Roles y Permisos

### Admin
✅ CRUD total (usuarios, pacientes, dispositivos, alertas)

### Médico
✅ CRUD pacientes  
✅ Leer dispositivos  
✅ Crear/resolver alertas  
✅ Ver histórico completo

### Enfermero
✅ Leer pacientes y dispositivos  
✅ Resolver alertas  
✅ Ver histórico

### Visor
✅ Lectura solo: pacientes, alertas, histórico  
❌ Sin permisos de escritura

---

## 🚀 Inicio Rápido

```bash
# 1. Registrar usuario
curl -X POST http://localhost:8000/auth/registro \
  -H "Content-Type: application/json" \
  -d '{"nombre":"Admin","email":"admin@test.com","password":"123456","rol":"admin"}'

# 2. Login (obtener tokens)
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@test.com","password":"123456"}'

# Respuesta:
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "rol": "admin",
  "nombre": "Admin"
}

# 3. Usar token
curl -X GET http://localhost:8000/pacientes/ \
  -H "Authorization: Bearer <ACCESS_TOKEN>"

# 4. Swagger UI
# Abrir: http://localhost:8000/docs
# Botón "Authorize" → pegar token → testear endpoints
```

---

## 📊 Flujo de Datos

```
Dispositivo ESP32
    ↓ (MQTT)
Broker (161.35.100.210:1884)
    ↓
mainf.py (on_message)
    ↓
Procesar → Base de datos
    ↓
Motor de alertas
    ↓
WebSocket → Frontend (tiempo real)
    ↓
Dashboard actualizado
```

---

## 🔐 Seguridad Implementada

✅ JWT con expiración  
✅ Bcrypt hashing  
✅ RBAC con matriz de permisos  
✅ Validación Pydantic en todos los inputs  
✅ Protección CORS  
✅ Variables de entorno (no hardcodear secretos)  
✅ Endpoints solo accesibles con token válido  

---

## 📈 Métricas de Calidad

- **Endpoints**: 21 protegidos con autenticación
- **Roles**: 4 (admin, médico, enfermero, visor)
- **Permisos**: 41 granulares
- **Entidades**: 10 modelos SQLAlchemy
- **Testing**: pytest (T3: ≥70% cobertura)

---

## 🤝 Contribuciones

Basado en plan de trabajo anual para becario junior:
- **T1 (Sem 1-13)**: Fundamentos y CRUD ✅
- **T2 (Sem 14-26)**: Autenticación y RBAC ✅
- **T3 (Sem 27-39)**: Testing y alertas automáticas 🔄
- **T4 (Sem 40-52)**: Documentación y deploy 📋

---

## 📞 Soporte y Documentación

- **Issues**: Crear issue en repositorio
- **Docs**: Ver carpeta `/docs`
- **API**: Swagger en `/docs` (desarrollo) o `/redoc`

---

## 📄 Licencia

Proyecto académico - Instituto Universitario

---

**Última actualización**: Junio 2026  
**Versión**: 2.0.0 (T2 Completo)  
**Status**: ✅ En desarrollo activo

