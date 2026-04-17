import threading
import tkinter as tk
from tkinter import messagebox, ttk

import requests

API_BASE_URL = "http://127.0.0.1:8001"

BG_APP = "#eef3f8"
BG_PANEL = "#ffffff"
BG_HEADER = "#0b4f73"
TXT_DARK = "#1f2d3d"
TXT_SOFT = "#5b7083"
ACCENT = "#1f7aa8"


class FormPaciente(tk.Toplevel):
    def __init__(self, master, callback, paciente=None):
        super().__init__(master)
        self.callback = callback
        self.paciente = paciente
        self.title("Ficha de Paciente" if paciente else "Nuevo Ingreso de Paciente")
        self.configure(bg=BG_APP)
        self.resizable(False, False)
        self.grab_set()
        self._build_ui()

    def _build_ui(self):
        card = tk.Frame(self, bg=BG_PANEL, bd=1, relief="solid")
        card.pack(padx=16, pady=16, fill="both", expand=True)

        tk.Label(
            card,
            text="Formulario de Archivo Clínico",
            bg=BG_PANEL,
            fg=TXT_DARK,
            font=("Segoe UI", 12, "bold"),
        ).grid(row=0, column=0, columnspan=2, padx=14, pady=(14, 4), sticky="w")

        tk.Label(
            card,
            text="Complete los datos obligatorios del paciente",
            bg=BG_PANEL,
            fg=TXT_SOFT,
            font=("Segoe UI", 9),
        ).grid(row=1, column=0, columnspan=2, padx=14, pady=(0, 12), sticky="w")

        fields = [
            ("Nombres", "nombre"),
            ("Apellidos", "apellido"),
            ("Fecha de nacimiento (YYYY-MM-DD)", "fecha_nacimiento"),
            ("Sexo", "sexo"),
            ("Teléfono", "telefono"),
            ("Dirección", "direccion"),
        ]

        self.entries = {}
        for idx, (label, key) in enumerate(fields, start=2):
            tk.Label(card, text=label, bg=BG_PANEL, fg=TXT_DARK, font=("Segoe UI", 9)).grid(
                row=idx,
                column=0,
                sticky="w",
                padx=14,
                pady=5,
            )
            entry = tk.Entry(card, width=38, relief="solid", bd=1, font=("Segoe UI", 9))
            entry.grid(row=idx, column=1, padx=14, pady=5, ipady=3)
            if self.paciente:
                entry.insert(0, self.paciente.get(key, "") or "")
            self.entries[key] = entry

        actions = tk.Frame(card, bg=BG_PANEL)
        actions.grid(row=idx + 1, column=0, columnspan=2, pady=14)

        self.btn_guardar = tk.Button(
            actions,
            text="Guardar ficha",
            bg=ACCENT,
            fg="white",
            activebackground="#176387",
            activeforeground="white",
            relief="flat",
            padx=16,
            pady=6,
            font=("Segoe UI", 9, "bold"),
            command=self._guardar_thread,
        )
        self.btn_guardar.pack(side="left", padx=4)

        tk.Button(
            actions,
            text="Cancelar",
            bg="#e7edf3",
            fg=TXT_DARK,
            relief="flat",
            padx=16,
            pady=6,
            font=("Segoe UI", 9),
            command=self.destroy,
        ).pack(side="left", padx=4)

    def _guardar_thread(self):
        self.btn_guardar.config(state="disabled", text="Guardando...")
        threading.Thread(target=self._guardar, daemon=True).start()

    def _guardar(self):
        data = {k: e.get().strip() for k, e in self.entries.items()}
        headers = self.master._headers() if hasattr(self.master, "_headers") else {}

        if not data["nombre"] or not data["apellido"] or not data["fecha_nacimiento"] or not data["sexo"]:
            self.after(0, lambda: self._error("Completa todos los campos obligatorios."))
            return

        try:
            if self.paciente:
                response = requests.put(
                    f"{API_BASE_URL}/pacientes/{self.paciente['id']}",
                    json=data,
                    headers=headers,
                    timeout=10,
                )
            else:
                response = requests.post(
                    f"{API_BASE_URL}/pacientes",
                    json=data,
                    headers=headers,
                    timeout=10,
                )

            if response.status_code in (200, 201):
                self.after(0, self._success)
            else:
                self.after(0, lambda: self._error(f"No se pudo guardar\n{response.text}"))

        except requests.exceptions.ConnectionError:
            self.after(0, lambda: self._error("No se pudo conectar al servidor."))
        except Exception as e:
            self.after(0, lambda: self._error(str(e)))

    def _success(self):
        messagebox.showinfo("Registro clínico", "Ficha guardada correctamente")
        self.callback()
        self.destroy()

    def _error(self, msg):
        messagebox.showerror("Error", msg)
        self.btn_guardar.config(state="normal", text="Guardar ficha")


class PacientesFrame(tk.Frame):
    def __init__(self, master, token, volver_callback=None):
        super().__init__(master, bg=BG_APP)
        self.token = token
        self.volver_callback = volver_callback
        self._pacientes_ids = []
        self._build_ui()

    def _headers(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    def _build_ui(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Hos.Treeview", rowheight=28, font=("Segoe UI", 9), background="white", fieldbackground="white")
        style.configure("Hos.Treeview.Heading", font=("Segoe UI", 9, "bold"), background="#d9e6f2", foreground=TXT_DARK)

        top = tk.Frame(self, bg=BG_HEADER, height=72)
        top.pack(fill="x")
        top.pack_propagate(False)
        tk.Label(
            top,
            text="Módulo de Pacientes - Archivo Clínico",
            bg=BG_HEADER,
            fg="white",
            font=("Segoe UI", 13, "bold"),
        ).pack(side="left", padx=16, pady=18)

        body = tk.Frame(self, bg=BG_APP)
        body.pack(fill="both", expand=True, padx=14, pady=12)

        card = tk.Frame(body, bg=BG_PANEL, bd=1, relief="solid")
        card.pack(fill="both", expand=True)

        header = tk.Frame(card, bg=BG_PANEL)
        header.pack(fill="x", padx=12, pady=(10, 6))
        tk.Label(header, text="Listado de pacientes activos", bg=BG_PANEL, fg=TXT_DARK, font=("Segoe UI", 11, "bold")).pack(side="left")

        self.status_lbl = tk.Label(header, text="", bg=BG_PANEL, fg=TXT_SOFT, font=("Segoe UI", 9))
        self.status_lbl.pack(side="right")

        columnas = ("id", "nombre", "apellido", "fecha_nacimiento", "sexo", "telefono", "direccion")
        self.tree = ttk.Treeview(card, columns=columnas, show="headings", style="Hos.Treeview")
        titles = {
            "id": "Expediente",
            "nombre": "Nombre",
            "apellido": "Apellido",
            "fecha_nacimiento": "Nacimiento",
            "sexo": "Sexo",
            "telefono": "Teléfono",
            "direccion": "Dirección",
        }
        widths = {
            "id": 240,
            "nombre": 130,
            "apellido": 130,
            "fecha_nacimiento": 110,
            "sexo": 90,
            "telefono": 120,
            "direccion": 190,
        }
        for col in columnas:
            self.tree.heading(col, text=titles[col])
            self.tree.column(col, width=widths[col], anchor="w")
        self.tree.pack(padx=12, pady=6, fill="both", expand=True)

        btns = tk.Frame(card, bg=BG_PANEL)
        btns.pack(fill="x", padx=12, pady=(4, 12))

        self._make_btn(btns, "Nuevo paciente", self._agregar).pack(side="left", padx=3)
        self._make_btn(btns, "Editar", self._editar).pack(side="left", padx=3)
        self._make_btn(btns, "Eliminar", self._eliminar).pack(side="left", padx=3)
        self._make_btn(btns, "Copiar ID", self._copiar_id, secondary=True).pack(side="left", padx=3)
        self._make_btn(btns, "Actualizar", self._cargar_pacientes, secondary=True).pack(side="left", padx=3)
        if self.volver_callback:
            self._make_btn(btns, "Volver", self.volver_callback, secondary=True).pack(side="right", padx=3)

        self._cargar_pacientes()

    def _display_id(self, paciente_id):
        if not paciente_id:
            return ""
        text = str(paciente_id).replace("-", "").upper()
        return f"HC-{text[:8]}"

    def _make_btn(self, parent, text, command, secondary=False):
        if secondary:
            return tk.Button(
                parent,
                text=text,
                command=command,
                bg="#e7edf3",
                fg=TXT_DARK,
                relief="flat",
                padx=12,
                pady=6,
                font=("Segoe UI", 9),
            )
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=ACCENT,
            fg="white",
            activebackground="#176387",
            activeforeground="white",
            relief="flat",
            padx=12,
            pady=6,
            font=("Segoe UI", 9, "bold"),
        )

    def _cargar_pacientes(self):
        self.status_lbl.config(text="Cargando registros...")
        threading.Thread(target=self._fetch_pacientes, daemon=True).start()

    def _fetch_pacientes(self):
        try:
            response = requests.get(f"{API_BASE_URL}/pacientes", headers=self._headers(), timeout=10)
            if response.status_code == 200:
                self.after(0, lambda: self._mostrar_pacientes(response.json()))
            else:
                self.after(0, lambda: messagebox.showerror("Error", f"No se pudo obtener la lista\n{response.text}"))
        except requests.exceptions.ConnectionError:
            self.after(0, lambda: messagebox.showerror("Error", "No se pudo conectar al servidor."))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error", str(e)))

    def _mostrar_pacientes(self, pacientes):
        self.tree.delete(*self.tree.get_children())
        self._pacientes_ids = []
        for p in pacientes:
            paciente_id = p.get("id")
            self.tree.insert("", "end", values=(
                self._display_id(paciente_id),
                p.get("nombre", ""),
                p.get("apellido", ""),
                p.get("fecha_nacimiento", ""),
                p.get("sexo", ""),
                p.get("telefono", "") or "",
                p.get("direccion", "") or "",
            ))
            self._pacientes_ids.append(paciente_id)
        self.status_lbl.config(text=f"{len(self._pacientes_ids)} pacientes activos")

    def _agregar(self):
        FormPaciente(self, self._cargar_pacientes)

    def _editar(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Aviso", "Selecciona un paciente")
            return

        index = self.tree.index(selected[0])
        if index >= len(self._pacientes_ids) or self._pacientes_ids[index] is None:
            messagebox.showerror("Error", "No se encontró el ID del paciente. Recarga la lista.")
            return

        values = self.tree.item(selected[0])["values"]
        paciente = {
            "id": self._pacientes_ids[index],
            "nombre": values[1],
            "apellido": values[2],
            "fecha_nacimiento": str(values[3]),
            "sexo": values[4],
            "telefono": str(values[5]) if values[5] else "",
            "direccion": str(values[6]) if values[6] else "",
        }
        FormPaciente(self, self._cargar_pacientes, paciente)

    def _copiar_id(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Aviso", "Selecciona un paciente")
            return
        index = self.tree.index(selected[0])
        if index >= len(self._pacientes_ids) or self._pacientes_ids[index] is None:
            messagebox.showerror("Error", "No se pudo obtener el ID")
            return
        paciente_id = str(self._pacientes_ids[index])
        self.clipboard_clear()
        self.clipboard_append(paciente_id)
        messagebox.showinfo("ID copiado", f"ID real del paciente copiado:\n{paciente_id}")

    def _eliminar(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Aviso", "Selecciona un paciente")
            return

        index = self.tree.index(selected[0])
        paciente_id = self._pacientes_ids[index]

        if not messagebox.askyesno("Confirmar", "¿Deseas dar de baja lógica a este paciente?"):
            return

        threading.Thread(target=self._delete_paciente, args=(paciente_id,), daemon=True).start()

    def _delete_paciente(self, paciente_id):
        try:
            response = requests.delete(
                f"{API_BASE_URL}/pacientes/{paciente_id}",
                headers=self._headers(),
                timeout=10,
            )
            if response.status_code == 200:
                self.after(0, lambda: messagebox.showinfo("Archivo clínico", "Paciente dado de baja"))
                self.after(0, self._cargar_pacientes)
            else:
                self.after(0, lambda: messagebox.showerror("Error", "No se pudo eliminar"))
        except requests.exceptions.ConnectionError:
            self.after(0, lambda: messagebox.showerror("Error", "No se pudo conectar al servidor."))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error", str(e)))