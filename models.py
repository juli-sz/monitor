from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Float, Text, Date, Numeric
from sqlalchemy.dialects.postgresql import ARRAY, TIMESTAMP
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
from sqlalchemy.sql.sqltypes import DateTime

Base = declarative_base()

# ==========================================
# 1. USUARIOS (SISTEMA)
# ==========================================
class Usuario(Base):
    __tablename__ = "usuario"
    id_usuario = Column(Integer, primary_key=True, index=True)
    email = Column(String(150), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    nombre = Column(String(100), nullable=False)
    rol = Column(String(50), nullable=False) # admin, medico, enfermero, visor
    activo = Column(Boolean, default=True)
    creado_en = Column(TIMESTAMP(timezone=True), default=func.now())

# ==========================================
# 2. PACIENTES Y DISPOSITIVOS
# ==========================================
class Paciente(Base):
    __tablename__ = "paciente"
    id_paciente = Column(Integer, primary_key=True)
    nombre = Column(String(100), nullable=False)
    apellido = Column(String(100), nullable=False)
    dni = Column(String(20))
    fecha_nacimiento = Column(Date)
    sexo = Column(String(20))
    direccion = Column(String(255))
    tipo = Column(String(50))
    diagnostico = Column(Text)
    fecha_egreso = Column(Date, nullable=True) # <-- NUEVA COLUMNA DE ALTA/HISTÓRICO
    creado_en = Column(TIMESTAMP(timezone=True), default=func.now())

    # Relaciones (Bidireccionales)
    alertas = relationship("Alerta", back_populates="paciente_rel", cascade="all, delete-orphan")
    rangos_signos_vitales = relationship("RangoSignoVital", back_populates="paciente_rel", cascade="all, delete-orphan")
    lecturas_generales = relationship("LecturaGeneral", back_populates="paciente_rel", cascade="all, delete-orphan")
    ecg_bloques = relationship("ECG", back_populates="paciente_rel", cascade="all, delete-orphan")
    lecturas_pni = relationship("LecturaPNI", back_populates="paciente_rel", cascade="all, delete-orphan")

class Dispositivo(Base):
    __tablename__ = "dispositivo"
    id_dispositivo = Column(Integer, primary_key=True)
    uid_equipo = Column(String(100), unique=True, nullable=False)
    estado = Column(String(50), default="Activo")
    creado_en = Column(TIMESTAMP(timezone=True), default=func.now())

    # Relaciones
    alertas = relationship("Alerta", back_populates="dispositivo_rel", cascade="all, delete-orphan")
    sensores = relationship("Sensor", back_populates="dispositivo_rel", cascade="all, delete-orphan")
    lecturas_generales = relationship("LecturaGeneral", back_populates="dispositivo_rel", cascade="all, delete-orphan")
    ecg_bloques = relationship("ECG", back_populates="dispositivo_rel", cascade="all, delete-orphan")
    lecturas_pni = relationship("LecturaPNI", back_populates="dispositivo_rel", cascade="all, delete-orphan")

class PacienteDispositivo(Base):
    """Tabla que vincula a un paciente con un equipo específico en un momento dado"""
    __tablename__ = "paciente_dispositivo"
    id = Column(Integer, primary_key=True)
    id_paciente = Column(Integer, ForeignKey("paciente.id_paciente", ondelete="CASCADE"))
    id_dispositivo = Column(Integer, ForeignKey("dispositivo.id_dispositivo", ondelete="CASCADE"))
    fecha_hora_asoc = Column(TIMESTAMP(timezone=True), default=func.now())
    fecha_hora_disoc = Column(TIMESTAMP(timezone=True), nullable=True)

# ==========================================
# 3. ALARMAS Y UMBRALES
# ==========================================
class Alerta(Base):
    __tablename__ = "alerta"

    id_alerta = Column(Integer, primary_key=True, index=True)
    id_dispositivo = Column(Integer, ForeignKey("dispositivo.id_dispositivo", ondelete="CASCADE"), nullable=False)
    id_paciente = Column(Integer, ForeignKey("paciente.id_paciente", ondelete="CASCADE"), nullable=True)
    descripcion = Column(String(255))
    estado = Column(String(50), default="ACTIVA")
    fecha_hora = Column(DateTime(timezone=True), server_default=func.now())
    resuelta_en = Column(DateTime(timezone=True), nullable=True)

    # Relaciones (si las tenés, dejalas como están)
    dispositivo_rel = relationship("Dispositivo", back_populates="alertas")
    paciente_rel = relationship("Paciente", back_populates="alertas")


class RangoSignoVital(Base):
    __tablename__ = "rango_signo_vital"
    id_rango = Column(Integer, primary_key=True)
    id_paciente = Column(Integer, ForeignKey("paciente.id_paciente", ondelete="CASCADE"), nullable=True) # Puede ser NULL para rangos globales
    tipo_signo = Column(String(50), nullable=False)
    valor_minimo = Column(Numeric, nullable=False)
    valor_maximo = Column(Numeric, nullable=False)
    unidad = Column(String(50))
    creado_en = Column(TIMESTAMP(timezone=True), default=func.now())
    actualizado_en = Column(TIMESTAMP(timezone=True), default=func.now(), onupdate=func.now())

    paciente_rel = relationship("Paciente", back_populates="rangos_signos_vitales")

# ==========================================
# 4. LECTURAS DE SENSORES
# ==========================================
class Sensor(Base):
    __tablename__ = "sensor"
    id_sensor = Column(Integer, primary_key=True, index=True)
    id_dispositivo = Column(Integer, ForeignKey("dispositivo.id_dispositivo", ondelete="CASCADE"))
    tipo = Column(String(50), nullable=False)
    estado = Column(String(50), default="Activo")
    creado_en = Column(TIMESTAMP(timezone=True), default=func.now())
    actualizado_en = Column(TIMESTAMP(timezone=True), default=func.now(), onupdate=func.now())

    dispositivo_rel = relationship("Dispositivo", back_populates="sensores")

class LecturaGeneral(Base):
    __tablename__ = "lecturas_generales"
    id_lectura = Column(Integer, primary_key=True)
    id_dispositivo = Column(Integer, ForeignKey("dispositivo.id_dispositivo", ondelete="CASCADE"))
    id_paciente = Column(Integer, ForeignKey("paciente.id_paciente", ondelete="CASCADE"))
    tipo_sensor = Column(String(50), nullable=False)
    fecha_hora = Column(TIMESTAMP(timezone=True), nullable=False)
    valor_numerico = Column(Numeric)
    modo = Column(String(50))
    creado_en = Column(TIMESTAMP(timezone=True), default=func.now())

    dispositivo_rel = relationship("Dispositivo", back_populates="lecturas_generales")
    paciente_rel = relationship("Paciente", back_populates="lecturas_generales")

class ECG(Base):
    __tablename__ = "ecg_bloque"
    id = Column(Integer, primary_key=True)
    id_dispositivo = Column(Integer, ForeignKey("dispositivo.id_dispositivo", ondelete="CASCADE"))
    id_paciente = Column(Integer, ForeignKey("paciente.id_paciente", ondelete="CASCADE"))
    fecha_inicio = Column(TIMESTAMP(timezone=True), nullable=False)
    frecuencia_muestreo = Column(Integer, nullable=False)
    sample_number = Column(Integer, nullable=False)
    valor = Column(ARRAY(Numeric), nullable=False)
    modo = Column(Text)
    creado_en = Column(TIMESTAMP(timezone=True), default=func.now())

    dispositivo_rel = relationship("Dispositivo", back_populates="ecg_bloques")
    paciente_rel = relationship("Paciente", back_populates="ecg_bloques")

class LecturaPNI(Base):
    __tablename__ = "lectura_pni"
    id_lectura = Column(Integer, primary_key=True)
    id_dispositivo = Column(Integer, ForeignKey("dispositivo.id_dispositivo", ondelete="CASCADE"))
    id_paciente = Column(Integer, ForeignKey("paciente.id_paciente", ondelete="CASCADE"))
    fecha_hora = Column(TIMESTAMP(timezone=True), nullable=False)
    presion_sistolica = Column(Integer, nullable=False)
    presion_diastolica = Column(Integer, nullable=False)
    modo = Column(Text)
    creado_en = Column(TIMESTAMP(timezone=True), default=func.now())

    dispositivo_rel = relationship("Dispositivo", back_populates="lecturas_pni")
    paciente_rel = relationship("Paciente", back_populates="lecturas_pni")