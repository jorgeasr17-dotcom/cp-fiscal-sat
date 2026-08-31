const $ = (id) => document.getElementById(id);

const munisPorEstado = {};
const nCpsPorEstado = {};
const seleccion = [];

function aviso(tipo, html) {
  return `<div class="aviso ${tipo}">${html}</div>`;
}

function esc(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function bajarTxt(nombre, texto) {
  const blob = new Blob([texto], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = nombre;
  a.click();
  URL.revokeObjectURL(url);
}

function pintarConteo() {
  const estado = $("estado").value;
  if (!estado) {
    $("conteo").textContent = "Elija un estado. Si no agrega municipio, se usa todo el estado.";
    return;
  }
  if (!seleccion.length) {
    const n = nCpsPorEstado[estado] || 0;
    $("conteo").innerHTML = `<b>${n}</b> CPs de todo ${esc(estado)}. <span class="muted">Municipio opcional: si lo agrega, se acota la búsqueda.</span>`;
    return;
  }
  const n = seleccion.reduce((s, m) => s + m.n_cps, 0);
  const nombres = seleccion.map((m) => m.nombre).join(", ");
  $("conteo").innerHTML = `<b>${n}</b> CPs a probar · ${esc(nombres)} <span class="muted">(si se solapan, el SAT recibe los únicos)</span>`;
}

function pintarChips() {
  $("chips").innerHTML = seleccion
    .map(
      (m, i) =>
        `<span class="chip">${esc(m.nombre)} <small>(${m.n_cps})</small>
         <button type="button" data-i="${i}" aria-label="Quitar">×</button></span>`
    )
    .join("");
  pintarConteo();
}

$("chips").addEventListener("click", (ev) => {
  const btn = ev.target.closest("button[data-i]");
  if (!btn) return;
  seleccion.splice(Number(btn.dataset.i), 1);
  pintarChips();
});

function llenarMunicipios(items) {
  const sel = $("municipio");
  sel.innerHTML = '<option value="">Opcional — vacío = todo el estado</option>';
  for (const m of items) {
    const opt = document.createElement("option");
    opt.value = m.nombre;
    opt.textContent = `${m.nombre} (${m.n_cps})`;
    opt.dataset.n = String(m.n_cps);
    sel.appendChild(opt);
  }
  sel.disabled = items.length === 0;
  $("agregar").disabled = items.length === 0;
}

async function cargarEstados() {
  const res = await fetch("/api/estados");
  const data = await res.json();
  const sel = $("estado");
  for (const e of data.estados || []) {
    const nombre = typeof e === "string" ? e : e.nombre;
    const opt = document.createElement("option");
    opt.value = nombre;
    opt.textContent = e.n_cps ? `${nombre} (${e.n_cps} CPs)` : nombre;
    if (e.n_cps) nCpsPorEstado[nombre] = e.n_cps;
    sel.appendChild(opt);
  }
}

$("estado").addEventListener("change", async () => {
  const estado = $("estado").value;
  seleccion.length = 0;
  pintarChips();
  if (!estado) {
    llenarMunicipios([]);
    return;
  }
  if (!munisPorEstado[estado]) {
    const res = await fetch(`/api/municipios?estado=${encodeURIComponent(estado)}`);
    const data = await res.json();
    munisPorEstado[estado] = data.municipios || [];
    if (data.n_cps_estado) nCpsPorEstado[estado] = data.n_cps_estado;
  }
  llenarMunicipios(munisPorEstado[estado]);
  pintarConteo();
});

$("agregar").addEventListener("click", () => {
  const sel = $("municipio");
  const nombre = sel.value;
  if (!nombre) return;
  if (seleccion.some((m) => m.nombre === nombre)) return;
  const n = Number(sel.selectedOptions[0].dataset.n || 0);
  seleccion.push({ nombre, n_cps: n });
  pintarChips();
  sel.value = "";
});

$("municipio").addEventListener("change", () => {
  if ($("municipio").value && !seleccion.length) $("agregar").click();
});

$("generar").addEventListener("click", async () => {
  if (!$("estado").value) {
    $("status-gen").textContent = "Elija un estado.";
    return;
  }
  const fd = new FormData();
  fd.append("rfc", $("rfc").value.trim());
  fd.append("nombre", $("nombre").value.trim());
  fd.append("estado", $("estado").value);
  for (const m of seleccion) fd.append("municipios", m.nombre);
  $("status-gen").textContent = "Armando…";
  const res = await fetch("/api/generar", { method: "POST", body: fd });
  const data = await res.json();
  if (!data.ok) {
    $("status-gen").textContent = data.error || "Error";
    return;
  }
  $("rfc").value = data.rfc;
  $("nombre").value = data.nombre;
  $("status-gen").textContent = `${data.lineas} líneas · ${data.archivo}`;
  bajarTxt(data.archivo, data.txt);
});

async function enviarRespuesta(file) {
  const fd = new FormData();
  fd.append("file", file);
  $("resultado").innerHTML = aviso("warn", "Leyendo respuesta…");
  const res = await fetch("/api/leer", { method: "POST", body: fd });
  const data = await res.json();
  pintarResultado(data);
}

function pintarResultado(data) {
  if (data.ok && data.cp) {
    const revisar = data.estado === "revisar_nombre";
    $("resultado").innerHTML = aviso(
      revisar ? "warn" : "ok",
      `<div>${revisar ? "Revise el nombre · CP encontrado" : "CP fiscal"}</div>
       <div class="cp-grande">${esc(data.cp)}</div>
       <div><b>${esc(data.rfc)}</b> · ${esc(data.nombre)}</div>
       <div class="hint" style="margin-top:6px">${esc(data.detalle)}</div>
       <div class="actions">
         <button class="btn" type="button" id="copiar-cp">Copiar CP</button>
       </div>`
    );
    $("copiar-cp").onclick = async () => {
      await navigator.clipboard.writeText(data.cp);
      $("copiar-cp").textContent = "Copiado";
    };
    return;
  }
  const tipo = data.estado === "nombre" || data.estado === "fuera" ? "warn" : "bad";
  let extra = "";
  if (data.estado === "fuera") {
    extra = "<br>Si acotó por municipio, quite los chips o agregue uno cercano. Si ya era todo el estado, el CP fiscal está en otra entidad.";
  }
  $("resultado").innerHTML = aviso(
    tipo,
    `<b>${esc(data.titulo || "No se pudo leer")}</b><br>${esc(data.detalle || data.error || "")}${extra}`
  );
}

const drop = $("drop");
drop.addEventListener("dragover", (ev) => {
  ev.preventDefault();
  drop.classList.add("over");
});
drop.addEventListener("dragleave", () => drop.classList.remove("over"));
drop.addEventListener("drop", (ev) => {
  ev.preventDefault();
  drop.classList.remove("over");
  const file = ev.dataTransfer.files[0];
  if (file) enviarRespuesta(file);
});
$("file").addEventListener("change", () => {
  const file = $("file").files[0];
  if (file) enviarRespuesta(file);
  $("file").value = "";
});

cargarEstados();
