from area_medica import AreaMedicaFrame


class MedicinaFamiliarFrame(AreaMedicaFrame):
    def __init__(self, master, token, volver_callback=None):
        super().__init__(
            master,
            token,
            "medicina_familiar",
            volver_callback,
            panel_title="Área Médica - Medicina Familiar",
            header_color="#245c3f",
            accent_color="#2f7a53",
        )
