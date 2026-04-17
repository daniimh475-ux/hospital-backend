import requests

try:
    response = requests.get("http://127.0.0.1:8000/pacientes", timeout=5)
    print("Status code:", response.status_code)
    print("Respuesta:", response.text)
except requests.ConnectionError as e:
    print("Error de conexión:", e)
except Exception as e:
    print("Otro error:", e)
