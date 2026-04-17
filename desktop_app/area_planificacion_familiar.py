from area_medica import AreaMedicaFrame


class PlanificacionFamiliarFrame(AreaMedicaFrame):
    def __init__(self, master, token, volver_callback=None):
        super().__init__(
            master,
            token,
            "planificacion_familiar",
            volver_callback,
            panel_title="Área Médica - Planificación Familiar",
            header_color="#6a3f7a",
            accent_color="#8a52a1",
        )
