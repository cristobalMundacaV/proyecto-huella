import json
import os
import random
import time
from urllib import error, request


API_URL = os.getenv("API_URL", "http://localhost:8000/api/iot/lecturas/")
INTERVAL_SECONDS = float(os.getenv("SIMULATOR_INTERVAL_SECONDS", "5"))

EMPRESAS = [
    "Maderas Los Robles SpA",
    "Maderas Andinas del Sur SpA",
    "Forestal Cordillera Austral SpA",
]

UNIDADES_OPERATIVAS = [
    "Aserradero Principal",
    "Despacho y Transporte",
    "Secado de Madera",
    "Bodega de Materias Primas",
    "Area de Mantencion",
    "Administracion",
    "Planta de Tratamiento",
]

SENSORES = [
    {"sensor": "SENSOR-DIESEL-001", "tipo": "diesel_litros", "min": 4, "max": 22},
    {"sensor": "SENSOR-ELECTRICIDAD-001", "tipo": "electricidad_kwh", "min": 12, "max": 95},
    {"sensor": "SENSOR-MAQUINARIA-001", "tipo": "horas_maquinaria", "min": 0.25, "max": 4},
    {"sensor": "SENSOR-TEMP-001", "tipo": "temperatura", "min": 12, "max": 38},
    {"sensor": "SENSOR-HUMEDAD-001", "tipo": "humedad", "min": 30, "max": 85},
]


def generar_lectura():
    sensor = random.choice(SENSORES)
    return {
        "empresa": random.choice(EMPRESAS),
        "unidad_operativa": random.choice(UNIDADES_OPERATIVAS),
        "sensor": sensor["sensor"],
        "tipo": sensor["tipo"],
        "valor": round(random.uniform(sensor["min"], sensor["max"]), 3),
    }


def enviar_lectura(payload):
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        API_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with request.urlopen(req, timeout=10) as response:
        body = response.read().decode("utf-8")
        return response.status, json.loads(body)


def describir_error_http(exc):
    try:
        body = exc.read().decode("utf-8", errors="replace")
    except Exception:
        body = ""

    if len(body) > 500:
        body = f"{body[:500]}..."

    return f"HTTP {exc.code} {exc.reason}. {body}".strip()


def main():
    print(f"Simulador IoT enviando lecturas a {API_URL}", flush=True)
    print(f"Intervalo de envio: {INTERVAL_SECONDS} segundos", flush=True)
    while True:
        payload = generar_lectura()
        try:
            status, response = enviar_lectura(payload)
            print(
                f"[{status}] {payload['sensor']} {payload['tipo']}="
                f"{payload['valor']} -> {response.get('co2e_estimado')} kg CO2e"
                ,
                flush=True,
            )
        except error.HTTPError as exc:
            print(f"[error] No se pudo enviar lectura: {describir_error_http(exc)}", flush=True)
        except (error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            print(f"[error] No se pudo enviar lectura: {exc}", flush=True)
        except Exception as exc:
            print(f"[error] Error inesperado: {exc}", flush=True)

        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
