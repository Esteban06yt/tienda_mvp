(function () {
  "use strict";

  var estado = { items: [], totalConfirmado: null, cliente: null, ventaActual: null };
  var peso = new Intl.NumberFormat("es-CO", { style: "currency", currency: "COP", maximumFractionDigits: 0 });

  function $(id) { return document.getElementById(id); }
  function el(tag, texto, clase) {
    var nodo = document.createElement(tag);
    if (texto !== undefined && texto !== null) { nodo.textContent = texto; }
    if (clase) { nodo.className = clase; }
    return nodo;
  }
  function vaciar(nodo) { while (nodo.firstChild) { nodo.removeChild(nodo.firstChild); } }
  function debounce(fn, ms) {
    var t;
    return function () { var a = arguments; clearTimeout(t); t = setTimeout(function () { fn.apply(null, a); }, ms); };
  }
  function api(url, opciones) {
    return fetch(url, opciones).then(function (r) {
      if (r.status === 204) { return { ok: true, status: 204, datos: null }; }
      return r.json().then(function (datos) { return { ok: r.ok, status: r.status, datos: datos }; });
    });
  }
  function alerta(texto, ok) {
    var caja = $("alerta");
    caja.textContent = texto;
    caja.className = ok ? "alerta ok" : "alerta";
    caja.hidden = false;
  }
  function ocultarAlerta() { $("alerta").hidden = true; }

  function total() {
    return estado.items.reduce(function (suma, i) { return suma + i.precio * i.cantidad; }, 0);
  }

  // ---------------------------------------------------------------- productos
  function buscarProductos() {
    var q = $("buscar-producto").value.trim();
    api("/api/productos?activo=1&per_page=8&query=" + encodeURIComponent(q)).then(function (r) {
      var lista = $("resultados-producto");
      vaciar(lista);
      $("vacio-busqueda").hidden = r.datos.items.length > 0;
      r.datos.items.forEach(function (p) {
        var li = el("li");
        var info = el("span", p.nombre + " - " + peso.format(p.precio) + " (existencia: " + p.existencia + ")");
        if (p.existencia === 0) { info.appendChild(el("span", "Agotado", "insignia")); }
        else if (p.bajo_minimo) { info.appendChild(el("span", "Bajo minimo", "insignia")); }
        var boton = el("button", "Agregar");
        boton.type = "button";
        boton.disabled = p.existencia === 0;
        boton.addEventListener("click", function () { agregar(p); });
        li.appendChild(info);
        li.appendChild(boton);
        lista.appendChild(li);
      });
    });
  }

  function agregar(p) {
    ocultarAlerta();
    var existente = estado.items.filter(function (i) { return i.producto_id === p.id; })[0];
    if (existente) {
      if (existente.cantidad >= p.existencia) {
        alerta("No hay existencia suficiente de " + p.nombre + " (disponible: " + p.existencia + ").");
        return;
      }
      existente.cantidad += 1;
    } else {
      estado.items.push({ producto_id: p.id, nombre: p.nombre, precio: p.precio, existencia: p.existencia, cantidad: 1 });
    }
    invalidarTotal();
    pintarItems();
  }

  function pintarItems() {
    var cuerpo = $("cuerpo-items");
    vaciar(cuerpo);
    $("vacio-items").hidden = estado.items.length > 0;
    estado.items.forEach(function (i, indice) {
      var fila = el("tr");
      fila.appendChild(el("td", i.nombre));
      fila.appendChild(el("td", peso.format(i.precio)));
      var celda = el("td");
      var campo = el("input");
      campo.type = "number";
      campo.min = "1";
      campo.max = String(i.existencia);
      campo.value = String(i.cantidad);
      campo.addEventListener("change", function () {
        var n = parseInt(campo.value, 10);
        if (isNaN(n) || n < 1) { n = 1; }
        if (n > i.existencia) {
          alerta("No hay existencia suficiente de " + i.nombre + " (disponible: " + i.existencia + ").");
          n = i.existencia;
        }
        i.cantidad = n;
        invalidarTotal();
        pintarItems();
      });
      celda.appendChild(campo);
      fila.appendChild(celda);
      fila.appendChild(el("td", peso.format(i.precio * i.cantidad)));
      var quitar = el("td");
      var boton = el("button", "Quitar", "peligro");
      boton.type = "button";
      boton.addEventListener("click", function () {
        estado.items.splice(indice, 1);
        invalidarTotal();
        pintarItems();
      });
      quitar.appendChild(boton);
      fila.appendChild(quitar);
      cuerpo.appendChild(fila);
    });
    $("total").textContent = peso.format(total());
    $("btn-confirmar-total").disabled = estado.items.length === 0;
  }

  // ---------------------------------------------------------------- R001 total confirmado
  function invalidarTotal() {
    estado.totalConfirmado = null;
    $("estado-total").textContent = "";
    actualizarPago();
  }

  function confirmarTotal() {
    ocultarAlerta();
    estado.totalConfirmado = total();
    $("estado-total").textContent = "Total confirmado con el cliente: " + peso.format(estado.totalConfirmado);
    actualizarPago();
  }

  // ---------------------------------------------------------------- pago
  function formaPago() {
    return document.querySelector("input[name=forma]:checked").value;
  }

  function actualizarPago() {
    var habilitado = estado.totalConfirmado !== null && estado.items.length > 0;
    $("grupo-pago").disabled = !habilitado;
    $("ayuda-pago").hidden = habilitado;
    var forma = formaPago();
    $("bloque-efectivo").hidden = forma !== "efectivo";
    $("nota-transferencia").hidden = forma !== "transferencia";
    $("nota-fiado").hidden = forma !== "fiado";
    var cambio = "";
    if (forma === "efectivo" && habilitado) {
      var recibido = parseInt($("efectivo-recibido").value, 10);
      if (!isNaN(recibido)) {
        cambio = recibido >= estado.totalConfirmado
          ? "Cambio a devolver: " + peso.format(recibido - estado.totalConfirmado)
          : "El efectivo recibido es menor al total.";
      }
    }
    $("cambio").textContent = cambio;
    $("btn-registrar").disabled = !habilitado;
  }

  // ---------------------------------------------------------------- cliente
  function buscarClientes() {
    var q = $("buscar-cliente").value.trim();
    var lista = $("resultados-cliente");
    vaciar(lista);
    if (q.length < 2) { return; }
    api("/api/clientes?query=" + encodeURIComponent(q)).then(function (r) {
      if (r.datos.length === 0) { lista.appendChild(el("li", "Sin resultados para el cliente buscado.", "vacio")); }
      r.datos.forEach(function (c) {
        var li = el("li");
        li.appendChild(el("span", c.nombre + " - " + c.telefono + (c.es_de_confianza ? " (de confianza)" : "")));
        var boton = el("button", "Elegir");
        boton.type = "button";
        boton.addEventListener("click", function () {
          estado.cliente = c;
          $("cliente-elegido").textContent = "Cliente: " + c.nombre + (c.es_de_confianza ? " (de confianza)" : " (no es de confianza)");
          vaciar(lista);
          $("buscar-cliente").value = "";
        });
        li.appendChild(boton);
        lista.appendChild(li);
      });
    });
  }

  // ---------------------------------------------------------------- registrar
  function registrar() {
    ocultarAlerta();
    var forma = formaPago();
    var cuerpo = {
      tendero_id: parseInt($("tendero").value, 10) || null,
      cliente_id: estado.cliente ? estado.cliente.id : null,
      items: estado.items.map(function (i) { return { producto_id: i.producto_id, cantidad: i.cantidad }; }),
      total_confirmado: estado.totalConfirmado,
      forma_pago: forma
    };
    if (forma === "efectivo") {
      cuerpo.billete_verificado = $("billete-verificado").checked;
      var recibido = parseInt($("efectivo-recibido").value, 10);
      cuerpo.efectivo_recibido = isNaN(recibido) ? null : recibido;
    }
    api("/api/ventas", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(cuerpo) })
      .then(function (r) {
        if (!r.ok) {
          alerta("[" + r.datos.regla + "] " + r.datos.error);
          return;
        }
        mostrarComprobante(r.datos);
        alerta("Venta " + r.datos.id + " registrada.", true);
      });
  }

  function mostrarComprobante(venta) {
    estado.ventaActual = venta;
    $("comprobante").hidden = false;
    var caja = $("comprobante-detalle");
    vaciar(caja);
    caja.appendChild(el("p", "Venta No. " + venta.id + " - " + venta.fecha));
    caja.appendChild(el("p", "Tendero: " + venta.tendero + (venta.cliente ? " | Cliente: " + venta.cliente : "")));
    var tabla = el("table");
    venta.items.forEach(function (i) {
      var fila = el("tr");
      fila.appendChild(el("td", i.cantidad + " x " + i.nombre));
      fila.appendChild(el("td", peso.format(i.subtotal)));
      tabla.appendChild(fila);
    });
    caja.appendChild(tabla);
    caja.appendChild(el("p", "Total: " + peso.format(venta.total), "total"));
    var pago = venta.pago;
    var texto = "Pago: " + pago.medio + " (" + pago.estado + ")";
    if (pago.medio === "efectivo") { texto += " | Recibido: " + peso.format(pago.efectivo_recibido) + " | Cambio: " + peso.format(pago.cambio); }
    caja.appendChild(el("p", texto));
    caja.appendChild(el("p", "Estado de la venta: " + venta.estado, "nota"));
    $("btn-confirmar-pago").hidden = venta.estado !== "pendiente_pago_virtual";
    reiniciarFormulario();
    buscarProductos();
  }

  function confirmarPagoVirtual() {
    ocultarAlerta();
    api("/api/ventas/" + estado.ventaActual.id + "/confirmar-pago", { method: "PATCH" }).then(function (r) {
      if (!r.ok) { alerta("[" + r.datos.regla + "] " + r.datos.error); return; }
      mostrarComprobante(r.datos);
      alerta("Pago confirmado. El inventario fue descontado.", true);
    });
  }

  function reiniciarFormulario() {
    estado.items = [];
    estado.totalConfirmado = null;
    estado.cliente = null;
    $("cliente-elegido").textContent = "";
    $("efectivo-recibido").value = "";
    $("billete-verificado").checked = false;
    $("estado-total").textContent = "";
    document.querySelector("input[name=forma][value=efectivo]").checked = true;
    pintarItems();
    actualizarPago();
  }

  // ---------------------------------------------------------------- inicio
  function iniciar() {
    api("/api/tenderos").then(function (r) {
      var select = $("tendero");
      r.datos.forEach(function (t) {
        var opcion = el("option", t.nombre);
        opcion.value = String(t.id);
        select.appendChild(opcion);
      });
    });
    $("buscar-producto").addEventListener("input", debounce(buscarProductos, 250));
    $("buscar-cliente").addEventListener("input", debounce(buscarClientes, 250));
    $("btn-confirmar-total").addEventListener("click", confirmarTotal);
    $("btn-registrar").addEventListener("click", registrar);
    $("btn-confirmar-pago").addEventListener("click", confirmarPagoVirtual);
    $("btn-nueva").addEventListener("click", function () { $("comprobante").hidden = true; ocultarAlerta(); });
    Array.prototype.forEach.call(document.querySelectorAll("input[name=forma]"), function (r) {
      r.addEventListener("change", actualizarPago);
    });
    $("efectivo-recibido").addEventListener("input", actualizarPago);
    pintarItems();
    actualizarPago();
    buscarProductos();
  }

  iniciar();
})();
