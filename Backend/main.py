import datetime
import logging
from fastapi import FastAPI
from pymongo import MongoClient
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from loki_logger_handler.loki_logger_handler import LokiLoggerHandler



# Set up logging
logger = logging.getLogger("custom_logger")
logging_data = os.getenv("LOGGING_DATA", "info").upper() 
if logging_data == "DEBUG":
    log_level = logging.DEBUG
elif logging_data == "INFO":
    log_level = logging.INFO

logger.setLevel(logging.DEBUG)

# Create an instance of the custom handler
custom_handler = LokiLoggerHandler(
    url="http://loki:3100/loki/api/v1/push",
    labels={"application": "FastApi"},
    label_keys={},
    timeout=10,
)

logger.addHandler(custom_handler)
logger.info("Logger initialized and sending logs to Loki")


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Conexión a MongoDB
mongo_client = MongoClient("mongodb://admin_user:web3@mongo:27017/")
database = mongo_client["practica1"]
collection_historial = database["historial"]

@app.get("/calculadora/sum")
def sumar(a: float, b: float):
    """
    Suma dos números que vienen como parámetros de query (?a=...&b=...)
    Ejemplo: /calculadora/sum?a=5&b=10
    """
    resultado = a + b
    document = {
        "resultado": resultado,
        "a": a,
        "b": b,
        "operacion": "suma",
        "date": datetime.datetime.now(tz=datetime.timezone.utc),
    }

    logger.info(f"operacion exitosa")
    logger.debug(f"Insertando documento en la base de datos: {document}")
    collection_historial.insert_one(document)

    return {"a": a, "b": b, "resultado": resultado}

# @app.get("/calculadora/resta")
# def restar(a: float, b: float):
#     """
#     Resta dos números que vienen como parámetros de query (?a=...&b=...)
#     Ejemplo: /calculadora/resta?a=5&b=10
#     """
#     resultado = a - b
#     document = {
#         "resultado": resultado,
#         "a": a,
#         "b": b,
#         "operacion": "resta",
#         "date": datetime.datetime.now(tz=datetime.timezone.utc),
#     }
#     collection_historial.insert_one(document)

#     return {"a": a, "b": b, "resultado": resultado}

# @app.get("/calculadora/mult")
# def multiplicar(a: float, b: float):
#     """
#     Multiplica dos números que vienen como parámetros de query (?a=...&b=...)
#     Ejemplo: /calculadora/mult?a=5&b=10
#     """
#     resultado = a * b
#     document = {
#         "resultado": resultado,
#         "a": a,
#         "b": b,
#         "operacion": "multiplicacion",
#         "date": datetime.datetime.now(tz=datetime.timezone.utc),
#     }
#     collection_historial.insert_one(document)

#     return {"a": a, "b": b, "resultado": resultado}

# @app.get("/calculadora/div")
# def multiplicar(a: float, b: float):
#     """
#     Divide dos números que vienen como parámetros de query (?a=...&b=...)
#     Ejemplo: /calculadora/resta?a=5&b=10
#     """
#     resultado = "indefinido"
#     if(b != 0):
#         resultado = a / b
    
#     document = {
#         "resultado": resultado,
#         "a": a,
#         "b": b,
#         "operacion": "division",
#         "date": datetime.datetime.now(tz=datetime.timezone.utc),
#     }
#     collection_historial.insert_one(document)

#     return {"a": a, "b": b, "resultado": resultado}


@app.get("/calculadora/historial")
def obtener_historial():
    operaciones = collection_historial.find({})
    historial = []
    for operacion in operaciones:
        historial.append({
            "a": operacion["a"],
            "b": operacion["b"],
            "resultado": operacion["resultado"],
            "date": operacion["date"].isoformat(),
            "operacion": operacion["operacion"]
        })
    return {"historial": historial}

Instrumentator().instrument(app).expose(app)

# forzar el backend 