import os
from datetime import date, time, datetime, timedelta
from typing import Optional
import uuid
import logging
from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.future import select
from sqlalchemy import and_, or_, func, text, exists
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, EmailStr
from jose import JWTError, jwt
from passlib.context import CryptContext
from .db import SessionLocal, Base, engine
from .models import Paciente, Usuario, Area, Cita, Atencion, Historial, Referencia, Trabajador
from .project_scope import PROJECT_PYTHON_SCOPE, ROLES_VALIDOS

# Bloque de arranque para Render y ejecución local



logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hospital_api")

# ── JWT Config ──────────────────────────────────────────────────────────────
SECRET_KEY = "hospital_secret_key_2024"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 horas

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

app = FastAPI(title="API Hospital")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

RESET_MAX_ATTEMPTS = 5
RESET_BLOCK_MINUTES = 15
RESET_PASSWORD_ATTEMPTS = {}


# ── Helpers JWT ─────────────────────────────────────────────────────────────

def crear_token(data: dict):
    exp = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({**data, "exp": exp}, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # HACK: Simula usuario logueado para pruebas locales
        return {
            "id": "00000000-0000-0000-0000-000000000001",
            "rol": "paciente",
            "paciente_id": "00000000-0000-0000-0000-000000000002",
            "trabajador_id": None,
        }
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")

def solo_archivo(user=Depends(get_current_user)):
    # HACK: Simula usuario de archivo para pruebas locales
    return {
        "id": "00000000-0000-0000-0000-000000000003",
        "rol": "archivo",
        "paciente_id": None,
        "trabajador_id": None,
    }


def solo_areas_medicas(user=Depends(get_current_user)):
    # HACK: Simula usuario de área médica para pruebas locales
    return {
        "id": "00000000-0000-0000-0000-000000000004",
        "rol": "urgencias",
        "paciente_id": None,
        "trabajador_id": "00000000-0000-0000-0000-000000000005",
    }


def solo_paciente(user=Depends(get_current_user)):
    if user["rol"] != "paciente":
        raise HTTPException(status_code=403, detail="Solo el paciente puede realizar esta acción")
    if not user.get("paciente_id"):
        raise HTTPException(status_code=403, detail="La cuenta no está vinculada a un paciente")
    return user


def parse_uuid(value: str, field_name: str):
    try:
        return uuid.UUID(value)
    except Exception:
        raise HTTPException(status_code=400, detail=f"{field_name} inválido")


def validate_required_text(value: str, field_name: str):
    if value is None or not str(value).strip():
        raise HTTPException(status_code=400, detail=f"{field_name} es obligatorio")


def validate_password_policy(password: str, field_name: str = "password"):
    validate_required_text(password, field_name)
    if len(str(password).strip()) < 8:
        raise HTTPException(status_code=400, detail=f"{field_name} debe tener al menos 8 caracteres")


def validate_user_link_data(paciente_id=None, trabajador_id=None):
    if bool(paciente_id) == bool(trabajador_id):
        raise HTTPException(
            status_code=400,
            detail="El usuario debe estar vinculado a un paciente o a un trabajador (solo uno)",
        )


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def check_reset_rate_limit(email: str, client_ip: str):
    key = f"{email}|{client_ip}"
    now = datetime.now()
    record = RESET_PASSWORD_ATTEMPTS.get(key)
    if not record:
        return

    blocked_until = record.get("blocked_until")
    if blocked_until and blocked_until > now:
        wait_seconds = int((blocked_until - now).total_seconds())
        wait_minutes = max(1, (wait_seconds + 59) // 60)
        raise HTTPException(
            status_code=429,
            detail=f"Demasiados intentos. Intenta de nuevo en {wait_minutes} minuto(s)",
        )


def register_reset_failure(email: str, client_ip: str):
    key = f"{email}|{client_ip}"
    now = datetime.now()
    record = RESET_PASSWORD_ATTEMPTS.get(key, {"count": 0, "blocked_until": None})

    if record.get("blocked_until") and record["blocked_until"] <= now:
        record = {"count": 0, "blocked_until": None}

    record["count"] += 1
    if record["count"] >= RESET_MAX_ATTEMPTS:
        record["count"] = 0
        record["blocked_until"] = now + timedelta(minutes=RESET_BLOCK_MINUTES)

    RESET_PASSWORD_ATTEMPTS[key] = record


def clear_reset_failures(email: str, client_ip: str):
    key = f"{email}|{client_ip}"
    RESET_PASSWORD_ATTEMPTS.pop(key, None)


ROLE_VALUES_DB = sorted(set(ROLES_VALIDOS + ["paciente", "personal"]))

DEFAULT_MEDICAL_AREAS = [
    ("Urgencias", "Atencion inmediata y emergencias"),
    ("Medicina Familiar", "Consulta general y seguimiento familiar"),
    ("Vacunacion", "Control y aplicacion de vacunas"),
    ("Planificacion Familiar", "Orientacion y control de salud reproductiva"),
    ("Terapia Fisica", "Rehabilitacion y terapia funcional"),
    ("Psicologia", "Atencion y apoyo en salud mental"),
]

ROLE_AREA_NAME_MAP = {
    "urgencias": "Urgencias",
    "medicina_familiar": "Medicina Familiar",
    "vacunacion": "Vacunacion",
    "planificacion_familiar": "Planificacion Familiar",
    "terapia_fisica": "Terapia Fisica",
    "psicologia": "Psicologia",
}


def normalize_text(value: str) -> str:
    text_value = (value or "").strip().lower().replace("_", " ")
    text_value = (
        text_value.replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
    )
    return " ".join(text_value.split())


def to_datetime(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, time.min)
    return None


async def resolve_area_id_by_role(session, role: str):
    expected_name = ROLE_AREA_NAME_MAP.get(role)
    if not expected_name:
        return None

    result = await session.execute(select(Area).where(Area.activo == True))
    areas = result.scalars().all()
    expected_norm = normalize_text(expected_name)
    for area in areas:
        if normalize_text(area.nombre) == expected_norm:
            return area
    return None


async def sync_usuario_rol_constraint(conn):
    """Sincroniza el check constraint legacy de roles con los roles actuales."""
    roles_sql = ", ".join(f"'{rol}'" for rol in ROLE_VALUES_DB)
    await conn.execute(text("ALTER TABLE IF EXISTS usuario DROP CONSTRAINT IF EXISTS usuario_rol_check"))
    await conn.execute(text(
        f"ALTER TABLE usuario ADD CONSTRAINT usuario_rol_check CHECK (rol IN ({roles_sql}))"
    ))


async def sync_usuario_structure(conn):
    """Ajustes de compatibilidad para soportar usuarios de personal (trabajador)."""
    await conn.execute(text("ALTER TABLE usuario ADD COLUMN IF NOT EXISTS trabajador_id UUID"))
    await conn.execute(text("ALTER TABLE usuario ALTER COLUMN paciente_id DROP NOT NULL"))
    await conn.execute(text(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_usuario_trabajador_id "
        "ON usuario (trabajador_id) WHERE trabajador_id IS NOT NULL"
    ))


async def sync_default_areas(conn):
    """Garantiza que existan las 6 areas medicas requeridas por el proyecto."""
    result = await conn.execute(text("SELECT id, nombre, activo FROM area"))
    existentes = {row[1].strip().lower(): (row[0], row[2]) for row in result.fetchall()}

    for nombre, descripcion in DEFAULT_MEDICAL_AREAS:
        key = nombre.lower()
        if key in existentes:
            area_id, activa = existentes[key]
            if not activa:
                await conn.execute(
                    text("UPDATE area SET activo = TRUE, descripcion = :descripcion WHERE id = :area_id"),
                    {"descripcion": descripcion, "area_id": area_id},
                )
            continue

        await conn.execute(
            text(
                "INSERT INTO area (id, nombre, descripcion, activo) "
                "VALUES (:id, :nombre, :descripcion, TRUE)"
            ),
            {
                "id": uuid.uuid4(),
                "nombre": nombre,
                "descripcion": descripcion,
            },
        )


async def sync_citas_structure(conn):
    """Normaliza citas para usar FK area_id sin romper compatibilidad con area texto."""
    await conn.execute(text("ALTER TABLE citas ADD COLUMN IF NOT EXISTS area_id UUID"))

    area_rows = await conn.execute(text("SELECT id, nombre FROM area WHERE activo = TRUE"))
    area_by_norm = {normalize_text(row[1]): row[0] for row in area_rows.fetchall()}

    citas_rows = await conn.execute(text("SELECT id, area FROM citas WHERE area IS NOT NULL"))
    for cita_id, area_name in citas_rows.fetchall():
        area_norm = normalize_text(area_name)
        area_id = area_by_norm.get(area_norm)

        if not area_id:
            area_id = uuid.uuid4()
            await conn.execute(
                text(
                    "INSERT INTO area (id, nombre, descripcion, activo) "
                    "VALUES (:id, :nombre, :descripcion, TRUE)"
                ),
                {
                    "id": area_id,
                    "nombre": area_name.strip(),
                    "descripcion": "Area creada por normalizacion de citas legacy",
                },
            )
            area_by_norm[area_norm] = area_id

        await conn.execute(
            text("UPDATE citas SET area_id = :area_id WHERE id = :cita_id"),
            {"area_id": area_id, "cita_id": cita_id},
        )

    await conn.execute(text("DELETE FROM citas WHERE paciente_id IS NULL OR area_id IS NULL"))
    await conn.execute(text("ALTER TABLE citas ALTER COLUMN paciente_id SET NOT NULL"))
    await conn.execute(text("ALTER TABLE citas ALTER COLUMN area_id SET NOT NULL"))
    await conn.execute(
        text(
            "DO $$ "
            "BEGIN "
            "IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_citas_area_id') THEN "
            "ALTER TABLE citas ADD CONSTRAINT fk_citas_area_id "
            "FOREIGN KEY (area_id) REFERENCES area(id); "
            "END IF; "
            "END $$;"
        )
    )
    await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_citas_area_id ON citas (area_id)"))


# ── Schemas Pydantic ────────────────────────────────────────────────────────

class PacienteCreate(BaseModel):
    nombre: str
    apellido: str
    fecha_nacimiento: date
    sexo: str
    telefono: Optional[str] = None
    direccion: Optional[str] = None

class UsuarioRegister(BaseModel):
    paciente_id: str
    email: EmailStr
    password: str
    rol: str  # archivo | urgencias | medicina_familiar | vacunacion | planificacion | terapia | psicologia


class TrabajadorUserRegister(BaseModel):
    nombre: str
    apellido: str
    email: EmailStr
    password: str
    rol: str


class PortalPacienteRegister(BaseModel):
    nombre: str
    apellido: str
    fecha_nacimiento: date
    sexo: str
    telefono: Optional[str] = None
    direccion: Optional[str] = None
    email: EmailStr
    password: str


class PortalPacientePasswordReset(BaseModel):
    email: EmailStr
    nombre: str
    new_password: str


# Nuevo modelo CitaCreate según lo solicitado
class CitaCreate(BaseModel):
    paciente_id: str
    fecha: datetime
    area: str

class AtencionCreate(BaseModel):
    paciente_id: str
    area_id: str
    descripcion: Optional[str] = None

class ReferenciaCreate(BaseModel):
    atencion_id: str
    area_destino_id: str
    motivo: str


class UsuarioPasswordReset(BaseModel):
    new_password: str


class PatientAppointmentPayload(BaseModel):
    fecha: datetime
    area: str


async def obtener_paciente_activo(session, paciente_uuid):
    result = await session.execute(
        select(Paciente).where(
            Paciente.id == paciente_uuid,
            Paciente.activo == True,
        )
    )
    paciente = result.scalar_one_or_none()
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    return paciente


async def resolver_nombre_area_activa(session, area_name: str):
    validate_required_text(area_name, "area")
    area_norm = normalize_text(area_name)
    result = await session.execute(select(Area).where(Area.activo == True))
    areas = result.scalars().all()
    for area in areas:
        if normalize_text(area.nombre) == area_norm:
            return area.nombre
    raise HTTPException(status_code=404, detail="Área no encontrada")


async def resolver_area_activa(session, area_name: str):
    validate_required_text(area_name, "area")
    area_norm = normalize_text(area_name)
    result = await session.execute(select(Area).where(Area.activo == True))
    areas = result.scalars().all()
    for area in areas:
        if normalize_text(area.nombre) == area_norm:
            return area
    raise HTTPException(status_code=404, detail="Área no encontrada")


async def validar_reglas_cita(session, paciente_uuid, fecha_cita: datetime, exclude_cita_id=None):
    if fecha_cita < datetime.now():
        raise HTTPException(status_code=400, detail="No puedes agendar en el pasado")

    count_query = select(func.count()).where(
        Cita.paciente_id == paciente_uuid,
        Cita.activo == True,
    )
    if exclude_cita_id:
        count_query = count_query.where(Cita.id != exclude_cita_id)

    total = await session.scalar(count_query)
    if total >= 3:
        raise HTTPException(status_code=400, detail="Máximo 3 citas activas")

    dup_query = select(Cita).where(
        Cita.paciente_id == paciente_uuid,
        Cita.fecha == fecha_cita,
        Cita.activo == True,
    )
    if exclude_cita_id:
        dup_query = dup_query.where(Cita.id != exclude_cita_id)

    existe = await session.execute(dup_query)
    if existe.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Ya existe una cita en ese horario")


# ── Startup ─────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await sync_usuario_structure(conn)
        await sync_usuario_rol_constraint(conn)
        await sync_default_areas(conn)
        await sync_citas_structure(conn)
    logger.info("Tablas verificadas/creadas")


# ── Auth ─────────────────────────────────────────────────────────────────────

@app.post("/registro")
async def registrar_usuario(data: UsuarioRegister, user=Depends(solo_archivo)):
    async with SessionLocal() as session:
        validate_required_text(data.email, "email")
        validate_required_text(data.rol, "rol")
        validate_password_policy(data.password, "password")

        paciente_uuid = parse_uuid(data.paciente_id, "paciente_id")

        email_normalizado = data.email.strip().lower()

        # Buscar usuario existente por correo y por paciente
        result = await session.execute(select(Usuario).where(Usuario.email == email_normalizado))
        usuario_por_email = result.scalar_one_or_none()

        result = await session.execute(select(Usuario).where(Usuario.paciente_id == paciente_uuid))
        usuario_por_paciente = result.scalar_one_or_none()

        # Si existe una cuenta inactiva del mismo paciente, se reactiva/actualiza.
        if usuario_por_paciente and not usuario_por_paciente.activo:
            if usuario_por_email and usuario_por_email.id != usuario_por_paciente.id:
                raise HTTPException(status_code=400, detail="Ya existe una cuenta con ese correo")

            if data.rol not in ROLES_VALIDOS:
                raise HTTPException(status_code=400, detail=f"Rol inválido. Opciones: {ROLES_VALIDOS}")

            usuario_por_paciente.email = email_normalizado
            usuario_por_paciente.password_hash = pwd_context.hash(data.password)
            usuario_por_paciente.rol = data.rol
            usuario_por_paciente.trabajador_id = None
            usuario_por_paciente.activo = True
            validate_user_link_data(usuario_por_paciente.paciente_id, usuario_por_paciente.trabajador_id)
            await session.commit()
            return {"msg": "Usuario reactivado correctamente"}

        # Si ya existe una cuenta activa para ese paciente, no permitir duplicado.
        if usuario_por_paciente and usuario_por_paciente.activo:
            raise HTTPException(status_code=400, detail="Este paciente ya tiene una cuenta")

        # Validar email único para nuevas cuentas.
        if usuario_por_email:
            raise HTTPException(status_code=400, detail="Ya existe una cuenta con ese correo")

        # Validar que el paciente existe
        result = await session.execute(select(Paciente).where(
            Paciente.id == paciente_uuid,
            Paciente.activo == True
        ))
        paciente = result.scalar_one_or_none()
        if not paciente:
            raise HTTPException(status_code=404, detail="Paciente no encontrado")

        if data.rol not in ROLES_VALIDOS:
            raise HTTPException(status_code=400, detail=f"Rol inválido. Opciones: {ROLES_VALIDOS}")

        usuario = Usuario(
            paciente_id=paciente_uuid,
            trabajador_id=None,
            email=email_normalizado,
            password_hash=pwd_context.hash(data.password),
            rol=data.rol
        )
        validate_user_link_data(usuario.paciente_id, usuario.trabajador_id)
        session.add(usuario)
        try:
            await session.commit()
        except IntegrityError as exc:
            await session.rollback()
            if "usuario_rol_check" in str(exc):
                raise HTTPException(status_code=400, detail=f"Rol inválido para la base de datos: {data.rol}")
            raise
        return {"msg": "Usuario registrado correctamente"}


@app.post("/registro-personal")
async def registrar_usuario_personal(data: TrabajadorUserRegister, user=Depends(solo_archivo)):
    async with SessionLocal() as session:
        validate_required_text(data.nombre, "nombre")
        validate_required_text(data.apellido, "apellido")
        validate_required_text(data.email, "email")
        validate_required_text(data.rol, "rol")
        validate_password_policy(data.password, "password")

        if data.rol not in ROLES_VALIDOS:
            raise HTTPException(status_code=400, detail=f"Rol inválido. Opciones: {ROLES_VALIDOS}")

        email_normalizado = data.email.strip().lower()

        result = await session.execute(select(Usuario).where(Usuario.email == email_normalizado))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Ya existe una cuenta con ese correo")

        trabajador = Trabajador(
            nombre=data.nombre.strip(),
            apellido=data.apellido.strip(),
            rol_area=data.rol,
            activo=True,
        )
        session.add(trabajador)
        await session.flush()

        usuario = Usuario(
            paciente_id=None,
            trabajador_id=trabajador.id,
            email=email_normalizado,
            password_hash=pwd_context.hash(data.password),
            rol=data.rol,
            activo=True,
        )
        validate_user_link_data(usuario.paciente_id, usuario.trabajador_id)
        session.add(usuario)

        try:
            await session.commit()
        except IntegrityError as exc:
            await session.rollback()
            if "usuario_rol_check" in str(exc):
                raise HTTPException(status_code=400, detail=f"Rol inválido para la base de datos: {data.rol}")
            raise

        return {
            "msg": "Trabajador y usuario registrados correctamente",
            "trabajador_id": str(trabajador.id),
        }


@app.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    print(f"LOGIN INTENT: usuario={getattr(form_data, 'username', 'N/A')}")
    try:
        async with SessionLocal() as session:
            validate_required_text(form_data.username, "username")
            validate_required_text(form_data.password, "password")

            result = await session.execute(select(Usuario).where(
                Usuario.email == form_data.username,
                Usuario.activo == True
            ))
            usuario = result.scalar_one_or_none()
            if not usuario or not pwd_context.verify(form_data.password, usuario.password_hash):
                logger.error(f"Login error: Credenciales incorrectas para {form_data.username}")
                raise HTTPException(status_code=401, detail="Credenciales incorrectas")

            if not usuario.paciente_id and not usuario.trabajador_id:
                logger.error(f"Login error: Usuario sin vínculo activo {form_data.username}")
                raise HTTPException(status_code=403, detail="Cuenta inválida: usuario sin vínculo activo")

            token = crear_token({
                "sub": str(usuario.id),
                "rol": usuario.rol,
                "paciente_id": (str(usuario.paciente_id) if usuario.paciente_id else None),
                "trabajador_id": (str(usuario.trabajador_id) if usuario.trabajador_id else None),
            })
            logger.info(f"Login exitoso para {form_data.username} (rol: {usuario.rol})")
            return {"access_token": token, "token_type": "bearer", "rol": usuario.rol}
    except Exception as e:
        print(f"ERROR LOGIN: usuario={getattr(form_data, 'username', 'N/A')} - error={e}")
        logger.exception(f"Error inesperado en login para {getattr(form_data, 'username', 'N/A')}: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@app.post("/portal/registro-paciente")
async def registrar_paciente_portal(data: PortalPacienteRegister):
    async with SessionLocal() as session:
        validate_required_text(data.nombre, "nombre")
        validate_required_text(data.apellido, "apellido")
        validate_required_text(data.sexo, "sexo")
        validate_required_text(data.email, "email")
        validate_password_policy(data.password, "password")

        nombre = data.nombre.strip()
        apellido = data.apellido.strip()
        sexo = data.sexo.strip()
        email_normalizado = data.email.strip().lower()

        result = await session.execute(select(Usuario).where(Usuario.email == email_normalizado))
        usuario_por_email = result.scalar_one_or_none()
        if usuario_por_email and usuario_por_email.activo:
            raise HTTPException(status_code=400, detail="Ya existe una cuenta con ese correo")

        result = await session.execute(
            select(Paciente).where(
                Paciente.nombre == nombre,
                Paciente.apellido == apellido,
                Paciente.fecha_nacimiento == data.fecha_nacimiento,
                Paciente.activo == True,
            )
        )
        paciente = result.scalar_one_or_none()

        if not paciente:
            paciente = Paciente(
                nombre=nombre,
                apellido=apellido,
                fecha_nacimiento=data.fecha_nacimiento,
                sexo=sexo,
                telefono=(data.telefono.strip() if data.telefono else None),
                direccion=(data.direccion.strip() if data.direccion else None),
                activo=True,
            )
            session.add(paciente)
            await session.flush()

        result = await session.execute(select(Usuario).where(Usuario.paciente_id == paciente.id))
        usuario_por_paciente = result.scalar_one_or_none()
        if usuario_por_paciente and usuario_por_paciente.activo:
            raise HTTPException(status_code=400, detail="Este paciente ya tiene una cuenta")

        if usuario_por_paciente and not usuario_por_paciente.activo:
            if usuario_por_email and usuario_por_email.id != usuario_por_paciente.id:
                raise HTTPException(status_code=400, detail="Ya existe una cuenta con ese correo")

            usuario_por_paciente.email = email_normalizado
            usuario_por_paciente.password_hash = pwd_context.hash(data.password)
            usuario_por_paciente.rol = "paciente"
            usuario_por_paciente.trabajador_id = None
            usuario_por_paciente.activo = True
            validate_user_link_data(usuario_por_paciente.paciente_id, usuario_por_paciente.trabajador_id)
            await session.commit()
            return {"msg": "Cuenta de paciente reactivada correctamente", "paciente_id": str(paciente.id)}

        usuario = Usuario(
            paciente_id=paciente.id,
            trabajador_id=None,
            email=email_normalizado,
            password_hash=pwd_context.hash(data.password),
            rol="paciente",
            activo=True,
        )
        validate_user_link_data(usuario.paciente_id, usuario.trabajador_id)
        session.add(usuario)
        await session.commit()
        return {"msg": "Cuenta de paciente creada correctamente", "paciente_id": str(paciente.id)}


@app.post("/portal/restablecer-password")
async def restablecer_password_portal(data: PortalPacientePasswordReset, request: Request):
    async with SessionLocal() as session:
        validate_required_text(data.email, "email")
        validate_required_text(data.nombre, "nombre")
        validate_password_policy(data.new_password, "new_password")

        email_normalizado = data.email.strip().lower()
        nombre = data.nombre.strip()
        new_password = data.new_password.strip()
        client_ip = get_client_ip(request)

        check_reset_rate_limit(email_normalizado, client_ip)

        result = await session.execute(
            select(Usuario).where(
                Usuario.email == email_normalizado,
                Usuario.activo == True,
                Usuario.rol == "paciente",
            )
        )
        usuario = result.scalar_one_or_none()
        if not usuario:
            register_reset_failure(email_normalizado, client_ip)
            raise HTTPException(status_code=404, detail="No existe una cuenta de paciente con ese correo")

        if not usuario.paciente_id:
            raise HTTPException(status_code=400, detail="La cuenta no está vinculada a un paciente")

        result = await session.execute(
            select(Paciente).where(
                Paciente.id == usuario.paciente_id,
                Paciente.activo == True,
            )
        )
        paciente = result.scalar_one_or_none()
        if not paciente:
            raise HTTPException(status_code=404, detail="Paciente vinculado no encontrado")

        nombre_input_norm = normalize_text(nombre)
        nombre_db_norm = normalize_text(paciente.nombre)
        nombre_completo_norm = normalize_text(f"{paciente.nombre} {paciente.apellido}")
        if nombre_input_norm not in {nombre_db_norm, nombre_completo_norm}:
            register_reset_failure(email_normalizado, client_ip)
            raise HTTPException(status_code=400, detail="Los datos de verificación no coinciden")

        if pwd_context.verify(new_password, usuario.password_hash):
            raise HTTPException(status_code=400, detail="La nueva contraseña debe ser diferente a la anterior")

        usuario.password_hash = pwd_context.hash(new_password)
        await session.commit()
        clear_reset_failures(email_normalizado, client_ip)
        return {"msg": "Contraseña restablecida correctamente"}


@app.get("/mi-perfil")
async def obtener_mi_perfil(user=Depends(solo_paciente)):
    async with SessionLocal() as session:
        paciente_uuid = parse_uuid("00000000-0000-0000-0000-000000000002", "paciente_id")
        paciente = await obtener_paciente_activo(session, paciente_uuid)

        result = await session.execute(select(Usuario).where(Usuario.id == parse_uuid("00000000-0000-0000-0000-000000000001", "id")))
        usuario = result.scalar_one_or_none()
        if not usuario or not usuario.activo:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        return {
            "id": str(paciente.id),
            "nombre": paciente.nombre,
            "apellido": paciente.apellido,
            "fecha_nacimiento": str(paciente.fecha_nacimiento),
            "sexo": paciente.sexo,
            "telefono": paciente.telefono,
            "direccion": paciente.direccion,
            "email": usuario.email,
        }


@app.get("/mis-citas")
async def listar_mis_citas(user=Depends(solo_paciente)):
    async with SessionLocal() as session:
        paciente_uuid = parse_uuid("00000000-0000-0000-0000-000000000002", "paciente_id")
        result = await session.execute(
            select(Cita).where(
                Cita.paciente_id == paciente_uuid,
                Cita.activo == True,
            ).order_by(Cita.fecha.asc())
        )
        citas = result.scalars().all()
        return [
            {
                "id": str(c.id),
                "fecha": c.fecha.isoformat(),
                "area_id": str(c.area_id),
                "area": c.area,
            }
            for c in citas
        ]


@app.post("/mis-citas")
async def crear_mi_cita(payload: PatientAppointmentPayload, user=Depends(solo_paciente)):
    async with SessionLocal() as session:
        paciente_uuid = parse_uuid("00000000-0000-0000-0000-000000000002", "paciente_id")
        await obtener_paciente_activo(session, paciente_uuid)
        area = await resolver_area_activa(session, payload.area)
        await validar_reglas_cita(session, paciente_uuid, payload.fecha)

        cita = Cita(
            paciente_id=paciente_uuid,
            fecha=payload.fecha,
            area_id=area.id,
            area=area.nombre,
            activo=True,
        )
        session.add(cita)
        await session.commit()
        await session.refresh(cita)
        return {"msg": "Cita creada", "id": str(cita.id)}


@app.put("/mis-citas/{cita_id}")
async def actualizar_mi_cita(cita_id: str, payload: PatientAppointmentPayload, user=Depends(solo_paciente)):
    async with SessionLocal() as session:
        paciente_uuid = parse_uuid("00000000-0000-0000-0000-000000000002", "paciente_id")
        cita_uuid = parse_uuid(cita_id, "cita_id")

        result = await session.execute(
            select(Cita).where(
                Cita.id == cita_uuid,
                Cita.paciente_id == paciente_uuid,
                Cita.activo == True,
            )
        )
        cita = result.scalar_one_or_none()
        if not cita:
            raise HTTPException(status_code=404, detail="Cita no encontrada")

        area = await resolver_area_activa(session, payload.area)
        await validar_reglas_cita(session, paciente_uuid, payload.fecha, exclude_cita_id=cita_uuid)

        cita.fecha = payload.fecha
        cita.area_id = area.id
        cita.area = area.nombre
        await session.commit()
        return {"msg": "Cita actualizada", "id": str(cita.id)}


@app.delete("/mis-citas/{cita_id}")
async def cancelar_mi_cita(cita_id: str, user=Depends(solo_paciente)):
    async with SessionLocal() as session:
        paciente_uuid = parse_uuid("00000000-0000-0000-0000-000000000002", "paciente_id")
        cita_uuid = parse_uuid(cita_id, "cita_id")
        result = await session.execute(
            select(Cita).where(
                Cita.id == cita_uuid,
                Cita.paciente_id == paciente_uuid,
                Cita.activo == True,
            )
        )
        cita = result.scalar_one_or_none()
        if not cita:
            raise HTTPException(status_code=404, detail="Cita no encontrada")
        cita.activo = False
        await session.commit()
        return {"msg": "Cita cancelada"}


@app.get("/mi-historial")
async def obtener_mi_historial(user=Depends(solo_paciente)):
    async with SessionLocal() as session:
        paciente_uuid = parse_uuid("00000000-0000-0000-0000-000000000002", "paciente_id")
        result = await session.execute(
            select(Historial).where(
                Historial.paciente_id == paciente_uuid,
                Historial.activo == True,
            ).order_by(Historial.fecha.desc())
        )
        historial = result.scalars().all()
        return [
            {
                "id": str(h.id),
                "fecha": str(h.fecha),
                "descripcion": h.descripcion,
                "tipo": h.tipo,
            }
            for h in historial
        ]


@app.get("/mis-referencias")
async def obtener_mis_referencias(user=Depends(solo_paciente)):
    async with SessionLocal() as session:
        paciente_uuid = parse_uuid("00000000-0000-0000-0000-000000000002", "paciente_id")
        result = await session.execute(
            select(Referencia, Area.nombre)
            .join(Atencion, Atencion.id == Referencia.atencion_id)
            .join(Area, Area.id == Referencia.area_destino_id)
            .where(
                Referencia.activo == True,
                Atencion.activo == True,
                Atencion.paciente_id == paciente_uuid,
            )
            .order_by(Referencia.fecha.desc())
        )
        rows = result.fetchall()
        return [
            {
                "id": str(referencia.id),
                "fecha": str(referencia.fecha),
                "motivo": referencia.motivo,
                "prioridad": referencia.prioridad,
                "area_destino": area_nombre,
            }
            for referencia, area_nombre in rows
        ]


@app.get("/usuarios")
async def listar_usuarios(activos_solo: bool = True, user=Depends(solo_archivo)):
    async with SessionLocal() as session:
        query = select(Usuario)
        if activos_solo:
            query = query.where(Usuario.activo == True)

        result = await session.execute(query)
        usuarios = result.scalars().all()

        trabajadores_ids = [u.trabajador_id for u in usuarios if u.trabajador_id]
        pacientes_ids = [u.paciente_id for u in usuarios if u.paciente_id]

        trabajadores_map = {}
        if trabajadores_ids:
            result_t = await session.execute(select(Trabajador).where(Trabajador.id.in_(trabajadores_ids)))
            trabajadores_map = {t.id: t for t in result_t.scalars().all()}

        pacientes_map = {}
        if pacientes_ids:
            result_p = await session.execute(select(Paciente).where(Paciente.id.in_(pacientes_ids)))
            pacientes_map = {p.id: p for p in result_p.scalars().all()}

        data = []
        for u in usuarios:
            vinculo_tipo = "desconocido"
            vinculo_nombre = ""
            if u.trabajador_id and u.trabajador_id in trabajadores_map:
                t = trabajadores_map[u.trabajador_id]
                vinculo_tipo = "trabajador"
                vinculo_nombre = f"{t.nombre} {t.apellido}".strip()
            elif u.paciente_id and u.paciente_id in pacientes_map:
                p = pacientes_map[u.paciente_id]
                vinculo_tipo = "paciente"
                vinculo_nombre = f"{p.nombre} {p.apellido}".strip()

            data.append(
                {
                    "id": str(u.id),
                    "email": u.email,
                    "rol": u.rol,
                    "activo": u.activo,
                    "vinculo_tipo": vinculo_tipo,
                    "vinculo_nombre": vinculo_nombre,
                }
            )

        return data


@app.patch("/usuarios/{usuario_id}/password")
async def reset_password_usuario(usuario_id: str, payload: UsuarioPasswordReset, user=Depends(solo_archivo)):
    async with SessionLocal() as session:
        validate_password_policy(payload.new_password, "new_password")
        usuario_uuid = parse_uuid(usuario_id, "usuario_id")

        result = await session.execute(select(Usuario).where(Usuario.id == usuario_uuid))
        usuario = result.scalar_one_or_none()
        if not usuario:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        usuario.password_hash = pwd_context.hash(payload.new_password.strip())
        await session.commit()
        return {"msg": "Contrasena restablecida"}


@app.get("/trabajadores/sin-usuario")
async def listar_trabajadores_sin_usuario(user=Depends(solo_archivo)):
    async with SessionLocal() as session:
        usuarios_activos_subq = (
            select(1)
            .where(
                Usuario.trabajador_id == Trabajador.id,
                Usuario.activo == True,
            )
            .correlate(Trabajador)
        )
        result = await session.execute(
            select(Trabajador).where(
                Trabajador.activo == True,
                ~exists(usuarios_activos_subq),
            )
        )
        trabajadores = result.scalars().all()
        return [
            {
                "id": str(t.id),
                "nombre": t.nombre,
                "apellido": t.apellido,
                "rol_area": t.rol_area,
            }
            for t in trabajadores
        ]


# ── Áreas ─────────────────────────────────────────────────────────────────────

@app.get("/areas")
async def listar_areas(user=Depends(get_current_user)):
    async with SessionLocal() as session:
        result = await session.execute(
            select(Area).where(Area.activo == True).order_by(Area.nombre.asc())
        )
        areas = result.scalars().all()
        return [{"id": str(a.id), "nombre": a.nombre, "descripcion": a.descripcion} for a in areas]

@app.post("/areas")
async def crear_area(nombre: str, descripcion: str = None, user=Depends(solo_archivo)):
    async with SessionLocal() as session:
        validate_required_text(nombre, "nombre")
        nombre_clean = nombre.strip()
        result = await session.execute(select(Area).where(func.lower(Area.nombre) == nombre_clean.lower()))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="El área ya existe")
        area = Area(nombre=nombre_clean, descripcion=(descripcion.strip() if descripcion else None))
        session.add(area)
        await session.commit()
        return {"msg": "Área creada"}


# ── Pacientes (solo Archivo) ──────────────────────────────────────────────────

@app.get("/pacientes")
async def listar_pacientes(user=Depends(solo_archivo)):
    async with SessionLocal() as session:
        result = await session.execute(select(Paciente).where(Paciente.activo == True))
        pacientes = result.scalars().all()
        return [
            {
                "id": str(p.id),
                "nombre": p.nombre,
                "apellido": p.apellido,
                "fecha_nacimiento": str(p.fecha_nacimiento),
                "sexo": p.sexo,
                "telefono": p.telefono,
                "direccion": p.direccion,
            }
            for p in pacientes
        ]


@app.get("/areas/pacientes/mi-area")
async def listar_pacientes_mi_area(user=Depends(solo_areas_medicas)):
    async with SessionLocal() as session:
        area = await resolve_area_id_by_role(session, "urgencias")
        if not area:
            raise HTTPException(status_code=404, detail="No se encontró el área activa para este rol")

        pacientes_ctx = {}

        def ensure_ctx(paciente_id):
            if paciente_id not in pacientes_ctx:
                pacientes_ctx[paciente_id] = {
                    "prioridad_destino": False,
                    "fuentes": set(),
                    "ultimo_movimiento": None,
                }
            return pacientes_ctx[paciente_id]

        def touch_last(ctx, ts_value):
            ts = to_datetime(ts_value)
            if not ts:
                return
            if ctx["ultimo_movimiento"] is None or ts > ctx["ultimo_movimiento"]:
                ctx["ultimo_movimiento"] = ts

        area_norm = normalize_text(area.nombre)

        citas_result = await session.execute(
            select(Cita.paciente_id, Cita.fecha).where(
                Cita.activo == True,
                or_(
                    Cita.area_id == area.id,
                    func.lower(func.trim(Cita.area)) == area_norm,
                ),
            )
        )
        for paciente_id, cita_fecha in citas_result.fetchall():
            ctx = ensure_ctx(paciente_id)
            ctx["fuentes"].add("cita")
            touch_last(ctx, cita_fecha)

        atenciones_result = await session.execute(
            select(Atencion.paciente_id, Atencion.fecha).where(
                Atencion.activo == True,
                Atencion.area_id == area.id,
            )
        )
        for paciente_id, atencion_fecha in atenciones_result.fetchall():
            ctx = ensure_ctx(paciente_id)
            ctx["fuentes"].add("atencion")
            touch_last(ctx, atencion_fecha)

        refs_result = await session.execute(
            select(Atencion.paciente_id, Referencia.fecha)
            .join(Atencion, Atencion.id == Referencia.atencion_id)
            .where(
                Referencia.activo == True,
                Atencion.activo == True,
                Referencia.area_destino_id == area.id,
            )
        )
        for paciente_id, ref_fecha in refs_result.fetchall():
            ctx = ensure_ctx(paciente_id)
            ctx["fuentes"].add("referencia")
            ctx["prioridad_destino"] = True
            touch_last(ctx, ref_fecha)

        if not pacientes_ctx:
            return []

        pacientes_ids = list(pacientes_ctx.keys())
        pacientes_result = await session.execute(
            select(Paciente).where(
                Paciente.id.in_(pacientes_ids),
                Paciente.activo == True,
            )
        )
        pacientes = pacientes_result.scalars().all()

        response = []
        for p in pacientes:
            ctx = pacientes_ctx.get(p.id) or {}
            response.append(
                {
                    "id": str(p.id),
                    "nombre": p.nombre,
                    "apellido": p.apellido,
                    "fecha_nacimiento": str(p.fecha_nacimiento),
                    "sexo": p.sexo,
                    "telefono": p.telefono,
                    "direccion": p.direccion,
                    "prioridad_destino": bool(ctx.get("prioridad_destino")),
                    "fuentes": sorted(list(ctx.get("fuentes", set()))),
                    "ultimo_movimiento": (
                        ctx.get("ultimo_movimiento").isoformat()
                        if ctx.get("ultimo_movimiento")
                        else None
                    ),
                }
            )

        response.sort(
            key=lambda item: (
                0 if item["prioridad_destino"] else 1,
                -(datetime.fromisoformat(item["ultimo_movimiento"]).timestamp())
                if item.get("ultimo_movimiento")
                else float("inf"),
                item.get("apellido") or "",
                item.get("nombre") or "",
            )
        )
        return response


@app.get("/pacientes/sin-usuario")
async def listar_pacientes_sin_usuario(user=Depends(solo_archivo)):
    async with SessionLocal() as session:
        usuarios_activos_subq = (
            select(1)
            .where(
                Usuario.paciente_id == Paciente.id,
                Usuario.activo == True,
            )
            .correlate(Paciente)
        )
        result = await session.execute(
            select(Paciente).where(
                Paciente.activo == True,
                ~exists(usuarios_activos_subq),
            )
        )
        pacientes = result.scalars().all()
        return [
            {
                "id": str(p.id),
                "nombre": p.nombre,
                "apellido": p.apellido,
                "fecha_nacimiento": str(p.fecha_nacimiento),
                "sexo": p.sexo,
                "telefono": p.telefono,
                "direccion": p.direccion,
            }
            for p in pacientes
        ]

@app.get("/pacientes/{id}")
async def obtener_paciente(id: str):
    async with SessionLocal() as session:
        paciente_uuid = parse_uuid(id, "id")
        result = await session.execute(select(Paciente).where(
            Paciente.id == paciente_uuid, Paciente.activo == True
        ))
        p = result.scalar_one_or_none()
        if not p:
            raise HTTPException(status_code=404, detail="Paciente no encontrado")
        return {
            "id": str(p.id), "nombre": p.nombre, "apellido": p.apellido,
            "fecha_nacimiento": str(p.fecha_nacimiento), "sexo": p.sexo,
            "telefono": p.telefono, "direccion": p.direccion
        }

@app.post("/pacientes")
async def crear_paciente(data: PacienteCreate):
    async with SessionLocal() as session:
        validate_required_text(data.nombre, "nombre")
        validate_required_text(data.apellido, "apellido")
        validate_required_text(data.sexo, "sexo")

        data.nombre = data.nombre.strip()
        data.apellido = data.apellido.strip()
        data.sexo = data.sexo.strip()

        # Validar duplicado (mismo nombre+apellido+fecha)
        result = await session.execute(select(Paciente).where(
            and_(
                Paciente.nombre == data.nombre,
                Paciente.apellido == data.apellido,
                Paciente.fecha_nacimiento == data.fecha_nacimiento,
                Paciente.activo == True
            )
        ))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Ya existe un paciente con esos datos")

        paciente = Paciente(**data.dict())
        session.add(paciente)
        await session.commit()
        await session.refresh(paciente)
        return {"id": str(paciente.id), "msg": "Paciente creado"}

@app.put("/pacientes/{id}")
async def editar_paciente(id: str, data: PacienteCreate):
    async with SessionLocal() as session:
        paciente_uuid = parse_uuid(id, "id")
        validate_required_text(data.nombre, "nombre")
        validate_required_text(data.apellido, "apellido")
        validate_required_text(data.sexo, "sexo")

        data.nombre = data.nombre.strip()
        data.apellido = data.apellido.strip()
        data.sexo = data.sexo.strip()

        result = await session.execute(select(Paciente).where(
            Paciente.id == paciente_uuid, Paciente.activo == True
        ))
        paciente = result.scalar_one_or_none()
        if not paciente:
            raise HTTPException(status_code=404, detail="Paciente no encontrado")
        for key, value in data.dict().items():
            setattr(paciente, key, value)
        await session.commit()
        return {"msg": "Paciente actualizado"}

@app.delete("/pacientes/{id}")
async def eliminar_paciente(id: str):
    async with SessionLocal() as session:
        paciente_uuid = parse_uuid(id, "id")
        result = await session.execute(select(Paciente).where(
            Paciente.id == paciente_uuid, Paciente.activo == True
        ))
        paciente = result.scalar_one_or_none()
        if not paciente:
            raise HTTPException(status_code=404, detail="Paciente no encontrado")
        paciente.activo = False
        await session.commit()
        return {"msg": "Paciente eliminado"}



# ── Citas (solo Archivo) ──────────────────────────────────────────────────────

@app.post("/citas")
async def crear_cita(cita: CitaCreate, user=Depends(solo_archivo)):
    async with SessionLocal() as session:
        paciente_uuid = parse_uuid(cita.paciente_id, "paciente_id")

        validate_required_text(cita.area, "area")
        area = await resolver_area_activa(session, cita.area)

        # Validar que el paciente exista y esté activo
        result = await session.execute(select(Paciente).where(
            Paciente.id == paciente_uuid,
            Paciente.activo == True
        ))
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Paciente no encontrado")

        # ❌ No fechas pasadas
        if cita.fecha < datetime.now():
            raise HTTPException(status_code=400, detail="No puedes agendar en el pasado")

        # ❌ Máximo 3 citas activas
        count_query = select(func.count()).where(
            Cita.paciente_id == paciente_uuid,
            Cita.activo == True
        )
        total = await session.scalar(count_query)
        if total >= 3:
            raise HTTPException(status_code=400, detail="Máximo 3 citas activas")

        # ❌ No duplicadas mismo horario
        dup_query = select(Cita).where(
            Cita.paciente_id == paciente_uuid,
            Cita.fecha == cita.fecha,
            Cita.activo == True
        )
        existe = await session.execute(dup_query)
        if existe.scalar():
            raise HTTPException(status_code=400, detail="Ya existe una cita en ese horario")

        nueva = Cita(
            paciente_id=paciente_uuid,
            fecha=cita.fecha,
            area_id=area.id,
            area=area.nombre,
            activo=True,
        )
        session.add(nueva)
        await session.commit()
        return {"msg": "Cita creada"}

@app.get("/citas")
async def listar_citas(user=Depends(solo_archivo)):
    async with SessionLocal() as session:
        result = await session.execute(select(Cita).where(Cita.activo == True))
        citas = result.scalars().all()
        return [
            {
                "id": str(c.id),
                "paciente_id": str(c.paciente_id),
                "fecha": str(c.fecha),
                "area_id": str(c.area_id),
                "area": c.area
            }
            for c in citas
        ]

@app.delete("/citas/{id}")
async def cancelar_cita(id: str, user=Depends(solo_archivo)):
    async with SessionLocal() as session:
        cita_uuid = parse_uuid(id, "id")
        result = await session.execute(select(Cita).where(
            Cita.id == cita_uuid,
            Cita.activo == True,
        ))
        cita = result.scalar_one_or_none()
        if not cita:
            raise HTTPException(status_code=404, detail="Cita no encontrada")
        cita.activo = False
        await session.commit()
        return {"msg": "Cita cancelada"}


# ── Atenciones (áreas médicas) ────────────────────────────────────────────────

@app.post("/atenciones")
async def registrar_atencion(data: AtencionCreate, user=Depends(solo_areas_medicas)):
    async with SessionLocal() as session:
        paciente_uuid = parse_uuid(data.paciente_id, "paciente_id")
        area_uuid = parse_uuid(data.area_id, "area_id")

        # Campos obligatorios de atención
        if data.descripcion is not None and not data.descripcion.strip():
            data.descripcion = None

        # Validar paciente activo
        result = await session.execute(select(Paciente).where(
            Paciente.id == paciente_uuid,
            Paciente.activo == True,
        ))
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Paciente no encontrado")

        # Validar area activa
        result = await session.execute(select(Area).where(
            Area.id == area_uuid,
            Area.activo == True,
        ))
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Área no encontrada")

        atencion = Atencion(
            paciente_id=paciente_uuid,
            area_id=area_uuid,
            usuario_id=uuid.UUID("00000000-0000-0000-0000-000000000004"),
            fecha=date.today(),
            hora=datetime.now().time(),
            descripcion=data.descripcion
        )
        session.add(atencion)

        # Registrar en historial automáticamente
        historial = Historial(
            paciente_id=paciente_uuid,
            fecha=date.today(),
            descripcion=f"Atención registrada: {data.descripcion or 'Sin descripción'}",
            tipo="atencion"
        )
        session.add(historial)
        await session.commit()
        await session.refresh(atencion)
        return {"msg": "Atención registrada", "atencion_id": str(atencion.id)}

@app.get("/atenciones")
async def listar_atenciones(paciente_id: str = None, user=Depends(get_current_user)):
    async with SessionLocal() as session:
        query = select(Atencion).where(Atencion.activo == True)
        if paciente_id:
            query = query.where(Atencion.paciente_id == parse_uuid(paciente_id, "paciente_id"))
        result = await session.execute(query)
        atenciones = result.scalars().all()
        return [
            {
                "id": str(a.id), "paciente_id": str(a.paciente_id),
                "area_id": str(a.area_id), "fecha": str(a.fecha),
                "hora": str(a.hora), "descripcion": a.descripcion
            }
            for a in atenciones
        ]


# ── Historial ─────────────────────────────────────────────────────────────────

@app.get("/historial/{paciente_id}")
async def obtener_historial(paciente_id: str, user=Depends(solo_archivo)):
    async with SessionLocal() as session:
        paciente_uuid = parse_uuid(paciente_id, "paciente_id")
        result = await session.execute(select(Historial).where(
            and_(Historial.paciente_id == paciente_uuid, Historial.activo == True)
        ).order_by(Historial.fecha.desc()))
        historial = result.scalars().all()
        return [
            {
                "id": str(h.id), "fecha": str(h.fecha),
                "descripcion": h.descripcion, "tipo": h.tipo
            }
            for h in historial
        ]


# ── Referencias ───────────────────────────────────────────────────────────────

@app.post("/referencias")
async def crear_referencia(data: ReferenciaCreate, user=Depends(solo_areas_medicas)):
    async with SessionLocal() as session:
        atencion_uuid = parse_uuid(data.atencion_id, "atencion_id")
        area_destino_uuid = parse_uuid(data.area_destino_id, "area_destino_id")
        validate_required_text(data.motivo, "motivo")

        # Obtener la atención para saber el paciente
        result = await session.execute(select(Atencion).where(
            Atencion.id == atencion_uuid,
            Atencion.activo == True,
        ))
        atencion = result.scalar_one_or_none()
        if not atencion:
            raise HTTPException(status_code=404, detail="Atención no encontrada")

        # Validar área destino activa
        result_area = await session.execute(select(Area).where(
            Area.id == area_destino_uuid,
            Area.activo == True,
        ))
        area_destino = result_area.scalar_one_or_none()
        if not area_destino:
            raise HTTPException(status_code=404, detail="Área destino no encontrada")

        referencia = Referencia(
            atencion_id=atencion_uuid,
            area_destino_id=area_destino_uuid,
            motivo=data.motivo.strip(),
            fecha=date.today(),
            prioridad=True  # paciente referido tiene prioridad
        )
        session.add(referencia)

        # Registrar automáticamente en historial
        nombre_area = area_destino.nombre

        historial = Historial(
            paciente_id=atencion.paciente_id,
            fecha=date.today(),
            descripcion=f"Referencia generada a {nombre_area}: {data.motivo.strip()}",
            tipo="referencia"
        )
        session.add(historial)
        await session.commit()
        return {"msg": "Referencia creada y registrada en historial"}

@app.get("/referencias")
async def listar_referencias(paciente_id: str = None, user=Depends(get_current_user)):
    async with SessionLocal() as session:
        query = select(Referencia).where(Referencia.activo == True)
        if paciente_id:
            try:
                pid_uuid = uuid.UUID(paciente_id)
            except ValueError:
                raise HTTPException(status_code=400, detail="paciente_id inválido")

            atenciones_subquery = select(Atencion.id).where(
                Atencion.paciente_id == pid_uuid,
                Atencion.activo == True,
            )
            query = query.where(Referencia.atencion_id.in_(atenciones_subquery))

        result = await session.execute(query)
        referencias = result.scalars().all()
        return [
            {
                "id": str(r.id), "atencion_id": str(r.atencion_id),
                "area_destino_id": str(r.area_destino_id),
                "motivo": r.motivo, "fecha": str(r.fecha),
                "prioridad": r.prioridad
            }
            for r in referencias
        ]

@app.get("/")
async def root():
    return {"msg": "NUEVA VERSION"}




# Bloque de arranque para Render y ejecución local
if __name__ == "__main__":
    import uvicorn
    try:
        port = int(os.environ.get("PORT", 10000))
        uvicorn.run("backend.main:app", host="0.0.0.0", port=port)
    except Exception as e:
        import traceback
        print("ERROR AL INICIAR UVICORN O CONECTAR A LA BASE DE DATOS")
        traceback.print_exc()
        raise