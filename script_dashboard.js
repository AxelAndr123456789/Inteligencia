// Verificar sesión
if (!sessionStorage.getItem('qbd_admin')) {
  window.location.href = 'login.html';
}

const API = 'https://inteligencia.onrender.com';

// Fecha actual
const meses = ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'];
const hoy = new Date();
document.getElementById('fechaActual').textContent = `${hoy.getDate()} de ${meses[hoy.getMonth()]} ${hoy.getFullYear()}`;

// Logout
document.getElementById('btnLogout').addEventListener('click', () => {
  sessionStorage.removeItem('qbd_admin');
  window.location.href = 'login.html';
});

// Navegación sidebar
const seccionesCargadas = {};



function initSeccion(sid) {
  if (!seccionesCargadas[sid]) {
    seccionesCargadas[sid] = true;
    if (sid === 'ventas' && metricasData) actualizarGraficoVentas(metricasData.ventas_fm_pt_mes);
    else if (sid === 'sedes' && metricasData) actualizarGraficoSedes(metricasData.ventas_sede_resumen);
    else if (sid === 'productos') cargarGraficosProductos();
    else if (sid === 'clientes') {
        cargarGraficosClientes().then(() => window.dispatchEvent(new Event('resize')));
    }
    else if (sid === 'prediccion') cargarGraficoPrediccion();
  }
  window.dispatchEvent(new Event('resize'));
}

document.querySelectorAll('.nav-item').forEach(item => {
  item.addEventListener('click', (e) => {
    e.preventDefault();
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    item.classList.add('active');
    const sid = item.dataset.section;
    document.getElementById(sid).classList.add('active');

    function run() {
      setTimeout(() => initSeccion(sid), 50);
    }

    if ((sid === 'ventas' || sid === 'sedes') && !metricasLoaded) {
      const w = setInterval(() => { if (metricasLoaded) { clearInterval(w); run(); } }, 100);
    } else {
      run();
    }
  });
});

// Menú móvil
document.getElementById('menuToggle').addEventListener('click', () => {
  document.getElementById('sidebar').classList.toggle('open');
});

// Tabs CRUD
document.querySelectorAll('.crud-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.crud-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.crud-table-container').forEach(c => c.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById(tab.dataset.tab).classList.add('active');
  });
});

// ====== CARGAR MÉTRICAS REALES ======
let metricasData = null;
let metricasLoaded = false;

async function cargarMetricas() {
  try {
    const res = await fetch(`${API}/api/metricas`);
    metricasData = await res.json();
    metricasLoaded = true;
    
    document.getElementById('kpiIngresos').textContent = `S/ ${metricasData.ingresos_totales.toLocaleString()}`;
    document.getElementById('kpiFM').textContent = `S/ ${metricasData.ingresos_fm.toLocaleString()}`;
    document.getElementById('kpiPT').textContent = `S/ ${metricasData.ingresos_pt.toLocaleString()}`;
    document.getElementById('kpiStock').textContent = `${metricasData.stock_total} unidades`;
    
    document.getElementById('kpiCountProd').textContent = metricasData.total_productos;
    document.getElementById('kpiCountForm').textContent = metricasData.total_formulas;
    document.getElementById('kpiCountCli').textContent = metricasData.total_clientes;
    document.getElementById('kpiCountMed').textContent = metricasData.total_medicos;
    
    actualizarGraficos(metricasData);
  } catch (error) {
    console.error('Error cargando métricas:', error);
    document.getElementById('kpiIngresos').textContent = 'Error de conexión';
  }
}

let chartParticipacion, chartSedeResumen, chartVentasMes, chartSedesMes;

function actualizarGraficos(data) {
  // Destruir gráficos anteriores
  if (chartParticipacion) chartParticipacion.destroy();
  if (chartSedeResumen) chartSedeResumen.destroy();
  
  chartParticipacion = new Chart(document.getElementById('chartParticipacion'), {
    type: 'doughnut',
    data: {
      labels: ['Fórmulas Magistrales', 'Productos Terminados'],
      datasets: [{
        data: [data.ingresos_fm, data.ingresos_pt],
        backgroundColor: ['#0d7a3e', '#f59e0b'],
        borderWidth: 0
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { position: 'bottom', labels: { font: { family: 'Poppins' } } } }
    }
  });
  
  const totalJuliaca = data.juliaca_total;
  const totalPuno = data.puno_total;
  const total = totalJuliaca + totalPuno || 1;
  
  chartSedeResumen = new Chart(document.getElementById('chartSedeResumen'), {
    type: 'doughnut',
    data: {
      labels: ['Juliaca', 'Puno'],
      datasets: [{
        data: [totalJuliaca, totalPuno],
        backgroundColor: ['#1e40af', '#f43f5e'],
        borderWidth: 0
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { position: 'bottom', labels: { font: { family: 'Poppins' } } } }
    }
  });
}

function actualizarGraficoVentas(ventasFmPtMes) {
  if (chartVentasMes) chartVentasMes.destroy();
  
  const labels = ventasFmPtMes.map(v => v.mes);
  const datosFM = ventasFmPtMes.map(v => v.fm);
  const datosPT = ventasFmPtMes.map(v => v.pt);
  
  chartVentasMes = new Chart(document.getElementById('chartVentasMensuales'), {
    type: 'line',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Fórmulas Magistrales',
          data: datosFM,
          borderColor: '#0d7a3e',
          backgroundColor: '#0d7a3e20',
          fill: true,
          tension: 0.4,
          borderWidth: 3
        },
        {
          label: 'Productos Terminados',
          data: datosPT,
          borderColor: '#f59e0b',
          backgroundColor: '#f59e0b20',
          fill: true,
          tension: 0.4,
          borderWidth: 3
        }
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { position: 'top', labels: { font: { family: 'Poppins' } } } },
      scales: { y: { beginAtZero: true, ticks: { callback: v => 'S/ ' + v.toLocaleString() } } }
    }
  });
}

function actualizarGraficoSedes(ventasSedeResumen) {
  if (chartSedesMes) chartSedesMes.destroy();
  
  const labels = ventasSedeResumen.map(v => v.sede);
  const datosFM = ventasSedeResumen.map(v => v.fm);
  const datosPT = ventasSedeResumen.map(v => v.pt);
  
  chartSedesMes = new Chart(document.getElementById('chartSedes'), {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Fórmulas Magistrales',
          data: datosFM,
          backgroundColor: '#0d7a3e',
          borderRadius: 6
        },
        {
          label: 'Productos Terminados',
          data: datosPT,
          backgroundColor: '#f59e0b',
          borderRadius: 6
        }
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { position: 'top', labels: { font: { family: 'Poppins', size: 11 } } } },
      scales: {
        y: { beginAtZero: true, ticks: { callback: v => 'S/ ' + v.toLocaleString() } },
        x: { ticks: { font: { size: 10 }, maxRotation: 0, autoSkip: true } }
      }
    }
  });
}

// ====== CRUD FUNCTIONS ======

// Cargar Productos
async function cargarProductos() {
  const res = await fetch(`${API}/api/productos`);
  const data = await res.json();
  const tbody = document.getElementById('tbodyProductos');
  tbody.innerHTML = data.map(p => `
    <tr>
      <td><strong>${p.CodProducto}</strong></td>
      <td>${p.DescripcionPT}</td>
      <td>${p.DescripcionUso || '-'}</td>
      <td>${p.UnidadMedidaPT}</td>
      <td>S/ ${p.CostoUnitarioPT}</td>
      <td>${p.StockPT}</td>
      <td><span class="estado-${p.EstadoPT.toLowerCase()}">${p.EstadoPT}</span></td>
      <td>
        <button class="btn-accion btn-editar" onclick="editarProducto('${p.CodProducto}')">Editar</button>
        <button class="btn-accion btn-eliminar" onclick="eliminarProducto('${p.CodProducto}')">Eliminar</button>
      </td>
    </tr>
  `).join('');
}

// Cargar Fórmulas
async function cargarFormulas() {
  const res = await fetch(`${API}/api/formulas`);
  const data = await res.json();
  const tbody = document.getElementById('tbodyFormulas');
  tbody.innerHTML = data.map(f => `
    <tr>
      <td><strong>${f.CodFormula}</strong></td>
      <td>${f.DescripcionFM}</td>
      <td>${f.UnidadMedidaFM}</td>
      <td>S/ ${f.CostoUnitarioFM}</td>
      <td><span class="estado-${f.EstadoFM.toLowerCase()}">${f.EstadoFM}</span></td>
      <td>
        <button class="btn-accion btn-editar" onclick="editarFormula('${f.CodFormula}')">Editar</button>
        <button class="btn-accion btn-eliminar" onclick="eliminarFormula('${f.CodFormula}')">Eliminar</button>
      </td>
    </tr>
  `).join('');
}

// Cargar Clientes
async function cargarClientes() {
  const res = await fetch(`${API}/api/clientes`);
  const data = await res.json();
  const tbody = document.getElementById('tbodyClientes');
  tbody.innerHTML = data.map(c => `
    <tr>
      <td>${c.ClienteKey}</td>
      <td>${c.DniCliente}</td>
      <td>${c.NombresC}</td>
      <td>${c.ApellidosC}</td>
      <td>${c.CelularC || '-'}</td>
      <td>
        <button class="btn-accion btn-editar" onclick="editarCliente(${c.ClienteKey})">Editar</button>
        <button class="btn-accion btn-eliminar" onclick="eliminarCliente(${c.ClienteKey})">Eliminar</button>
      </td>
    </tr>
  `).join('');
}

// Cargar Médicos
async function cargarMedicos() {
  const res = await fetch(`${API}/api/medicos`);
  const data = await res.json();
  const tbody = document.getElementById('tbodyMedicos');
  tbody.innerHTML = data.map(m => `
    <tr>
      <td>${m.MedicoKey}</td>
      <td>${m.ColegiaturaMedico}</td>
      <td>${m.NombresM}</td>
      <td>${m.ApellidosM}</td>
      <td>${m.CelularM || '-'}</td>
      <td><span class="estado-${m.EstadoM.toLowerCase()}">${m.EstadoM}</span></td>
      <td>
        <button class="btn-accion btn-editar" onclick="editarMedico(${m.MedicoKey})">Editar</button>
        <button class="btn-accion btn-eliminar" onclick="eliminarMedico(${m.MedicoKey})">Eliminar</button>
      </td>
    </tr>
  `).join('');
}

// Cargar Sedes
async function cargarSedes() {
  const res = await fetch(`${API}/api/sedes`);
  const data = await res.json();
  const tbody = document.getElementById('tbodySedes');
  tbody.innerHTML = data.map(s => `
    <tr>
      <td>${s.SedeKey}</td>
      <td>${s.NombreSede}</td>
      <td>${s.Ciudad}</td>
      <td>${s.Direccion}</td>
      <td>${s.Region}</td>
      <td>
        <button class="btn-accion btn-editar" onclick="editarSede(${s.SedeKey})">Editar</button>
        <button class="btn-accion btn-eliminar" onclick="eliminarSede(${s.SedeKey})">Eliminar</button>
      </td>
    </tr>
  `).join('');
}

// Cargar Ventas
async function cargarVentas() {
  const res = await fetch(`${API}/api/ventas`);
  const data = await res.json();
  const tbody = document.getElementById('tbodyVentas');
  tbody.innerHTML = data.map(v => `
    <tr>
      <td><strong>${v.CodVenta}</strong></td>
      <td><span class="badge-${v.Tipo.toLowerCase()}">${v.Tipo}</span></td>
      <td>${v.Producto}</td>
      <td>${v.Cliente}</td>
      <td>${v.Sede}</td>
      <td>${v.Cantidad}</td>
      <td>S/ ${v.SubTotal}</td>
      <td>
        <button class="btn-accion btn-editar" onclick="editarVenta('${v.CodVenta}','${v.Tipo}')">Editar</button>
        <button class="btn-accion btn-eliminar" onclick="eliminarVenta('${v.CodVenta}','${v.Tipo}')">Eliminar</button>
      </td>
    </tr>
  `).join('');
}

// ====== MODAL FUNCTIONS ======
let editando = false;
let tipoActual = '';

function abrirModal(tipo, datos = null) {
  tipoActual = tipo;
  editando = datos !== null;
  const overlay = document.getElementById('modalOverlay');
  const titulo = document.getElementById('modalTitulo');
  const form = document.getElementById('modalForm');
  
  titulo.textContent = editando ? `Editar ${tipo}` : `Nuevo ${tipo}`;
  
  const formularios = {
    producto: `
      <div class="form-group"><label>Código</label><input type="text" id="fCod" ${editando ? 'readonly' : ''} required></div>
      <div class="form-group"><label>Descripción</label><input type="text" id="fDesc" required></div>
      <div class="form-group"><label>Uso</label><textarea id="fUso" rows="3"></textarea></div>
      <div class="form-group"><label>Unidad</label><input type="text" id="fUnidad" required></div>
      <div class="form-group"><label>Precio (S/)</label><input type="number" step="0.01" id="fPrecio" required></div>
      <div class="form-group"><label>Stock</label><input type="number" id="fStock" required></div>
      <div class="form-group"><label>Estado</label><select id="fEstado"><option>Activo</option><option>Inactivo</option><option>Agotado</option></select></div>
    `,
    formula: `
      <div class="form-group"><label>Código</label><input type="text" id="fCod" ${editando ? 'readonly' : ''} required></div>
      <div class="form-group"><label>Descripción</label><input type="text" id="fDesc" required></div>
      <div class="form-group"><label>Unidad</label><input type="text" id="fUnidad" required></div>
      <div class="form-group"><label>Precio (S/)</label><input type="number" step="0.01" id="fPrecio" required></div>
      <div class="form-group"><label>Estado</label><select id="fEstado"><option>Activo</option><option>Inactivo</option></select></div>
    `,
    cliente: `
      <div class="form-group"><label>Key</label><input type="number" id="fKey" ${editando ? 'readonly' : ''} required></div>
      <div class="form-group"><label>DNI</label><input type="text" id="fDni" maxlength="8" required></div>
      <div class="form-group"><label>Nombres</label><input type="text" id="fNombres" required></div>
      <div class="form-group"><label>Apellidos</label><input type="text" id="fApellidos" required></div>
      <div class="form-group"><label>Celular</label><input type="text" id="fCelular" maxlength="9"></div>
    `,
    medico: `
      <div class="form-group"><label>Key</label><input type="number" id="fKey" ${editando ? 'readonly' : ''} required></div>
      <div class="form-group"><label>Colegiatura</label><input type="text" id="fColegiatura" required></div>
      <div class="form-group"><label>Nombres</label><input type="text" id="fNombres" required></div>
      <div class="form-group"><label>Apellidos</label><input type="text" id="fApellidos" required></div>
      <div class="form-group"><label>Celular</label><input type="text" id="fCelular" maxlength="9"></div>
      <div class="form-group"><label>Estado</label><select id="fEstado"><option>Activo</option><option>Inactivo</option></select></div>
    `,
    sede: `
      <div class="form-group"><label>Key</label><input type="number" id="fKey" ${editando ? 'readonly' : ''} required></div>
      <div class="form-group"><label>Nombre</label><input type="text" id="fNombre" required></div>
      <div class="form-group"><label>Ciudad</label><input type="text" id="fCiudad" required></div>
      <div class="form-group"><label>Direccion</label><input type="text" id="fDireccion" required></div>
      <div class="form-group"><label>Region</label><input type="text" id="fRegion" required></div>
    `,
    venta: `
      <div class="form-group"><label>Codigo Venta</label><input type="text" id="fCodVenta" placeholder="VFM-031" required></div>
      <div class="form-group"><label>Tipo</label><select id="fTipoVenta"><option value="FM">Formula Magistral</option><option value="PT">Producto Terminado</option></select></div>
      <div class="form-group"><label>Producto / Formula</label><select id="fCodProdFM"><option value="">Cargando...</option></select></div>
      <div class="form-group"><label>Fecha</label><select id="fFechaKey"><option value="">Cargando...</option></select></div>
      <div class="form-group"><label>Cliente</label><select id="fClienteKey"><option value="">Cargando...</option></select></div>
      <div class="form-group"><label>Sede</label><select id="fSedeKey"><option value="">Cargando...</option></select></div>
      <div class="form-group"><label>Medico</label><select id="fMedicoKey"><option value="">Cargando...</option></select></div>
      <div class="form-group"><label>Medidas</label><input type="text" id="fMedidas" placeholder="Ej: 50g, 100ml"></div>
      <div class="form-group"><label>Cantidad</label><input type="number" id="fCantidad" min="1" required></div>
      <div class="form-group"><label>Precio Unitario (S/)</label><input type="number" step="0.01" id="fCostoUnit" required></div>
    `
  };
  
  form.innerHTML = formularios[tipo] + `
    <div class="form-actions">
      <button type="button" class="btn-cancelar" onclick="cerrarModal()">Cancelar</button>
      <button type="submit" class="btn-guardar">${editando ? 'Actualizar' : 'Guardar'}</button>
    </div>
  `;

  if (tipo === 'venta') {
    setTimeout(() => cargarDropdownsVenta(editando ? datos : null), 100);
  }
  
  if (datos) {
    setTimeout(() => {
      if (tipo === 'producto') {
        document.getElementById('fCod').value = datos.CodProducto || '';
        document.getElementById('fDesc').value = datos.DescripcionPT || '';
        document.getElementById('fUso').value = datos.DescripcionUso || '';
        document.getElementById('fUnidad').value = datos.UnidadMedidaPT || '';
        document.getElementById('fPrecio').value = datos.CostoUnitarioPT || '';
        document.getElementById('fStock').value = datos.StockPT || '';
        document.getElementById('fEstado').value = datos.EstadoPT || 'Activo';
      } else if (tipo === 'formula') {
        document.getElementById('fCod').value = datos.CodFormula || '';
        document.getElementById('fDesc').value = datos.DescripcionFM || '';
        document.getElementById('fUnidad').value = datos.UnidadMedidaFM || '';
        document.getElementById('fPrecio').value = datos.CostoUnitarioFM || '';
        document.getElementById('fEstado').value = datos.EstadoFM || 'Activo';
      } else if (tipo === 'cliente') {
        document.getElementById('fKey').value = datos.ClienteKey || '';
        document.getElementById('fDni').value = datos.DniCliente || '';
        document.getElementById('fNombres').value = datos.NombresC || '';
        document.getElementById('fApellidos').value = datos.ApellidosC || '';
        document.getElementById('fCelular').value = datos.CelularC || '';
      } else if (tipo === 'medico') {
        document.getElementById('fKey').value = datos.MedicoKey || '';
        document.getElementById('fColegiatura').value = datos.ColegiaturaMedico || '';
        document.getElementById('fNombres').value = datos.NombresM || '';
        document.getElementById('fApellidos').value = datos.ApellidosM || '';
        document.getElementById('fCelular').value = datos.CelularM || '';
        document.getElementById('fEstado').value = datos.EstadoM || 'Activo';
      } else if (tipo === 'sede') {
        document.getElementById('fKey').value = datos.SedeKey || '';
        document.getElementById('fNombre').value = datos.NombreSede || '';
        document.getElementById('fCiudad').value = datos.Ciudad || '';
        document.getElementById('fDireccion').value = datos.Direccion || '';
        document.getElementById('fRegion').value = datos.Region || '';
      }
    }, 50);
  }
  
  form.onsubmit = async (e) => {
    e.preventDefault();
    await guardarRegistro();
  };
  
  overlay.classList.add('active');
}

async function cargarDropdownsVenta(datos) {
  const res = await fetch(`${API}/api/ventas/dropdowns`);
  const dd = await res.json();
  const tipo = document.getElementById('fTipoVenta').value;

  function llenarSelect(id, items, valueKey, labelKey) {
    const sel = document.getElementById(id);
    sel.innerHTML = items.map(i => `<option value="${i[valueKey]}">${i[labelKey]}</option>`).join('');
  }

  function llenarSelectConPrecio(id, items, valueKey, labelKey, precioKey) {
    const sel = document.getElementById(id);
    sel.innerHTML = items.map(i => `<option value="${i[valueKey]}" data-precio="${i[precioKey]}">${i[labelKey]} - S/ ${i[precioKey]}</option>`).join('');
  }

  if (tipo === 'FM') {
    llenarSelectConPrecio('fCodProdFM', dd.formulas, 'CodFormula', 'DescripcionFM', 'CostoUnitarioFM');
    llenarSelect('fFechaKey', dd.fechas_fm, 'FechaKey', 'Fecha');
  } else {
    llenarSelectConPrecio('fCodProdFM', dd.productos, 'CodProducto', 'DescripcionPT', 'CostoUnitarioPT');
    llenarSelect('fFechaKey', dd.fechas_pt, 'FechaKey', 'Fecha');
  }

  llenarSelect('fClienteKey', dd.clientes, 'ClienteKey', 'Nombre');
  llenarSelect('fSedeKey', dd.sedes, 'SedeKey', 'NombreSede');
  llenarSelect('fMedicoKey', dd.medicos, 'MedicoKey', 'Nombre');

  document.getElementById('fTipoVenta').onchange = () => cargarDropdownsVenta(datos);

  document.getElementById('fCodProdFM').onchange = function() {
    const opt = this.options[this.selectedIndex];
    const precio = opt.getAttribute('data-precio');
    if (precio) document.getElementById('fCostoUnit').value = precio;
  };

  if (datos) {
    document.getElementById('fCodVenta').value = datos.CodVenta || '';
    document.getElementById('fTipoVenta').value = datos.Tipo || 'FM';
    await cargarDropdownsVenta(null);
    setTimeout(() => {
      document.getElementById('fCodProdFM').value = datos.Codigo || '';
      document.getElementById('fCantidad').value = datos.Cantidad || '';
    }, 100);
  } else {
    document.getElementById('fCodVenta').value = '';
    document.getElementById('fCantidad').value = '';
    document.getElementById('fCostoUnit').value = '';
  }
}

function cerrarModal() {
  document.getElementById('modalOverlay').classList.remove('active');
  editando = false;
}

async function guardarRegistro() {
  let url, body;
  
  if (tipoActual === 'producto') {
    body = {
      CodProducto: document.getElementById('fCod').value,
      DescripcionPT: document.getElementById('fDesc').value,
      DescripcionUso: document.getElementById('fUso').value,
      UnidadMedidaPT: document.getElementById('fUnidad').value,
      CostoUnitarioPT: parseFloat(document.getElementById('fPrecio').value),
      StockPT: parseInt(document.getElementById('fStock').value),
      EstadoPT: document.getElementById('fEstado').value
    };
    url = editando ? `${API}/api/productos/${body.CodProducto}` : `${API}/api/productos`;
  } else if (tipoActual === 'formula') {
    body = {
      CodFormula: document.getElementById('fCod').value,
      DescripcionFM: document.getElementById('fDesc').value,
      UnidadMedidaFM: document.getElementById('fUnidad').value,
      CostoUnitarioFM: parseFloat(document.getElementById('fPrecio').value),
      EstadoFM: document.getElementById('fEstado').value
    };
    url = editando ? `${API}/api/formulas/${body.CodFormula}` : `${API}/api/formulas`;
  } else if (tipoActual === 'cliente') {
    body = {
      ClienteKey: parseInt(document.getElementById('fKey').value),
      DniCliente: document.getElementById('fDni').value,
      NombresC: document.getElementById('fNombres').value,
      ApellidosC: document.getElementById('fApellidos').value,
      CelularC: document.getElementById('fCelular').value
    };
    url = editando ? `${API}/api/clientes/${body.ClienteKey}` : `${API}/api/clientes`;
  } else if (tipoActual === 'medico') {
    body = {
      MedicoKey: parseInt(document.getElementById('fKey').value),
      ColegiaturaMedico: document.getElementById('fColegiatura').value,
      NombresM: document.getElementById('fNombres').value,
      ApellidosM: document.getElementById('fApellidos').value,
      CelularM: document.getElementById('fCelular').value,
      EstadoM: document.getElementById('fEstado').value
    };
    url = editando ? `${API}/api/medicos/${body.MedicoKey}` : `${API}/api/medicos`;
  } else if (tipoActual === 'sede') {
    body = {
      SedeKey: parseInt(document.getElementById('fKey').value),
      NombreSede: document.getElementById('fNombre').value,
      Ciudad: document.getElementById('fCiudad').value,
      Direccion: document.getElementById('fDireccion').value,
      Region: document.getElementById('fRegion').value
    };
    url = editando ? `${API}/api/sedes/${body.SedeKey}` : `${API}/api/sedes`;
  } else if (tipoActual === 'venta') {
    const tipo = document.getElementById('fTipoVenta').value;
    const cantidad = parseInt(document.getElementById('fCantidad').value) || 1;
    const costo = parseFloat(document.getElementById('fCostoUnit').value) || 0;
    const codProd = document.getElementById('fCodProdFM').value;
    body = {
      codVenta: document.getElementById('fCodVenta').value,
      tipo: tipo,
      codProducto: codProd,
      fechaKey: document.getElementById('fFechaKey').value,
      clienteKey: document.getElementById('fClienteKey').value,
      sedeKey: document.getElementById('fSedeKey').value,
      medicoKey: document.getElementById('fMedicoKey').value || '1',
      medidas: document.getElementById('fMedidas').value,
      cantidad: cantidad,
      costoUnitario: costo,
      subtotal: (cantidad * costo).toFixed(2),
      stockDespues: 0
    };
    url = editando ? `${API}/api/ventas/${body.codVenta}/${body.tipo}` : `${API}/api/ventas`;
  }
  
  const method = editando ? 'PUT' : 'POST';
  await fetch(url, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
  
  cerrarModal();
  recargarTodo();
}

// ====== EDITAR/ELIMINAR ======
async function editarProducto(cod) {
  const res = await fetch(`${API}/api/productos`);
  const data = await res.json();
  const prod = data.find(p => p.CodProducto === cod);
  if (prod) abrirModal('producto', prod);
}

async function eliminarProducto(cod) {
  if (confirm('¿Eliminar este producto?')) {
    await fetch(`${API}/api/productos/${cod}`, { method: 'DELETE' });
    recargarTodo();
  }
}

async function editarFormula(cod) {
  const res = await fetch(`${API}/api/formulas`);
  const data = await res.json();
  const form = data.find(f => f.CodFormula === cod);
  if (form) abrirModal('formula', form);
}

async function eliminarFormula(cod) {
  if (confirm('¿Eliminar esta fórmula?')) {
    await fetch(`${API}/api/formulas/${cod}`, { method: 'DELETE' });
    recargarTodo();
  }
}

async function editarCliente(key) {
  const res = await fetch(`${API}/api/clientes`);
  const data = await res.json();
  const cli = data.find(c => c.ClienteKey === key);
  if (cli) abrirModal('cliente', cli);
}

async function eliminarCliente(key) {
  if (confirm('¿Eliminar este cliente?')) {
    await fetch(`${API}/api/clientes/${key}`, { method: 'DELETE' });
    recargarTodo();
  }
}

async function editarMedico(key) {
  const res = await fetch(`${API}/api/medicos`);
  const data = await res.json();
  const med = data.find(m => m.MedicoKey === key);
  if (med) abrirModal('medico', med);
}

async function eliminarMedico(key) {
  if (confirm('¿Eliminar este médico?')) {
    await fetch(`${API}/api/medicos/${key}`, { method: 'DELETE' });
    recargarTodo();
  }
}

async function editarSede(key) {
  const res = await fetch(`${API}/api/sedes`);
  const data = await res.json();
  const sede = data.find(s => s.SedeKey === key);
  if (sede) abrirModal('sede', sede);
}

async function eliminarSede(key) {
  if (confirm('¿Eliminar esta sede?')) {
    await fetch(`${API}/api/sedes/${key}`, { method: 'DELETE' });
    recargarTodo();
  }
}

async function editarVenta(cod, tipo) {
  const res = await fetch(`${API}/api/ventas`);
  const data = await res.json();
  const venta = data.find(v => v.CodVenta === cod && v.Tipo === tipo);
  if (venta) {
    venta.Tipo = tipo;
    abrirModal('venta', venta);
  }
}

async function eliminarVenta(cod, tipo) {
  if (confirm('¿Eliminar esta venta?')) {
    await fetch(`${API}/api/ventas/${cod}/${tipo}`, { method: 'DELETE' });
    recargarTodo();
  }
}

// ====== RECARGAR TODO ======
function recargarTodo() {
  cargarMetricas();
  cargarProductos();
  cargarFormulas();
  cargarClientes();
  cargarMedicos();
  cargarSedes();
  cargarVentas();
}

// ====== GRÁFICOS POR SECCIÓN (se cargan al mostrar) ======
const colores = {
  primary: '#0d7a3e',
  blue: '#1e40af',
  amber: '#f59e0b',
  purple: '#8b5cf6',
  red: '#ef4444',
  cyan: '#06b6d4'
};

function cargarGraficosProductos() {
  new Chart(document.getElementById('chartTopProductos'), {
    type: 'bar',
    data: {
      labels: ['Paracetamol', 'Ibuprofeno', 'Omeprazol', 'Amoxicilina', 'FM Ac. Hialuronico'],
      datasets: [{
        label: 'Unidades vendidas',
        data: [18, 16, 12, 10, 8],
        backgroundColor: [colores.primary, colores.blue, colores.amber, colores.purple, colores.cyan],
        borderRadius: 8
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      indexAxis: 'y',
      plugins: { legend: { display: false } },
      scales: { x: { beginAtZero: true, grid: { display: false } }, y: { grid: { display: false } } }
    }
  });

  new Chart(document.getElementById('chartTipoProducto'), {
    type: 'doughnut',
    data: {
      labels: ['Fórmulas Magistrales', 'Productos Terminados'],
      datasets: [{
        data: [55, 45],
        backgroundColor: [colores.primary, colores.amber],
        borderWidth: 0
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      cutout: '60%',
      plugins: { legend: { position: 'bottom', labels: { font: { family: 'Poppins', size: 12 }, padding: 16 } } }
    }
  });
}

function cargarGraficosClientes() {
  fetch(`${API}/api/clientes/segmentacion`)
    .then(r => r.json())
    .then(data => {
      if (!data.clusters || data.clusters.length === 0) return;
      const labels = data.clusters.map(c => c.nombre);
      const cantidades = data.clusters.map(c => c.cantidad);
      const gastos = data.clusters.map(c => c.gasto_promedio);
      const total = data.total || cantidades.reduce((a, b) => a + b, 0);
      const coloresArr = [colores.primary, colores.amber, colores.purple];

      new Chart(document.getElementById('chartClientesTipo'), {
        type: 'doughnut',
        data: { labels, datasets: [{ data: cantidades, backgroundColor: coloresArr.slice(0, labels.length), borderWidth: 0 }] },
        options: { responsive: true, maintainAspectRatio: false, cutout: '60%', plugins: { legend: { position: 'bottom', labels: { font: { family: 'Poppins', size: 12 }, padding: 16 } } } }
      });

      new Chart(document.getElementById('chartClientesCompras'), {
        type: 'bar',
        data: { labels, datasets: [{ label: 'Gasto promedio (S/)', data: gastos, backgroundColor: coloresArr.slice(0, labels.length), borderRadius: 8 }] },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { callback: v => 'S/ ' + v }, grid: { display: false } }, x: { grid: { display: false } } } }
      });

      const segIds = ['seg0', 'seg1', 'seg2'];
      data.clusters.forEach((c, i) => {
        if (i > 2) return;
        const pct = total > 0 ? ((c.cantidad / total) * 100).toFixed(1) : 0;
        document.getElementById(segIds[i] + 'Name').textContent = c.nombre;
        document.getElementById(segIds[i] + 'Count').textContent = `${c.cantidad} clientes (${pct}%)`;
        document.getElementById(segIds[i] + 'Gasto').textContent = `Gasto promedio: S/ ${c.gasto_promedio}`;
        document.getElementById(segIds[i] + 'Accion').textContent = c.accion;
      });
      setTimeout(() => window.dispatchEvent(new Event('resize')), 50);
    }).catch(() => {});
}

function cargarGraficoPrediccion() {
  new Chart(document.getElementById('chartPrediccion'), {
    type: 'line',
    data: {
      labels: ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic', 'Ene 26', 'Feb 26', 'Mar 26'],
      datasets: [
        {
          label: 'Ventas Reales',
          data: [10900, 11200, 11600, 10700, 11900, 12500, 13100, 13700, 14400, 15400, 17400, 19400, null, null, null],
          borderColor: colores.primary,
          backgroundColor: colores.primary + '20',
          fill: true,
          tension: 0.4,
          borderWidth: 3,
          pointRadius: 4,
          pointBackgroundColor: colores.primary
        },
        {
          label: 'Proyección',
          data: [null, null, null, null, null, null, null, null, null, null, null, 19400, 11495, 11922, 12348],
          borderColor: colores.purple,
          borderDash: [8, 4],
          tension: 0.4,
          borderWidth: 3,
          pointRadius: 4,
          pointBackgroundColor: colores.purple
        }
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { position: 'top', labels: { font: { family: 'Poppins', size: 11 } } } },
      scales: {
        y: { beginAtZero: false, ticks: { callback: v => 'S/ ' + (v/1000).toFixed(0) + 'k' }, grid: { color: '#f3f4f6' } },
        x: { grid: { display: false } }
      }
    }
  });
}

// ====== INICIALIZAR ======
cargarMetricas();
cargarProductos();
cargarFormulas();
cargarClientes();
cargarMedicos();
cargarSedes();
cargarVentas();

// Ajustar tamaño al cambiar ventana
window.addEventListener('resize', () => {
  const seccionActiva = document.querySelector('.section.active');
  if (seccionActiva) ajustarSeccion(seccionActiva.id);
});

// Ajustar resumen al cargar
setTimeout(() => ajustarSeccion('resumen'), 800);

