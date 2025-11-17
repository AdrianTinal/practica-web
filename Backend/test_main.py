import pytest
import mongomock
from fastapi.testclient import TestClient
import main  
from datetime import datetime, timezone 

client = TestClient(main.app)


mongo_client = mongomock.MongoClient()
database = mongo_client.practica1
mock_collection = database.historial


@pytest.mark.parametrize("a, b, expected", [
    (1, 2, 3),
    (0, 0, 0),
    (1e10, 1e10, 2e10)
])
def test_sum_numbers_valid_post(monkeypatch, a, b, expected):
    monkeypatch.setattr(main, "collection_historial", mock_collection)
    mock_collection.delete_many({})


    response = client.post("/calculadora/sum", json={"a": a, "b": b})
    
    assert response.status_code == 200
    assert response.json()["resultado"] == expected
    
    saved = mock_collection.find_one({"a": a, "b": b})
    assert saved is not None
    assert saved["resultado"] == expected


@pytest.mark.parametrize("a, b", [
    (-1, 5),
    (10, -2),
    (-3, -4)
])
def test_sum_negative_numbers(monkeypatch, a, b):
    monkeypatch.setattr(main, "collection_historial", mock_collection)
    mock_collection.delete_many({})

    response = client.post("/calculadora/sum", json={"a": a, "b": b})

    assert response.status_code == 400
    assert response.json() == {"detail": "No se aceptan números negativos."}

@pytest.mark.parametrize("a, b, expected", [
    (10, 5, 5), (0, 0, 0), (5, 10, -5), (10.5, 5.5, 5.0)
])
def test_resta_valid_post(monkeypatch, a, b, expected):
    monkeypatch.setattr(main, "collection_historial", mock_collection)
    mock_collection.delete_many({})
    response = client.post("/calculadora/resta", json={"a": a, "b": b})
    assert response.status_code == 200
    assert response.json()["resultado"] == expected
    saved = mock_collection.find_one({"a": a, "b": b})
    assert saved is not None
    assert saved["resultado"] == expected

@pytest.mark.parametrize("a, b", [(-1, 5), (10, -2), (-3, -4)])
def test_resta_negative_numbers(monkeypatch, a, b):
    monkeypatch.setattr(main, "collection_historial", mock_collection)
    mock_collection.delete_many({})
    response = client.post("/calculadora/resta", json={"a": a, "b": b})
    assert response.status_code == 400
    assert response.json() == {"detail": "No se aceptan números negativos."}


@pytest.mark.parametrize("a, b, expected", [
    (2, 3, 6), (5, 0, 0), (2.5, 2, 5.0)
])
def test_multiplicacion_valid_post(monkeypatch, a, b, expected):
    monkeypatch.setattr(main, "collection_historial", mock_collection)
    mock_collection.delete_many({})
    response = client.post("/calculadora/mult", json={"a": a, "b": b})
    assert response.status_code == 200
    assert response.json()["resultado"] == expected
    saved = mock_collection.find_one({"a": a, "b": b})
    assert saved is not None
    assert saved["resultado"] == expected

@pytest.mark.parametrize("a, b", [(-2, 3), (5, -2), (-3, -4)])
def test_multiplicacion_negative_numbers(monkeypatch, a, b):
    monkeypatch.setattr(main, "collection_historial", mock_collection)
    mock_collection.delete_many({})
    response = client.post("/calculadora/mult", json={"a": a, "b": b})
    assert response.status_code == 400
    assert response.json() == {"detail": "No se aceptan números negativos."}


@pytest.mark.parametrize("a, b, expected", [
    (10, 5, 2), (8, 2, 4), (100, 10, 10), (7.5, 2.5, 3.0)
])
def test_division_valid_post(monkeypatch, a, b, expected):
    monkeypatch.setattr(main, "collection_historial", mock_collection)
    mock_collection.delete_many({})
    response = client.post("/calculadora/div", json={"a": a, "b": b})
    assert response.status_code == 200
    assert response.json()["resultado"] == expected
    saved = mock_collection.find_one({"a": a, "b": b})
    assert saved is not None
    assert saved["resultado"] == expected

def test_division_por_cero(monkeypatch):
    monkeypatch.setattr(main, "collection_historial", mock_collection)
    mock_collection.delete_many({})
    response = client.post("/calculadora/div", json={"a": 10, "b": 0})
    assert response.status_code == 403
    assert response.json() == {"detail": "No se permite la división entre cero."}

@pytest.mark.parametrize("a, b", [(-1, 5), (10, -2), (-3, -4)])
def test_division_negative_numbers(monkeypatch, a, b):
    monkeypatch.setattr(main, "collection_historial", mock_collection)
    mock_collection.delete_many({})
    response = client.post("/calculadora/div", json={"a": a, "b": b})
    assert response.status_code == 400
    assert response.json() == {"detail": "No se aceptan números negativos."}


def test_historial(monkeypatch):
    monkeypatch.setattr(main, "collection_historial", mock_collection)
    mock_collection.delete_many({})


    doc_sum = {"a": 1.0, "b": 2.0, "resultado": 3.0, "operacion": "sum", "date": datetime.now(tz=timezone.utc)}
    doc_resta = {"a": 5.0, "b": 2.0, "resultado": 3.0, "operacion": "resta", "date": datetime.now(tz=timezone.utc)}
    mock_collection.insert_one(doc_sum)
    mock_collection.insert_one(doc_resta)
    
    # Se cambió client.get por client.post
    response = client.post("/calculadora/historial", json={})
    assert response.status_code == 200
    
    expected_historial = []
    for doc in mock_collection.find({}):
        expected_historial.append({
            "a": doc["a"],
            "b": doc["b"],
            "resultado": doc["resultado"],
            "operacion": doc["operacion"],
            "date": doc["date"].isoformat()
        })
    
    assert response.json() == {"historial": expected_historial}


def test_operaciones_en_grupo_exitosas(monkeypatch):
    monkeypatch.setattr(main, "collection_historial", mock_collection)
    mock_collection.delete_many({})

    payload = {
        "operaciones": [
            {"operacion": "sum", "a": 5, "b": 3},
            {"operacion": "resta", "a": 10, "b": 4},
            {"operacion": "mult", "a": 2, "b": 5},
            {"operacion": "div", "a": 15, "b": 3}
        ]
    }

    response = client.post("/calculadora/operaciones-agrupadas", json=payload)

    assert response.status_code == 200
    assert response.json()["resultados"][0]["resultado"] == 8
    assert response.json()["resultados"][1]["resultado"] == 6
    assert response.json()["resultados"][2]["resultado"] == 10
    assert response.json()["resultados"][3]["resultado"] == 5

    historial = list(mock_collection.find({}))
    assert len(historial) == 4


def test_operaciones_en_grupo_con_errores(monkeypatch):
    monkeypatch.setattr(main, "collection_historial", mock_collection)
    mock_collection.delete_many({})

    payload = {
        "operaciones": [
            {"operacion": "sum", "a": -5, "b": 3}, # Error por negativo
            {"operacion": "div", "a": 10, "b": 0},  # Error por división entre cero
            {"operacion": "mult", "a": 2, "b": 5} # Operación válida
        ]
    }
    response = client.post("/calculadora/operaciones-agrupadas", json=payload)

    assert response.status_code == 200
    assert "No se aceptan números negativos" in response.json()["resultados"][0]["error"]
    assert response.json()["resultados"][1]["resultado"] == "No se permite la división entre cero."
    assert response.json()["resultados"][2]["resultado"] == 10

    historial = list(mock_collection.find({}))
    assert len(historial) == 1
    assert historial[0]["operacion"] == "mult"