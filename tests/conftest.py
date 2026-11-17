import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app  # noqa: E402


@pytest.fixture
def client(tmp_path):
    app = create_app(str(tmp_path / "prueba.db"))
    app.config["TESTING"] = True
    return app.test_client()


@pytest.fixture
def crear_producto(client):
    def _crear(nombre="Producto de prueba", precio=1000, existencia=10, stock_minimo=2):
        r = client.post(
            "/api/productos",
            json={"nombre": nombre, "categoria": "Prueba", "precio": precio, "existencia": existencia, "stock_minimo": stock_minimo},
        )
        assert r.status_code == 201
        return r.get_json()

    return _crear


def cliente_id(client, de_confianza):
    # Marta Gomez es de confianza y Carlos Diaz no lo es (ver seed.py)
    nombre = "Marta" if de_confianza else "Carlos"
    return client.get("/api/clientes?query=" + nombre).get_json()[0]["id"]
