# MVP Tienda de barrio: Registrar venta + CRUD de Producto

Proyecto grupal de Ingeniería de Software. Implementa dos pantallas ejecutables sobre el modelo de la tienda de barrio del Student Book:

- **Transacción (CU-01 Registrar venta, caso de uso estrella):** `/venta`
- **CRUD (CU-02 Gestionar productos, caso de uso secundario):** `/productos`

Stack: Python 3.10+, Flask y SQLite (sin servicios externos). La base de datos `tienda.db` se crea y se llena con datos de prueba la primera vez que se ejecuta.

## Cómo ejecutarlo

```bash
python -m venv .venv
source .venv/bin/activate          # En Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py                      # abre http://127.0.0.1:5000
```

cd C:\Users\esteb\Downloads\Tienda_MVP_Registrar_Venta\tienda_mvp
python app.py

Para empezar con la base de datos limpia, borra el archivo `tienda.db` y vuelve a ejecutar.

## Cómo correr las pruebas

```bash
python -m pytest -q
```

Hay 12 pruebas: 8 casos Given-When-Then de la transacción (`tests/test_ventas.py`) y 4 del CRUD (`tests/test_productos.py`).

## Datos de prueba (`seed.py`)

- 2 tenderos demo (no hay login: el tendero se elige en la pantalla de venta).
- 12 clientes (6 de confianza). Ejemplos: *Marta Gomez* (de confianza) y *Carlos Diaz* (no es de confianza).
- 24 productos en 6 categorías. Dos agotados (*Queso campesino 250g*, *Jabon de barra*) y varios bajo el stock mínimo (*Jugo de caja 1L*, *Frijol 500g*, *Chocolatina*).

> Los nombres de los datos de prueba están escritos sin tildes a propósito (el código fuente no usa tildes ni eñes).

## Reglas de negocio implementadas (`reglas.py`)

| Regla | Qué valida | Dónde se valida |
|---|---|---|
| R001 | El total se informa y confirma con el cliente antes de cobrar | Interfaz (el pago se habilita al confirmar el total) y backend (`total_confirmado` debe coincidir con el total calculado) |
| R003 | Todo pago en efectivo se verifica antes de aceptarse | Interfaz (casilla "Billete verificado") y backend |
| R005 | El fiado solo se autoriza a clientes de confianza | Backend (la interfaz exige elegir cliente) |
| R006 | No se vende más de lo que hay en existencia | Interfaz (cantidad máxima) y backend |
| R007 | Con transferencia la venta queda pendiente y el inventario no se descuenta hasta confirmar el pago | Backend (`PATCH /api/ventas/<id>/confirmar-pago`) |
| R008 | Toda venta registra el tendero y la fecha | Backend |

R006, R007 y R008 son reglas nuevas respecto a las reglas 001 a 005 del Student Book (agréguenlas allá si las usan). Las reglas 002 y 004 pertenecen a Compra y Devolución y quedan fuera de este MVP.

## API

| Método y ruta | Uso |
|---|---|
| `GET /api/productos?query=&page=&per_page=&activo=1` | Listar y buscar (paginado) |
| `POST /api/productos` | Crear producto |
| `GET`, `PATCH`, `DELETE /api/productos/<id>` | Consultar, actualizar y eliminar (no se elimina si ya tiene ventas) |
| `GET /api/clientes?query=` | Buscar clientes |
| `GET /api/tenderos` | Listar tenderos |
| `POST /api/ventas` | Registrar venta (valida R001, R003, R005, R006, R008) |
| `GET /api/ventas/<id>` | Ver comprobante |
| `PATCH /api/ventas/<id>/confirmar-pago` | Confirmar pago virtual (R007) |

Los errores devuelven JSON con `error`, `regla` y `campo`, y el código HTTP 422 (regla incumplida), 409 (conflicto) o 404.

## Trazabilidad (requisito, caso de uso, widget, endpoint, prueba)

| Requisito | Caso de uso | Widget | Endpoint | Prueba |
|---|---|---|---|---|
| RQ-013 Agregar productos a la venta | CU-01 | `#buscar-producto`, `#tabla-items` | `GET /api/productos` | humo manual |
| RQ-014 Existencia y precio | CU-01 | `#resultados-producto` | `GET /api/productos` | GWT2 |
| RQ-015 Calcular total | CU-01 | `#total` | `POST /api/ventas` | GWT1 |
| RQ-016 Total antes del pago (R001) | CU-01 | `#btn-confirmar-total` | `POST /api/ventas` | GWT6 |
| RQ-017 Forma de pago | CU-01 | `#grupo-pago` | `POST /api/ventas` | GWT1, GWT5, GWT7 |
| RQ-018 Verificar efectivo (R003) | CU-01 | `#billete-verificado` | `POST /api/ventas` | GWT3 |
| RQ-019 Calcular cambio | CU-01 | `#cambio` | `POST /api/ventas` | GWT1 |
| RQ-020 Pago virtual pendiente (R007) | CU-01 | `#btn-confirmar-pago` | `PATCH /api/ventas/<id>/confirmar-pago` | GWT7 |
| RQ-021 Fiado solo de confianza (R005) | CU-01 | `#buscar-cliente` | `POST /api/ventas` | GWT4, GWT5 |
| RQ-022 Registrar venta (R008) | CU-01 | `#btn-registrar` | `POST /api/ventas` | GWT1, GWT8 |
| RQ-023 Comprobante | CU-01 | `#comprobante` | `GET /api/ventas/<id>` | GWT1 |
| RQ-002 Descontar inventario | CU-01 | (automático) | `POST /api/ventas` | GWT1, GWT7 |
| RQ-033 Gestionar productos | CU-02 | formulario de `/productos` | `/api/productos` | pruebas del CRUD |

Fuera del MVP: RQ-034 (reporte bajo mínimo; la lista de productos solo marca los productos bajo el mínimo) y RQ-035 (cuadre de caja).

## Estructura

```
app.py          rutas y acceso a datos (SQLite)
reglas.py       reglas de negocio y validaciones
seed.py         datos de prueba
templates/      base.html, venta.html, productos.html
static/         app.css, venta.js, productos.js
tests/          pruebas Given-When-Then
```

## Limitaciones conocidas

- No hay autenticación: el tendero se elige en la pantalla.
- No hay cuadre de caja ni módulos de Compra y Devolución (fuera del alcance del MVP).
- La confirmación del total (R001) se valida comparando el valor enviado con el calculado por el servidor; no registra quién lo confirmó.
