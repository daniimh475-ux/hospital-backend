import tkinter as tk
from tkinter import messagebox
from login import LoginFrame
from panel import PanelFrame
from pacientes import PacientesFrame
from citas import CitasFrame
from historial_refs import HistorialFrame, ReferenciasFrame
from usuarios import UsuariosFrame
from area_medica import AreaMedicaFrame
from area_urgencias import UrgenciasFrame
from area_medicina_familiar import MedicinaFamiliarFrame
from area_vacunacion import VacunacionFrame
from area_planificacion_familiar import PlanificacionFamiliarFrame
from area_terapia_fisica import TerapiaFisicaFrame
from area_psicologia import PsicologiaFrame


ROLE_FRAME_MAP = {
    "urgencias": UrgenciasFrame,
    "medicina_familiar": MedicinaFamiliarFrame,
    "vacunacion": VacunacionFrame,
    "planificacion_familiar": PlanificacionFamiliarFrame,
    "terapia_fisica": TerapiaFisicaFrame,
    "psicologia": PsicologiaFrame,
}

class AppArchivo(tk.Tk):
    def __init__(self):
        super().__init__()
        self.token = None
        self.user_email = None
        self.user_role = None
        self.title('Hospital - Archivo Clínico')
        self.geometry('560x420')
        self._show_login()

    def _set_login_window(self):
        self.geometry('560x420')

    def _set_main_window(self):
        try:
            # En Windows, "zoomed" abre la ventana maximizada.
            self.state('zoomed')
        except Exception:
            self.geometry('1200x800')

    def _clear(self):
        for widget in self.winfo_children():
            widget.destroy()

    def _show_login(self):
        self._clear()
        self.token = None
        self.user_email = None
        self.user_role = None
        self._set_login_window()
        frame = LoginFrame(self, self._show_panel)
        frame.pack(fill='both', expand=True)

    def _show_panel(self, token, user_email, user_role=None):
        self.token = token
        self.user_email = user_email
        self.user_role = user_role or self.user_role
        self._clear()
        self._set_main_window()

        if self.user_role and self.user_role != 'archivo':
            medical_frame_cls = ROLE_FRAME_MAP.get(self.user_role)
            if medical_frame_cls:
                frame = medical_frame_cls(self, self.token, self._show_login)
            else:
                frame = AreaMedicaFrame(self, self.token, self.user_role, self._show_login)
            frame.pack(fill='both', expand=True)
            return

        frame = PanelFrame(
            self,
            self._show_usuarios,
            self._show_pacientes,
            self._show_citas,
            self._show_historial,
            self._show_referencias,
            self._show_login,
        )
        frame.pack(fill='both', expand=True)

    def _show_pacientes(self):
        self._clear()
        frame = PacientesFrame(self, self.token, self._show_panel_from_child)
        frame.pack(fill='both', expand=True)

    def _show_usuarios(self):
        self._clear()
        frame = UsuariosFrame(self, self.token, self._show_panel_from_child)
        frame.pack(fill='both', expand=True)

    def _show_citas(self):
        self._clear()
        frame = CitasFrame(self, self.token, self._show_panel_from_child)
        frame.pack(fill='both', expand=True)

    def _show_historial(self):
        self._clear()
        frame = HistorialFrame(self, self.token, self._show_panel_from_child)
        frame.pack(fill='both', expand=True)

    def _show_referencias(self):
        self._clear()
        frame = ReferenciasFrame(self, self.token, self._show_panel_from_child)
        frame.pack(fill='both', expand=True)

    def _show_panel_from_child(self):
        if self.token and self.user_email:
            self._show_panel(self.token, self.user_email, self.user_role)
        else:
            self._show_login()



if __name__ == '__main__':
    app = AppArchivo()
    app.mainloop()
