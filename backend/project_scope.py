"""Definicion oficial del alcance y reglas del Sistema Integral Hospitalario (Python)."""

AREAS_HOSPITALARIAS = [
    "urgencias",
    "medicina_familiar",
    "vacunacion",
    "planificacion_familiar",
    "terapia_fisica",
    "psicologia",
]

ROLES_VALIDOS = ["archivo", *AREAS_HOSPITALARIAS]

PLANTEAMIENTO = {
    "problema": (
        "Un hospital requiere gestionar ingreso y atencion de pacientes en varias areas, "
        "con control total de altas, bajas y modificaciones restringido al area de Archivo Clinico."
    ),
    "areas": [
        "Urgencias",
        "Medicina Familiar",
        "Vacunacion",
        "Planificacion Familiar",
        "Terapia Fisica",
        "Psicologia",
    ],
    "capacidades_por_area": [
        "Registrar pacientes atendidos",
        "Consultar informacion basica del paciente",
        "Referir pacientes a otras areas del hospital",
    ],
}

OBJETIVOS_ESPECIFICOS = [
    "Implementar un sistema de escritorio en Python para el area de Archivo",
    "Implementar un backend con API REST obligatoria",
    "Controlar el acceso y permisos segun el tipo de usuario",
    "Implementar logica de negocio para referencia de pacientes entre areas",
    "Garantizar integridad, seguridad y consistencia de los datos",
]

ALCANCE_DESKTOP_ARCHIVO = [
    "Uso exclusivo para el area de Archivo",
    "CRUD completo de pacientes",
    "Consulta de historial clinico",
    "Administracion de citas",
    "Visualizacion de referencias entre areas",
]

FUNCIONES_AREA_ARCHIVO = [
    "Crear paciente",
    "Editar paciente",
    "Eliminar paciente (eliminacion logica)",
    "Consultar pacientes",
    "Consultar historial completo",
    "Validar duplicidad de registros",
]

FUNCIONES_AREAS_MEDICAS = [
    "Registrar atencion de paciente",
    "Consultar datos del paciente (solo lectura)",
    "Generar referencia a otra area",
]

ARQUITECTURA = {
    "componentes": [
        "Frontend Web (HTML, CSS, JS o framework)",
        "Backend Web (API REST)",
        "Aplicacion Desktop en Python (Tkinter, PyQt o similar)",
        "Base de Datos en la nube (MySQL, PostgreSQL o similar)",
    ],
    "comunicacion": [
        "Desktop -> Backend -> Base de Datos",
        "Web -> Backend -> Base de Datos",
    ],
    "restriccion_obligatoria": "Prohibido acceso directo del frontend a la base de datos",
}

REGLAS_NEGOCIO_CRITICAS = [
    "Solo Archivo puede realizar CRUD sobre pacientes",
    "Ninguna area medica puede modificar datos personales",
    "Un usuario debe registrarse antes de utilizar el sistema",
    "Cada usuario debe estar vinculado a un paciente",
    "No puede existir mas de una cuenta por correo electronico",
    "Un paciente no puede tener citas duplicadas en el mismo horario",
    "Un paciente no puede tener mas de 3 citas activas",
    "No se pueden agendar citas en fechas pasadas",
    "Las referencias deben registrarse automaticamente en el historial",
    "Un paciente referido debe tener prioridad en el area destino",
    "Eliminacion logica obligatoria (no borrado fisico)",
    "Validacion obligatoria de todos los campos",
    "Acceso restringido a funcionalidades sin autenticacion",
]

PROJECT_PYTHON_SCOPE = {
    "titulo": "Sistema Integral Hospitalario - PYTHON",
    "planteamiento": PLANTEAMIENTO,
    "objetivos_especificos": OBJETIVOS_ESPECIFICOS,
    "alcance_del_proyecto": "El sistema debera contemplar:",
    "alcance_desktop_archivo": ALCANCE_DESKTOP_ARCHIVO,
    "area_de_archivo": {
        "titulo": "Area de Archivo (Aplicacion Desktop en Python)",
        "funciones": FUNCIONES_AREA_ARCHIVO,
    },
    "areas_medicas": {
        "titulo": "Areas Medicas",
        "funciones": FUNCIONES_AREAS_MEDICAS,
    },
    "arquitectura": ARQUITECTURA,
    "reglas_negocio_criticas": REGLAS_NEGOCIO_CRITICAS,
}
