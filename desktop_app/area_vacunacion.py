from area_medica import AreaMedicaFrame


class VacunacionFrame(AreaMedicaFrame):
    def __init__(self, master, token, volver_callback=None):
        super().__init__(
            master,
            token,
            "vacunacion",
            volver_callback,
            panel_title="Área Médica - Vacunación",
            header_color="#1f4f7a",
            accent_color="#2b6ea8",
        )
