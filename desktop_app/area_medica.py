import threading
import tkinter as tk
from tkinter import messagebox, ttk

import requests

API_BASE_URL = "https://hospital-backend-o0on.onrender.com"

BG_APP = "#eef3f8"
BG_PANEL = "#ffffff"
BG_HEADER = "#375a7f"
TXT_DARK = "#1f2d3d"
TXT_SOFT = "#5b7083"
ACCENT = "#2f6fae"

ROLE_TO_AREA = {
    "urgencias": "Urgencias",
    "medicina_familiar": "Medicina Familiar",
    "vacunacion": "Vacunacion",
    "planificacion_familiar": "Planificacion Familiar",
    "terapia_fisica": "Terapia Fisica",
    "psicologia": "Psicologia",
}


def _norm(value: str) -> str:
    text = (value or "").strip().lower()
    text = text.replace("_", " ")
    text = (
        text.replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
    )
    return " ".join(text.split())


def _api_error_message(resp):
    try:
        data = resp.json()
        if isinstance(data, dict) and data.get("detail"):
            return str(data["detail"])
    except Exception:
        pass
    return resp.text


class AreaMedicaFrame(tk.Frame):
    def __init__(
        self,
        master,
        token,
        rol,
        volver_callback=None,
        panel_title=None,
        header_color=None,
        accent_color=None,
    ):
        super().__init__(master, bg=BG_APP)
        self.token = token
        self.rol = rol
        self.volver_callback = volver_callback
        self.panel_title = panel_title or f"Área Médica - {self.rol.replace('_', ' ').title()}"
        self.header_color = header_color or BG_HEADER
        self.accent_color = accent_color or ACCENT
        self.area_id = None
        self.areas_map = {}
        self.pacientes = []
        self._build_ui()
        self._load_context()

    def _headers(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    def _build_ui(self):
        top = tk.Frame(self, bg=self.header_color, height=72)
        top.pack(fill="x")
        top.pack_propagate(False)
        tk.Label(
            top,
            text=self.panel_title,
            bg=self.header_color,
            fg="white",
            font=("Segoe UI", 13, "bold"),
        ).pack(side="left", padx=16, pady=18)

        body = tk.Frame(self, bg=BG_APP)
        body.pack(fill="both", expand=True, padx=14, pady=12)

        card = tk.Frame(body, bg=BG_PANEL, bd=1, relief="solid")
        card.pack(fill="both", expand=True)

        self.tabs = ttk.Notebook(card)
        self.tabs.pack(fill="both", expand=True, padx=12, pady=12)

        self.tab_pacientes = tk.Frame(self.tabs, bg=BG_PANEL)
        self.tab_atencion = tk.Frame(self.tabs, bg=BG_PANEL)
        self.tab_referencia = tk.Frame(self.tabs, bg=BG_PANEL)
        self.tabs.add(self.tab_pacientes, text="Pacientes")
        self.tabs.add(self.tab_atencion, text="Registrar atención")
        self.tabs.add(self.tab_referencia, text="Generar referencia")

        self._build_tab_pacientes()
        self._build_tab_atencion()
        self._build_tab_referencia()

        actions = tk.Frame(card, bg=BG_PANEL)
        actions.pack(fill="x", padx=12, pady=(0, 12))
        tk.Button(
            actions,
            text="Actualizar",
            command=self._load_context,
            bg="#e7edf3",
            fg=TXT_DARK,
            relief="flat",
            padx=12,
            pady=6,
            font=("Segoe UI", 9),
        ).pack(side="left", padx=3)
        if self.volver_callback:
            tk.Button(
                actions,
                text="Cerrar sesión",
                command=self.volver_callback,
                bg="#e7edf3",
                fg=TXT_DARK,
                relief="flat",
                padx=12,
                pady=6,
                font=("Segoe UI", 9),
            ).pack(side="right", padx=3)

        self.status_lbl = tk.Label(card, text="", bg=BG_PANEL, fg=TXT_SOFT, font=("Segoe UI", 9))
        self.status_lbl.pack(anchor="w", padx=12, pady=(0, 10))

    def _build_tab_pacientes(self):
        tk.Label(
            self.tab_pacientes,
            text="Consulta básica de pacientes (solo lectura)",
            bg=BG_PANEL,
            fg=TXT_DARK,
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", padx=8, pady=(8, 6))

        cols = ("expediente", "nombre", "sexo", "fecha", "prioridad")
        self.tree = ttk.Treeview(self.tab_pacientes, columns=cols, show="headings")
        self.tree.heading("expediente", text="Expediente")
        self.tree.heading("nombre", text="Paciente")
        self.tree.heading("sexo", text="Sexo")
        self.tree.heading("fecha", text="Nacimiento")
        self.tree.heading("prioridad", text="Prioridad")
        self.tree.column("expediente", width=120, anchor="w")
        self.tree.column("nombre", width=230, anchor="w")
        self.tree.column("sexo", width=90, anchor="w")
        self.tree.column("fecha", width=130, anchor="w")
        self.tree.column("prioridad", width=110, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=8, pady=(0, 10))

    def _build_tab_atencion(self):
        tk.Label(
            self.tab_atencion,
            text="Registrar atención del paciente",
            bg=BG_PANEL,
            fg=TXT_DARK,
            font=("Segoe UI", 10, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(8, 8))

        tk.Label(self.tab_atencion, text="Paciente (UUID o HC-XXXXXXXX)", bg=BG_PANEL, fg=TXT_DARK, font=("Segoe UI", 9)).grid(row=1, column=0, sticky="w", padx=8, pady=5)
        self.paciente_entry = tk.Entry(self.tab_atencion, width=46, relief="solid", bd=1, font=("Segoe UI", 9))
        self.paciente_entry.grid(row=1, column=1, sticky="w", padx=8, pady=5, ipady=3)

        tk.Label(self.tab_atencion, text="Área actual", bg=BG_PANEL, fg=TXT_DARK, font=("Segoe UI", 9)).grid(row=2, column=0, sticky="w", padx=8, pady=5)
        self.area_lbl = tk.Label(self.tab_atencion, text=ROLE_TO_AREA.get(self.rol, self.rol), bg=BG_PANEL, fg=TXT_SOFT, font=("Segoe UI", 9, "bold"))
        self.area_lbl.grid(row=2, column=1, sticky="w", padx=8, pady=5)

        tk.Label(self.tab_atencion, text="Descripción", bg=BG_PANEL, fg=TXT_DARK, font=("Segoe UI", 9)).grid(row=3, column=0, sticky="nw", padx=8, pady=5)
        self.desc_text = tk.Text(self.tab_atencion, width=46, height=6, relief="solid", bd=1, font=("Segoe UI", 9))
        self.desc_text.grid(row=3, column=1, sticky="w", padx=8, pady=5)

        self.btn_atencion = tk.Button(
            self.tab_atencion,
            text="Registrar atención",
            command=self._registrar_atencion,
            bg=self.accent_color,
            fg="white",
            activebackground="#2b5f8f",
            activeforeground="white",
            relief="flat",
            padx=12,
            pady=6,
            font=("Segoe UI", 9, "bold"),
        )
        self.btn_atencion.grid(row=4, column=1, sticky="w", padx=8, pady=10)

    def _build_tab_referencia(self):
        tk.Label(
            self.tab_referencia,
            text="Generar referencia a otra área",
            bg=BG_PANEL,
            fg=TXT_DARK,
            font=("Segoe UI", 10, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(8, 8))

        tk.Label(self.tab_referencia, text="Atención ID", bg=BG_PANEL, fg=TXT_DARK, font=("Segoe UI", 9)).grid(row=1, column=0, sticky="w", padx=8, pady=5)
        self.atencion_entry = tk.Entry(self.tab_referencia, width=46, relief="solid", bd=1, font=("Segoe UI", 9))
        self.atencion_entry.grid(row=1, column=1, sticky="w", padx=8, pady=5, ipady=3)

        tk.Label(self.tab_referencia, text="Área destino", bg=BG_PANEL, fg=TXT_DARK, font=("Segoe UI", 9)).grid(row=2, column=0, sticky="w", padx=8, pady=5)
        self.area_destino = ttk.Combobox(self.tab_referencia, width=43, state="readonly")
        self.area_destino.grid(row=2, column=1, sticky="w", padx=8, pady=5)

        tk.Label(self.tab_referencia, text="Motivo", bg=BG_PANEL, fg=TXT_DARK, font=("Segoe UI", 9)).grid(row=3, column=0, sticky="nw", padx=8, pady=5)
        self.motivo_text = tk.Text(self.tab_referencia, width=46, height=6, relief="solid", bd=1, font=("Segoe UI", 9))
        self.motivo_text.grid(row=3, column=1, sticky="w", padx=8, pady=5)

        self.btn_referencia = tk.Button(
            self.tab_referencia,
            text="Generar referencia",
            command=self._generar_referencia,
            bg=self.accent_color,
            fg="white",
            activebackground="#2b5f8f",
            activeforeground="white",
            relief="flat",
            padx=12,
            pady=6,
            font=("Segoe UI", 9, "bold"),
        )
        self.btn_referencia.grid(row=4, column=1, sticky="w", padx=8, pady=10)

    def _load_context(self):
        self.status_lbl.config(text="Cargando pacientes y áreas...")
        threading.Thread(target=self._fetch_context, daemon=True).start()

    def _fetch_context(self):
        try:
            p_resp = requests.get(f"{API_BASE_URL}/areas/pacientes/mi-area", headers=self._headers(), timeout=10)
            a_resp = requests.get(f"{API_BASE_URL}/areas", headers=self._headers(), timeout=10)

            if p_resp.status_code != 200:
                msg = _api_error_message(p_resp)
                self.after(0, lambda: messagebox.showerror("Error", msg))
                self.after(0, lambda: self.status_lbl.config(text="No se pudieron cargar pacientes"))
                return
            if a_resp.status_code != 200:
                msg = _api_error_message(a_resp)
                self.after(0, lambda: messagebox.showerror("Error", msg))
                self.after(0, lambda: self.status_lbl.config(text="No se pudieron cargar áreas"))
                return

            self.pacientes = p_resp.json()
            areas = a_resp.json()
            self.areas_map = {a["nombre"]: a["id"] for a in areas}

            area_name = ROLE_TO_AREA.get(self.rol, self.rol)
            self.area_id = None
            for nombre, aid in self.areas_map.items():
                if _norm(nombre) == _norm(area_name):
                    self.area_id = aid
                    break

            def update_ui():
                self._render_pacientes()
                area_actual_norm = _norm(ROLE_TO_AREA.get(self.rol, self.rol))
                opciones = sorted(
                    [nombre for nombre in self.areas_map.keys() if _norm(nombre) != area_actual_norm]
                )
                self.area_destino["values"] = opciones
                if opciones:
                    self.area_destino.set("Selecciona un área destino")
                    self.btn_referencia.config(state="normal")
                else:
                    self.area_destino.set("Sin áreas destino disponibles")
                    self.btn_referencia.config(state="disabled")
                self.status_lbl.config(text=f"Contexto listo. Pacientes: {len(self.pacientes)}")

            self.after(0, update_ui)
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error", str(e)))
            self.after(0, lambda: self.status_lbl.config(text=""))

    def _expediente(self, paciente_id):
        text = str(paciente_id).replace("-", "").upper()
        return f"HC-{text[:8]}"

    def _render_pacientes(self):
        if not hasattr(self, "tree") or not self.tree.winfo_exists():
            return
        self.tree.delete(*self.tree.get_children())
        for p in self.pacientes:
            pid = p.get("id")
            nombre = f"{p.get('nombre', '')} {p.get('apellido', '')}".strip()
            self.tree.insert(
                "",
                "end",
                values=(
                    self._expediente(pid),
                    nombre,
                    p.get("sexo", ""),
                    p.get("fecha_nacimiento", ""),
                    "Prioritario" if p.get("prioridad_destino") else "Normal",
                )
            )

    def _resolve_paciente(self, raw):
        value = raw.strip()
        if not value:
            return None
        if len(value) >= 32 and "-" in value:
            return value
        exp = value.upper()
        if exp.startswith("HC-"):
            for p in self.pacientes:
                pid = p.get("id")
                if pid and self._expediente(pid) == exp:
                    return pid
        return value

    def _registrar_atencion(self):
        paciente_raw = self.paciente_entry.get().strip()
        descripcion = self.desc_text.get("1.0", "end").strip()
        paciente_id = self._resolve_paciente(paciente_raw)

        if not paciente_id:
            messagebox.showwarning("Campos requeridos", "Ingresa un paciente válido")
            return
        if not self.area_id:
            messagebox.showerror("Error", "No se encontró el área para este rol")
            return

        self.btn_atencion.config(state="disabled", text="Guardando...")
        self.status_lbl.config(text="Registrando atención...")
        payload = {
            "paciente_id": paciente_id,
            "area_id": self.area_id,
            "descripcion": descripcion,
        }

        def req():
            try:
                r = requests.post(
                    f"{API_BASE_URL}/atenciones",
                    json=payload,
                    headers=self._headers(),
                    timeout=10,
                )
                if r.status_code == 200:
                    atencion_id = r.json().get("atencion_id", "")
                    self.after(0, lambda: messagebox.showinfo("OK", f"Atención registrada\nID: {atencion_id}"))
                    self.after(0, lambda: self.atencion_entry.delete(0, "end"))
                    self.after(0, lambda: self.atencion_entry.insert(0, atencion_id))
                    self.after(0, lambda: self.desc_text.delete("1.0", "end"))
                    self.after(0, lambda: self.status_lbl.config(text="Atención registrada correctamente"))
                else:
                    msg = _api_error_message(r)
                    self.after(0, lambda: messagebox.showerror("Error", msg))
                    self.after(0, lambda: self.status_lbl.config(text="No se pudo registrar la atención"))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", str(e)))
                self.after(0, lambda: self.status_lbl.config(text="Error de conexión al registrar atención"))
            finally:
                self.after(0, lambda: self.btn_atencion.config(state="normal", text="Registrar atención"))

        threading.Thread(target=req, daemon=True).start()

    def _generar_referencia(self):
        atencion_id = self.atencion_entry.get().strip()
        area_nombre = self.area_destino.get().strip()
        motivo = self.motivo_text.get("1.0", "end").strip()

        if not atencion_id or not area_nombre or not motivo:
            messagebox.showwarning("Campos requeridos", "Completa atención, área destino y motivo")
            return

        if area_nombre in ("Selecciona un área destino", "Sin áreas destino disponibles"):
            messagebox.showwarning("Área requerida", "Selecciona un área destino válida")
            return

        area_destino_id = self.areas_map.get(area_nombre)
        if not area_destino_id:
            messagebox.showerror("Error", "Área destino inválida")
            return

        self.btn_referencia.config(state="disabled", text="Guardando...")
        self.status_lbl.config(text="Generando referencia...")
        payload = {
            "atencion_id": atencion_id,
            "area_destino_id": area_destino_id,
            "motivo": motivo,
        }

        def req():
            try:
                r = requests.post(
                    f"{API_BASE_URL}/referencias",
                    json=payload,
                    headers=self._headers(),
                    timeout=10,
                )
                if r.status_code == 200:
                    self.after(0, lambda: messagebox.showinfo("OK", "Referencia generada"))
                    self.after(0, lambda: self.motivo_text.delete("1.0", "end"))
                    self.after(0, lambda: self.status_lbl.config(text="Referencia generada correctamente"))
                else:
                    msg = _api_error_message(r)
                    self.after(0, lambda: messagebox.showerror("Error", msg))
                    self.after(0, lambda: self.status_lbl.config(text="No se pudo generar la referencia"))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", str(e)))
                self.after(0, lambda: self.status_lbl.config(text="Error de conexión al generar referencia"))
            finally:
                self.after(0, lambda: self.btn_referencia.config(state="normal", text="Generar referencia"))

        threading.Thread(target=req, daemon=True).start()
