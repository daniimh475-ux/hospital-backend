from area_medica import AreaMedicaFrame


class TerapiaFisicaFrame(AreaMedicaFrame):
    def __init__(self, master, token, volver_callback=None):
        super().__init__(
            master,
            token,
            "terapia_fisica",
            volver_callback,
            panel_title="Área Médica - Terapia Física",
            header_color="#7a5a1f",
            accent_color="#9c7429",
        )
