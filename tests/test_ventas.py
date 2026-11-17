"""Casos de aceptacion (Given-When-Then) de la transaccion Registrar venta."""
from conftest import cliente_id


def venta(producto, cantidad=1, **extra):
    total = producto["precio"] * cantidad
    cuerpo = {
        "tendero_id": 1,
        "items": [{"producto_id": producto["id"], "cantidad": cantidad}],
        "total_confirmado": total,
        "forma_pago": "efectivo",
        "billete_verificado": True,
        "efectivo_recibido": total,
    }
    cuerpo.update(extra)
    return cuerpo


def existencia(client, producto):
    return client.get("/api/productos/%d" % producto["id"]).get_json()["existencia"]


def test_gwt1_venta_en_efectivo_exitosa(client, crear_producto):
    # Given un producto con existencia 10 y un billete verificado
    p = crear_producto(precio=2000, existencia=10)
    # When el tendero confirma una venta de 3 unidades pagando con 10000
    r = client.post("/api/ventas", json=venta(p, 3, efectivo_recibido=10000))
    # Then la venta queda confirmada, con cambio y tendero, y el inventario baja
    assert r.status_code == 201
    v = r.get_json()
    assert v["estado"] == "confirmada"
    assert v["total"] == 6000
    assert v["pago"]["cambio"] == 4000
    assert v["tendero"] == "Tendero Demo 1"
    assert v["fecha"]
    assert existencia(client, p) == 7


def test_gwt2_sin_existencia_suficiente_bloquea(client, crear_producto):
    # Given un producto con existencia 2
    p = crear_producto(existencia=2)
    # When se intenta vender 5
    r = client.post("/api/ventas", json=venta(p, 5))
    # Then se bloquea por R006 y la existencia no cambia
    assert r.status_code == 422
    assert r.get_json()["regla"] == "R006"
    assert existencia(client, p) == 2


def test_gwt3_efectivo_sin_verificar_bloquea(client, crear_producto):
    # Given un pago en efectivo con el billete sin verificar
    p = crear_producto(existencia=5)
    # When el tendero intenta registrar la venta
    r = client.post("/api/ventas", json=venta(p, 1, billete_verificado=False))
    # Then se bloquea por R003 y no se crea la venta
    assert r.status_code == 422
    assert r.get_json()["regla"] == "R003"
    assert existencia(client, p) == 5


def test_gwt4_fiado_a_cliente_no_de_confianza_bloquea(client, crear_producto):
    # Given un cliente que no es de confianza
    p = crear_producto(existencia=5)
    cid = cliente_id(client, de_confianza=False)
    # When se intenta registrar una venta fiada
    r = client.post("/api/ventas", json=venta(p, 1, forma_pago="fiado", cliente_id=cid))
    # Then se bloquea por R005
    assert r.status_code == 422
    assert r.get_json()["regla"] == "R005"
    assert existencia(client, p) == 5


def test_gwt5_fiado_a_cliente_de_confianza_se_registra(client, crear_producto):
    # Given un cliente de confianza
    p = crear_producto(existencia=5)
    cid = cliente_id(client, de_confianza=True)
    # When se registra la venta fiada
    r = client.post("/api/ventas", json=venta(p, 2, forma_pago="fiado", cliente_id=cid))
    # Then queda como fiado pendiente y el inventario baja
    assert r.status_code == 201
    assert r.get_json()["estado"] == "fiado_pendiente"
    assert existencia(client, p) == 3


def test_gwt6_total_no_confirmado_bloquea(client, crear_producto):
    # Given una venta cuyo total no fue confirmado con el cliente
    p = crear_producto(precio=1500, existencia=5)
    # When el tendero intenta cobrar con un total confirmado distinto
    r = client.post("/api/ventas", json=venta(p, 2, total_confirmado=1))
    # Then se bloquea por R001
    assert r.status_code == 422
    assert r.get_json()["regla"] == "R001"


def test_gwt7_transferencia_queda_pendiente_hasta_confirmar(client, crear_producto):
    # Given un pago por transferencia
    p = crear_producto(precio=3000, existencia=6)
    r = client.post("/api/ventas", json=venta(p, 2, forma_pago="transferencia"))
    # When se registra la venta, queda pendiente y el inventario no se descuenta (R007)
    assert r.status_code == 201
    v = r.get_json()
    assert v["estado"] == "pendiente_pago_virtual"
    assert existencia(client, p) == 6
    # When se confirma que el dinero llego
    c = client.patch("/api/ventas/%d/confirmar-pago" % v["id"])
    # Then la venta se confirma y el inventario baja
    assert c.status_code == 200
    assert c.get_json()["estado"] == "confirmada"
    assert existencia(client, p) == 4
    # y no se puede confirmar dos veces
    assert client.patch("/api/ventas/%d/confirmar-pago" % v["id"]).status_code == 409


def test_gwt8_sin_tendero_bloquea(client, crear_producto):
    # Given una venta sin tendero
    p = crear_producto(existencia=5)
    cuerpo = venta(p, 1)
    cuerpo.pop("tendero_id")
    # When se intenta registrar
    r = client.post("/api/ventas", json=cuerpo)
    # Then se bloquea por R008
    assert r.status_code == 422
    assert r.get_json()["regla"] == "R008"
