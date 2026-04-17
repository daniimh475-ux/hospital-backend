from __future__ import annotations

import asyncio
import sys
import uuid
from datetime import datetime, timedelta
from typing import Any

import requests
from sqlalchemy import text

from backend.db import engine

BASE_URL = "http://127.0.0.1:8001"
ARCHIVO_USER = "admin"
ARCHIVO_PASS = "admin"
TIMEOUT = 10
TEST_TAG = "[RUNTIME_TEST]"


async def cleanup_runtime_artifacts() -> None:
        """Desactiva registros de prueba para no ensuciar los modulos visuales."""
        statements = [
                text(
                        """
                        UPDATE referencia
                        SET activo = FALSE
                        WHERE activo = TRUE
                            AND (
                                motivo ILIKE '%Referencia de prueba runtime%'
                                OR motivo ILIKE :tag_like
                            )
                        """
                ),
                text(
                        """
                        UPDATE atencion
                        SET activo = FALSE
                        WHERE activo = TRUE
                            AND (
                                descripcion ILIKE '%Atencion de prueba runtime%'
                                OR descripcion ILIKE :tag_like
                            )
                        """
                ),
                text(
                        """
                        UPDATE historial
                        SET activo = FALSE
                        WHERE activo = TRUE
                            AND (
                                descripcion ILIKE '%prueba runtime%'
                                OR descripcion ILIKE :tag_like
                            )
                        """
                ),
                text(
                        """
                        UPDATE citas
                        SET activo = FALSE
                        WHERE activo = TRUE
                            AND paciente_id IN (
                                SELECT id
                                FROM paciente
                                WHERE apellido = 'Runtime'
                                    AND (
                                        nombre ILIKE 'Test%'
                                        OR nombre ILIKE 'RTTest%'
                                    )
                            )
                        """
                ),
                text(
                        """
                        UPDATE usuario
                        SET activo = FALSE
                        WHERE activo = TRUE
                            AND (
                                email ILIKE 'urg.demo.%@gmail.com'
                                OR email ILIKE 'rt.runtime.%@gmail.com'
                            )
                        """
                ),
                text(
                        """
                        UPDATE paciente
                        SET activo = FALSE
                        WHERE activo = TRUE
                            AND apellido = 'Runtime'
                            AND (
                                nombre ILIKE 'Test%'
                                OR nombre ILIKE 'RTTest%'
                            )
                        """
                ),
        ]

        async with engine.begin() as conn:
                for stmt in statements:
                        await conn.execute(stmt, {"tag_like": f"%{TEST_TAG}%"})


class RuntimeValidator:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.failures: list[str] = []

    def _record(self, name: str, ok: bool, detail: str = "") -> None:
        if ok:
            print(f"OK   {name}")
            return
        msg = f"FAIL {name}"
        if detail:
            msg = f"{msg} -> {detail}"
        print(msg)
        self.failures.append(msg)

    def _request(
        self,
        method: str,
        path: str,
        expected_status: int | None = None,
        token: str | None = None,
        **kwargs: Any,
    ) -> requests.Response:
        headers = kwargs.pop("headers", {})
        if token:
            headers["Authorization"] = f"Bearer {token}"
        response = requests.request(
            method=method,
            url=f"{self.base_url}{path}",
            headers=headers,
            timeout=TIMEOUT,
            **kwargs,
        )
        if expected_status is not None:
            self._record(
                f"{method.upper()} {path} == {expected_status}",
                response.status_code == expected_status,
                f"status={response.status_code}, body={response.text[:180]}",
            )
        return response

    def _login(self, username: str, password: str, label: str) -> str | None:
        response = self._request(
            "post",
            "/login",
            data={"username": username, "password": password},
        )
        self._record(label, response.status_code == 200, f"status={response.status_code}")
        if response.status_code != 200:
            return None
        return response.json().get("access_token")

    def run(self) -> int:
        # Reutilizar el mismo loop evita errores de asyncpg por cambio de event loop.
        cleanup_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(cleanup_loop)
        cleanup_loop.run_until_complete(cleanup_runtime_artifacts())

        try:
            archivo_token = self._login(ARCHIVO_USER, ARCHIVO_PASS, "login_archivo")
            if not archivo_token:
                print("\nNo se puede continuar sin login de Archivo.")
                return 1

            pacientes_resp = self._request("get", "/pacientes", token=archivo_token)
            self._record("archivo_get_pacientes", pacientes_resp.status_code == 200)
            if pacientes_resp.status_code != 200:
                return 1

            areas_resp = self._request("get", "/areas", token=archivo_token)
            self._record("archivo_get_areas", areas_resp.status_code == 200)
            if areas_resp.status_code != 200:
                return 1

            areas = areas_resp.json()

            if not areas:
                create_area = self._request(
                    "post",
                    "/areas",
                    token=archivo_token,
                    params={"nombre": "Urgencias", "descripcion": "Area de urgencias"},
                )
                self._record("archivo_crea_area_si_no_existe", create_area.status_code in (200, 400))
                areas_resp = self._request("get", "/areas", token=archivo_token)
                areas = areas_resp.json() if areas_resp.status_code == 200 else []

            if not areas:
                self._record("existen_areas", False, "No se pudo obtener/crear areas")
                return 1

            area_urgencias = next((a for a in areas if a.get("nombre") == "Urgencias"), None)
            if not area_urgencias:
                self._record("existe_area_urgencias", False, str(areas))
                return 1

            area_id = area_urgencias["id"]

            # Crear paciente de prueba aislado.
            suffix = uuid.uuid4().hex[:6]
            nuevo_paciente_resp = self._request(
                "post",
                "/pacientes",
                token=archivo_token,
                json={
                    "nombre": f"RTTest{suffix}",
                    "apellido": "Runtime",
                    "fecha_nacimiento": "2000-01-01",
                    "sexo": "M",
                    "telefono": "",
                    "direccion": "",
                },
            )
            self._record("archivo_crear_paciente_prueba", nuevo_paciente_resp.status_code == 200)
            if nuevo_paciente_resp.status_code != 200:
                return 1

            paciente_for_user = nuevo_paciente_resp.json().get("id")
            if not paciente_for_user:
                self._record("paciente_prueba_con_id", False, str(nuevo_paciente_resp.text))
                return 1

            # Registrar usuario medico temporal.
            med_email = f"rt.runtime.{uuid.uuid4().hex[:8]}@gmail.com"
            med_pass = "Demo1234"
            register_resp = self._request(
                "post",
                "/registro",
                token=archivo_token,
                json={
                    "paciente_id": paciente_for_user,
                    "email": med_email,
                    "password": med_pass,
                    "rol": "urgencias",
                },
            )
            self._record("registro_urgencias", register_resp.status_code == 200, f"status={register_resp.status_code}")
            if register_resp.status_code != 200:
                print(register_resp.text)
                return 1

            medico_token = self._login(med_email, med_pass, "login_urgencias")
            if not medico_token:
                return 1

            # Permisos de pacientes
            self._request(
                "post",
                "/pacientes",
                expected_status=403,
                token=medico_token,
                json={"nombre": "X", "apellido": "Y", "fecha_nacimiento": "2000-01-01", "sexo": "M"},
            )
            self._request("get", "/pacientes", expected_status=200, token=medico_token)

            # Atencion y referencia
            atencion_resp = self._request(
                "post",
                "/atenciones",
                token=medico_token,
                json={
                    "paciente_id": paciente_for_user,
                    "area_id": area_id,
                    "descripcion": f"Atencion de prueba runtime {TEST_TAG}",
                },
            )
            self._record("medico_post_atenciones", atencion_resp.status_code == 200)
            if atencion_resp.status_code != 200:
                return 1

            atencion_id = atencion_resp.json().get("atencion_id")
            ref_resp = self._request(
                "post",
                "/referencias",
                token=medico_token,
                json={
                    "atencion_id": atencion_id,
                    "area_destino_id": area_id,
                    "motivo": f"Referencia de prueba runtime {TEST_TAG}",
                },
            )
            self._record("medico_post_referencias", ref_resp.status_code == 200)

            pacientes_area_resp = self._request("get", "/areas/pacientes/mi-area", token=medico_token)
            self._record("medico_get_pacientes_mi_area", pacientes_area_resp.status_code == 200)
            if pacientes_area_resp.status_code == 200:
                pacientes_area = pacientes_area_resp.json()
                existe_en_area = any(p.get("id") == paciente_for_user for p in pacientes_area)
                self._record("medico_ve_paciente_en_mi_area", existe_en_area)

            # Historial por rol
            self._request(
                "get",
                f"/historial/{paciente_for_user}",
                expected_status=403,
                token=medico_token,
            )
            self._request(
                "get",
                f"/historial/{paciente_for_user}",
                expected_status=200,
                token=archivo_token,
            )

            # Reglas de citas: maximo 3, no duplicadas, no pasado
            start = (datetime.now() + timedelta(days=1)).replace(minute=0, second=0, microsecond=0)
            cita_statuses: list[int] = []
            for i in range(1, 5):
                cita_resp = self._request(
                    "post",
                    "/citas",
                    token=archivo_token,
                    json={
                        "paciente_id": paciente_for_user,
                        "fecha": (start + timedelta(hours=i)).isoformat(),
                        "area": "Urgencias",
                    },
                )
                cita_statuses.append(cita_resp.status_code)

            self._record("archivo_crear_3_citas", cita_statuses[:3] == [200, 200, 200], str(cita_statuses))
            self._record("archivo_bloquea_4ta_cita", cita_statuses[3] == 400, str(cita_statuses))

            dup_resp = self._request(
                "post",
                "/citas",
                token=archivo_token,
                json={
                    "paciente_id": paciente_for_user,
                    "fecha": (start + timedelta(hours=1)).isoformat(),
                    "area": "Urgencias",
                },
            )
            self._record("archivo_cita_duplicada_bloqueada", dup_resp.status_code == 400)

            past_resp = self._request(
                "post",
                "/citas",
                token=archivo_token,
                json={
                    "paciente_id": paciente_for_user,
                    "fecha": (datetime.now() - timedelta(days=1)).isoformat(),
                    "area": "Urgencias",
                },
            )
            self._record("archivo_cita_pasada_bloqueada", past_resp.status_code == 400)

            print("\nResumen:")
            if self.failures:
                print(f"- Fallas: {len(self.failures)}")
                for failure in self.failures:
                    print(f"  {failure}")
                return 1

            print("- Todas las validaciones pasaron correctamente.")
            return 0
        finally:
            try:
                cleanup_loop.run_until_complete(cleanup_runtime_artifacts())
            finally:
                cleanup_loop.close()


def main() -> None:
    print(f"Validando reglas runtime contra {BASE_URL}")
    validator = RuntimeValidator(BASE_URL)
    code = validator.run()
    sys.exit(code)


if __name__ == "__main__":
    main()
