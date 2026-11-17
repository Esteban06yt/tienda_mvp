"""CRUD de Producto: listar, crear, actualizar y eliminar con validaciones."""


def test_listado_con_paginacion_y_busqueda(client):
    r = client.get("/api/productos?per_page=5").get_json()
    assert r["total"] >= 20
    assert len(r["items"]) == 5
    assert r["pages"] >= 4
    r = client.get("/api/productos?query=gaseosa").get_json()
    assert r["total"] == 2
    todos = client.get("/api/productos?per_page=50").get_json()["items"]
    assert any(p["bajo_minimo"] for p in todos)


def test_crear_valida_campos(client):
    assert client.post("/api/productos", json={"nombre": "", "precio": 100, "existencia": 1}).status_code == 422
    assert client.post("/api/productos", json={"nombre": "X", "precio": 0, "existencia": 1}).status_code == 422
    assert client.post("/api/productos", json={"nombre": "X", "precio": 100, "existencia": -1}).status_code == 422


def test_crear_actualizar_y_eliminar(client):
    r = client.post("/api/productos", json={"nombre": "Nuevo", "precio": 900, "existencia": 4, "stock_minimo": 2})
    assert r.status_code == 201
    pid = r.get_json()["id"]
    # nombre repetido
    assert client.post("/api/productos", json={"nombre": "nuevo", "precio": 900, "existencia": 4}).status_code == 409
    r = client.patch("/api/productos/%d" % pid, json={"precio": 1200, "activo": False})
    assert r.status_code == 200
    assert r.get_json()["precio"] == 1200
    assert r.get_json()["activo"] is False
    assert client.delete("/api/productos/%d" % pid).status_code == 204
    assert client.get("/api/productos/%d" % pid).status_code == 404


def test_no_se_elimina_producto_con_ventas(client, crear_producto):
    p = crear_producto(precio=1000, existencia=5)
    client.post(
        "/api/ventas",
        json={
            "tendero_id": 1,
            "items": [{"producto_id": p["id"], "cantidad": 1}],
            "total_confirmado": 1000,
            "forma_pago": "efectivo",
            "billete_verificado": True,
            "efectivo_recibido": 1000,
        },
    )
    r = client.delete("/api/productos/%d" % p["id"])
    assert r.status_code == 409
