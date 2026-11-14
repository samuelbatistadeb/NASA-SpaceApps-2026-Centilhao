"use strict";

/* ============================================================
 * SPHEREx Explorer — frontend
 * Ajuste CONFIG e a função normalizeObservation() conforme
 * docs/architecture/api-contract.md.
 * ============================================================ */
const CONFIG = {
  API_BASE: "http://localhost:8000",
  OBSERVATIONS_PATH: "/api/observations", // ASSUMIDO: GET ?ra=&dec=&fov=
  TARGETS_PATH: "/api/targets", // ASSUMIDO: lista de alvos com coordenadas, fornecida pelo backend
  TIMEOUT_MS: 30000,
  EXTRA_PARAMS: {}, // ex.: { release: "qr3" } para trocar a versão dos dados sem mudar o código
  FOV_MIN: 0.5,
  FOV_MAX: 30, // minutos de arco (confirmar unidade com o backend)
};

const $ = (id) => document.getElementById(id);
const el = {
  form: $("form"), ra: $("ra"), dec: $("dec"), fov: $("fov"),
  buscar: $("buscar"), mock: $("mock"), status: $("status"),
  player: $("player"), avisoMock: $("aviso-mock"),
  img: $("imagem"), legenda: $("legenda"),
  prev: $("prev"), play: $("play"), next: $("next"), speed: $("speed"),
  slider: $("slider"),
  detBox: $("detectores"), faixa: $("faixa-wl"), wlMin: $("wl-min"), wlMax: $("wl-max"),
  wlMinOut: $("wl-min-out"), wlMaxOut: $("wl-max-out"), contagem: $("contagem"),
  visor: $("visor"), filtroVazio: $("filtro-vazio"), reset: $("filtro-reset"), galeria: $("galeria-lista"), galeriaVazio: $("galeria-vazio"), tIni: $("t-ini"), tFim: $("t-fim"), meta: $("meta"),
};

const state = { all: [], wls: [], detectors: new Set(), frames: [], index: 0, timer: null, isMock: false, controller: null };

/* ---------- Utilitários ---------- */
const parseNum = (v) => Number(String(v).trim().replace(",", "."));

// Aceita graus decimais ("133.795") ou sexagesimal ("08h55m10.831s", "-7d14m42.53s",
// "8 55 10.8", "-07:14:42.5"). Retorna graus, ou NaN se o texto for inválido.
function parseCoord(raw, kind) {
  const s = String(raw).trim().replace(",", ".").replace(/[−–]/g, "-");
  if (!s || /[^\d\s.+\-hmsd°'’"′″:]/i.test(s)) return NaN;
  const nums = s.match(/\d+(?:\.\d+)?/g);
  if (!nums || nums.length > 3) return NaN;
  const neg = s.startsWith("-");
  const [a, b = 0, c = 0] = nums.map(Number);
  const hasUnit = /[hdms°'’"′″:]/i.test(s) || nums.length > 1;
  if (!hasUnit) return neg ? -a : a;
  if (b >= 60 || c >= 60) return NaN;
  let v = a + b / 60 + c / 3600;
  if (kind === "ra" && !/[d°]/i.test(s)) v *= 15; // RA sexagesimal está em horas
  return neg ? -v : v;
}

const fmtWl = (w) => `${w.toFixed(2).replace(".", ",")} µm`;

const fmtDate = (iso) =>
  new Date(iso).toLocaleDateString("pt-BR", { dateStyle: "long", timeZone: "UTC" });

function setStatus(msg, kind = "") {
  el.status.textContent = msg;
  el.status.className = "status " + kind;
}

/* ---------- Validação ---------- */
const RULES = {
  ra:  { min: 0,   max: 360, msg: "Informe graus (0 a 360) ou h/m/s, ex.: 08h55m10.831s." },
  dec: { min: -90, max: 90,  msg: "Informe graus (−90 a 90) ou °/′/″, ex.: -7d14m42.53s." },
  fov: { min: CONFIG.FOV_MIN, max: CONFIG.FOV_MAX,
         msg: `Informe um número entre ${CONFIG.FOV_MIN} e ${CONFIG.FOV_MAX}.` },
};

function validate() {
  const values = {};
  let firstInvalid = null;
  for (const [name, rule] of Object.entries(RULES)) {
    const input = el[name];
    const n = name === "fov" ? parseNum(input.value) : parseCoord(input.value, name);
    const ok = input.value.trim() !== "" && Number.isFinite(n) && n >= rule.min && n <= rule.max;
    input.setAttribute("aria-invalid", String(!ok));
    $(name + "-erro").textContent = ok ? "" : rule.msg;
    if (!ok && !firstInvalid) firstInvalid = input;
    values[name] = Number(n.toFixed(6));
  }
  if (firstInvalid) { firstInvalid.focus(); return null; }
  return values;
}

/* ---------- API ---------- */
// Converte a resposta do backend para o formato interno.
function normalizeObservation(o) {
  const img = o.image_url ?? o.imageUrl ?? o.image ?? "";
  const wlRaw = o.wavelength_um ?? o.wavelength ?? o.lambda ?? null;
  const wl = wlRaw === null || wlRaw === "" ? NaN : Number(wlRaw);
  const det = parseInt(String(o.detector ?? o.detector_id ?? "").replace(/\D/g, ""), 10);
  const detOk = det >= 1 && det <= 6; // SPHEREx: seis conjuntos de detectores
  return {
    id: o.product_id ?? o.id ?? "—",
    date: o.obs_date ?? o.date ?? o.epoch ?? null, // ISO 8601
    imageUrl: /^(https?:|data:)/.test(img) ? img : CONFIG.API_BASE + img,
    detector: detOk ? det : null,
    detectorLabel: detOk ? "D" + det : String(o.detector ?? "—"),
    wavelength: Number.isFinite(wl) ? wl : null, // micrômetros
    band: o.band_index ?? o.band ?? "—",
    product: o.product_type ?? o.product ?? "—",
  };
}

async function fetchObservations({ ra, dec, fov }) {
  state.controller?.abort();
  const controller = (state.controller = new AbortController());
  const timeout = setTimeout(() => controller.abort("timeout"), CONFIG.TIMEOUT_MS);
  const url = new URL(CONFIG.OBSERVATIONS_PATH, CONFIG.API_BASE);
  url.search = new URLSearchParams({ ra, dec, fov, ...CONFIG.EXTRA_PARAMS }).toString();

  try {
    const res = await fetch(url, { signal: controller.signal });
    if (!res.ok) throw new Error("http-" + res.status);
    const data = await res.json();
    const list = Array.isArray(data) ? data : data.observations ?? [];
    return list
      .map(normalizeObservation)
      .filter((f) => f.date && !Number.isNaN(Date.parse(f.date)))
      .sort((a, b) => Date.parse(a.date) - Date.parse(b.date));
    // TODO: se a API devolver várias bandas na mesma época, agrupar por data
    // para que bandas nunca sejam exibidas como quadros de tempo diferentes.
  } finally {
    clearTimeout(timeout);
  }
}

/* ---------- Dados fictícios (apenas teste de interface) ---------- */
function mockObservations() {
  const frames = [];
  const start = Date.UTC(2025, 4, 1);
  for (let i = 0; i < 12; i++) {
    const c = document.createElement("canvas");
    c.width = c.height = 128;
    const g = c.getContext("2d");
    g.fillStyle = "#050510";
    g.fillRect(0, 0, 128, 128);
    for (let s = 0; s < 40; s++) { // estrelas fixas, determinísticas
      const x = (s * 53) % 128, y = (s * 97) % 128;
      g.fillStyle = `rgba(255,255,255,${0.2 + ((s * 7) % 5) / 8})`;
      g.fillRect(x, y, 1.5, 1.5);
    }
    g.fillStyle = "#ff5c8a"; // fonte que se desloca
    g.beginPath();
    g.arc(30 + i * 6, 40 + i * 3, 3.5, 0, Math.PI * 2);
    g.fill();
    frames.push({
      id: "FICTICIO-" + String(i + 1).padStart(2, "0"),
      date: new Date(start + i * 30 * 864e5).toISOString(),
      imageUrl: c.toDataURL("image/png"),
      detector: (i % 6) + 1, detectorLabel: "D" + ((i % 6) + 1), wavelength: 0.75 + i * 0.35,
      band: String(i + 1), product: "teste de interface",
    });
  }
  return frames;
}

/* ---------- Visualizador ---------- */
function showFrame(i) {
  const f = state.frames[i];
  if (!f) return;
  state.index = i;
  el.img.src = f.imageUrl;
  el.img.alt = `Região do céu observada em ${fmtDate(f.date)}`;
  el.legenda.textContent = `${fmtDate(f.date)} — quadro ${i + 1} de ${state.frames.length}`;
  el.slider.value = i;
  el.slider.setAttribute("aria-valuetext", fmtDate(f.date));
  el.galeria.querySelectorAll("button").forEach((b, k) =>
    k === i ? b.setAttribute("aria-current", "true") : b.removeAttribute("aria-current"));

  const rows = [
    ["Data da observação", f.date.slice(0, 10)],
    ["Identificador do produto", f.id],
    ["Detector", f.detectorLabel],
    ["Banda", f.band],
    ["Comprimento de onda", f.wavelength === null ? "—" : fmtWl(f.wavelength)],
    ["Tipo de produto", f.product],
    ["Fonte dos dados", state.isMock ? "Fictícia (teste)" : "SPHEREx / IRSA-IPAC"],
  ];
  el.meta.replaceChildren(
    ...rows.flatMap(([k, v]) => {
      const dt = document.createElement("dt"); dt.textContent = k;
      const dd = document.createElement("dd"); dd.textContent = v;
      return [dt, dd];
    })
  );
}

function clearGallery() {
  el.galeria.replaceChildren();
  el.galeriaVazio.hidden = false;
}

function renderGallery(frames) {
  el.galeriaVazio.hidden = true;
  el.galeria.replaceChildren(
    ...frames.map((f, i) => {
      const li = document.createElement("li");
      const btn = document.createElement("button");
      btn.type = "button";
      const img = document.createElement("img");
      img.src = f.imageUrl;
      img.loading = "lazy";
      img.alt = "";
      const label = document.createElement("span");
      label.textContent = fmtDate(f.date);
      btn.setAttribute("aria-label", `Ver observação de ${fmtDate(f.date)}`);
      btn.append(img, label);
      btn.addEventListener("click", () => { stop(); showFrame(i); });
      li.append(btn);
      return li;
    })
  );
}

function stop() {
  clearInterval(state.timer);
  state.timer = null;
  el.play.textContent = "Reproduzir";
  el.play.setAttribute("aria-pressed", "false");
}

function start() {
  if (state.frames.length < 2) return;
  stop();
  el.play.textContent = "Pausar";
  el.play.setAttribute("aria-pressed", "true");
  state.timer = setInterval(
    () => showFrame((state.index + 1) % state.frames.length),
    Number(el.speed.value)
  );
}

function step(delta) {
  stop();
  const n = state.frames.length;
  showFrame((state.index + delta + n) % n);
}

/* ---------- Filtros (detector e comprimento de onda) ---------- */
const DET_COLORS = ["#E69F00", "#56B4E9", "#009E73", "#F0E442", "#0072B2", "#D55E00"]; // paleta Okabe-Ito

function setupFilters(frames) {
  const present = new Set(frames.map((f) => f.detector).filter(Boolean));
  state.detectors = new Set(present);
  el.detBox.hidden = present.size === 0;
  el.detBox.replaceChildren(
    ...[1, 2, 3, 4, 5, 6].map((d) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "det";
      const sw = document.createElement("span");
      sw.className = "sw";
      sw.style.background = DET_COLORS[d - 1];
      sw.setAttribute("aria-hidden", "true");
      b.append(sw, document.createTextNode("Detector " + d));
      b.disabled = !present.has(d);
      b.setAttribute("aria-pressed", String(present.has(d)));
      if (!present.has(d)) b.title = "Sem observações deste detector nesta busca";
      b.addEventListener("click", () => {
        state.detectors.has(d) ? state.detectors.delete(d) : state.detectors.add(d);
        b.setAttribute("aria-pressed", String(state.detectors.has(d)));
        applyFilters();
      });
      return b;
    })
  );

  state.wls = [...new Set(frames.map((f) => f.wavelength).filter((w) => w !== null))].sort((a, b) => a - b);
  const last = Math.max(state.wls.length - 1, 0);
  el.faixa.hidden = state.wls.length < 2;
  el.wlMin.max = el.wlMax.max = last;
  el.wlMin.value = 0;
  el.wlMax.value = last;
}

function isVisible(f) {
  if (f.detector && !state.detectors.has(f.detector)) return false;
  if (f.wavelength !== null && state.wls.length > 1) {
    const lo = state.wls[Number(el.wlMin.value)];
    const hi = state.wls[Number(el.wlMax.value)];
    if (f.wavelength < lo || f.wavelength > hi) return false;
  }
  return true;
}

function applyFilters() {
  const keepId = state.frames[state.index]?.id;
  const frames = state.all.filter(isVisible);
  if (state.wls.length > 1) {
    el.wlMinOut.textContent = fmtWl(state.wls[Number(el.wlMin.value)]);
    el.wlMaxOut.textContent = fmtWl(state.wls[Number(el.wlMax.value)]);
  }
  el.contagem.textContent = `Mostrando ${frames.length} de ${state.all.length} observações.`;

  stop();
  state.frames = frames;
  el.visor.hidden = !frames.length;
  el.filtroVazio.hidden = !!frames.length;
  if (!frames.length) { clearGallery(); return; }

  el.slider.max = frames.length - 1;
  el.tIni.textContent = fmtDate(frames[0].date);
  el.tFim.textContent = fmtDate(frames.at(-1).date);
  renderGallery(frames);
  const idx = frames.findIndex((f) => f.id === keepId);
  showFrame(idx >= 0 ? idx : 0);
}

el.wlMin.addEventListener("input", () => {
  if (Number(el.wlMin.value) > Number(el.wlMax.value)) el.wlMax.value = el.wlMin.value;
  applyFilters();
});
el.wlMax.addEventListener("input", () => {
  if (Number(el.wlMax.value) < Number(el.wlMin.value)) el.wlMin.value = el.wlMax.value;
  applyFilters();
});
el.reset.addEventListener("click", () => { setupFilters(state.all); applyFilters(); });

function loadFrames(frames, isMock) {
  stop();
  state.all = frames;
  state.isMock = isMock;
  el.avisoMock.hidden = !isMock;
  setupFilters(frames);
  el.player.hidden = false;
  applyFilters();
}

/* ---------- Fluxo de busca ---------- */
async function onSubmit(e) {
  e.preventDefault();
  const values = validate();
  if (!values) {
    if (document.body.classList.contains("embed")) setStatus("Coordenadas inválidas na URL.", "erro");
    return;
  }
  state.values = values;
  if (!el.mock.checked) updateUrl(values);

  stop();
  el.player.hidden = true;
  clearGallery();
  el.buscar.disabled = true;
  setStatus("Buscando observações no arquivo SPHEREx… isso pode levar alguns segundos.", "carregando");

  try {
    const frames = el.mock.checked ? mockObservations() : await fetchObservations(values);
    if (!frames.length) {
      setStatus("Nenhuma observação encontrada para essa região. Tente aumentar o tamanho da área (FOV) ou escolher outro ponto.");
      return;
    }
    loadFrames(frames, el.mock.checked);
    setStatus(`${frames.length} observações em ordem cronológica · RA ${values.ra}°, Dec ${values.dec}°, FOV ${values.fov}′.`);
  } catch (err) {
    const timedOut = err === "timeout" || err?.name === "AbortError";
    if (timedOut && state.controller?.signal.reason !== "timeout") return; // busca substituída
    setStatus(
      timedOut
        ? "A busca demorou demais. Tente novamente em instantes."
        : "Não foi possível conectar ao servidor. Verifique se o backend está em execução e tente de novo.",
      "erro"
    );
  } finally {
    el.buscar.disabled = false;
  }
}

/* ---------- Eventos ---------- */
el.form.addEventListener("submit", onSubmit);
el.prev.addEventListener("click", () => step(-1));
el.next.addEventListener("click", () => step(1));
el.play.addEventListener("click", () => (state.timer ? stop() : start()));
el.speed.addEventListener("change", () => state.timer && start());
el.slider.addEventListener("input", () => { stop(); showFrame(Number(el.slider.value)); });
el.img.addEventListener("error", () =>
  setStatus("Não foi possível carregar esta imagem. Tente outro quadro.", "erro"));

// Alvos de exemplo: nomes e coordenadas vêm do backend (o frontend não guarda coordenadas).
// Formato esperado: [{ name, ra, dec, fov?, note? }] ou { targets: [...] }, RA/Dec em graus.
function normalizeTarget(t) {
  return {
    name: String(t.name ?? t.id ?? ""),
    ra: Number(t.ra), dec: Number(t.dec),
    fov: Number(t.fov ?? t.default_fov ?? 3),
    note: t.note ?? t.description ?? "",
  };
}

async function loadTargets() {
  const box = $("presets");
  try {
    const res = await fetch(new URL(CONFIG.TARGETS_PATH, CONFIG.API_BASE), { signal: AbortSignal.timeout(10000) });
    if (!res.ok) throw new Error("http-" + res.status);
    const data = await res.json();
    const list = (Array.isArray(data) ? data : data.targets ?? [])
      .map(normalizeTarget)
      .filter((t) => t.name && Number.isFinite(t.ra) && Number.isFinite(t.dec));
    if (!list.length) throw new Error("vazio");
    for (const t of list) {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "chip";
      b.textContent = t.name;
      if (t.note) b.title = t.note;
      b.addEventListener("click", () => {
        el.ra.value = t.ra;
        el.dec.value = t.dec;
        el.fov.value = t.fov;
        el.form.requestSubmit();
      });
      box.append(b);
    }
  } catch {
    box.querySelector("span").textContent = "Alvos de exemplo indisponíveis no momento. Informe as coordenadas manualmente.";
  }
}
loadTargets();

/* ---------- URL, compartilhamento e modo incorporado ---------- */
function updateUrl({ ra, dec, fov }) {
  const q = new URLSearchParams(location.search);
  q.set("ra", ra); q.set("dec", dec); q.set("fov", fov);
  try { history.replaceState(null, "", "?" + q); } catch { /* ex.: file:// */ }
}

function shareUrl(embed) {
  const { ra, dec, fov } = state.values;
  const u = new URL(location.href);
  u.hash = "";
  u.search = new URLSearchParams({ ra, dec, fov, ...(embed ? { embed: 1 } : {}) });
  return u.toString();
}

async function copy(text, okMsg) {
  try {
    await navigator.clipboard.writeText(text);
    $("copiado").textContent = okMsg;
  } catch {
    $("copiado").textContent = "Não foi possível copiar automaticamente.";
  }
}
$("copiar-link").addEventListener("click", () => copy(shareUrl(false), "Link copiado."));
$("copiar-embed").addEventListener("click", () =>
  copy(`<iframe src="${shareUrl(true)}" width="100%" height="640" style="border:0" title="SPHEREx Explorer" loading="lazy"></iframe>`,
       "Código copiado."));

(function initFromUrl() {
  const q = new URLSearchParams(location.search);
  if (q.get("embed") === "1") document.body.classList.add("embed");
  if (q.has("ra") && q.has("dec")) {
    el.ra.value = q.get("ra");
    el.dec.value = q.get("dec");
    if (q.has("fov")) el.fov.value = q.get("fov");
    el.form.requestSubmit();
  }
})();

// Atalhos de teclado no visualizador (fora de campos de texto)
document.addEventListener("keydown", (e) => {
  if (el.player.hidden || e.target.matches("input, select, textarea")) return;
  if (e.key === "ArrowLeft") step(-1);
  else if (e.key === "ArrowRight") step(1);
});

// Destaca no menu lateral a seção visível
const navLinks = [...document.querySelectorAll('.sidebar a[href^="#"]')];
const sections = navLinks.map((a) => document.querySelector(a.hash)).filter(Boolean);
const spy = new IntersectionObserver(
  (entries) => entries.forEach((en) => {
    if (!en.isIntersecting) return;
    navLinks.forEach((a) =>
      a.hash === "#" + en.target.id ? a.setAttribute("aria-current", "true") : a.removeAttribute("aria-current"));
  }),
  { rootMargin: "-20% 0px -70% 0px" }
);
sections.forEach((s) => spy.observe(s));
