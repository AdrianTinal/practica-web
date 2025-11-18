import datetime
import logging
import os, sys
from fastapi import FastAPI
from pymongo import MongoClient
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from loki_logger_handler.loki_logger_handler import LokiLoggerHandler

# Set up logging
logger = logging.getLogger("custom_logger")
logging_data = os.getenv("LOG_LEVEL", "INFO").upper()

if logging_data == "DEBUG":
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)

# Create a console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logger.level)
formatter = logging.Formatter(
    "%(levelname)s: %(asctime)s - %(name)s - %(message)s"
)
console_handler.setFormatter(formatter)

# Create an instance of the custom handler
loki_handler = LokiLoggerHandler(
    url="http://loki:3100/loki/api/v1/push",
    labels={"application": "FastApi"},
    label_keys={},
    timeout=10,
)

logger.addHandler(loki_handler)
logger.addHandler(console_handler)
logger.info("Logger initialized")

class Numbers(BaseModel):
    a: float
    b: float

class HistorialFilter(BaseModel):
    operacion: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    order_by: Optional[str] = "date"  
    order_direction: Optional[str] = "desc" 

class GrupoOperacion(BaseModel):
    operacion: str
    a: float
    b: float

class GrupoOperacionesRequest(BaseModel):
    operaciones: List[GrupoOperacion]

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

mongo_client = MongoClient("mongodb://admin_user:web3@mongo:27017/")
database = mongo_client["practica1"]
collection_historial = database["historial"]

@app.post("/calculadora/sum")
def sumar(numbers: Numbers):
    """
    Suma dos números que vienen en el body de la solicitud.
    """
    if numbers.a < 0 or numbers.b < 0:
        raise HTTPException(status_code=400, detail="No se aceptan números negativos.")

    resultado = numbers.a + numbers.b
    document = {
        "resultado": resultado,
        "a": numbers.a,
        "b": numbers.b,
        "operacion": "sum", 
        "date": datetime.now(tz=timezone.utc),
        }
    collection_historial.insert_one(document)

    return {"a": numbers.a, "b": numbers.b, "resultado": resultado}

@app.post("/calculadora/resta")
def restar(numbers: Numbers):
    if numbers.a < 0 or numbers.b < 0:
        raise HTTPException(status_code=400, detail="No se aceptan números negativos.")
    
    resultado = numbers.a - numbers.b
    document = {
        "resultado": resultado,
        "a": numbers.a,
        "b": numbers.b,
        "operacion": "resta",
        "date": datetime.now(tz=timezone.utc),
    }
    collection_historial.insert_one(document)

    return {"a": numbers.a, "b": numbers.b, "resultado": resultado}

@app.post("/calculadora/mult")
def multiplicar(numbers: Numbers):
    if numbers.a < 0 or numbers.b < 0:
        raise HTTPException(status_code=400, detail="No se aceptan números negativos.")
    
    resultado = numbers.a * numbers.b
    document = {
        "resultado": resultado,
        "a": numbers.a,
        "b": numbers.b,
        "operacion": "mult", 
        "date": datetime.now(tz=timezone.utc),
    }
    collection_historial.insert_one(document)

    return {"a": numbers.a, "b": numbers.b, "resultado": resultado}

@app.post("/calculadora/div")
def dividir(numbers: Numbers):
    if numbers.a < 0 or numbers.b < 0:
        raise HTTPException(status_code=400, detail="No se aceptan números negativos.")
    if numbers.b == 0:
        raise HTTPException(status_code=403, detail="No se permite la división entre cero.")
    
    resultado = numbers.a / numbers.b
    document = {
        "resultado": resultado,
        "a": numbers.a,
        "b": numbers.b,
        "operacion": "div", 
        "date": datetime.now(tz=timezone.utc),
    }
    collection_historial.insert_one(document)

    return {"a": numbers.a, "b": numbers.b, "resultado": resultado}

# main.py
# ... (tu código actual) ...

@app.post("/calculadora/historial") 
def obtener_historial(filters: HistorialFilter):
    query = {}
    if filters.operacion:
        query["operacion"] = filters.operacion
    if filters.start_date or filters.end_date:
        query["date"] = {}
        if filters.start_date:
            query["date"]["$gte"] = filters.start_date
        if filters.end_date:
            query["date"]["$lte"] = filters.end_date

    sort_direction = 1 if filters.order_direction == "asc" else -1
    operaciones = collection_historial.find(query).sort(filters.order_by, sort_direction)

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



@app.post("/calculadora/operaciones-agrupadas")
def operaciones(request: GrupoOperacionesRequest):
    resultados = []
    for op in request.operaciones:
        # Validación de números negativos
        if op.a < 0 or op.b < 0:
            resultados.append({
                "operacion": op.operacion,
                "error": f"No se aceptan números negativos en la operación: {op.operacion} con a={op.a} y b={op.b}"
            })
            continue

        if op.operacion == "sum":
            res = op.a + op.b
        elif op.operacion == "resta":
            res = op.a - op.b
        elif op.operacion == "mult":
            res = op.a * op.b
        elif op.operacion == "div":
            if op.b == 0:
                res = "No se permite la división entre cero."
            else:
                res = op.a / op.b
        else:
            res = f"Operación no válida: {op.operacion}"


        if op.operacion == "div" and op.b == 0:
            res_dict = {"operacion": op.operacion, "resultado": res}
        else:
            document = {
                "resultado": res,
                "a": op.a,
                "b": op.b,
                "operacion": op.operacion,
                "date": datetime.now(tz=timezone.utc),
            }
            collection_historial.insert_one(document)
            res_dict = {"operacion": op.operacion, "resultado": res}

        resultados.append(res_dict)
        
    return {"resultados": resultados}


Instrumentator().instrument(app).expose(app)

# forzar el backend 