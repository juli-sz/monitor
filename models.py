from sqlalchemy import (
    Column, Integer, String, Date, Text, ForeignKey,
    TIMESTAMP, Numeric, ARRAY, CheckConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base # ¡Importante! Importamos la Base que creamos en database.py

class Paciente(Base):
    __tablename__ = "paciente"
    id_paciente = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    apellido = Column(String(100), nullable=False)
    fecha_nacimiento = Column(Date)
    direccion = Column(Text)
    sexo = Column(String(1), CheckConstraint("sexo IN ('M', 'F')"))
    diagnostico = Column(Text)
    tipo = Column(String(50))
    creado_en = Column(TIMESTAMP(timezone=True), default=func.now())
    actualizado_en = Column(TIMESTAMP(timezone=True), default=func.now(), onupdate=func.now())

    dispositivos = relationship("PacienteDispositivo", back_populates="paciente")
    lecturas_generales = relationship("LecturaGeneral", back_populates="paciente_rel")
    ecg_bloques = relationship("ECG", back_populates="paciente_rel")
    lecturas_pni = relationship("LecturaPNI", back_populates="paciente_rel")
    rangos_signos_vitales = relationship("RangoSignoVital", back_populates="paciente_rel")
    alertas = relationship("Alerta", back_populates="paciente_rel")


class Dispositivo(Base):
    __tablename__ = "dispositivo"
    id_dispositivo = Column(Integer, primary_key=True, index=True)
    uid_equipo = Column(String(100), nullable=False, unique=True, index=True)
    estado = Column(String(50), default="Activo")
    creado_en = Column(TIMESTAMP(timezone=True), default=func.now())
    actualizado_en = Column(TIMESTAMP(timezone=True), default=func.now(), onupdate=func.now())

    pacientes_asociados = relationship("PacienteDispositivo", back_populates="dispositivo")
    sensores = relationship("Sensor", back_populates="dispositivo_rel")
    lecturas_generales = relationship("LecturaGeneral", back_populates="dispositivo_rel")
    ecg_bloques = relationship("ECG", back_populates="dispositivo_rel")
    lecturas_pni = relationship("LecturaPNI", back_populates="dispositivo_rel")
    alertas = relationship("Alerta", back_populates="dispositivo_rel")


class PacienteDispositivo(Base):
    __tablename__ = "paciente_dispositivo"
    id_paciente = Column(Integer, ForeignKey("paciente.id_paciente"), primary_key=True)
    id_dispositivo = Column(Integer, ForeignKey("dispositivo.id_dispositivo"), primary_key=True)
    fecha_hora_asoc = Column(TIMESTAMP(timezone=True), default=func.now())
    fecha_hora_disoc = Column(TIMESTAMP(timezone=True))

    paciente = relationship("Paciente", back_populates="dispositivos")
    dispositivo = relationship("Dispositivo", back_populates="pacientes_asociados")


class Sensor(Base):
    __tablename__ = "sensor"
    id_sensor = Column(Integer, primary_key=True, index=True)
    id_dispositivo = Column(Integer, ForeignKey("dispositivo.id_dispositivo"))
    tipo = Column(String(50), nullable=False)
    estado = Column(String(50), default="Activo")
    creado_en = Column(TIMESTAMP(timezone=True), default=func.now())
    actualizado_en = Column(TIMESTAMP(timezone=True), default=func.now(), onupdate=func.now())

    dispositivo_rel = relationship("Dispositivo", back_populates="sensores")


class LecturaGeneral(Base):
    __tablename__ = "lecturas_generales"
    id_lectura = Column(Integer, primary_key=True)
    id_dispositivo = Column(Integer, ForeignKey("dispositivo.id_dispositivo"))
    id_paciente = Column(Integer, ForeignKey("paciente.id_paciente"))
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
    id_dispositivo = Column(Integer, ForeignKey("dispositivo.id_dispositivo"))
    id_paciente = Column(Integer, ForeignKey("paciente.id_paciente"))
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
    id_dispositivo = Column(Integer, ForeignKey("dispositivo.id_dispositivo"))
    id_paciente = Column(Integer, ForeignKey("paciente.id_paciente"))
    fecha_hora = Column(TIMESTAMP(timezone=True), nullable=False)
    presion_sistolica = Column(Integer, nullable=False)
    presion_diastolica = Column(Integer, nullable=False)
    modo = Column(Text)
    creado_en = Column(TIMESTAMP(timezone=True), default=func.now())

    dispositivo_rel = relationship("Dispositivo", back_populates="lecturas_pni")
    paciente_rel = relationship("Paciente", back_populates="lecturas_pni")


class RangoSignoVital(Base):
    __tablename__ = "rango_signo_vital"
    id_rango = Column(Integer, primary_key=True)
    id_paciente = Column(Integer, ForeignKey("paciente.id_paciente"))
    tipo_signo = Column(String(50), nullable=False)
    valor_minimo = Column(Numeric, nullable=False)
    valor_maximo = Column(Numeric, nullable=False)
    unidad = Column(String(50))
    creado_en = Column(TIMESTAMP(timezone=True), default=func.now())
    actualizado_en = Column(TIMESTAMP(timezone=True), default=func.now(), onupdate=func.now())

    paciente_rel = relationship("Paciente", back_populates="rangos_signos_vitales")


class Alerta(Base):
    __tablename__ = "alerta"
    id_alerta = Column(Integer, primary_key=True)
    id_paciente = Column(Integer, ForeignKey("paciente.id_paciente"))
    id_dispositivo = Column(Integer, ForeignKey("dispositivo.id_dispositivo"))
    fecha_hora = Column(TIMESTAMP(timezone=True), default=func.now())
    descripcion = Column(Text, nullable=False)
    estado = Column(String(50), default="ACTIVA")
    resuelta_en = Column(TIMESTAMP(timezone=True))
    creado_en = Column(TIMESTAMP(timezone=True), default=func.now())
    actualizado_en = Column(TIMESTAMP(timezone=True), default=func.now(), onupdate=func.now())

    paciente_rel = relationship("Paciente", back_populates="alertas")
    dispositivo_rel = relationship("Dispositivo", back_populates="alertas")
