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
git clone https://github.com/salvadorcarlos/signos-vitales.git](https://github.com/salvadorcarlos/monitor.git
cd signos-vitales
```

---

### 2. Crear entorno virtual

```bash o en la misma termina del vsc
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

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

---

## ⚙️ Configuración

### 🔹 Base de datos PostgreSQL

Crear base de datos:

```sql
CREATE DATABASE tu_basededatos ( aca le ponen el nombre q quieran peor recomiendo q se mantenga el nombre "tus_basedadatos" xq es el q usa el codigo;
```

---



---

## ▶️ Ejecución

```bash
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
signos-vitales/
│── mainf.py
│── requirements.txt
│── .gitignore
│── README.md
```

---

pasemos al frontend se debe tener habilitado la conexiòn websocket en la pc
flujo 
1 corren la api con uvicorn mainf:app --reload
2 conectan un esp32 ( corren el script de muestra con el nombre de paciente1 0 paciente 2)
3 con click derecho en el archivo index y abrir con live server ( si no lo tienen se debe instalar en visual estudio la extension live server)
esto abre una ventana en el navegador mostrando las terjetas de los dispositivos conectados
---

## 👨‍💻 Autor

Desarrollado por Salvador Carlos

---

## 📄 Licencia

Este proyecto es de uso educativo y profesional.

