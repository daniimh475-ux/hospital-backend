import requests

url = "http://127.0.0.1:8000/pacientes"

try:
    response = requests.get(url, timeout=5)
    print("Status code:", response.status_code)
    print("Respuesta:", response.text)
except requests.ConnectionError as e:
    print("Error de conexión:", e)
except Exception as e:
    print("Otro error:", e)
