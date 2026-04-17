# Sistema Integral Hospitalario

## Planteamiento Del Problema
Un hospital requiere un sistema que permita gestionar el ingreso y atencion de pacientes en las siguientes areas:
- Urgencias
- Medicina Familiar
- Vacunacion
- Planificacion Familiar
- Terapia Fisica
- Psicologia

Cada area debe poder:
- Registrar pacientes atendidos.
- Consultar informacion basica del paciente.
- Referir pacientes a otras areas del hospital.

Sin embargo, el control total de la informacion (altas, bajas y modificaciones) estara restringido exclusivamente al area de Archivo Clinico.

## Objetivos Especificos
- Implementar un sistema de escritorio en Python para el area de Archivo.
- Implementar un backend con API REST obligatoria.
- Controlar el acceso y permisos segun el tipo de usuario.
- Implementar logica de negocio para referencia de pacientes entre areas.
- Garantizar integridad, seguridad y consistencia de los datos.

## Alcance Del Proyecto
El sistema debera contemplar:

### Aplicacion De Escritorio (Python)
- Uso exclusivo para el area de Archivo.
- CRUD completo de pacientes.
- Consulta de historial clinico.
- Administracion de citas.
- Visualizacion de referencias entre areas.

## Arquitectura Del Sistema
El sistema esta compuesto por:
- Frontend Web (HTML, CSS, JS).
- Backend Web (API REST obligatoria).
- Aplicacion Desktop en Python (Tkinter).
- Base de Datos en la nube (PostgreSQL).

Comunicacion:
- Desktop -> Backend -> Base de Datos.
- Web -> Backend -> Base de Datos.

Restriccion obligatoria:
- Prohibido acceso directo del frontend a la base de datos.

## Funciones Por Area

### Area De Archivo (Aplicacion Desktop En Python)
- Crear paciente.
- Editar paciente.
- Eliminar paciente (eliminacion logica).
- Consultar pacientes.
- Consultar historial completo.
- Validar duplicidad de registros.

### Areas Medicas
- Registrar atencion de paciente.
- Consultar datos del paciente (solo lectura).
- Generar referencia a otra area.

## Reglas De Negocio Criticas
- Solo el area de Archivo puede realizar operaciones CRUD sobre pacientes.
- Ninguna area medica puede modificar datos personales.
- Un usuario debe registrarse antes de utilizar el sistema.
- Cada usuario debe estar vinculado a un paciente.
- No puede existir mas de una cuenta por correo electronico.
- Un paciente no puede tener citas duplicadas en el mismo horario.
- Un paciente no puede tener mas de 3 citas activas.
- No se pueden agendar citas en fechas pasadas.
- Las referencias deben registrarse automaticamente en el historial.
- Un paciente referido debe tener prioridad en el area destino.
- Eliminacion logica obligatoria (no borrado fisico).
- Validacion obligatoria de todos los campos.
- Acceso restringido a funcionalidades sin autenticacion.

## Estado Actual De Implementacion
- `backend/main.py`: API REST con autenticacion JWT, pacientes, citas, atenciones, historial y referencias.
- `desktop_app/`: app de Archivo con login, pacientes, citas, historial y referencias.
- Base de datos PostgreSQL en la nube configurada por variables en `.env`.
