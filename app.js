// ==========================================
// CONTROL DE ACCESO (GUARDIA DE SEGURIDAD)
// ==========================================
const token = localStorage.getItem("token");

// Si no hay token guardado en el navegador, lo pateamos al login
if (!token) {
  window.location.replace("../login.html");
  throw new Error("Usuario no autenticado. Deteniendo ejecución.");
}

console.log("✅ Usuario autenticado. Iniciando sistema...");

// ==========================================
// CONFIGURACIÓN DE RUTAS
// ==========================================
const CONFIG = {
  API_BASE_URL: "http://localhost:8000",
  WS_URL: "ws://localhost:8000/ws/datos",
  INTERVALO_ALERTAS_MS: 5000 // Consultar alertas cada 5 segundos máximo para no saturar
};

// ==========================================
// ESTADO GLOBAL
// ==========================================
const equipoToPaciente = {};
const ultimasAlertasCheck = {}; // Guarda cuándo fue la última vez que revisamos alertas por UID
let umbralesGlobales = {};
let alarmasActivas = {};

// ==========================================
// UI & EVENTOS BÁSICOS
// ==========================================
const toggleButton = document.getElementById("menu-toggle");
const sidebar = document.getElementById("sidebar");

if (toggleButton && sidebar) {
    toggleButton.addEventListener("click", () => {
      sidebar.classList.toggle("hidden");
      document.body.style.marginLeft = sidebar.classList.contains("hidden") ? "0" : "220px";
    });
}

// ==========================================
// FUNCIONES DE DATOS (API REST)
// ==========================================
async function getNombrePacientePorUid(uid_equipo) {
  if (equipoToPaciente[uid_equipo] !== undefined) {
    return equipoToPaciente[uid_equipo];
  }
  
  try {
    const resp = await fetch(`${CONFIG.API_BASE_URL}/pacientes_por_dispositivo_uid/${uid_equipo}`, {
      headers: { "Authorization": `Bearer ${token}` }
    });
    
    if (!resp.ok) throw new Error("No encontrado");
    
    const paciente = await resp.json();
    if (paciente && paciente.nombre && paciente.apellido) {
      const nombreCompleto = `${paciente.nombre} ${paciente.apellido}`;
      equipoToPaciente[uid_equipo] = nombreCompleto;
      return nombreCompleto;
    }
  } catch (error) {
    console.warn(`Error al buscar paciente para equipo ${uid_equipo}`);
  }
  
  equipoToPaciente[uid_equipo] = `Equipo: ${uid_equipo} (Sin Asociar)`;
  return equipoToPaciente[uid_equipo];
}

async function cargarUmbrales() {
    try {
        const res = await fetch("http://localhost:8000/sensores", {
            headers: { "Authorization": `Bearer ${token}` }
        });
        const data = await res.json();
        data.forEach(u => {
            umbralesGlobales[u.tipo_signo.toLowerCase()] = { 
                min: parseFloat(u.valor_minimo), 
                max: parseFloat(u.valor_maximo) 
            };
        });
    } catch (e) { console.error("Error cargando umbrales:", e); }
}
cargarUmbrales();

function evaluarUmbral(uid, sensor, valorNumerico, valorTexto) {
    const umbral = umbralesGlobales[sensor.toLowerCase()];
    if (!umbral) return; // Si no hay umbral configurado, ignoramos

    const tarjeta = document.getElementById(`card-${uid}`);
    if (!tarjeta) return;

    const claveAlarma = `${uid}-${sensor}`;
    const esAnomalia = valorNumerico < umbral.min || valorNumerico > umbral.max;

    if (esAnomalia) {
        tarjeta.classList.add("alerta-activa");
        if (!alarmasActivas[claveAlarma]) {
            alarmasActivas[claveAlarma] = true;
            fetch("http://localhost:8000/alertas", {
                method: "POST",
                headers: { 
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify({ uid_equipo: uid, sensor: sensor, valor: valorTexto })
            });
        }
    } else {
        tarjeta.classList.remove("alerta-activa");
        if (alarmasActivas[claveAlarma]) {
            delete alarmasActivas[claveAlarma];
        }
    }
}

async function verificarAlertas(uid, id_paciente) {
  const ahora = Date.now();
  if (ultimasAlertasCheck[uid] && (ahora - ultimasAlertasCheck[uid] < CONFIG.INTERVALO_ALERTAS_MS)) {
    return;
  }
  ultimasAlertasCheck[uid] = ahora;

  try {
    // Usamos el endpoint correcto: /alertas/?estado=ACTIVA y filtramos por paciente en el cliente
    const res = await fetch(`${CONFIG.API_BASE_URL}/alertas/?estado=ACTIVA`, {
      headers: { "Authorization": `Bearer ${token}` }
    });

    if (!res.ok) return;

    const alertas = await res.json();
    const card = document.getElementById(`card-${uid}`);
    if (!card) return;

    const tieneActivas = alertas.some(a => a.id_paciente === id_paciente);
    if (tieneActivas) {
      card.classList.add("alerta-activa");
    } else {
      card.classList.remove("alerta-activa");
    }
  } catch (err) {
    console.error("Error consultando alertas:", err);
  }
}

// ==========================================
// FUNCIONES DE RENDERIZADO (DOM DINÁMICO)
// ==========================================
function actualizarTituloTarjeta(uid, nombrePaciente) {
  const titulo = document.getElementById(`titulo-paciente-${uid}`);
  if (titulo && titulo.textContent !== nombrePaciente) {
    titulo.textContent = nombrePaciente;
  }
}

// Crea la estructura vacía de la tarjeta
function crearTarjetaPaciente(uid, nombrePaciente) {
  const contenedor = document.getElementById("contenedor-pacientes");
  if (!contenedor) return;
  
  const col = document.createElement("div");
  col.className = "col-md-4 mb-4";
  
  col.innerHTML = `
    <div class="card sensor-card h-100" id="card-${uid}">
      <div class="card-body d-flex flex-column">
        <h5 class="card-title text-center fw-bold text-truncate" id="titulo-paciente-${uid}">${nombrePaciente}</h5>
        
        <div id="sensores-container-${uid}" class="mt-3 flex-grow-1"></div>
        
        <hr>
        <small class="text-muted d-block text-center mb-3" id="last-update-${uid}">Esperando datos...</small>
        
        <button class="btn btn-primary w-100 fw-bold mt-auto" onclick="window.location.href='detalle.html?uid=${uid}'">
          Ver Perfil Completo
        </button>
      </div>
    </div>`;
    
  contenedor.appendChild(col);
}

// Agrega o actualiza un sensor específico dentro de la tarjeta
function actualizarSensorDinamico(uid, idSensor, label, valor, colorClass = "text-dark") {
    const container = document.getElementById(`sensores-container-${uid}`);
    if (!container) return;

    let elementoValor = document.getElementById(`${idSensor}-${uid}`);
    
    // Si el sensor no existe en la UI, lo agregamos
    if (!elementoValor) {
        const div = document.createElement("div");
        div.className = "mb-2";
        div.innerHTML = `
            <p class="label mb-0 text-muted small fw-bold">${label}</p>
            <p id="${idSensor}-${uid}" class="sensor-value ${colorClass} mb-0" style="font-size: 1.4em;">${valor}</p>
        `;
        container.appendChild(div);
    } else {
        // Si ya existe, solo le cambiamos el texto
        elementoValor.textContent = valor;
    }
}

// ==========================================
// WEBSOCKETS (CON RECONEXIÓN AUTOMÁTICA)
// ==========================================
let ws;

function conectarWebSocket() {
  // Un WebSocket del navegador no puede mandar headers en el handshake,
  // así que el token viaja como query param.
  ws = new WebSocket(`${CONFIG.WS_URL}?token=${token}`);

  ws.onopen = () => {
    console.log("✅ Conectado al WebSocket de la API");
  };

  ws.onclose = () => {
    console.warn("❌ Desconectado del WebSocket. Reintentando en 3 segundos...");
    setTimeout(conectarWebSocket, 3000);
  };

  ws.onerror = (err) => {
    console.error("Error en WebSocket:", err);
    ws.close(); 
  };

  ws.onmessage = async (event) => {
    try {
      const rawData = JSON.parse(event.data);
      const { sensor, payload } = rawData;
      const uid = payload.Uid_Equipo;

      if (!uid) return;

      const timestamp = new Date().toLocaleTimeString();
      let nombrePaciente = await getNombrePacientePorUid(uid);

      if (!document.getElementById(`card-${uid}`)) {
        crearTarjetaPaciente(uid, nombrePaciente);
      } else {
        actualizarTituloTarjeta(uid, nombrePaciente);
      }

      // ==========================================
      // PARSEAR Y EVALUAR SENSORES (DINÁMICO)
      // ==========================================
      if (sensor === "spo2") {
        actualizarSensorDinamico(uid, "spo2", "Saturación (SpO₂)", `${payload.value ?? "--"} %`, "text-primary");
        if (payload.value !== undefined) {
            evaluarUmbral(uid, "spo2", parseFloat(payload.value), `${payload.value}%`);
        }

        if (payload.pulso || payload.Pr) {
          const pulso = payload.pulso || payload.Pr;
          actualizarSensorDinamico(uid, "pulso", "Frecuencia Cardíaca", `${pulso} bpm`, "text-danger");
          evaluarUmbral(uid, "pulso", parseFloat(pulso), `${pulso} bpm`);
        }
      } 
      else if (sensor === "pni") {
        const val = payload.value ? payload.value.split("/") : ["--", "--"];
        actualizarSensorDinamico(uid, "pni", "Presión Arterial", `${val[0]}/${val[1]} mmHg`, "text-success");
      } 
      else if (sensor === "temp" || sensor === "temperatura_piel") {
        actualizarSensorDinamico(uid, "temperatura", "Temp. de Piel", `${payload.value ?? "--"} °C`, "text-warning");
        if (payload.value !== undefined) {
            evaluarUmbral(uid, "temperatura", parseFloat(payload.value), `${payload.value} °C`);
        }
      } 
      else if ((sensor === "pulso" || sensor === "bpm") && payload.value !== undefined) {
        actualizarSensorDinamico(uid, "pulso", "Frecuencia Cardíaca", `${payload.value} bpm`, "text-danger");
        evaluarUmbral(uid, "pulso", parseFloat(payload.value), `${payload.value} bpm`);
      }
      // SI LLEGA UN SENSOR NUEVO QUE NO PROGRAMAMOS ARRIBA, LO DIBUJA IGUAL:
      else if (sensor !== "ecg") { 
        actualizarSensorDinamico(uid, sensor, sensor.toUpperCase(), `${payload.value ?? '--'}`, "text-info");
      }

      // Actualizamos la hora de última lectura
      const lastUpdateEl = document.getElementById(`last-update-${uid}`);
      if(lastUpdateEl) {
        lastUpdateEl.textContent = `Actualizado: ${timestamp}`;
      }

      try {
        const resPaciente = await fetch(`${CONFIG.API_BASE_URL}/pacientes_por_dispositivo_uid/${uid}`, {
          headers: { "Authorization": `Bearer ${token}` }
        });
        if (resPaciente.ok) {
          const paciente = await resPaciente.json();
          verificarAlertas(uid, paciente.id_paciente);
        }
      } catch (e) { /* Error silencioso */ }

    } catch (e) {
      console.error("Error al procesar el mensaje:", e);
    }
  };
}

// ======================================================
// BUSCADOR EN TIEMPO REAL
// ======================================================
document.addEventListener("DOMContentLoaded", () => {
    const buscador = document.getElementById("buscador-pacientes");
    
    if (buscador) {
        buscador.addEventListener("input", function() {
            const filtro = this.value.toLowerCase();
            const tarjetas = document.querySelectorAll(".sensor-card");
            
            tarjetas.forEach(tarjeta => {
                const contenedorPadre = tarjeta.parentElement; 
                const textoTarjeta = tarjeta.innerText.toLowerCase();
                
                if (textoTarjeta.includes(filtro)) {
                    contenedorPadre.style.display = ""; 
                } else {
                    contenedorPadre.style.display = "none"; 
                }
            });
        });
    }
});

// Iniciar la conexión al cargar el script
conectarWebSocket();