# ⚕️ Estructura del Proyecto — Telemetría

Este documento contiene la documentación completa de la arquitectura del sistema de telemetría, mapeando el Frontend, los Servicios Backend, los Endpoints de la API, el Esquema de la Base de Datos y los Flujos de Datos principales.

---

## 📊 Páginas Frontend

### Vistas Principales
* **🔐 Login** (`login.html`)
    * *Descripción:* Autenticación de usuarios. Guarda el token JWT en `localStorage` y redirige a `panel.html`.
* **📊 Panel (Index)** (`admin/panel.html` · `app.js`)
    * *Descripción:* Vista principal del sistema. Muestra tarjetas en tiempo real por cada dispositivo activo con un badge rojo si existen alarmas activas. Transmite signos vitales mediante conexión directa.
    * *Tecnología:* `WebSocket`
* **👥 Pacientes** (`admin/pacientes.html`)
    * *Descripción:* Tabla general de pacientes activos e históricos con CRUD completo. El botón "Ver" redirige al detalle específico del paciente pasando su ID por parámetro (`?id=`).
* **🧑‍⚕️ Detalle del Paciente** (`admin/detalle.html`)
    * *Descripción:* Permite visualizar la historia clínica, los umbrales configurados, signos vitales en tiempo real y el historial completo de alarmas. Entrada mediante parámetros `?uid=` o `?id=`.
    * *Tecnología:* `WebSocket`
* **📺 Monitor ECG** (`admin/monitorU1.html`)
    * *Descripción:* Monitor clínico a pantalla completa. Renderiza gráficos de ECG y SpO₂ de alta fidelidad utilizando la librería **uPlot**. Cuenta con un panel lateral de vitales y una barra con PNI histórico, temperatura, luz ambiente y algoritmo de detección de asistolia.
    * *Tecnología:* `WebSocket`
* **🔔 Alarmas** (`admin/alarmas.html`)
    * *Descripción:* Vista agrupada de contingencias y alarmas activas. Muestra una tarjeta por paciente con la última alerta disparada por tipo de sensor.
* **📟 Equipos** (`admin/equipos.html`)
    * *Descripción:* Listado de dispositivos de telemetría registrados en el sistema. Muestra su estado actual, el paciente vinculado y permite operaciones de edición y eliminación.
* **📈 Sensores / Umbrales** (`admin/sensores.html`)
    * *Descripción:* Panel de configuración paramétrica de sensores y umbrales de alarma, ya sea de forma personalizada por paciente o generales del sistema.
* **👤 Usuarios** (`admin/usuarios.html`)
    * *Descripción:* Gestión de usuarios y personal de salud. Soporta asignación de roles (`admin`, `medico`, `enfermero`, `visor`) y acciones para activar o desactivar cuentas.

---

## 📡 Servicios Backend

* **📡 MQTT Service** (`services/mqtt_service.py`)
    * *Descripción:* Cliente MQTT basado en la librería `paho`. Se encarga de suscribirse y recibir los datos de los dispositivos físicos a través de los tópicos designados. Invoca al procesador de señales para el análisis de ECG y hace el broadcast al gestor de WebSockets.
* **🔌 WebSocket Manager** (`services/websocket_manager.py`)
    * *Descripción:* Administra centralizadamente todas las conexiones WebSocket activas en el servidor y realiza el broadcast de mensajes en tiempo real a los clientes de la interfaz.
* **🫀 Signal Processor** (`services/signal_processor.py`)
    * *Descripción:* Módulo encargado de aplicar filtros digitales a la señal de ECG en tiempo real (`ecg_filter_realtime`), normalizando y limpiando el ruido de la onda antes de enviarla al frontend.
* **🔐 Auth Service** (`services/auth_service.py`)
    * *Descripción:* Servicio de seguridad encargado de la generación y validación de tokens JWT, además del hashing de contraseñas. Funciona como una dependencia inyectable para proteger las rutas de la API.

---

## 🚀 Endpoints API

| Método | Path | Descripción | Archivo Origen |
| :--- | :--- | :--- | :--- |
| **`POST`** | `/auth/registro` | Registro de nuevo usuario | `routes/auth.py` |
| **`POST`** | `/auth/login` | Login — devuelve JWT | `routes/auth.py` |
| **`GET`** | `/pacientes/` | Lista todos los pacientes | `routes/pacientes.py` |
| **`GET`** | `/pacientes/{id}` | Detalle de un paciente | `routes/pacientes.py` |
| **`POST`** | `/pacientes/` | Crear paciente | `routes/pacientes.py` |
| **`PATCH`** | `/pacientes/{id}` | Editar paciente | `routes/pacientes.py` |
| **`DELETE`** | `/pacientes/{id}` | Eliminar paciente | `routes/pacientes.py` |
| **`GET`** | `/dispositivos/` | Lista dispositivos (incluye id_paciente activo) | `routes/dispositivos.py` |
| **`POST`** | `/dispositivos/` | Registrar dispositivo | `routes/dispositivos.py` |
| **`PATCH`** | `/dispositivos/{id}` | Editar / vincular dispositivo a paciente | `routes/dispositivos.py` |
| **`DELETE`** | `/dispositivos/{id}` | Eliminar dispositivo | `routes/dispositivos.py` |
| **`POST`** | `/alertas/` | Crear nueva alerta | `routes/alertas.py` |
| **`GET`** | `/alertas/?estado=` | Listar alertas (filtro: `ACTIVA` \| `RESUELTA`) | `routes/alertas.py` |
| **`PATCH`** | `/alertas/resolver/paciente/{id}` | Resolver alertas activas de un paciente | `routes/alertas.py` |
| **`GET`** | `/alertas/paciente/{id}` | Historial completo de alertas de un paciente | `routes/alertas.py` |
| **`GET`** | `/sensores/` | Lista todos los sensores | `routes/sensores.py` |
| **`POST`** | `/sensores/` | Crear sensor | `routes/sensores.py` |
| **`GET`** | `/sensores/paciente/{id}` | Umbrales configurados para un paciente | `routes/sensores.py` |
| **`GET`** | `/historico/{uid}/{sensor}` | Historial de lecturas de un sensor por equipo | `routes/historico.py` |
| **`GET`** | `/ecg/imagen_10s/{uid}` | Imagen PNG del último bloque ECG de 10 segundos | `routes/historico.py` |
| **`GET`** | `/historico_ecg/{uid}` | Bloques ECG del equipo | `routes/historico.py` |
| **`GET`** | `/historico_ecg_segmentado/{uid}` | ECG segmentado por latidos | `routes/historico.py` |
| **`GET`** | `/usuarios/` | Lista usuarios del sistema | `routes/usuarios.py` |
| **`POST`** | `/usuarios/` | Crear usuario | `routes/usuarios.py` |
| **`PATCH`** | `/usuarios/{id}/estado` | Activar / desactivar usuario | `routes/usuarios.py` |
| **`GET`** | `/pacientes_por_dispositivo_uid/{uid}` | Paciente activo vinculado a un equipo por UID | `mainf.py` |
| **`🔀 WS`** | `/ws/datos` | WebSocket — broadcast de todos los sensores en tiempo real | `routes/websockets.py` |

---

## 🗄️ Base de Datos (Esquema de Tablas)

### 📌 `usuario`
* **PK:** `id_usuario`
* **Campos:** `email`, `password_hash`, `nombre`, `rol`, `activo`, `creado_en`
* *Nota:* Roles admitidos: `admin` · `medico` · `enfermero` · `visor`.

### 📌 `paciente`
* **PK:** `id_paciente`
* **Campos:** `nombre`, `apellido`, `dni`, `fecha_nacimiento`, `sexo`, `tipo`, `diagnostico`, `fecha_egreso`, `creado_en`
* *Nota:* Si `fecha_egreso = NULL` el paciente se considera activo. Caso contrario, es histórico.

### 📌 `dispositivo`
* **PK:** `id_dispositivo`
* **Campos:** `uid_equipo`, `estado`, `creado_en`
* *Nota:* El campo `uid_equipo` representa el identificador físico único del hardware (ej: `Eq1`).

### 📌 `paciente_dispositivo`
* **PK:** `id`
* **Campos:** `id_paciente (FK)`, `id_dispositivo (FK)`, `fecha_hora_asoc`, `fecha_hora_disoc`
* *Nota:* Tabla pivot de vinculación. Si `fecha_hora_disoc = NULL` la asociación está vigente.

### 📌 `alerta`
* **PK:** `id_alerta`
* **Campos:** `id_dispositivo (FK)`, `id_paciente (FK)`, `descripcion`, `estado`, `fecha_hora`, `resuelta_en`
* *Nota:* Estados posibles: `ACTIVA` \| `RESUELTA`.

### 📌 `rango_signo_vital`
* **PK:** `id_rango`
* **Campos:** `id_paciente (FK, nullable)`, `tipo_signo`, `valor_minimo`, `valor_maximo`, `unidad`
* *Nota:* Si `id_paciente = NULL` el rango se asume como una métrica global por defecto del sistema.

### 📌 `sensor`
* **PK:** `id_sensor`
* **Campos:** `id_dispositivo (FK)`, `tipo`, `estado`, `creado_en`

### 📌 `lecturas_generales`
* **PK:** `id_lectura`
* **Campos:** `id_dispositivo (FK)`, `id_paciente (FK)`, `tipo_sensor`, `fecha_hora`, `valor_numerico`, `modo`
* *Nota:* Registra métricas de SpO₂, temperatura y luz ambiente. Un registro individual por cada lectura.

### 📌 `ecg_bloque`
* **PK:** `id`
* **Campos:** `id_dispositivo (FK)`, `id_paciente (FK)`, `fecha_inicio`, `frecuencia_muestreo`, `sample_number`, `valor [ ]`, `modo`
* *Nota:* El campo `valor` almacena un `ARRAY` de muestras analógicas puras (crudas) del electrocardiograma.

### 📌 `lectura_pni`
* **PK:** `id_lectura`
* **Campos:** `id_dispositivo (FK)`, `id_paciente (FK)`, `fecha_hora`, `presion_sistolica`, `presion_diastolica`, `modo`

---

## 🔗 Relaciones entre Tablas

┌───────────┐             ┌──────────────────────┐             ┌─────────────┐
│  paciente │ 1 ─────── N │  paciente_dispositivo│ N ─────── 1 │ dispositivo │
└─────┬─────┘             └──────────────────────┘             └──────┬──────┘
│                                                               │
├─► alerta (1:N)                                                ├─► alerta (1:N)
├─► rango_signo_vital (1:N)                                      ├─► sensor (1:N)
├─► lecturas_generales (1:N)                                    ├─► lecturas_generales (1:N)
├─► ecg_bloque (1:N)                                            ├─► ecg_bloque (1:N)
└─► lectura_pni (1:N)                                           └─► lectura_pni (1:N)

* **`paciente`:** Posee relación uno a muchos hacia las tablas de telemetría y eventos (`alerta`, `rango_signo_vital`, `lecturas_generales`, `ecg_bloque`, `lectura_pni`). Se vincula bidireccionalmente con `dispositivo` mediante la tabla intermedia `paciente_dispositivo`.
* **`dispositivo`:** Mapea múltiples registros en sensores, alertas, lecturas y bloques de ondas. Su conexión con el paciente activo depende de la tabla pivote.
* **`paciente_dispositivo` (Tabla Pivot):** Contiene las llaves foráneas `id_paciente` e `id_dispositivo`. La bandera de conexión se determina validando que `fecha_hora_disoc` se encuentre vacía (`NULL`).
* **`rango_signo_vital`:** Su clave `id_paciente` es nullable; los registros con herencia huérfana (`NULL`) se consideran la base reglamentaria global del hospital.

---

## 🔄 Flujos de Datos Principales

### 1. Tiempo Real (Sensores ➔ Frontend)
1. El **Dispositivo físico** publica los paquetes de telemetría en el *MQTT Broker* bajo tópicos específicos por sensor.
2. El script `mqtt_service.py` captura el mensaje entrante y deriva los datos al `signal_processor` para filtrar e interpolar la onda de ECG.
3. El `ws_manager.broadcast(msg)` toma la carga limpia y la distribuye a todas las terminales cliente activas.
4. Los scripts cliente (`app.js`, `detalle.html`, `monitorU1.html`) atrapan el JSON y discriminan la información mediante el identificador físico (`uid_equipo`).
5. La **UI de usuario** refresca de manera asíncrona los contenedores, las gráficas dinámicas de `uPlot` y los displays numéricos.

### 2. Ciclo de Vida de una Alarma
1. El backend (`signal_processor`) intercepta una lectura que supera o disminuye los límites configurados en `rango_signo_vital` para ese paciente.
2. Se ejecuta una petición interna al endpoint `POST /alertas/`, generando un evento en la base de datos con estado primario `ACTIVA`.
3. El cliente web interroga periódicamente o mediante eventos a `GET /alertas/?estado=ACTIVA`, provocando que la UI dibuje un *badge* de peligro color rojo en el panel general.
4. El personal de guardia visualiza la contingencia desde `admin/alarmas.html` (agrupada convenientemente con la última anomalía detectada).
5. Tras estabilizar al paciente, el médico interactúa con la plataforma disparando un `PATCH /alertas/resolver/paciente/{id}`, actualizando la base de datos con estado `RESUELTA` y estampando la marca temporal `resuelta_en = now()`.

### 3. Vinculación Paciente ↔ Dispositivo
1. Se consume el endpoint `PATCH /dispositivos/{id}` asociando un `id_paciente`, lo que genera una nueva tupla en `paciente_dispositivo` registrando la fecha de inicio (`fecha_hora_asoc`).
2. La API resuelve mediante `GET /pacientes_por_dispositivo_uid/{uid}` filtrando rigurosamente aquellas filas donde `fecha_hora_disoc IS NULL`.
3. Para dar de baja una asignación, el método `PATCH` sobreescribe el registro activo modificando el atributo `fecha_hora_disoc` con la marca de tiempo actual (`now()`).
4. Por consiguiente, las llamadas posteriores a `GET /dispositivos/` retornarán de manera transparente el ID del paciente actualmente acoplado.

### 4. Mapa de Navegación Frontend

[login.html] ──(Valida JWT)──► [admin/panel.html]
│
(Click Card) ├─► [admin/detalle.html?uid={uid}] ──► [admin/monitorU1.html?uid={uid}]
│
[admin/pacientes.html] ──────┼─► (Botón Ver) ──► [admin/detalle.html?id={id_paciente}]
│
[admin/alarmas.html] ────────┴─► (Click Badge) ──► [admin/detalle.html?id={id_paciente}]

