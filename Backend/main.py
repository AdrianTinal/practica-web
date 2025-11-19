import datetime
import logging
import os, sys
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Counter # Importamos Counter para métricas custom
from loki_logger_handler.loki_logger_handler import LokiLoggerHandler
from pydantic import BaseModel # 1. Importar BaseModel

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
# NOTA: Asegúrate de que el contenedor de Loki esté accesible en 'http://loki:3100'
loki_handler = LokiLoggerHandler(
    url="http://loki:3100/loki/api/v1/push",
    # Añadimos etiquetas globales útiles para Grafana/Loki
    labels={"application": "FastApi", "environment": "dev"}, 
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

# ======================
# MODELO DE DATOS (Pydantic)
# ======================
# Modelo de datos para las peticiones POST (todos los endpoints)
class OperacionRequest(BaseModel):
    a: float
    b: float

# ======================
# MÉTRICAS PROMETHEUS
# ======================
# Contador personalizado para errores de lógica de negocio (negativos, división por cero, fallos de DB)
CALCULATOR_ERRORS = Counter(
    "calculator_operation_errors_total",
    "Total number of business logic errors in calculator operations",
    ["operation", "error_type"] # Etiquetas para distinguir la operación y el tipo de error
)

# Inicializa y expone las métricas HTTP predeterminadas
Instrumentator(
    excluded_handlers=[".*/metrics"],
).instrument(app).expose(app)

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
    Valida números de entrada y registra errores de negocio.
    """
    if a < 0 or b < 0:
        error_type = "NegativeNumber"
        msg = f"Operación {operacion} inválida: no se permiten números negativos (a={a}, b={b})"
        # Loggear error de forma detallada para Loki
        logger.error(msg, extra={"operation": operacion, "error_type": error_type, "a": a, "b": b})
        # Incrementar contador custom para Prometheus
        CALCULATOR_ERRORS.labels(operation=operacion, error_type=error_type).inc()
        raise HTTPException(status_code=400, detail=msg)

    if operacion == "division" and b == 0:
        error_type = "DivisionByZero"
        msg = f"Operación division inválida: intento de dividir entre cero (a={a}, b={b})"
        # Loggear error de forma detallada para Loki
        logger.error(msg, extra={"operation": operacion, "error_type": error_type, "a": a, "b": b})
        # Incrementar contador custom para Prometheus
        CALCULATOR_ERRORS.labels(operation=operacion, error_type=error_type).inc()
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
        # Requerimiento global: Loggear éxito
        logger.info(f"Operación {operacion} almacenada correctamente en MongoDB", extra={"operation": operacion, "status": "db_success"})
    except Exception as e:
        error_type = "DatabaseConnection"
        # Requerimiento global: Loggear error con la causa (ej. no conexión a mongo)
        msg = f"Error al guardar operación {operacion} en MongoDB: No se pudo conectar/escribir. Causa: {e}"
        logger.error(msg, extra={"operation": operacion, "error_type": error_type, "exception_detail": str(e)})
        # Incrementar contador custom para Prometheus
        CALCULATOR_ERRORS.labels(operation=operacion, error_type=error_type).inc()
        raise HTTPException(
            status_code=500,
            detail=f"Error al guardar en historial (Mongo): {str(e)}",
        )


# =========================
# ENDPOINTS DE OPERACIONES
# =========================

@app.post("/calculadora/sum") # <-- CAMBIO A POST
def sumar(request_data: OperacionRequest): # <-- RECIBE OBJETO MODELO
    """
    Suma dos números (POST con Request Body: {"a": 5, "b": 10})
    """
    try:
        a = request_data.a # Extraer del modelo
        b = request_data.b # Extraer del modelo
        
        validar_entrada(a, b, "suma")
        resultado = a + b
        guardar_operacion(a, b, resultado, "suma")

        # Requerimiento global: Loggear éxito de la operación
        logger.info(f"Operación suma exitosa: {a} + {b} = {resultado}", extra={"operation": "suma", "status": "success", "a": a, "b": b, "resultado": resultado})
        return {"a": a, "b": b, "resultado": resultado}
    except HTTPException:
        # Los errores 400 y 500 ya fueron loggeados e instrumentados
        raise
    except Exception as e:
        # Manejo de cualquier error inesperado (ej. código)
        error_type = "InternalServerError"
        msg = f"Error inesperado en suma: {e}"
        logger.error(msg, extra={"operation": "suma", "error_type": error_type, "exception_detail": str(e)})
        CALCULATOR_ERRORS.labels(operation="suma", error_type=error_type).inc()
        raise HTTPException(status_code=500, detail="Error interno inesperado en suma")


@app.post("/calculadora/resta") # <-- CAMBIO A POST
def restar(request_data: OperacionRequest): # <-- RECIBE OBJETO MODELO
    """
    Resta dos números (POST con Request Body: {"a": 5, "b": 10})
    """
    try:
        a = request_data.a # Extraer del modelo
        b = request_data.b # Extraer del modelo
        
        validar_entrada(a, b, "resta")
        resultado = a - b
        guardar_operacion(a, b, resultado, "resta")

        # Requerimiento global: Loggear éxito de la operación
        logger.info(f"Operación resta exitosa: {a} - {b} = {resultado}", extra={"operation": "resta", "status": "success", "a": a, "b": b, "resultado": resultado})
        return {"a": a, "b": b, "resultado": resultado}
    except HTTPException:
        raise
    except Exception as e:
        error_type = "InternalServerError"
        msg = f"Error inesperado en resta: {e}"
        logger.error(msg, extra={"operation": "resta", "error_type": error_type, "exception_detail": str(e)})
        CALCULATOR_ERRORS.labels(operation="resta", error_type=error_type).inc()
        raise HTTPException(status_code=500, detail="Error interno inesperado en resta")


@app.post("/calculadora/mult") # <-- CAMBIO A POST
def multiplicar(request_data: OperacionRequest): # <-- RECIBE OBJETO MODELO
    """
    Multiplica dos números (POST con Request Body: {"a": 5, "b": 10})
    """
    try:
        a = request_data.a # Extraer del modelo
        b = request_data.b # Extraer del modelo
        
        validar_entrada(a, b, "multiplicacion")
        resultado = a * b
        guardar_operacion(a, b, resultado, "multiplicacion")

        # Requerimiento global: Loggear éxito de la operación
        logger.info(f"Operación multiplicación exitosa: {a} * {b} = {resultado}", extra={"operation": "multiplicacion", "status": "success", "a": a, "b": b, "resultado": resultado})
        return {"a": a, "b": b, "resultado": resultado}
    except HTTPException:
        raise
    except Exception as e:
        error_type = "InternalServerError"
        msg = f"Error inesperado en multiplicación: {e}"
        logger.error(msg, extra={"operation": "multiplicacion", "error_type": error_type, "exception_detail": str(e)})
        CALCULATOR_ERRORS.labels(operation="multiplicacion", error_type=error_type).inc()
        raise HTTPException(status_code=500, detail="Error interno inesperado en multiplicación")


@app.post("/calculadora/div") # <-- CAMBIO A POST
def dividir(request_data: OperacionRequest): # <-- RECIBE OBJETO MODELO
    """
    Divide dos números (POST con Request Body: {"a": 5, "b": 10})
    """
    try:
        a = request_data.a # Extraer del modelo
        b = request_data.b # Extraer del modelo
        
        validar_entrada(a, b, "division")
        resultado = a / b  # Ya se validó que b != 0
        guardar_operacion(a, b, resultado, "division")

        # Requerimiento global: Loggear éxito de la operación
        logger.info(f"Operación división exitosa: {a} / {b} = {resultado}", extra={"operation": "division", "status": "success", "a": a, "b": b, "resultado": resultado})
        return {"a": a, "b": b, "resultado": resultado}
    except HTTPException:
        raise
    except Exception as e:
        error_type = "InternalServerError"
        msg = f"Error inesperado en división: {e}"
        logger.error(msg, extra={"operation": "division", "error_type": error_type, "exception_detail": str(e)})
        CALCULATOR_ERRORS.labels(operation="division", error_type=error_type).inc()
        raise HTTPException(status_code=500, detail="Error interno inesperado en división")


# ======================
# ENDPOINT HISTORIAL
# ======================

@app.get("/calculadora/historial")
def obtener_historial():
    try:
        operaciones = collection_historial.find({})
        historial = []
        for operacion in operaciones:
            # Quitamos el ID de Mongo por seguridad/limpieza
            operacion.pop('_id', None)
            historial.append({
                "a": operacion["a"],
                "b": operacion["b"],
                "resultado": operacion["resultado"],
                # Se utiliza .isoformat() para serializar datetime correctamente
                "date": operacion["date"].isoformat(), 
                "operacion": operacion["operacion"],
            })

        logger.info("Consulta de historial exitosa", extra={"operation": "historial", "status": "success", "count": len(historial)})
        return {"historial": historial}
    except Exception as e:
        # Requerimiento global: Loggear error con la causa
        error_type = "DatabaseConnection"
        msg = f"Error al obtener historial de MongoDB: {e}"
        logger.error(msg, extra={"operation": "historial", "error_type": error_type, "exception_detail": str(e)})
        raise HTTPException(status_code=500, detail=f"Error al obtener historial de Mongo: {str(e)}")