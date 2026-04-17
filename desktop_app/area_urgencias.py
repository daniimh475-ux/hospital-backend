from area_medica import AreaMedicaFrame


class UrgenciasFrame(AreaMedicaFrame):
    def __init__(self, master, token, volver_callback=None):
        super().__init__(
            master,
            token,
            "urgencias",
            volver_callback,
            panel_title="Área Médica - Urgencias",
            header_color="#8b1e2d",
            accent_color="#b3273a",
        )
