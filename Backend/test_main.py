import pytest
import mongomock
from fastapi.testclient import TestClient
import main  # important: we need to patch main.collection_historial
import datetime

client = TestClient(main.app)

# Create mock DB and collection
mongo_client = mongomock.MongoClient()
database = mongo_client.practica1
mock_collection = database.historial


@pytest.mark.parametrize("a, b, expected", [
    (2, 2, 4),
    (0, 0, 0),
    (-1, 1, 0),
    (2.5, 2.5, 5.0),
    (1e10, 1e10, 2e10)
])
def test_sum_numbers(monkeypatch, a, b, expected):
    # 🔹 Patch the collection that main.py uses
    monkeypatch.setattr(main, "collection_historial", mock_collection)

    # Clean before test
    mock_collection.delete_many({})

    response = client.get(f"/calculadora/sum?a={a}&b={b}")
    
    # ✅ Assert response correctness
    assert response.status_code == 200
    assert response.json() == {"a": a, "b": b, "resultado": expected}
    
    # ✅ Assert that the record was inserted into mongomock
    saved = mock_collection.find_one({"a": a, "b": b})
    assert saved is not None
    assert saved["resultado"] == expected

# En tu archivo test_main.py, dentro de la función test_historial
# ...
def test_historial(monkeypatch):
    monkeypatch.setattr(main, "collection_historial", mock_collection)
    
    # 🚨 Es necesario insertar datos de prueba para poder recuperar algo.
    # Como la prueba test_sum_numbers falla al guardar, la colección está vacía.
    # Por eso, la prueba de historial falla.
    # Vamos a insertar un documento para que la prueba tenga datos.
    doc_sum = {
        "a": 10000000000.0,
        "b": 10000000000.0,
        "resultado": 20000000000.0,
        "date": datetime.datetime(2025, 10, 1, 10, 24, 19, 116000, tzinfo=datetime.timezone.utc),
        "operacion": "suma"
    }
    mock_collection.insert_one(doc_sum)
    
    response = client.get("/calculadora/historial")
    assert response.status_code == 200
    
    expected_historial = []
    for doc in mock_collection.find({}):
        expected_historial.append({
            "a": doc["a"],
            "b": doc["b"],
            "resultado": doc["resultado"],
            "operacion": doc["operacion"],  # 🚨 Añade esta línea
            "date": doc["date"].isoformat()
        })
    
    # print(f"debug: expected_historial: {expected_historial}")
    # print(f"debug: response.json(): {response.json()}")
    
    assert response.json() == {"historial": expected_historial}