(function () {
  "use strict";

  var estado = { pagina: 1, paginas: 1, consulta: "" };
  var peso = new Intl.NumberFormat("es-CO", { style: "currency", currency: "COP", maximumFractionDigits: 0 });
  var CAMPOS = ["nombre", "categoria", "precio", "existencia", "stock_minimo"];

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
  function limpiarErrores() {
    CAMPOS.forEach(function (c) { $("e-" + c).textContent = ""; });
    $("alerta").hidden = true;
  }

  function cargar() {
    var url = "/api/productos?per_page=8&page=" + estado.pagina + "&query=" + encodeURIComponent(estado.consulta);
    api(url).then(function (r) {
      var cuerpo = $("cuerpo");
      vaciar(cuerpo);
      estado.paginas = r.datos.pages;
      $("vacio").hidden = r.datos.items.length > 0;
      r.datos.items.forEach(function (p) {
        var fila = el("tr");
        fila.appendChild(el("td", p.nombre));
        fila.appendChild(el("td", p.categoria || "-"));
        fila.appendChild(el("td", peso.format(p.precio)));
        var celdaExistencia = el("td", String(p.existencia));
        if (p.existencia === 0) { celdaExistencia.appendChild(el("span", "Agotado", "insignia")); }
        else if (p.bajo_minimo) { celdaExistencia.appendChild(el("span", "Bajo minimo", "insignia")); }
        fila.appendChild(celdaExistencia);
        fila.appendChild(el("td", String(p.stock_minimo)));
        fila.appendChild(el("td", p.activo ? "Activo" : "Inactivo"));
        var acciones = el("td");
        var editar = el("button", "Editar");
        editar.type = "button";
        editar.addEventListener("click", function () { editarProducto(p); });
        var borrar = el("button", "Eliminar", "peligro");
        borrar.type = "button";
        borrar.addEventListener("click", function () { eliminar(p); });
        acciones.appendChild(editar);
        acciones.appendChild(borrar);
        fila.appendChild(acciones);
        cuerpo.appendChild(fila);
      });
      $("pagina").textContent = "Pagina " + r.datos.page + " de " + r.datos.pages + " (" + r.datos.total + " productos)";
      $("anterior").disabled = r.datos.page <= 1;
      $("siguiente").disabled = r.datos.page >= r.datos.pages;
    });
  }

  function limpiarFormulario() {
    limpiarErrores();
    $("f-id").value = "";
    CAMPOS.forEach(function (c) { $("f-" + c).value = ""; });
    $("f-activo").checked = true;
    $("titulo-form").textContent = "Nuevo producto";
  }

  function editarProducto(p) {
    limpiarErrores();
    $("f-id").value = String(p.id);
    $("f-nombre").value = p.nombre;
    $("f-categoria").value = p.categoria || "";
    $("f-precio").value = String(p.precio);
    $("f-existencia").value = String(p.existencia);
    $("f-stock_minimo").value = String(p.stock_minimo);
    $("f-activo").checked = p.activo;
    $("titulo-form").textContent = "Editar producto " + p.id;
  }

  function leerNumero(id) {
    var valor = $(id).value.trim();
    return valor === "" ? null : Number(valor);
  }

  function guardar(evento) {
    evento.preventDefault();
    limpiarErrores();
    var cuerpo = {
      nombre: $("f-nombre").value,
      categoria: $("f-categoria").value,
      precio: leerNumero("f-precio"),
      existencia: leerNumero("f-existencia"),
      stock_minimo: leerNumero("f-stock_minimo"),
      activo: $("f-activo").checked
    };
    var id = $("f-id").value;
    var url = id ? "/api/productos/" + id : "/api/productos";
    api(url, { method: id ? "PATCH" : "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(cuerpo) })
      .then(function (r) {
        if (!r.ok) {
          var caja = r.datos.campo ? $("e-" + r.datos.campo) : null;
          if (caja) { caja.textContent = r.datos.error; } else { alerta(r.datos.error); }
          return;
        }
        alerta(id ? "Producto actualizado." : "Producto creado.", true);
        limpiarFormulario();
        cargar();
      });
  }

  function eliminar(p) {
    if (!window.confirm("Eliminar el producto " + p.nombre + "?")) { return; }
    limpiarErrores();
    api("/api/productos/" + p.id, { method: "DELETE" }).then(function (r) {
      if (!r.ok) { alerta(r.datos.error); return; }
      alerta("Producto eliminado.", true);
      cargar();
    });
  }

  $("filtro").addEventListener("input", debounce(function () {
    estado.consulta = $("filtro").value.trim();
    estado.pagina = 1;
    cargar();
  }, 250));
  $("anterior").addEventListener("click", function () { if (estado.pagina > 1) { estado.pagina -= 1; cargar(); } });
  $("siguiente").addEventListener("click", function () { if (estado.pagina < estado.paginas) { estado.pagina += 1; cargar(); } });
  $("form").addEventListener("submit", guardar);
  $("cancelar").addEventListener("click", limpiarFormulario);
  cargar();
})();
