from area_medica import AreaMedicaFrame


class PsicologiaFrame(AreaMedicaFrame):
    def __init__(self, master, token, volver_callback=None):
        super().__init__(
            master,
            token,
            "psicologia",
            volver_callback,
            panel_title="Área Médica - Psicología",
            header_color="#3f4a6a",
            accent_color="#556490",
        )
