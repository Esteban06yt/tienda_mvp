"""Reglas de negocio de la transaccion Registrar venta y validaciones del CRUD de productos.

Cada regla lanza ReglaError con su codigo (R001, R003, ...) para que la interfaz
muestre un mensaje alineado a la regla que se incumplio.
"""

FORMAS_PAGO = ("efectivo", "transferencia", "fiado")


class ReglaError(Exception):
    def __init__(self, regla, mensaje, campo=None, status=422):
        super().__init__(mensaje)
        self.regla = regla
        self.mensaje = mensaje
        self.campo = campo
        self.status = status


def _entero(valor, nombre, campo, regla, minimo=None):
    try:
        if isinstance(valor, bool):
            raise ValueError
        numero = int(valor)
    except (TypeError, ValueError):
        raise ReglaError(regla, "El campo %s debe ser un numero entero." % nombre, campo)
    if minimo is not None and numero < minimo:
        raise ReglaError(regla, "El campo %s debe ser mayor o igual a %d." % (nombre, minimo), campo)
    return numero


def calcular_items(db, items):
    """R006: no se vende mas de lo que hay en existencia."""
    if not isinstance(items, list) or not items:
        raise ReglaError("R006", "La venta debe tener al menos un producto.", "items")
    calculados = []
    vistos = set()
    for item in items:
        if not isinstance(item, dict):
            raise ReglaError("R006", "Linea de venta invalida.", "items")
        pid = _entero(item.get("producto_id"), "producto", "items", "R006", 1)
        cantidad = _entero(item.get("cantidad"), "cantidad", "items", "R006", 1)
        if pid in vistos:
            raise ReglaError("R006", "El producto %d esta repetido; suma las cantidades en una sola linea." % pid, "items")
        vistos.add(pid)
        producto = db.execute("SELECT * FROM productos WHERE id = ?", (pid,)).fetchone()
        if producto is None:
            raise ReglaError("R006", "El producto %d no existe." % pid, "items", 404)
        if not producto["activo"]:
            raise ReglaError("R006", "El producto %s esta inactivo." % producto["nombre"], "items")
        if cantidad > producto["existencia"]:
            raise ReglaError(
                "R006",
                "No hay existencia suficiente de %s (disponible: %d)." % (producto["nombre"], producto["existencia"]),
                "items",
            )
        calculados.append(
            {
                "producto_id": pid,
                "nombre": producto["nombre"],
                "cantidad": cantidad,
                "precio_unitario": producto["precio"],
                "subtotal": cantidad * producto["precio"],
            }
        )
    return calculados


def validar_venta(db, datos):
    """validarReglas(): devuelve los datos listos para crear la venta o lanza ReglaError."""
    if not isinstance(datos, dict):
        raise ReglaError("R006", "Solicitud invalida.", None, 400)

    # R008: toda venta registra el tendero que la confirma (la fecha la pone el sistema).
    tendero_id = datos.get("tendero_id")
    tendero = None
    if tendero_id is not None:
        tendero = db.execute("SELECT * FROM tenderos WHERE id = ?", (tendero_id,)).fetchone()
    if tendero is None:
        raise ReglaError("R008", "Debes indicar el tendero que registra la venta.", "tendero_id")

    items = calcular_items(db, datos.get("items"))
    total = sum(i["subtotal"] for i in items)

    # R001: el total se informa y confirma con el cliente antes de cobrar.
    if datos.get("total_confirmado") != total:
        raise ReglaError(
            "R001",
            "Debes informar y confirmar el total al cliente antes de cobrar (total calculado: %d)." % total,
            "total_confirmado",
        )

    forma_pago = datos.get("forma_pago")
    if forma_pago not in FORMAS_PAGO:
        raise ReglaError("R006", "Forma de pago invalida (efectivo, transferencia o fiado).", "forma_pago")

    cliente = None
    cliente_id = datos.get("cliente_id")
    if cliente_id is not None:
        cliente = db.execute("SELECT * FROM clientes WHERE id = ?", (cliente_id,)).fetchone()
        if cliente is None:
            raise ReglaError("R006", "El cliente indicado no existe.", "cliente_id", 404)

    efectivo_recibido = None
    cambio = None
    if forma_pago == "efectivo":
        # R003: todo pago en efectivo se verifica antes de aceptarse.
        if datos.get("billete_verificado") is not True:
            raise ReglaError("R003", "Verifica el billete antes de aceptar el pago en efectivo.", "billete_verificado")
        efectivo_recibido = _entero(datos.get("efectivo_recibido"), "efectivo recibido", "efectivo_recibido", "R003", 0)
        if efectivo_recibido < total:
            raise ReglaError("R003", "El efectivo recibido es menor al total de la venta.", "efectivo_recibido")
        cambio = efectivo_recibido - total
    elif forma_pago == "fiado":
        # R005: el fiado solo se autoriza a clientes de confianza.
        if cliente is None or not cliente["es_de_confianza"]:
            raise ReglaError("R005", "El fiado solo se autoriza a clientes de confianza.", "cliente_id")

    return {
        "tendero_id": tendero["id"],
        "cliente_id": cliente["id"] if cliente else None,
        "items": items,
        "total": total,
        "forma_pago": forma_pago,
        "efectivo_recibido": efectivo_recibido,
        "cambio": cambio,
    }


def validar_producto(datos, parcial=False):
    """Validaciones basicas del CRUD de productos."""
    if not isinstance(datos, dict):
        raise ReglaError("CRUD", "Solicitud invalida.", None, 400)
    limpio = {}
    if not parcial or "nombre" in datos:
        nombre = (datos.get("nombre") or "").strip() if isinstance(datos.get("nombre"), str) else ""
        if not nombre:
            raise ReglaError("CRUD", "El nombre es obligatorio.", "nombre")
        if len(nombre) > 80:
            raise ReglaError("CRUD", "El nombre no puede superar 80 caracteres.", "nombre")
        limpio["nombre"] = nombre
    if not parcial or "categoria" in datos:
        categoria = datos.get("categoria") or ""
        if not isinstance(categoria, str) or len(categoria.strip()) > 40:
            raise ReglaError("CRUD", "La categoria no puede superar 40 caracteres.", "categoria")
        limpio["categoria"] = categoria.strip()
    if not parcial or "precio" in datos:
        limpio["precio"] = _entero(datos.get("precio"), "precio", "precio", "CRUD", 1)
    if not parcial or "existencia" in datos:
        limpio["existencia"] = _entero(datos.get("existencia"), "existencia", "existencia", "CRUD", 0)
    if not parcial or "stock_minimo" in datos:
        limpio["stock_minimo"] = _entero(datos.get("stock_minimo", 0), "stock minimo", "stock_minimo", "CRUD", 0)
    if "activo" in datos:
        if not isinstance(datos["activo"], bool):
            raise ReglaError("CRUD", "El campo activo debe ser verdadero o falso.", "activo")
        limpio["activo"] = 1 if datos["activo"] else 0
    elif not parcial:
        limpio["activo"] = 1
    return limpio
