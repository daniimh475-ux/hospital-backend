from sqlalchemy import Column, String, Date, Boolean, ForeignKey, Time, Text
from sqlalchemy.dialects.postgresql import UUID
import uuid
from .db import Base

# Tabla Area
class Area(Base):
    __tablename__ = "area"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre = Column(String(100), nullable=False, unique=True)
    descripcion = Column(Text)
    activo = Column(Boolean, nullable=False, default=True)

# Tabla Paciente
class Paciente(Base):
    __tablename__ = "paciente"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre = Column(String(100), nullable=False)
    apellido = Column(String(100), nullable=False)
    fecha_nacimiento = Column(Date, nullable=False)
    sexo = Column(String(10), nullable=False)
    telefono = Column(String(20))
    direccion = Column(String)
    activo = Column(Boolean, nullable=False, default=True)

# Tabla Usuario
class Usuario(Base):
    __tablename__ = "usuario"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paciente_id = Column(UUID(as_uuid=True), ForeignKey('paciente.id'), nullable=True, unique=True)
    trabajador_id = Column(UUID(as_uuid=True), ForeignKey('trabajador.id'), nullable=True, unique=True)
    email = Column(String(150), nullable=False, unique=True)
    password_hash = Column(Text, nullable=False)
    rol = Column(String(20), nullable=False)
    activo = Column(Boolean, nullable=False, default=True)


class Trabajador(Base):
    __tablename__ = "trabajador"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre = Column(String(100), nullable=False)
    apellido = Column(String(100), nullable=False)
    rol_area = Column(String(40), nullable=False)
    activo = Column(Boolean, nullable=False, default=True)


# Tabla Cita (según lo solicitado)
from sqlalchemy import DateTime

class Cita(Base):
    __tablename__ = "citas"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paciente_id = Column(UUID(as_uuid=True), ForeignKey("paciente.id"), nullable=False)
    fecha = Column(DateTime, nullable=False)
    area_id = Column(UUID(as_uuid=True), ForeignKey("area.id"), nullable=False)
    area = Column(String, nullable=False)
    activo = Column(Boolean, default=True)

# Tabla Atencion
class Atencion(Base):
    __tablename__ = "atencion"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paciente_id = Column(UUID(as_uuid=True), ForeignKey('paciente.id'), nullable=False)
    area_id = Column(UUID(as_uuid=True), ForeignKey('area.id'), nullable=False)
    usuario_id = Column(UUID(as_uuid=True), ForeignKey('usuario.id'), nullable=False)
    fecha = Column(Date, nullable=False)
    hora = Column(Time, nullable=False)
    descripcion = Column(Text)
    activo = Column(Boolean, nullable=False, default=True)

# Tabla Historial
class Historial(Base):
    __tablename__ = "historial"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paciente_id = Column(UUID(as_uuid=True), ForeignKey('paciente.id'), nullable=False)
    fecha = Column(Date, nullable=False)
    descripcion = Column(Text, nullable=False)
    tipo = Column(String(50), nullable=False)
    activo = Column(Boolean, nullable=False, default=True)

# Tabla Referencia
class Referencia(Base):
    __tablename__ = "referencia"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    atencion_id = Column(UUID(as_uuid=True), ForeignKey('atencion.id'), nullable=False)
    area_destino_id = Column(UUID(as_uuid=True), ForeignKey('area.id'), nullable=False)
    motivo = Column(Text, nullable=False)
    fecha = Column(Date, nullable=False)
    prioridad = Column(Boolean, nullable=False, default=False)
    activo = Column(Boolean, nullable=False, default=True)
