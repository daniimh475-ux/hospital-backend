import threading
import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime, timedelta

import requests

try:
    from tkcalendar import DateEntry
except Exception:
    DateEntry = None

API_BASE_URL = "https://hospital-backend-o0on.onrender.com"

BG_APP = "#eef3f8"
BG_PANEL = "#ffffff"
BG_HEADER = "#0a5a5a"
TXT_DARK = "#1f2d3d"
TXT_SOFT = "#5b7083"
ACCENT = "#208b7a"

AREAS_HOSPITAL = [
    "Urgencias",
    "Medicina Familiar",
    "Vacunacion",
    "Planificacion Familiar",
    "Terapia Fisica",
    "Psicologia",
]


class CitasFrame(tk.Frame):
    def __init__(self, master, token, volver_callback=None):
        super().__init__(master, bg=BG_APP)
        self.token = token
        self.volver_callback = volver_callback
        self._build_ui()
        self._cargar()

    def _headers(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    def _build_ui(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("HosC.Treeview", rowheight=28, font=("Segoe UI", 9), background="white", fieldbackground="white")
        style.configure("HosC.Treeview.Heading", font=("Segoe UI", 9, "bold"), background="#d7f0ec", foreground=TXT_DARK)

        top = tk.Frame(self, bg=BG_HEADER, height=72)
        top.pack(fill="x")
        top.pack_propagate(False)
        tk.Label(
            top,
            text="Módulo de Citas - Agenda Hospitalaria",
            bg=BG_HEADER,
            fg="white",
            font=("Segoe UI", 13, "bold"),
        ).pack(side="left", padx=16, pady=18)

        body = tk.Frame(self, bg=BG_APP)
        body.pack(fill="both", expand=True, padx=14, pady=12)

        card = tk.Frame(body, bg=BG_PANEL, bd=1, relief="solid")
        card.pack(fill="both", expand=True)

        card_head = tk.Frame(card, bg=BG_PANEL)
        card_head.pack(fill="x", padx=12, pady=(10, 6))
        tk.Label(card_head, text="Citas programadas", bg=BG_PANEL, fg=TXT_DARK, font=("Segoe UI", 11, "bold")).pack(side="left")
        self.status_lbl = tk.Label(card_head, text="", bg=BG_PANEL, fg=TXT_SOFT, font=("Segoe UI", 9))
        self.status_lbl.pack(side="right")

        columnas = ("paciente_id", "fecha", "area")
        self.tree = ttk.Treeview(card, columns=columnas, show="headings", style="HosC.Treeview")

        titles = {"paciente_id": "Paciente (Expediente)", "fecha": "Fecha y hora", "area": "Área"}
        widths = {"paciente_id": 280, "fecha": 220, "area": 220}

        for col in columnas:
            self.tree.heading(col, text=titles[col])
            self.tree.column(col, width=widths[col], anchor="w")

        self.tree.pack(fill="both", expand=True, padx=12, pady=6)

        btns = tk.Frame(card, bg=BG_PANEL)
        btns.pack(fill="x", padx=12, pady=(4, 12))

        tk.Button(
            btns,
            text="Nueva cita",
            command=self._agregar,
            bg=ACCENT,
            fg="white",
            activebackground="#176f61",
            activeforeground="white",
            relief="flat",
            padx=12,
            pady=6,
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left", padx=3)
        tk.Button(
            btns,
            text="Actualizar",
            command=self._cargar,
            bg="#e7edf3",
            fg=TXT_DARK,
            relief="flat",
            padx=12,
            pady=6,
            font=("Segoe UI", 9),
        ).pack(side="left", padx=3)
        if self.volver_callback:
            tk.Button(
                btns,
                text="Volver",
                command=self.volver_callback,
                bg="#e7edf3",
                fg=TXT_DARK,
                relief="flat",
                padx=12,
                pady=6,
                font=("Segoe UI", 9),
            ).pack(side="right", padx=3)

    def _cargar(self):
        self.status_lbl.config(text="Cargando agenda...")
        threading.Thread(target=self._fetch, daemon=True).start()

    def _fetch(self):
        try:
            r = requests.get(f"{API_BASE_URL}/citas", headers=self._headers(), timeout=10)
            data = r.json()
            self.after(0, lambda: self._mostrar(data))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error", str(e)))

    def _mostrar(self, citas):
        self.tree.delete(*self.tree.get_children())
        for c in citas:
            pid = str(c["paciente_id"]).replace("-", "").upper()
            expediente = f"HC-{pid[:8]}"
            self.tree.insert("", "end", values=(
                expediente,
                c["fecha"],
                c["area"],
            ))
        self.status_lbl.config(text=f"{len(citas)} citas activas")

    def _agregar(self):
        FormCita(self, self.token, self._cargar)


class FormCita(tk.Toplevel):
    def __init__(self, master, token, callback):
        super().__init__(master)
        self.token = token
        self.callback = callback
        self.title("Nueva cita")
        self.configure(bg=BG_APP)
        self.resizable(False, False)
        self.grab_set()

        card = tk.Frame(self, bg=BG_PANEL, bd=1, relief="solid")
        card.pack(padx=16, pady=16, fill="both", expand=True)

        tk.Label(card, text="Programar nueva cita", bg=BG_PANEL, fg=TXT_DARK, font=("Segoe UI", 12, "bold")).grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="w",
            padx=14,
            pady=(14, 4),
        )
        tk.Label(card, text="Formato clínico de agenda", bg=BG_PANEL, fg=TXT_SOFT, font=("Segoe UI", 9)).grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="w",
            padx=14,
            pady=(0, 12),
        )

        tk.Label(card, text="Paciente ID o Expediente (HC-XXXXXXXX)", bg=BG_PANEL, fg=TXT_DARK, font=("Segoe UI", 9)).grid(row=2, column=0, sticky="w", padx=14, pady=5)
        tk.Label(card, text="Fecha", bg=BG_PANEL, fg=TXT_DARK, font=("Segoe UI", 9)).grid(row=3, column=0, sticky="w", padx=14, pady=5)
        tk.Label(card, text="Hora", bg=BG_PANEL, fg=TXT_DARK, font=("Segoe UI", 9)).grid(row=4, column=0, sticky="w", padx=14, pady=5)
        tk.Label(card, text="Área", bg=BG_PANEL, fg=TXT_DARK, font=("Segoe UI", 9)).grid(row=5, column=0, sticky="w", padx=14, pady=5)

        self.paciente = tk.Entry(card, width=40, relief="solid", bd=1, font=("Segoe UI", 9))
        self.paciente.grid(row=2, column=1, padx=14, pady=5, ipady=3)

        if DateEntry:
            self.fecha = DateEntry(card, date_pattern="yyyy-mm-dd", width=38, font=("Segoe UI", 9))
        else:
            self.fecha = tk.Entry(card, width=40, relief="solid", bd=1, font=("Segoe UI", 9))
            self.fecha.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.fecha.grid(row=3, column=1, padx=14, pady=5, ipady=3)

        now_plus = datetime.now() + timedelta(minutes=30)
        self.hora_var = tk.StringVar(value=f"{now_plus.hour:02d}")
        self.min_var = tk.StringVar(value=f"{(now_plus.minute // 5) * 5:02d}")

        hora_frame = tk.Frame(card, bg=BG_PANEL)
        hora_frame.grid(row=4, column=1, padx=14, pady=5, sticky="w")
        ttk.Combobox(hora_frame, textvariable=self.hora_var, values=[f"{h:02d}" for h in range(24)], width=5, state="readonly").pack(side="left")
        tk.Label(hora_frame, text=":", bg=BG_PANEL, fg=TXT_DARK, font=("Segoe UI", 10, "bold")).pack(side="left", padx=4)
        ttk.Combobox(hora_frame, textvariable=self.min_var, values=[f"{m:02d}" for m in range(0, 60, 5)], width=5, state="readonly").pack(side="left")

        self.area = ttk.Combobox(card, values=AREAS_HOSPITAL, state="readonly", width=38, font=("Segoe UI", 9))
        self.area.grid(row=5, column=1, padx=14, pady=5)

        actions = tk.Frame(card, bg=BG_PANEL)
        actions.grid(row=6, column=0, columnspan=2, pady=14)

        self.btn_guardar = tk.Button(
            actions,
            text="Guardar cita",
            command=self._guardar,
            bg=ACCENT,
            fg="white",
            activebackground="#176f61",
            activeforeground="white",
            relief="flat",
            padx=16,
            pady=6,
            font=("Segoe UI", 9, "bold"),
        )
        self.btn_guardar.pack(side="left", padx=4)
        tk.Button(
            actions,
            text="Cancelar",
            command=self.destroy,
            bg="#e7edf3",
            fg=TXT_DARK,
            relief="flat",
            padx=16,
            pady=6,
            font=("Segoe UI", 9),
        ).pack(side="left", padx=4)

    def _headers(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    def _expediente(self, paciente_id):
        text = str(paciente_id).replace("-", "").upper()
        return f"HC-{text[:8]}"

    def _resolver_uuid(self, pid_input):
        raw = pid_input.strip()
        if len(raw) >= 32 and "-" in raw:
            return raw

        expediente = raw.upper()
        if expediente.startswith("HC-"):
            r = requests.get(f"{API_BASE_URL}/pacientes", headers=self._headers(), timeout=10)
            if r.status_code != 200:
                return None
            for p in r.json():
                pid = p.get("id")
                if pid and self._expediente(pid) == expediente:
                    return pid
        return raw

    def _fecha_hora_seleccionada(self):
        try:
            if DateEntry and hasattr(self.fecha, "get_date"):
                selected_date = self.fecha.get_date()
                date_text = selected_date.strftime("%Y-%m-%d")
            else:
                date_text = self.fecha.get().strip()
                datetime.strptime(date_text, "%Y-%m-%d")
            hour = self.hora_var.get().strip()
            minute = self.min_var.get().strip()
            return datetime.strptime(f"{date_text} {hour}:{minute}", "%Y-%m-%d %H:%M")
        except Exception:
            return None

    def _guardar(self):
        raw_paciente = self.paciente.get().strip()
        area = self.area.get().strip()
        fecha_hora = self._fecha_hora_seleccionada()

        if not raw_paciente or not area or not fecha_hora:
            messagebox.showwarning("Campos requeridos", "Completa paciente, fecha, hora y área.", parent=self)
            return

        # Permite agendar hoy, pero en una hora futura.
        if fecha_hora <= datetime.now():
            messagebox.showerror("Horario inválido", "Selecciona una hora futura para la cita.", parent=self)
            return

        paciente_id = self._resolver_uuid(raw_paciente)
        if not paciente_id:
            messagebox.showerror("Paciente inválido", "No se pudo resolver el expediente/ID del paciente.", parent=self)
            return

        data = {
            "paciente_id": paciente_id,
            "fecha": fecha_hora.strftime("%Y-%m-%d %H:%M:%S"),
            "area": area,
        }

        self.btn_guardar.config(state="disabled", text="Guardando...")

        def req():
            try:
                r = requests.post(
                    f"{API_BASE_URL}/citas",
                    json=data,
                    headers={"Authorization": f"Bearer {self.token}"} if self.token else {},
                    timeout=10,
                )
                if r.status_code == 200:
                    self.after(0, lambda: messagebox.showinfo("OK", "Cita creada"))
                    self.after(0, self.callback)
                    self.after(0, self.destroy)
                else:
                    self.after(0, lambda: messagebox.showerror("Error", r.text))
                    self.after(0, lambda: self.btn_guardar.config(state="normal", text="Guardar cita"))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", str(e)))
                self.after(0, lambda: self.btn_guardar.config(state="normal", text="Guardar cita"))

        threading.Thread(target=req, daemon=True).start()
