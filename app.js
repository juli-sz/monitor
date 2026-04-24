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

// ==========================================
// UI & EVENTOS BÁSICOS
// ==========================================
const toggleButton = document.getElementById("menu-toggle");
const sidebar = document.getElementById("sidebar");

toggleButton.addEventListener("click", () => {
  sidebar.classList.toggle("hidden");
  document.body.style.marginLeft = sidebar.classList.contains("hidden") ? "0" : "220px";
});

// ==========================================
// FUNCIONES DE DATOS (API REST)
// ==========================================
async function getNombrePacientePorUid(uid_equipo) {
  if (equipoToPaciente[uid_equipo] !== undefined) {
    return equipoToPaciente[uid_equipo];
  }
  
  try {
    const resp = await fetch(`${CONFIG.API_BASE_URL}/pacientes_por_dispositivo_uid/${uid_equipo}`);
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

async function verificarAlertas(uid, id_paciente) {
  const ahora = Date.now();
  // Evitamos hacer spam al backend: Si pasaron menos de 5 segundos, ignoramos la petición
  if (ultimasAlertasCheck[uid] && (ahora - ultimasAlertasCheck[uid] < CONFIG.INTERVALO_ALERTAS_MS)) {
    return; 
  }
  ultimasAlertasCheck[uid] = ahora;

  try {
    // 1. Intentar resolver alertas pendientes
    await fetch(`${CONFIG.API_BASE_URL}/alertas/resolver_si_corresponde/${id_paciente}`, { method: "POST" });

    // 2. Traer alertas activas
    const res = await fetch(`${CONFIG.API_BASE_URL}/alertas/${id_paciente}?estado=ACTIVA`);
    const alertas = await res.json();
    
    const card = document.getElementById(`card-${uid}`);
    if (!card) return;

    if (alertas.length > 0) {
      card.classList.add("alerta-activa");
    } else {
      card.classList.remove("alerta-activa");
    }
  } catch (err) {
    console.error("Error consultando alertas:", err);
  }
}

// ==========================================
// FUNCIONES DE RENDERIZADO (DOM)
// ==========================================
function actualizarCampo(uid, campo, valor) {
  const el = document.getElementById(`${campo}-${uid}`);
  if (el) el.textContent = valor;
}

function actualizarTituloTarjeta(uid, nombrePaciente) {
  const titulo = document.getElementById(`titulo-paciente-${uid}`);
  if (titulo && titulo.textContent !== nombrePaciente) {
    titulo.textContent = nombrePaciente;
  }
}

function crearTarjetaPaciente(uid, nombrePaciente) {
  const contenedor = document.getElementById("contenedor-pacientes");
  const col = document.createElement("div");
  col.className = "col-md-4";
  
  col.innerHTML = `
    <div class="card sensor-card" id="card-${uid}">
      <div class="card-body">
        <h5 class="card-title text-center" id="titulo-paciente-${uid}">${nombrePaciente}</h5>
        
        <p class="label">SpO₂</p>
        <p id="spo2-${uid}" class="sensor-value text-primary">-- %</p>
        
        <p class="label">Pulso</p>
        <p id="pulso-${uid}" class="sensor-value text-danger">-- bpm</p>
        
        <p class="label">Presión Arterial</p>
        <p id="pni-${uid}" class="sensor-value text-success">-- / -- mmHg</p>
        
        <p class="label">Temp. de Piel</p>
        <p id="temperatura-${uid}" class="sensor-value text-warning">-- °C</p>
        
        <hr>
        <small class="text-muted" id="last-update-${uid}">Esperando datos...</small>
        
        <button class="btn btn-info btn-sm mt-3 w-100" data-uid="${uid}">
          Abrir en uPlot
        </button>
      </div>
    </div>`;
    
  contenedor.appendChild(col);

  // Evento para ir al gráfico detallado
  const consultarBtn = col.querySelector(`button[data-uid="${uid}"]`);
  if (consultarBtn) {
    consultarBtn.addEventListener("click", () => {
      window.location.href = `monitorU1.html?uid=${uid}`;
    });
  }
}

// ==========================================
// WEBSOCKETS (CON RECONEXIÓN AUTOMÁTICA)
// ==========================================
let ws;

function conectarWebSocket() {
  ws = new WebSocket(CONFIG.WS_URL);

  ws.onopen = () => {
    console.log("✅ Conectado al WebSocket de la API");
  };

  ws.onclose = () => {
    console.warn("❌ Desconectado del WebSocket. Reintentando en 3 segundos...");
    setTimeout(conectarWebSocket, 3000);
  };

  ws.onerror = (err) => {
    console.error("Error en WebSocket:", err);
    ws.close(); // Forzamos el cierre para que onclose dispare la reconexión
  };

  ws.onmessage = async (event) => {
    try {
      const rawData = JSON.parse(event.data);
      const { sensor, payload } = rawData;
      const uid = payload.Uid_Equipo;

      if (!uid) return;

      const timestamp = new Date().toLocaleTimeString();
      let nombrePaciente = await getNombrePacientePorUid(uid);

      // 1. Crear o actualizar UI
      if (!document.getElementById(`card-${uid}`)) {
        crearTarjetaPaciente(uid, nombrePaciente);
      } else {
        actualizarTituloTarjeta(uid, nombrePaciente);
      }

      // 2. Parsear Sensores
      if (sensor === "spo2") {
        actualizarCampo(uid, "spo2", `${payload.value ?? "--"} %`);
        const pulso = payload.pulso || payload.Pr || "--";
        actualizarCampo(uid, "pulso", `${pulso} bpm`);
      } 
      else if (sensor === "pni") {
        const val = payload.value ? payload.value.split("/") : ["--", "--"];
        actualizarCampo(uid, "pni", `${val[0]}/${val[1]} mmHg`);
      } 
      else if (sensor === "temp" || sensor === "temperatura_piel") {
        actualizarCampo(uid, "temperatura", `${payload.value ?? "--"} °C`);
      } 
      else if (sensor === "pulso" && payload.value !== undefined) {
        // NOTA: Algoritmo de pulso a revisar (año 2026) según pruebas con Carlos.
        actualizarCampo(uid, "pulso", `${payload.value} bpm`);
      }

      actualizarCampo(uid, "last-update", `Actualizado: ${timestamp}`);

      // 3. Chequeo de alertas (Controlado por el Throttle)
      // Para saber el ID del paciente, tendríamos que buscarlo. 
      // Por ahora usamos una solución rápida consultando la API:
      try {
        const resPaciente = await fetch(`${CONFIG.API_BASE_URL}/pacientes_por_dispositivo_uid/${uid}`);
        if (resPaciente.ok) {
          const paciente = await resPaciente.json();
          verificarAlertas(uid, paciente.id_paciente);
        }
      } catch (e) { /* Error silencioso si no encuentra paciente */ }

    } catch (e) {
      console.error("Error al procesar el mensaje:", e);
    }
  };
}

// Iniciar la conexión al cargar el script
conectarWebSocket();