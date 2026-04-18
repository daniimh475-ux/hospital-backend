import threading
import tkinter as tk
from tkinter import messagebox

import requests

API_BASE_URL = "https://hospital-backend-o0on.onrender.com"

BG_COLOR = "#eaf3f8"
CARD_COLOR = "#ffffff"
TITLE_COLOR = "#0f4c81"
TEXT_COLOR = "#2b3a42"
MUTED_COLOR = "#5e6b73"
INPUT_BG = "#f7fbfd"
INPUT_BORDER = "#c9d8e2"
BTN_BG = "#0f6cab"
BTN_BG_HOVER = "#0c5a8f"
BTN_TEXT = "#ffffff"

class LoginFrame(tk.Frame):
    def __init__(self, master, success_callback):
        super().__init__(master, bg=BG_COLOR)
        self.success_callback = success_callback
        self.status_var = tk.StringVar(value="")
        self._build_ui()

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        hero = tk.Frame(self, bg=BG_COLOR)
        hero.grid(row=0, column=0, sticky="nsew", padx=26, pady=26)
        hero.columnconfigure(0, weight=1)
        hero.rowconfigure(0, weight=1)

        card = tk.Frame(
            hero,
            bg=CARD_COLOR,
            highlightthickness=1,
            highlightbackground="#d7e5ee",
            bd=0,
        )
        card.grid(row=0, column=0, sticky="nsew")
        card.columnconfigure(0, weight=1)

        top_band = tk.Frame(card, bg=TITLE_COLOR, height=14)
        top_band.grid(row=0, column=0, sticky="ew")

        body = tk.Frame(card, bg=CARD_COLOR)
        body.grid(row=1, column=0, sticky="nsew", padx=24, pady=18)
        body.columnconfigure(0, weight=1)

        tk.Label(
            body,
            text="Hospital - Acceso al sistema",
            font=("Segoe UI Semibold", 14),
            fg=TITLE_COLOR,
            bg=CARD_COLOR,
        ).grid(row=0, column=0, sticky="w")

        tk.Label(
            body,
            text="Ingresa con tu usuario o correo para continuar.",
            font=("Segoe UI", 9),
            fg=MUTED_COLOR,
            bg=CARD_COLOR,
        ).grid(row=1, column=0, sticky="w", pady=(2, 14))

        tk.Label(
            body,
            text="Usuario o correo",
            font=("Segoe UI", 9),
            fg=TEXT_COLOR,
            bg=CARD_COLOR,
        ).grid(row=2, column=0, sticky="w", pady=(0, 4))

        self.user_entry = tk.Entry(
            body,
            font=("Segoe UI", 10),
            relief="flat",
            bg=INPUT_BG,
            highlightthickness=1,
            highlightbackground=INPUT_BORDER,
            highlightcolor=BTN_BG,
            insertbackground=TEXT_COLOR,
        )
        self.user_entry.grid(row=3, column=0, sticky="ew", ipady=7)

        tk.Label(
            body,
            text="Contraseña",
            font=("Segoe UI", 9),
            fg=TEXT_COLOR,
            bg=CARD_COLOR,
        ).grid(row=4, column=0, sticky="w", pady=(12, 4))

        self.pass_entry = tk.Entry(
            body,
            show="*",
            font=("Segoe UI", 10),
            relief="flat",
            bg=INPUT_BG,
            highlightthickness=1,
            highlightbackground=INPUT_BORDER,
            highlightcolor=BTN_BG,
            insertbackground=TEXT_COLOR,
        )
        self.pass_entry.grid(row=5, column=0, sticky="ew", ipady=7)

        self.show_pass = tk.BooleanVar(value=False)
        show_btn = tk.Checkbutton(
            body,
            text="Ver",
            variable=self.show_pass,
            command=self._toggle_password,
            bg=CARD_COLOR,
            fg=MUTED_COLOR,
            activebackground=CARD_COLOR,
            activeforeground=TEXT_COLOR,
            selectcolor=CARD_COLOR,
            font=("Segoe UI", 8),
            bd=0,
            padx=8,
        )
        show_btn.grid(row=6, column=0, sticky="e", pady=(4, 0))

        self.status_label = tk.Label(
            body,
            textvariable=self.status_var,
            font=("Segoe UI", 9),
            fg="#a33d1a",
            bg=CARD_COLOR,
        )
        self.status_label.grid(row=7, column=0, sticky="w", pady=(10, 2))

        self.login_button = tk.Button(
            body,
            text="Entrar",
            command=self._login,
            font=("Segoe UI Semibold", 10),
            relief="flat",
            bg=BTN_BG,
            fg=BTN_TEXT,
            activebackground=BTN_BG_HOVER,
            activeforeground=BTN_TEXT,
            cursor="hand2",
            padx=12,
            pady=8,
        )
        self.login_button.grid(row=8, column=0, sticky="ew", pady=(8, 0))

        self.login_button.bind("<Enter>", lambda _e: self.login_button.configure(bg=BTN_BG_HOVER))
        self.login_button.bind("<Leave>", lambda _e: self.login_button.configure(bg=BTN_BG))

        self.user_entry.bind("<Return>", lambda _e: self._login())
        self.pass_entry.bind("<Return>", lambda _e: self._login())
        self.user_entry.focus_set()

    def _toggle_password(self):
        self.pass_entry.configure(show="" if self.show_pass.get() else "*")

    def _login(self):
        user = self.user_entry.get().strip()
        pwd = self.pass_entry.get().strip()
        if not user or not pwd:
            self.status_var.set('Ingresa usuario y contraseña')
            messagebox.showerror('Error', 'Ingresa usuario y contraseña')
            return

        self.status_var.set("")
        self.login_button.config(state='disabled', text='Entrando...', bg=BTN_BG_HOVER)
        threading.Thread(target=self._login_request, args=(user, pwd), daemon=True).start()

    def _login_request(self, user, pwd):
        try:
            response = requests.post(
                f"{API_BASE_URL}/login",
                data={"username": user, "password": pwd},
                timeout=10,
            )
            if response.status_code == 200:
                data = response.json()
                token = data.get("access_token")
                rol = data.get("rol")
                if not token:
                    self.after(0, lambda: self._login_error('Respuesta de login inválida'))
                    return
                self.after(0, lambda: self.success_callback(token, user, rol))
            else:
                try:
                    detail = response.json().get("detail", response.text)
                except Exception:
                    detail = response.text
                self.after(0, lambda: self._login_error(detail or 'Credenciales incorrectas'))
        except requests.exceptions.ConnectionError:
            self.after(0, lambda: self._login_error('No se pudo conectar al backend'))
        except Exception as e:
            self.after(0, lambda e=e: self._login_error(str(e)))

    def _login_error(self, message):
        self.login_button.config(state='normal', text='Entrar', bg=BTN_BG)
        self.status_var.set(message)
        messagebox.showerror('Error', message)
