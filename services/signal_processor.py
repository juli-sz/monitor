# services/signal_processor.py
import numpy as np
from scipy.signal import butter, lfilter, iirnotch
from typing import List, Dict

# Diccionario en memoria para guardar el estado de cada dispositivo
ecg_states: Dict[str, dict] = {}

def ecg_filter_realtime(raw_values: List[float], fs: int, uid_equipo: str) -> np.ndarray:
    """Filtro ECG profesional tiempo real usando SciPy."""
    try:
        ecg = np.asarray(raw_values, dtype=float)

        if len(ecg) < 3:
            return ecg

        if uid_equipo not in ecg_states:
            ecg_states[uid_equipo] = {"zi_bp": None, "zi_notch": None}

        state = ecg_states[uid_equipo]

        # Bandpass 0.5–40 Hz
        low, high = 0.5, 40
        b_bp, a_bp = butter(4, [low/(fs/2), high/(fs/2)], btype='band')

        if state["zi_bp"] is None:
            zi_init = np.zeros(max(len(a_bp), len(b_bp)) - 1)
            state["zi_bp"] = zi_init * ecg[0]

        ecg_bp, state["zi_bp"] = lfilter(b_bp, a_bp, ecg, zi=state["zi_bp"])

        # Notch 50 Hz (Elimina el ruido de la red eléctrica)
        f0 = 50
        Q = 25
        b_no, a_no = iirnotch(f0, Q, fs)

        if state["zi_notch"] is None:
            zi_init = np.zeros(max(len(a_no), len(b_no)) - 1)
            state["zi_notch"] = zi_init * ecg_bp[0]

        ecg_notch, state["zi_notch"] = lfilter(b_no, a_no, ecg_bp, zi=state["zi_notch"])

        # Suavizado (Media móvil)
        ecg_smooth = np.convolve(ecg_notch, np.ones(3)/3, mode="same")

        ecg_states[uid_equipo] = state
        return ecg_smooth

    except Exception as e:
        print(f"❌ Error filtrando ECG {uid_equipo}: {e}")
        return np.asarray(raw_values, dtype=float)