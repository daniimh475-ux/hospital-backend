import tkinter as tk

API_BASE_URL = "https://hospital-backend-o0on.onrender.com"


class PanelFrame(tk.Frame):
    def __init__(self, master, usuarios_callback, pacientes_callback, citas_callback, historial_callback, referencias_callback, salir_callback):
        super().__init__(master)
        self.usuarios_callback = usuarios_callback
        self.pacientes_callback = pacientes_callback
        self.citas_callback = citas_callback
        self.historial_callback = historial_callback
        self.referencias_callback = referencias_callback
        self.salir_callback = salir_callback
        self._build_ui()

    def _build_ui(self):
        # Header
        header = tk.Frame(self, bg="#1a5276", height=60)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="Sistema Integral Hospitalario — Archivo Clínico",
            font=("Arial", 13, "bold"),
            bg="#1a5276",
            fg="white"
        ).pack(side="left", padx=15, pady=15)

        # Sidebar
        sidebar = tk.Frame(self, bg="#2c3e50", width=200)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        tk.Label(
            sidebar,
            text="MENÚ",
            font=("Arial", 9, "bold"),
            bg="#2c3e50",
            fg="#7f8c8d"
        ).pack(pady=(20, 5))

        btn_usuarios = tk.Button(
            sidebar,
            text="🧑‍⚕️  Alta de usuarios",
            anchor="w",
            font=("Arial", 11),
            bg="#2c3e50",
            fg="white",
            activebackground="#1a252f",
            relief="flat",
            bd=0,
            padx=20,
            pady=10,
            command=self.usuarios_callback
        )
        btn_usuarios.pack(fill="x")

        btn_pacientes = tk.Button(
            sidebar,
            text="👥  Pacientes",
            anchor="w",
            font=("Arial", 11),
            bg="#2c3e50",
            fg="white",
            activebackground="#1a252f",
            relief="flat",
            bd=0,
            padx=20,
            pady=10,
            command=self.pacientes_callback
        )
        btn_pacientes.pack(fill="x")

        btn_citas = tk.Button(
            sidebar,
            text="📅  Citas",
            anchor="w",
            font=("Arial", 11),
            bg="#2c3e50",
            fg="white",
            activebackground="#1a252f",
            relief="flat",
            bd=0,
            padx=20,
            pady=10,
            command=self.citas_callback
        )
        btn_citas.pack(fill="x")

        btn_historial = tk.Button(
            sidebar,
            text="📋  Historial",
            anchor="w",
            font=("Arial", 11),
            bg="#2c3e50",
            fg="white",
            activebackground="#1a252f",
            relief="flat",
            bd=0,
            padx=20,
            pady=10,
            command=self.historial_callback
        )
        btn_historial.pack(fill="x")

        btn_referencias = tk.Button(
            sidebar,
            text="🔗  Referencias",
            anchor="w",
            font=("Arial", 11),
            bg="#2c3e50",
            fg="white",
            activebackground="#1a252f",
            relief="flat",
            bd=0,
            padx=20,
            pady=10,
            command=self.referencias_callback
        )
        btn_referencias.pack(fill="x")

        # ...existing code...

        # Botón salir con validación
        tk.Button(
            sidebar,
            text="⬅  Cerrar sesión",
            anchor="w",
            font=("Arial", 10),
            bg="#2c3e50",
            fg="#e74c3c",
            activebackground="#1a252f",
            relief="flat",
            bd=0,
            padx=20,
            pady=10,
            command=self.salir_callback
        ).pack(fill="x", side="bottom", pady=10)

        # Área de contenido
        self.content = tk.Frame(self, bg="#ecf0f1")
        self.content.pack(side="left", fill="both", expand=True)

    def _navegar(self, seccion):
        # Limpiar contenido
        for widget in self.content.winfo_children():
            widget.destroy()

        # Resaltar botón activo
        for key, btn in self.btn_refs.items():
            btn.config(bg="#2c3e50" if key != seccion else "#1a5276")

        # Ejecutar callback
        callback = self.callbacks.get(seccion)

        if not callback:
            # 👇 Fallback visual (esto evita pantalla en blanco)
            tk.Label(
                self.content,
                text=f"⚠ No hay vista implementada para: {seccion}",
                font=("Arial", 12),
                bg="#ecf0f1",
                fg="red"
            ).pack(pady=20)
            return

        try:
            callback(self.content)
        except Exception as e:
            # 👇 Debug visual (clave para no perder tiempo)
            tk.Label(
                self.content,
                text=f"❌ Error al cargar {seccion}:\n{str(e)}",
                font=("Arial", 10),
                bg="#ecf0f1",
                fg="red"
            ).pack(pady=20)