"""MVP de la tienda de barrio: transaccion Registrar venta + CRUD de Producto.

Ejecutar: python app.py   (abre http://127.0.0.1:5000)
"""
import os
import sqlite3
from datetime import datetime

from flask import Flask, g, jsonify, redirect, render_template, request

from reglas import ReglaError, calcular_items, validar_producto, validar_venta
from seed import sembrar

SCHEMA = """
CREATE TABLE IF NOT EXISTS tenderos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS clientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    telefono TEXT,
    es_de_confianza INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS productos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL UNIQUE COLLATE NOCASE,
    categoria TEXT,
    precio INTEGER NOT NULL CHECK (precio > 0),
    existencia INTEGER NOT NULL CHECK (existencia >= 0),
    stock_minimo INTEGER NOT NULL DEFAULT 0 CHECK (stock_minimo >= 0),
    activo INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS ventas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha TEXT NOT NULL,
    tendero_id INTEGER NOT NULL REFERENCES tenderos(id),
    cliente_id INTEGER REFERENCES clientes(id),
    total INTEGER NOT NULL,
    estado TEXT NOT NULL CHECK (estado IN ('confirmada', 'pendiente_pago_virtual', 'fiado_pendiente'))
);
CREATE TABLE IF NOT EXISTS venta_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    venta_id INTEGER NOT NULL REFERENCES ventas(id),
    producto_id INTEGER NOT NULL REFERENCES productos(id),
    cantidad INTEGER NOT NULL,
    precio_unitario INTEGER NOT NULL,
    subtotal INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS pagos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    venta_id INTEGER NOT NULL UNIQUE REFERENCES ventas(id),
    medio TEXT NOT NULL CHECK (medio IN ('efectivo', 'transferencia', 'fiado')),
    monto INTEGER NOT NULL,
    estado TEXT NOT NULL CHECK (estado IN ('verificado', 'pendiente', 'confirmado', 'fiado')),
    efectivo_recibido INTEGER,
    cambio INTEGER
);
"""


def ahora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def create_app(db_path=None):
    app = Flask(__name__)
    app.config["DB_PATH"] = db_path or os.environ.get(
        "TIENDA_DB", os.path.join(os.path.dirname(os.path.abspath(__file__)), "tienda.db")
    )

    def conectar():
        con = sqlite3.connect(app.config["DB_PATH"])
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON")
        return con

    con = conectar()
    con.executescript(SCHEMA)
    sembrar(con)
    con.close()

    def db():
        if "db" not in g:
            g.db = conectar()
        return g.db

    @app.teardown_appcontext
    def cerrar(_error):
        con_actual = g.pop("db", None)
        if con_actual is not None:
            con_actual.close()

    @app.errorhandler(ReglaError)
    def error_regla(e):
        return jsonify({"error": e.mensaje, "regla": e.regla, "campo": e.campo}), e.status

    # ------------------------------------------------------------ paginas
    @app.get("/")
    def inicio():
        return redirect("/venta")

    @app.get("/venta")
    def pantalla_venta():
        return render_template("venta.html")

    @app.get("/productos")
    def pantalla_productos():
        return render_template("productos.html")

    # ------------------------------------------------------------ catalogos
    @app.get("/api/tenderos")
    def listar_tenderos():
        filas = db().execute("SELECT id, nombre FROM tenderos ORDER BY id").fetchall()
        return jsonify([dict(f) for f in filas])

    @app.get("/api/clientes")
    def listar_clientes():
        consulta = "%" + (request.args.get("query") or "").strip() + "%"
        filas = db().execute(
            "SELECT id, nombre, telefono, es_de_confianza FROM clientes "
            "WHERE nombre LIKE ? OR telefono LIKE ? ORDER BY nombre LIMIT 10",
            (consulta, consulta),
        ).fetchall()
        return jsonify([dict(f) for f in filas])

    # ------------------------------------------------------------ CRUD producto
    def producto_dict(fila):
        d = dict(fila)
        d["activo"] = bool(d["activo"])
        d["bajo_minimo"] = d["existencia"] < d["stock_minimo"]
        return d

    @app.get("/api/productos")
    def listar_productos():
        consulta = "%" + (request.args.get("query") or "").strip() + "%"
        try:
            pagina = max(int(request.args.get("page", 1)), 1)
            por_pagina = min(max(int(request.args.get("per_page", 10)), 1), 50)
        except ValueError:
            raise ReglaError("CRUD", "Parametros de paginacion invalidos.", None, 400)
        filtro = "(nombre LIKE ? OR categoria LIKE ?)"
        params = [consulta, consulta]
        if request.args.get("activo") == "1":
            filtro += " AND activo = 1"
        total = db().execute("SELECT COUNT(*) FROM productos WHERE " + filtro, params).fetchone()[0]
        filas = db().execute(
            "SELECT * FROM productos WHERE " + filtro + " ORDER BY nombre LIMIT ? OFFSET ?",
            params + [por_pagina, (pagina - 1) * por_pagina],
        ).fetchall()
        paginas = max((total + por_pagina - 1) // por_pagina, 1)
        return jsonify(
            {
                "items": [producto_dict(f) for f in filas],
                "page": pagina,
                "per_page": por_pagina,
                "total": total,
                "pages": paginas,
            }
        )

    @app.get("/api/productos/<int:pid>")
    def obtener_producto(pid):
        fila = db().execute("SELECT * FROM productos WHERE id = ?", (pid,)).fetchone()
        if fila is None:
            raise ReglaError("CRUD", "El producto no existe.", None, 404)
        return jsonify(producto_dict(fila))

    @app.post("/api/productos")
    def crear_producto():
        datos = validar_producto(request.get_json(silent=True))
        repetido = db().execute("SELECT 1 FROM productos WHERE nombre = ?", (datos["nombre"],)).fetchone()
        if repetido:
            raise ReglaError("CRUD", "Ya existe un producto con ese nombre.", "nombre", 409)
        cur = db().execute(
            "INSERT INTO productos (nombre, categoria, precio, existencia, stock_minimo, activo) "
            "VALUES (:nombre, :categoria, :precio, :existencia, :stock_minimo, :activo)",
            datos,
        )
        db().commit()
        fila = db().execute("SELECT * FROM productos WHERE id = ?", (cur.lastrowid,)).fetchone()
        return jsonify(producto_dict(fila)), 201

    @app.patch("/api/productos/<int:pid>")
    def actualizar_producto(pid):
        fila = db().execute("SELECT * FROM productos WHERE id = ?", (pid,)).fetchone()
        if fila is None:
            raise ReglaError("CRUD", "El producto no existe.", None, 404)
        cambios = validar_producto(request.get_json(silent=True), parcial=True)
        if not cambios:
            raise ReglaError("CRUD", "No hay campos para actualizar.", None, 400)
        if "nombre" in cambios:
            repetido = db().execute(
                "SELECT 1 FROM productos WHERE nombre = ? AND id <> ?", (cambios["nombre"], pid)
            ).fetchone()
            if repetido:
                raise ReglaError("CRUD", "Ya existe un producto con ese nombre.", "nombre", 409)
        asignaciones = ", ".join("%s = :%s" % (campo, campo) for campo in cambios)
        cambios["id"] = pid
        db().execute("UPDATE productos SET " + asignaciones + " WHERE id = :id", cambios)
        db().commit()
        fila = db().execute("SELECT * FROM productos WHERE id = ?", (pid,)).fetchone()
        return jsonify(producto_dict(fila))

    @app.delete("/api/productos/<int:pid>")
    def eliminar_producto(pid):
        fila = db().execute("SELECT * FROM productos WHERE id = ?", (pid,)).fetchone()
        if fila is None:
            raise ReglaError("CRUD", "El producto no existe.", None, 404)
        con_ventas = db().execute("SELECT 1 FROM venta_items WHERE producto_id = ?", (pid,)).fetchone()
        if con_ventas:
            raise ReglaError(
                "CRUD", "No se puede eliminar: el producto tiene ventas registradas. Marcalo como inactivo.", None, 409
            )
        db().execute("DELETE FROM productos WHERE id = ?", (pid,))
        db().commit()
        return "", 204

    # ------------------------------------------------------------ transaccion
    def venta_dict(venta_id):
        venta = db().execute(
            "SELECT v.*, t.nombre AS tendero, c.nombre AS cliente FROM ventas v "
            "JOIN tenderos t ON t.id = v.tendero_id LEFT JOIN clientes c ON c.id = v.cliente_id WHERE v.id = ?",
            (venta_id,),
        ).fetchone()
        if venta is None:
            raise ReglaError("CRUD", "La venta no existe.", None, 404)
        items = db().execute(
            "SELECT i.producto_id, p.nombre, i.cantidad, i.precio_unitario, i.subtotal FROM venta_items i "
            "JOIN productos p ON p.id = i.producto_id WHERE i.venta_id = ?",
            (venta_id,),
        ).fetchall()
        pago = db().execute("SELECT * FROM pagos WHERE venta_id = ?", (venta_id,)).fetchone()
        d = dict(venta)
        d["items"] = [dict(i) for i in items]
        d["pago"] = dict(pago) if pago else None
        return d

    def descontar_inventario(items):
        for item in items:
            db().execute(
                "UPDATE productos SET existencia = existencia - ? WHERE id = ?",
                (item["cantidad"], item["producto_id"]),
            )

    @app.post("/api/ventas")
    def registrar_venta():
        datos = validar_venta(db(), request.get_json(silent=True))
        estado_venta, estado_pago = {
            "efectivo": ("confirmada", "verificado"),
            "transferencia": ("pendiente_pago_virtual", "pendiente"),
            "fiado": ("fiado_pendiente", "fiado"),
        }[datos["forma_pago"]]
        cur = db().execute(
            "INSERT INTO ventas (fecha, tendero_id, cliente_id, total, estado) VALUES (?, ?, ?, ?, ?)",
            (ahora(), datos["tendero_id"], datos["cliente_id"], datos["total"], estado_venta),
        )
        venta_id = cur.lastrowid
        for item in datos["items"]:
            db().execute(
                "INSERT INTO venta_items (venta_id, producto_id, cantidad, precio_unitario, subtotal) "
                "VALUES (?, ?, ?, ?, ?)",
                (venta_id, item["producto_id"], item["cantidad"], item["precio_unitario"], item["subtotal"]),
            )
        db().execute(
            "INSERT INTO pagos (venta_id, medio, monto, estado, efectivo_recibido, cambio) VALUES (?, ?, ?, ?, ?, ?)",
            (venta_id, datos["forma_pago"], datos["total"], estado_pago, datos["efectivo_recibido"], datos["cambio"]),
        )
        # R007: con pago por transferencia el inventario solo se descuenta al confirmar el ingreso.
        if estado_venta != "pendiente_pago_virtual":
            descontar_inventario(datos["items"])
        db().commit()
        return jsonify(venta_dict(venta_id)), 201

    @app.get("/api/ventas/<int:venta_id>")
    def obtener_venta(venta_id):
        return jsonify(venta_dict(venta_id))

    @app.patch("/api/ventas/<int:venta_id>/confirmar-pago")
    def confirmar_pago(venta_id):
        venta = db().execute("SELECT * FROM ventas WHERE id = ?", (venta_id,)).fetchone()
        if venta is None:
            raise ReglaError("CRUD", "La venta no existe.", None, 404)
        if venta["estado"] != "pendiente_pago_virtual":
            raise ReglaError("R007", "La venta no esta pendiente de confirmacion de pago virtual.", None, 409)
        lineas = db().execute(
            "SELECT producto_id, cantidad FROM venta_items WHERE venta_id = ?", (venta_id,)
        ).fetchall()
        calcular_items(db(), [{"producto_id": l["producto_id"], "cantidad": l["cantidad"]} for l in lineas])
        descontar_inventario([dict(l) for l in lineas])
        db().execute("UPDATE ventas SET estado = 'confirmada' WHERE id = ?", (venta_id,))
        db().execute("UPDATE pagos SET estado = 'confirmado' WHERE venta_id = ?", (venta_id,))
        db().commit()
        return jsonify(venta_dict(venta_id))

    return app


if __name__ == "__main__":
    create_app().run(debug=True)
