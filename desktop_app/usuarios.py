import threading
import tkinter as tk
from tkinter import messagebox, ttk

import requests

API_BASE_URL = "https://hospital-backend-o0on.onrender.com"

BG_APP = "#eef3f8"
BG_PANEL = "#ffffff"
BG_HEADER = "#1f4e79"
TXT_DARK = "#1f2d3d"
TXT_SOFT = "#5b7083"
ACCENT = "#2563a6"

ROLES_AREAS = [
    "urgencias",
    "medicina_familiar",
    "vacunacion",
    "planificacion_familiar",
    "terapia_fisica",
    "psicologia",
]


def _api_error_message(resp):
    try:
        data = resp.json()
        if isinstance(data, dict) and data.get("detail"):
            return str(data["detail"])
    except Exception:
        pass
    return resp.text


class UsuariosFrame(tk.Frame):
    def __init__(self, master, token, volver_callback=None):
        super().__init__(master, bg=BG_APP)
        self.token = token
        self.volver_callback = volver_callback
        self._build_ui()
        self._cargar_trabajadores_sin_usuario()

    def _headers(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    def _build_ui(self):
        top = tk.Frame(self, bg=BG_HEADER, height=72)
        top.pack(fill="x")
        top.pack_propagate(False)
        tk.Label(
            top,
            text="Módulo de Alta de Usuarios por Área",
            bg=BG_HEADER,
            fg="white",
            font=("Segoe UI", 13, "bold"),
        ).pack(side="left", padx=16, pady=18)

        body = tk.Frame(self, bg=BG_APP)
        body.pack(fill="both", expand=True, padx=14, pady=12)

        card = tk.Frame(body, bg=BG_PANEL, bd=1, relief="solid")
        card.pack(fill="x", padx=120, pady=8)

        tk.Label(card, text="Crear cuenta de usuario", bg=BG_PANEL, fg=TXT_DARK, font=("Segoe UI", 11, "bold")).pack(
            anchor="w", padx=12, pady=(10, 4)
        )
        tk.Label(
            card,
            text="Registro real de personal hospitalario (no pacientes).",
            bg=BG_PANEL,
            fg=TXT_SOFT,
            font=("Segoe UI", 9),
        ).pack(anchor="w", padx=12, pady=(0, 10))

        form = tk.Frame(card, bg=BG_PANEL)
        form.pack(fill="x", padx=12)

        tk.Label(form, text="Nombre", bg=BG_PANEL, fg=TXT_DARK, font=("Segoe UI", 9)).grid(row=0, column=0, sticky="w", pady=5)
        self.nombre_entry = tk.Entry(form, width=56, relief="solid", bd=1, font=("Segoe UI", 9))
        self.nombre_entry.grid(row=0, column=1, sticky="w", pady=5, ipady=3)

        tk.Label(form, text="Apellido", bg=BG_PANEL, fg=TXT_DARK, font=("Segoe UI", 9)).grid(row=1, column=0, sticky="w", pady=5)
        self.apellido_entry = tk.Entry(form, width=56, relief="solid", bd=1, font=("Segoe UI", 9))
        self.apellido_entry.grid(row=1, column=1, sticky="w", pady=5, ipady=3)

        tk.Label(form, text="Correo", bg=BG_PANEL, fg=TXT_DARK, font=("Segoe UI", 9)).grid(row=2, column=0, sticky="w", pady=5)
        self.email_entry = tk.Entry(form, width=56, relief="solid", bd=1, font=("Segoe UI", 9))
        self.email_entry.grid(row=2, column=1, sticky="w", pady=5, ipady=3)

        tk.Label(form, text="Contraseña", bg=BG_PANEL, fg=TXT_DARK, font=("Segoe UI", 9)).grid(row=3, column=0, sticky="w", pady=5)
        self.pass_entry = tk.Entry(form, width=56, relief="solid", bd=1, font=("Segoe UI", 9), show="*")
        self.pass_entry.grid(row=3, column=1, sticky="w", pady=5, ipady=3)

        tk.Label(form, text="Área/Rol", bg=BG_PANEL, fg=TXT_DARK, font=("Segoe UI", 9)).grid(row=4, column=0, sticky="w", pady=5)
        self.rol_combo = ttk.Combobox(form, values=ROLES_AREAS, width=54, state="readonly")
        self.rol_combo.grid(row=4, column=1, sticky="w", pady=5)
        if ROLES_AREAS:
            self.rol_combo.current(0)

        actions = tk.Frame(card, bg=BG_PANEL)
        actions.pack(fill="x", padx=12, pady=(10, 12))

        self.btn_guardar = tk.Button(
            actions,
            text="Dar de alta usuario",
            command=self._registrar,
            bg=ACCENT,
            fg="white",
            activebackground="#1f4e83",
            activeforeground="white",
            relief="flat",
            padx=12,
            pady=6,
            font=("Segoe UI", 9, "bold"),
        )
        self.btn_guardar.pack(side="left", padx=3)

        tk.Button(
            actions,
            text="Refrescar disponibles",
            command=self._cargar_trabajadores_sin_usuario,
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
                text="Volver al menú",
                command=self.volver_callback,
                bg="#e7edf3",
                fg=TXT_DARK,
                relief="flat",
                padx=12,
                pady=6,
                font=("Segoe UI", 9),
            ).pack(side="left", padx=3)

        tk.Label(
            card,
            text="Trabajadores sin cuenta activa:",
            bg=BG_PANEL,
            fg=TXT_DARK,
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w", padx=12, pady=(4, 2))

        self.disponibles_lbl = tk.Label(card, text="", bg=BG_PANEL, fg=TXT_SOFT, font=("Segoe UI", 9))
        self.disponibles_lbl.pack(anchor="w", padx=12, pady=(0, 6))

        self.status_lbl = tk.Label(card, text="", bg=BG_PANEL, fg=TXT_SOFT, font=("Segoe UI", 9))
        self.status_lbl.pack(anchor="w", padx=12, pady=(0, 12))

        admin_card = tk.Frame(body, bg=BG_PANEL, bd=1, relief="solid")
        admin_card.pack(fill="both", expand=True, padx=120, pady=(0, 8))

        tk.Label(admin_card, text="Gestión de accesos", bg=BG_PANEL, fg=TXT_DARK, font=("Segoe UI", 11, "bold")).pack(
            anchor="w", padx=12, pady=(10, 4)
        )
        tk.Label(
            admin_card,
            text="Aquí puedes ver correos registrados y restablecer contraseña si la olvidan.",
            bg=BG_PANEL,
            fg=TXT_SOFT,
            font=("Segoe UI", 9),
        ).pack(anchor="w", padx=12, pady=(0, 8))

        cols = ("email", "rol", "tipo", "nombre")
        tree_wrap = tk.Frame(admin_card, bg=BG_PANEL)
        tree_wrap.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        self.users_tree = ttk.Treeview(tree_wrap, columns=cols, show="headings", height=6)
        self.users_tree.heading("email", text="Correo")
        self.users_tree.heading("rol", text="Rol")
        self.users_tree.heading("tipo", text="Vinculo")
        self.users_tree.heading("nombre", text="Nombre")
        self.users_tree.column("email", width=260, anchor="w")
        self.users_tree.column("rol", width=130, anchor="w")
        self.users_tree.column("tipo", width=100, anchor="w")
        self.users_tree.column("nombre", width=220, anchor="w")

        y_scroll = ttk.Scrollbar(tree_wrap, orient="vertical", command=self.users_tree.yview)
        x_scroll = ttk.Scrollbar(tree_wrap, orient="horizontal", command=self.users_tree.xview)
        self.users_tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        self.users_tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        tree_wrap.grid_rowconfigure(0, weight=1)
        tree_wrap.grid_columnconfigure(0, weight=1)

        reset_row = tk.Frame(admin_card, bg=BG_PANEL)
        reset_row.pack(fill="x", padx=12, pady=(0, 10))
        tk.Label(reset_row, text="Nueva contraseña", bg=BG_PANEL, fg=TXT_DARK, font=("Segoe UI", 9)).pack(side="left")
        self.reset_pass_entry = tk.Entry(reset_row, width=24, relief="solid", bd=1, font=("Segoe UI", 9), show="*")
        self.reset_pass_entry.pack(side="left", padx=8, ipady=2)

        tk.Button(
            reset_row,
            text="Restablecer seleccion",
            command=self._reset_password,
            bg="#e7edf3",
            fg=TXT_DARK,
            relief="flat",
            padx=12,
            pady=6,
            font=("Segoe UI", 9),
        ).pack(side="left", padx=4)

        tk.Button(
            reset_row,
            text="Refrescar usuarios",
            command=self._cargar_usuarios,
            bg="#e7edf3",
            fg=TXT_DARK,
            relief="flat",
            padx=12,
            pady=6,
            font=("Segoe UI", 9),
        ).pack(side="left", padx=4)

    def _cargar_trabajadores_sin_usuario(self):
        self.status_lbl.config(text="Cargando trabajadores sin cuenta...")
        threading.Thread(target=self._fetch_trabajadores_sin_usuario, daemon=True).start()
        self._cargar_usuarios()

    def _cargar_usuarios(self):
        threading.Thread(target=self._fetch_usuarios, daemon=True).start()

    def _fetch_usuarios(self):
        try:
            r = requests.get(f"{API_BASE_URL}/usuarios", headers=self._headers(), timeout=10)
            if r.status_code != 200:
                self.after(0, lambda: self.status_lbl.config(text="No se pudo cargar la lista de usuarios"))
                return
            usuarios = r.json()

            def update_ui():
                self.users_tree.delete(*self.users_tree.get_children())
                for u in usuarios:
                    self.users_tree.insert(
                        "",
                        "end",
                        iid=u["id"],
                        values=(u.get("email", ""), u.get("rol", ""), u.get("vinculo_tipo", ""), u.get("vinculo_nombre", "")),
                    )
                self.status_lbl.config(text=f"Usuarios activos cargados: {len(usuarios)}")

            self.after(0, update_ui)
        except Exception:
            self.after(0, lambda: self.status_lbl.config(text="Error de conexión al cargar usuarios"))

    def _fetch_trabajadores_sin_usuario(self):
        try:
            r = requests.get(f"{API_BASE_URL}/trabajadores/sin-usuario", headers=self._headers(), timeout=10)
            if r.status_code != 200:
                msg = _api_error_message(r)
                self.after(0, lambda: messagebox.showerror("Error", msg))
                self.after(0, lambda: self.status_lbl.config(text=""))
                return

            trabajadores = r.json()
            nombres = [
                f"- {t.get('nombre', '')} {t.get('apellido', '')} ({t.get('rol_area', '')})".strip()
                for t in trabajadores
            ]

            def update_ui():
                # La lista de pendientes es informativa; el alta manual debe seguir disponible.
                self.btn_guardar.config(state="normal", text="Dar de alta usuario")
                if nombres:
                    self.disponibles_lbl.config(text="\n".join(nombres[:8]))
                    self.status_lbl.config(text=f"{len(nombres)} trabajadores sin cuenta")
                else:
                    self.disponibles_lbl.config(text="No hay trabajadores pendientes")
                    self.status_lbl.config(text="Puedes registrar personal nuevo desde el formulario")

            self.after(0, update_ui)
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error", str(e)))
            self.after(0, lambda: self.status_lbl.config(text=""))

    def _registrar(self):
        nombre = self.nombre_entry.get().strip()
        apellido = self.apellido_entry.get().strip()
        email = self.email_entry.get().strip().lower()
        password = self.pass_entry.get().strip()
        rol = self.rol_combo.get().strip()

        if not nombre or not apellido or not email or not password or not rol:
            messagebox.showwarning("Campos requeridos", "Completa nombre, apellido, correo, contraseña y área.")
            return

        self.btn_guardar.config(state="disabled", text="Registrando...")
        self.status_lbl.config(text="Registrando usuario...")

        data = {
            "nombre": nombre,
            "apellido": apellido,
            "email": email,
            "password": password,
            "rol": rol,
        }

        def req():
            try:
                r = requests.post(
                    f"{API_BASE_URL}/registro-personal",
                    json=data,
                    headers=self._headers(),
                    timeout=10,
                )
                if r.status_code == 200:
                    self.after(0, lambda: messagebox.showinfo("OK", "Usuario dado de alta correctamente"))
                    self.after(0, lambda: self.nombre_entry.delete(0, "end"))
                    self.after(0, lambda: self.apellido_entry.delete(0, "end"))
                    self.after(0, lambda: self.email_entry.delete(0, "end"))
                    self.after(0, lambda: self.pass_entry.delete(0, "end"))
                    self.after(0, self._cargar_trabajadores_sin_usuario)
                    self.after(0, lambda: self.status_lbl.config(text="Alta completada correctamente"))
                else:
                    msg = _api_error_message(r)
                    self.after(0, lambda: messagebox.showerror("Error", msg))
                    self.after(0, lambda: self.status_lbl.config(text="No se pudo completar el alta"))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", str(e)))
                self.after(0, lambda: self.status_lbl.config(text="Error de conexión al registrar usuario"))
            finally:
                self.after(0, lambda: self.btn_guardar.config(state="normal", text="Dar de alta usuario"))

        threading.Thread(target=req, daemon=True).start()

    def _reset_password(self):
        selected = self.users_tree.selection()
        if not selected:
            messagebox.showwarning("Seleccion requerida", "Selecciona un usuario en la lista")
            return

        new_password = self.reset_pass_entry.get().strip()
        if not new_password:
            messagebox.showwarning("Campo requerido", "Ingresa la nueva contraseña")
            return

        usuario_id = selected[0]
        self.status_lbl.config(text="Restableciendo contraseña...")

        def req():
            try:
                r = requests.patch(
                    f"{API_BASE_URL}/usuarios/{usuario_id}/password",
                    json={"new_password": new_password},
                    headers=self._headers(),
                    timeout=10,
                )
                if r.status_code == 200:
                    self.after(0, lambda: messagebox.showinfo("OK", "Contraseña restablecida"))
                    self.after(0, lambda: self.reset_pass_entry.delete(0, "end"))
                    self.after(0, lambda: self.status_lbl.config(text="Contraseña restablecida correctamente"))
                else:
                    msg = _api_error_message(r)
                    self.after(0, lambda: messagebox.showerror("Error", msg))
                    self.after(0, lambda: self.status_lbl.config(text="No se pudo restablecer la contraseña"))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", str(e)))
                self.after(0, lambda: self.status_lbl.config(text="Error de conexión al restablecer contraseña"))

        threading.Thread(target=req, daemon=True).start()
