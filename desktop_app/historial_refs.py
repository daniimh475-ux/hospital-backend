import tkinter as tk
import threading
from tkinter import messagebox, ttk

import requests

API_BASE_URL = "https://hospital-backend-o0on.onrender.com"

BG_APP = "#eef3f8"
BG_PANEL = "#ffffff"
BG_HEADER = "#2b4c7e"
TXT_DARK = "#1f2d3d"
TXT_SOFT = "#5b7083"
ACCENT = "#315f9f"


class HistorialFrame(tk.Frame):
    def __init__(self, master, token, volver_callback=None):
        super().__init__(master, bg=BG_APP)
        self.token = token
        self.volver_callback = volver_callback
        self._build_ui()

    def _build_ui(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("HosH.Treeview", rowheight=28, font=("Segoe UI", 9), background="white", fieldbackground="white")
        style.configure("HosH.Treeview.Heading", font=("Segoe UI", 9, "bold"), background="#dfe8f7", foreground=TXT_DARK)

        top = tk.Frame(self, bg=BG_HEADER, height=72)
        top.pack(fill="x")
        top.pack_propagate(False)
        tk.Label(
            top,
            text="Módulo de Historial Clínico",
            bg=BG_HEADER,
            fg="white",
            font=("Segoe UI", 13, "bold"),
        ).pack(side="left", padx=16, pady=18)

        body = tk.Frame(self, bg=BG_APP)
        body.pack(fill="both", expand=True, padx=14, pady=12)

        card = tk.Frame(body, bg=BG_PANEL, bd=1, relief="solid")
        card.pack(fill="both", expand=True)

        search = tk.Frame(card, bg=BG_PANEL)
        search.pack(fill="x", padx=12, pady=(10, 6))

        tk.Label(search, text="ID o Expediente", bg=BG_PANEL, fg=TXT_DARK, font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 6))
        self.id_entry = tk.Entry(search, width=42, relief="solid", bd=1, font=("Segoe UI", 9))
        self.id_entry.pack(side="left", padx=4, ipady=3)

        tk.Button(
            search,
            text="Buscar historial",
            command=self._buscar,
            bg=ACCENT,
            fg="white",
            activebackground="#294f86",
            activeforeground="white",
            relief="flat",
            padx=12,
            pady=6,
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left", padx=4)

        if self.volver_callback:
            tk.Button(
                search,
                text="Volver",
                command=self.volver_callback,
                bg="#e7edf3",
                fg=TXT_DARK,
                relief="flat",
                padx=12,
                pady=6,
                font=("Segoe UI", 9),
            ).pack(side="right")

        info = tk.Frame(card, bg=BG_PANEL)
        info.pack(fill="x", padx=12, pady=(0, 4))
        tk.Label(info, text="Resultados de historial", bg=BG_PANEL, fg=TXT_DARK, font=("Segoe UI", 11, "bold")).pack(side="left")
        self.status_lbl = tk.Label(info, text="", bg=BG_PANEL, fg=TXT_SOFT, font=("Segoe UI", 9))
        self.status_lbl.pack(side="right")

        tk.Label(
            card,
            text="Puedes buscar por UUID completo o por expediente corto (ejemplo: HC-B3B8C7E2)",
            bg=BG_PANEL,
            fg=TXT_SOFT,
            font=("Segoe UI", 8),
        ).pack(anchor="w", padx=12, pady=(0, 6))

        cols = ("fecha", "tipo", "descripcion")
        self.tree = ttk.Treeview(card, columns=cols, show="headings", style="HosH.Treeview")
        self.tree.heading("fecha", text="Fecha")
        self.tree.heading("tipo", text="Tipo")
        self.tree.heading("descripcion", text="Descripción")
        self.tree.column("fecha", width=130, anchor="w")
        self.tree.column("tipo", width=130, anchor="w")
        self.tree.column("descripcion", width=620, anchor="w")
        self.tree.pack(padx=12, pady=(4, 12), fill="both", expand=True)

    def _headers(self):
        return {"Authorization": f"Bearer {self.token}"}

    def _buscar(self):
        pid = self.id_entry.get().strip()
        if not pid:
            messagebox.showwarning("Aviso", "Ingresa el ID o expediente del paciente")
            return
        self.status_lbl.config(text="Consultando historial...")
        threading.Thread(target=self._fetch, args=(pid,), daemon=True).start()

    def _expediente(self, paciente_id):
        text = str(paciente_id).replace("-", "").upper()
        return f"HC-{text[:8]}"

    def _resolver_uuid(self, pid_input):
        # Si parece UUID completo, se usa tal cual.
        if len(pid_input) >= 32 and "-" in pid_input:
            return pid_input

        # Si viene en formato de expediente corto HC-XXXXXXXX, resolver por listado de pacientes.
        expediente = pid_input.strip().upper()
        if expediente.startswith("HC-"):
            r = requests.get(f"{API_BASE_URL}/pacientes", headers=self._headers(), timeout=10)
            if r.status_code != 200:
                return None
            for p in r.json():
                pid = p.get("id")
                if pid and self._expediente(pid) == expediente:
                    return pid
        return pid_input

    def _fetch(self, paciente_id):
        try:
            resolved_id = self._resolver_uuid(paciente_id)
            if not resolved_id:
                self.after(0, lambda: messagebox.showerror("Error", "No se pudo resolver el expediente a un paciente válido"))
                self.after(0, lambda: self.status_lbl.config(text=""))
                return

            r = requests.get(f"{API_BASE_URL}/historial/{resolved_id}",
                             headers=self._headers(), timeout=10)
            if r.status_code == 200:
                self.after(0, lambda: self._mostrar(r.json()))
            else:
                msg = r.json().get("detail", r.text)
                self.after(0, lambda: messagebox.showerror("Error", msg))
                self.after(0, lambda: self.status_lbl.config(text=""))
        except Exception as e:
            err = str(e)
            self.after(0, lambda: messagebox.showerror("Error", err))
            self.after(0, lambda: self.status_lbl.config(text=""))

    def _mostrar(self, registros):
        self.tree.delete(*self.tree.get_children())
        for h in registros:
            self.tree.insert("", "end", values=(h["fecha"], h["tipo"], h["descripcion"]))
        self.status_lbl.config(text=f"{len(registros)} registros")


class ReferenciasFrame(tk.Frame):
    def __init__(self, master, token, volver_callback=None):
        super().__init__(master, bg=BG_APP)
        self.token = token
        self.volver_callback = volver_callback
        self._build_ui()

    def _build_ui(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("HosR.Treeview", rowheight=28, font=("Segoe UI", 9), background="white", fieldbackground="white")
        style.configure("HosR.Treeview.Heading", font=("Segoe UI", 9, "bold"), background="#e1eef8", foreground=TXT_DARK)

        top = tk.Frame(self, bg=BG_HEADER, height=72)
        top.pack(fill="x")
        top.pack_propagate(False)
        tk.Label(
            top,
            text="Módulo de Referencias Inter-áreas",
            bg=BG_HEADER,
            fg="white",
            font=("Segoe UI", 13, "bold"),
        ).pack(side="left", padx=16, pady=18)

        body = tk.Frame(self, bg=BG_APP)
        body.pack(fill="both", expand=True, padx=14, pady=12)

        card = tk.Frame(body, bg=BG_PANEL, bd=1, relief="solid")
        card.pack(fill="both", expand=True)

        head = tk.Frame(card, bg=BG_PANEL)
        head.pack(fill="x", padx=12, pady=(10, 6))
        tk.Label(head, text="Referencias registradas", bg=BG_PANEL, fg=TXT_DARK, font=("Segoe UI", 11, "bold")).pack(side="left")
        self.status_lbl = tk.Label(head, text="", bg=BG_PANEL, fg=TXT_SOFT, font=("Segoe UI", 9))
        self.status_lbl.pack(side="right")

        cols = ("fecha", "atencion_id", "area_destino", "motivo", "prioridad")
        self.tree = ttk.Treeview(card, columns=cols, show="headings", style="HosR.Treeview")
        headers = {
            "fecha": "Fecha",
            "atencion_id": "Atención ID",
            "area_destino": "Área destino",
            "motivo": "Motivo clínico",
            "prioridad": "Prioridad",
        }
        widths = {"fecha": 120, "atencion_id": 230, "area_destino": 230, "motivo": 320, "prioridad": 90}
        for c in cols:
            self.tree.heading(c, text=headers[c])
            self.tree.column(c, width=widths[c], anchor="w")
        self.tree.pack(padx=12, pady=(4, 8), fill="both", expand=True)

        actions = tk.Frame(card, bg=BG_PANEL)
        actions.pack(fill="x", padx=12, pady=(0, 12))
        tk.Button(
            actions,
            text="Actualizar",
            command=self._cargar,
            bg=ACCENT,
            fg="white",
            activebackground="#294f86",
            activeforeground="white",
            relief="flat",
            padx=12,
            pady=6,
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left", padx=3)
        if self.volver_callback:
            tk.Button(
                actions,
                text="Volver",
                command=self.volver_callback,
                bg="#e7edf3",
                fg=TXT_DARK,
                relief="flat",
                padx=12,
                pady=6,
                font=("Segoe UI", 9),
            ).pack(side="right", padx=3)
        self._cargar()

    def _headers(self):
        return {"Authorization": f"Bearer {self.token}"}

    def _cargar(self):
        self.status_lbl.config(text="Actualizando referencias...")
        threading.Thread(target=self._fetch, daemon=True).start()

    def _fetch(self):
        try:
            r = requests.get(f"{API_BASE_URL}/referencias",
                             headers=self._headers(), timeout=10)
            if r.status_code == 200:
                self.after(0, lambda: self._mostrar(r.json()))
        except Exception as e:
            err = str(e)
            self.after(0, lambda: messagebox.showerror("Error", err))

    def _mostrar(self, refs):
        self.tree.delete(*self.tree.get_children())
        for r in refs:
            self.tree.insert("", "end", values=(
                r["fecha"], r["atencion_id"], r.get("area_destino", r.get("area_destino_id", "")),
                r["motivo"], "Sí" if r["prioridad"] else "No"
            ))
        self.status_lbl.config(text=f"{len(refs)} referencias")
