# 🏥 API de Monitoreo de Signos Vitales

API desarrollada con FastAPI para la gestión y monitoreo en tiempo real de signos vitales (ECG, SpO₂, temperatura, PNI) mediante dispositivos conectados por MQTT.

---

## 🚀 Tecnologías utilizadas

* Python 3
* FastAPI
* PostgreSQL
* SQLAlchemy
* MQTT (paho-mqtt)
* NumPy / SciPy (procesamiento de señal ECG)
* WebSockets
* Matplotlib

---

## 📦 Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/juli-sz/monitor
cd monitor
```

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
3. con click derecho en el archivo index y abrir con live server (si no lo tienen se debe instalar en visual estudio la extension live server o entrar a la direccion http://127.0.0.1:5500/index.html)
esto abre una ventana en el navegador mostrando las tarjetas de los dispositivos conectados


## 👨‍💻 Autor

Desarrollado por Salvador Carlos

Actualmente modificandose por Juliana Saez

---

## 📄 Licencia

Este proyecto es de uso educativo y profesional.

