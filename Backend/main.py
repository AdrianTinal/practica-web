import datetime
import logging
import os, sys

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from prometheus_fastapi_instrumentator import Instrumentator
from loki_logger_handler.loki_logger_handler import LokiLoggerHandler

# =========================
# CONFIGURACIÓN DE LOGGING
# =========================
logger = logging.getLogger("custom_logger")

logging_data = os.getenv("LOG_LEVEL", "INFO").upper()
if logging_data == "DEBUG":
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)

# Consola
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logger.level)
formatter = logging.Formatter(
    "%(levelname)s: %(asctime)s - %(name)s - %(message)s"
)
console_handler.setFormatter(formatter)

# Loki
loki_handler = LokiLoggerHandler(
    url="http://loki:3100/loki/api/v1/push",
    labels={"application": "FastApi"},
    label_keys={},
    timeout=10,
)

logger.addHandler(console_handler)
logger.addHandler(loki_handler)
logger.info("Logger initialized")

# ===============
# CONFIG FASTAPI
# ===============
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================
# CONEXIÓN A MONGODB
# =====================
mongo_client = MongoClient("mongodb://admin_user:web3@mongo:27017/")
database = mongo_client["practica1"]
collection_historial = database["historial"]


# ============
# HELPERS
# ============

def validar_entrada(a: float, b: float, operacion: str):
    """
    Valida números de entrada. Aquí puedes forzar los errores
    que el profe quiere que muestres (negativos, división entre 0, etc.)
    """
    if a < 0 or b < 0:
        msg = f"Operación {operacion} inválida: no se permiten números negativos (a={a}, b={b})"
        logger.error(msg)
        raise HTTPException(status_code=400, detail=msg)

    if operacion == "division" and b == 0:
        msg = f"Operación division inválida: intento de dividir entre cero (a={a}, b={b})"
        logger.error(msg)
        raise HTTPException(status_code=400, detail=msg)


def guardar_operacion(a: float, b: float, resultado, operacion: str):
    """Intenta guardar en Mongo y loggea éxito / error."""
    document = {
        "resultado": resultado,
        "a": a,
        "b": b,
        "operacion": operacion,
        "date": datetime.datetime.now(tz=datetime.timezone.utc),
    }

    try:
        logger.debug(f"Insertando documento en la base de datos: {document}")
        collection_historial.insert_one(document)
        logger.info(f"Operación {operacion} almacenada correctamente en MongoDB")
    except Exception as e:
        # ERROR por problemas con la base de datos (lo que pide el PDF)
        logger.error(f"Error al guardar operación {operacion} en MongoDB: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al guardar en historial: {str(e)}",
        )


# =========================
# ENDPOINTS DE OPERACIONES
# =========================

@app.get("/calculadora/sum")
def sumar(a: float, b: float):
    """
    Suma dos números
    Ejemplo: /calculadora/sum?a=5&b=10
    """
    try:
        validar_entrada(a, b, "suma")
        resultado = a + b
        guardar_operacion(a, b, resultado, "suma")

        logger.info(f"Operación suma exitosa: {a} + {b} = {resultado}")
        return {"a": a, "b": b, "resultado": resultado}
    except HTTPException:
        # Ya loggeamos dentro de validar_entrada/guardar_operacion
        raise
    except Exception as e:
        logger.error(f"Error inesperado en suma: {e}")
        raise HTTPException(status_code=500, detail="Error interno en suma")


@app.get("/calculadora/resta")
def restar(a: float, b: float):
    """
    Resta dos números
    Ejemplo: /calculadora/resta?a=5&b=10
    """
    try:
        validar_entrada(a, b, "resta")
        resultado = a - b
        guardar_operacion(a, b, resultado, "resta")

        logger.info(f"Operación resta exitosa: {a} - {b} = {resultado}")
        return {"a": a, "b": b, "resultado": resultado}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inesperado en resta: {e}")
        raise HTTPException(status_code=500, detail="Error interno en resta")


@app.get("/calculadora/mult")
def multiplicar(a: float, b: float):
    """
    Multiplica dos números
    Ejemplo: /calculadora/mult?a=5&b=10
    """
    try:
        validar_entrada(a, b, "multiplicacion")
        resultado = a * b
        guardar_operacion(a, b, resultado, "multiplicacion")

        logger.info(f"Operación multiplicación exitosa: {a} * {b} = {resultado}")
        return {"a": a, "b": b, "resultado": resultado}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inesperado en multiplicación: {e}")
        raise HTTPException(status_code=500, detail="Error interno en multiplicación")


@app.get("/calculadora/div")
def dividir(a: float, b: float):
    """
    Divide dos números
    Ejemplo: /calculadora/div?a=5&b=10
    """
    try:
        validar_entrada(a, b, "division")
        resultado = a / b   # aquí ya sabemos que b != 0
        guardar_operacion(a, b, resultado, "division")

        logger.info(f"Operación división exitosa: {a} / {b} = {resultado}")
        return {"a": a, "b": b, "resultado": resultado}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inesperado en división: {e}")
        raise HTTPException(status_code=500, detail="Error interno en división")


# ======================
# ENDPOINT HISTORIAL
# ======================

@app.get("/calculadora/historial")
def obtener_historial():
    try:
        operaciones = collection_historial.find({})
        historial = []
        for operacion in operaciones:
            historial.append({
                "a": operacion["a"],
                "b": operacion["b"],
                "resultado": operacion["resultado"],
                "date": operacion["date"].isoformat(),
                "operacion": operacion["operacion"],
            })

        logger.info("Consulta de historial exitosa")
        return {"historial": historial}
    except Exception as e:
        logger.error(f"Error al obtener historial de MongoDB: {e}")
        raise HTTPException(status_code=500, detail="Error al obtener historial")


# ======================
# MÉTRICAS PROMETHEUS
# ======================
Instrumentator().instrument(app).expose(app)