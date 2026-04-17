from pathlib import Path

from fastapi import FastAPI
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import requests
from requests import RequestException


WEB_DIR = Path(__file__).resolve().parent
BACKEND_BASE_URL = "http://127.0.0.1:8001"

app = FastAPI(title="Portal Paciente Web")


@app.api_route(
	"/api/{path:path}",
	methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
)
async def proxy_to_backend(path: str, request: Request):
	url = f"{BACKEND_BASE_URL}/{path}"
	if request.url.query:
		url = f"{url}?{request.url.query}"

	body = await request.body()
	skip_headers = {"host", "content-length", "connection"}
	headers = {
		key: value
		for key, value in request.headers.items()
		if key.lower() not in skip_headers
	}

	try:
		backend_response = requests.request(
			method=request.method,
			url=url,
			headers=headers,
			data=body,
			timeout=30,
		)
	except RequestException:
		return JSONResponse(
			status_code=503,
			content={
				"detail": (
					"No se pudo conectar con el backend. "
					"Verifica que la API esté ejecutándose en http://127.0.0.1:8001"
				)
			},
		)

	response_headers = {}
	for key, value in backend_response.headers.items():
		if key.lower() in {"content-length", "transfer-encoding", "connection"}:
			continue
		response_headers[key] = value

	return Response(
		content=backend_response.content,
		status_code=backend_response.status_code,
		headers=response_headers,
	)


app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="portal")


if __name__ == "__main__":
	host = "127.0.0.1"
	port = 8080
	print(f"Portal web disponible en: http://{host}:{port}")
	uvicorn.run(app, host=host, port=port, log_level="info")