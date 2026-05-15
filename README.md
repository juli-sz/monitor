# 🏥 API de Monitoreo de Signos Vitales

API desarrollada con FastAPI para la gestión y monitoreo en tiempo real de signos vitales (ECG, SpO₂, temperatura, PNI) mediante dispositivos conectados por MQTT.

---

## 🚀 Tecnologías utilizadas

* **Backend:** Python 3.10+ (FastAPI, Uvicorn)
* FastAPI
* **Base de Datos:** PostgreSQL & SQLAlchemy (ORM)
* **Protocolos:** MQTT (paho-mqtt) para recepción de sensores & WebSockets para streaming en vivo.
* **Procesamiento:** NumPy & SciPy (Filtros digitales para ondas ECG).
* **Frontend:** HTML5, CSS3, JavaScript (Bootstrap 5).
* **Servicios:** Eclipse Mosquitto (Broker MQTT).
* WebSockets
* Matplotlib

---

## 📁 Estructura del Proyecto

```text
📂 monitor
 ┣ 📂admin                # Interfaz del panel de control web (Frontend)
 ┃ ┣ 📜alarmas.html       # Central de monitoreo de alarmas críticas
 ┃ ┣ 📜equipos.html       # Gestión y vinculación de hardware a pacientes
 ┃ ┗ 📜pacientes.html     # ABM de internados e historial clínico
 ┣ 📂routes               # Endpoints de la API (Controladores)
 ┃ ┣ 📜alertas.py         # Lógica de disparadores y resolución de alarmas
 ┃ ┣ 📜dispositivos.py    # Gestión de hardware físico
 ┃ ┗ 📜pacientes.py       # Gestión de ingreso/egreso de pacientes
 ┣ 📂schemas              # Modelos de validación (Pydantic)
 ┣ 📂services             # Lógica de negocio (MQTT & Signal Processing)
 ┣ 📜database.py          # Configuración de conexión a PostgreSQL
 ┣ 📜mainf.py             # Punto de entrada principal de la aplicación
 ┣ 📜models.py            # Definición de tablas (SQLAlchemy Models)
 ┗ 📜requirements.txt     # Dependencias del proyecto

---

## 📦 Instalación

### 1. Clonar y Preparar el Entorno Python

# Clonar el repositorio
git clone [https://github.com/juli-sz/monitor](https://github.com/juli-sz/monitor)
cd monitor

# Crear entorno virtual
python -m venv venv

# Activar entorno (Windows)
venv\Scripts\activate

# Instalar dependencias

pip install -r requirements.txt

---

### 2. Crear entorno virtual

```bash o en la misma terminal del vsc
python -m venv venv
```

### Activar entorno:

* Windows:

```bash
venv\Scripts\activate
```

* Linux/macOS:

```bash
source venv/bin/activate
```

---

### 3. Instalar dependencias (dentro del venv)

```bash
pip install -r requirements.txt
```

---

## ⚙️ Configuración

### 🔹 Base de datos PostgreSQL

Crear base de datos:

```sql desde postgres (pgAdmin4 x ej)
CREATE DATABASE tu_basededatos 
```

---



---

## ▶️ Ejecución


```bash (desde el venv)
uvicorn mainf:app --reload
```

API disponible en:

```
http://127.0.0.1:8000
```

Documentación automática:

```
http://127.0.0.1:8000/docs
```

---

## 📡 Funcionalidades principales

* Recepción de datos en tiempo real vía MQTT
* Procesamiento de señal ECG (filtro digital)
* Almacenamiento en PostgreSQL
* WebSockets para streaming en vivo
* Endpoints REST para consultas históricas
* Generación de imágenes ECG

---

## 📁 Estructura del proyecto

```
📂 monitor
 ┣ 📂routes
 ┃ ┣ 📜historico.py
 ┃ ┣ 📜pacientes.py
 ┃ ┗ 📜websockets.py
 ┣ 📂services
 ┃ ┣ 📜mqtt_service.py
 ┃ ┣ 📜signal_processor.py
 ┃ ┗ 📜websocket_manager.py 
 ┣ 📜.gitignore
 ┣ 📜app.js
 ┣ 📜config.py
 ┣ 📜database.py
 ┣ 📜index.html
 ┣ 📜mainf.py
 ┣ 📜models.py
 ┣ 📜monitorU1.html
 ┣ 📜paciente1.py
 ┣ 📜paciente2.py
 ┣ 📜README.md
 ┣ 📜requirements.txt
 ┗ 📜styles.css
```



## Conexión del Frontend 
(se debe tener habilitado la conexiòn websocket en la pc) (haber instalado mosquito y configurarlo)
1. corren la api con uvicorn mainf:app --reload
2. conectan un esp32 ( corren el script de muestra con el nombre de paciente1 0 paciente 2)
3. con click derecho en el archivo index y abrir con live server (si no lo tienen se debe instalar en visual estudio la extension live server o entrar a la direccion http://127.0.0.1:5500/monitor/index.html)
esto abre una ventana en el navegador mostrando las tarjetas de los dispositivos conectados


## 👨‍💻 Autor

Desarrollado por Salvador Carlos

Actualmente modificandose por Juliana Saez

---

## 📄 Licencia

Este proyecto es de uso educativo y profesional.

