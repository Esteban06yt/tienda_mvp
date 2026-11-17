"""Datos de prueba: 2 tenderos demo, 12 clientes y 24 productos (algunos agotados o bajo el minimo)."""

TENDEROS = ["Tendero Demo 1", "Tendero Demo 2"]

CLIENTES = [
    ("Marta Gomez", "3001112201", 1),
    ("Luis Perez", "3001112202", 1),
    ("Ana Rojas", "3001112203", 1),
    ("Carlos Diaz", "3001112204", 0),
    ("Sofia Torres", "3001112205", 0),
    ("Jorge Ramirez", "3001112206", 1),
    ("Laura Castro", "3001112207", 0),
    ("Pedro Molina", "3001112208", 0),
    ("Diana Ortiz", "3001112209", 1),
    ("Camilo Vargas", "3001112210", 0),
    ("Paola Herrera", "3001112211", 0),
    ("Andres Silva", "3001112212", 1),
]

# nombre, categoria, precio, existencia, stock minimo
PRODUCTOS = [
    ("Gaseosa 1.5L", "Bebidas", 4500, 18, 6),
    ("Gaseosa 400ml", "Bebidas", 2000, 30, 10),
    ("Agua botella 600ml", "Bebidas", 1800, 25, 8),
    ("Jugo de caja 1L", "Bebidas", 3800, 3, 6),
    ("Cerveza lata", "Bebidas", 3200, 24, 12),
    ("Leche entera 1L", "Lacteos", 4200, 12, 8),
    ("Huevos unidad", "Lacteos", 450, 60, 30),
    ("Queso campesino 250g", "Lacteos", 6500, 0, 3),
    ("Pan tajado", "Panaderia", 5200, 8, 5),
    ("Pan unidad", "Panaderia", 300, 40, 20),
    ("Arroz 1kg", "Granos", 4300, 20, 10),
    ("Frijol 500g", "Granos", 5600, 2, 6),
    ("Lentejas 500g", "Granos", 4100, 10, 5),
    ("Azucar 1kg", "Abarrotes", 4600, 15, 8),
    ("Sal 500g", "Abarrotes", 1500, 18, 6),
    ("Aceite 1L", "Abarrotes", 11500, 6, 4),
    ("Cafe molido 250g", "Abarrotes", 9800, 9, 5),
    ("Panela unidad", "Abarrotes", 2800, 14, 6),
    ("Papel higienico x4", "Aseo", 6200, 11, 5),
    ("Jabon de barra", "Aseo", 2200, 0, 6),
    ("Detergente 500g", "Aseo", 5400, 7, 4),
    ("Galletas de sal", "Snacks", 1500, 22, 10),
    ("Papas fritas 40g", "Snacks", 2200, 16, 8),
    ("Chocolatina", "Snacks", 1800, 4, 10),
]


def sembrar(db):
    """Inserta los datos de prueba solo si las tablas estan vacias."""
    if db.execute("SELECT COUNT(*) FROM productos").fetchone()[0] == 0:
        db.executemany(
            "INSERT INTO productos (nombre, categoria, precio, existencia, stock_minimo) VALUES (?, ?, ?, ?, ?)",
            PRODUCTOS,
        )
    if db.execute("SELECT COUNT(*) FROM clientes").fetchone()[0] == 0:
        db.executemany("INSERT INTO clientes (nombre, telefono, es_de_confianza) VALUES (?, ?, ?)", CLIENTES)
    if db.execute("SELECT COUNT(*) FROM tenderos").fetchone()[0] == 0:
        db.executemany("INSERT INTO tenderos (nombre) VALUES (?)", [(t,) for t in TENDEROS])
    db.commit()
