"use strict";

/* ============================================================
 * SPHEREx Explorer — frontend
 * Contrato: src/backend/app/api/observations.py e
 * src/backend/app/schemas/observation.py
 * GET /api/observations?ra_deg=&dec_deg=&fov_arcmin=
 * ============================================================ */
const CONFIG = {
  API_BASE: "http://localhost:8000",
  OBSERVATIONS_PATH: "/api/observations",
  TIMEOUT_MS: 120000, // a primeira consulta ao IRSA (sem cache) pode demorar
  FOV_MIN: 0.1,  // minutos de arco (padrão do backend: SPHEREX_MIN_FOV_ARCMIN)
  FOV_MAX: 120,  // minutos de arco (padrão do backend: SPHEREX_MAX_FOV_ARCMIN)
  GALLERY_MAX: 60, // miniaturas exibidas na galeria (as demais ficam no player)
};

const $ = (id) => document.getElementById(id);
const el = {
  form: $("form"), ra: $("ra"), dec: $("dec"), fov: $("fov"),
  buscar: $("buscar"), mock: $("mock"), status: $("status"),
  player: $("player"), avisoMock: $("aviso-mock"),
  img: $("imagem"), legenda: $("legenda"),
  prev: $("prev"), play: $("play"), next: $("next"), speed: $("speed"),
  detector: $("detector"),
  slider: $("slider"), galeria: $("galeria-lista"), galeriaVazio: $("galeria-vazio"),
  galeriaAviso: $("galeria-aviso"), tIni: $("t-ini"), tFim: $("t-fim"), meta: $("meta"),
};

const state = {
  allFrames: [], frames: [], index: 0, timer: null, isMock: false, controller: null,
  omitted: 0, // observações sem observed_at (fora da sequência temporal)
};

/* ---------- Utilitários ---------- */
const parseNum = (v) => Number(String(v).trim().replace(",", "."));

const fmtDate = (iso) =>
  new Date(iso).toLocaleDateString("pt-BR", { dateStyle: "long", timeZone: "UTC" });

// Vários detectores podem ter observações no mesmo dia: mostra também a hora (UTC).
const fmtDateTime = (iso) =>
  new Date(iso).toLocaleString("pt-BR", { dateStyle: "medium", timeStyle: "short", timeZone: "UTC" }) + " UTC";

const show = (v) => (v === null || v === undefined || v === "" ? "—" : String(v));

// Erro retornado pelo backend no envelope {"error": {"code", "message"}}.
class ApiError extends Error {
  constructor(code, message, status) {
    super(message);
    this.code = code;
    this.status = status;
  }
}

function setStatus(msg, kind = "") {
  el.status.textContent = msg;
  el.status.className = "status " + kind;
}

/* ---------- Validação ---------- */
const RULES = {
  // RA: 0 <= ra < 360 (360 é o mesmo ponto que 0 e o backend o rejeita).
  ra:  { min: 0,   max: 360, maxExclusive: true, msg: "Informe um número de 0 até menos de 360." },
  dec: { min: -90, max: 90,  msg: "Informe um número entre −90 e 90." },
  fov: { min: CONFIG.FOV_MIN, max: CONFIG.FOV_MAX,
         msg: `Informe um número entre ${String(CONFIG.FOV_MIN).replace(".", ",")} e ${CONFIG.FOV_MAX}.` },
};

function validate() {
  const values = {};
  let firstInvalid = null;
  for (const [name, rule] of Object.entries(RULES)) {
    const input = el[name];
    const n = parseNum(input.value);
    const belowMax = rule.maxExclusive ? n < rule.max : n <= rule.max;
    const ok = input.value.trim() !== "" && Number.isFinite(n) && n >= rule.min && belowMax;
    input.setAttribute("aria-invalid", String(!ok));
    $(name + "-erro").textContent = ok ? "" : rule.msg;
    if (!ok && !firstInvalid) firstInvalid = input;
    values[name] = n;
  }
  if (firstInvalid) { firstInvalid.focus(); return null; }
  return values;
}

/* ---------- API ---------- */
// Converte uma observação do backend (schema Observation) para o formato interno.
function normalizeObservation(o) {
  const m = o.metadata ?? {};
  const img = o.image_url ?? "";
  return {
    id: o.id ?? "—",
    date: o.observed_at ?? null, // ISO 8601 UTC ou null
    imageUrl: !img ? null : /^(https?:|data:)/.test(img) ? img : CONFIG.API_BASE + img,
    detector: o.detector ?? null,
    band: o.band ?? null,
    meta: m,
  };
}

// Separa as observações com data válida (sequência temporal) das sem data.
function toFrames(list) {
  const all = list.map(normalizeObservation);
  const frames = all
    .filter((f) => f.date && !Number.isNaN(Date.parse(f.date)))
    .sort((a, b) => Date.parse(a.date) - Date.parse(b.date));
  return { frames, omitted: all.length - frames.length };
}

async function readApiError(res) {
  try {
    const body = await res.json();
    if (body?.error?.code) return new ApiError(body.error.code, body.error.message ?? "", res.status);
  } catch { /* corpo não é JSON */ }
  return new ApiError("HTTP_" + res.status, "", res.status);
}

async function fetchObservations({ ra, dec, fov }) {
  state.controller?.abort();
  const controller = (state.controller = new AbortController());
  const timeout = setTimeout(() => controller.abort("timeout"), CONFIG.TIMEOUT_MS);
  const url = new URL(CONFIG.OBSERVATIONS_PATH, CONFIG.API_BASE);
  url.search = new URLSearchParams({ ra_deg: ra, dec_deg: dec, fov_arcmin: fov }).toString();

  try {
    const res = await fetch(url, { signal: controller.signal });
    if (!res.ok) throw await readApiError(res);
    const data = await res.json();
    return toFrames(Array.isArray(data?.observations) ? data.observations : []);
  } finally {
    clearTimeout(timeout);
  }
}

// Mensagem amigável para cada código de erro do contrato.
function errorMessage(err) {
  if (err instanceof ApiError) {
    switch (err.code) {
      case "NO_OBSERVATIONS_FOUND":
        return "Nenhuma observação SPHEREx encontrada para essa região. Tente aumentar o tamanho da área (FOV) ou escolher outro ponto.";
      case "SOURCE_UNAVAILABLE":
        return "O arquivo IRSA (fonte dos dados SPHEREx) está indisponível no momento. Tente novamente em alguns minutos.";
      default:
        return err.message || `O servidor respondeu com erro (HTTP ${err.status}).`;
    }
  }
  return "Não foi possível conectar ao servidor. Verifique se o backend está em execução e tente de novo.";
}

/* ---------- Dados fictícios (apenas teste de interface) ---------- */
// Gera observações no MESMO formato do backend (dois detectores por instante e
// uma sem data), para exercitar o filtro por detector e o aviso de omitidas.
function mockObservations() {
  const list = [];
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
    const observedAt = new Date(start + i * 30 * 864e5).toISOString();
    const image = c.toDataURL("image/png");
    for (const det of ["D1", "D2"]) {
      list.push({
        id: `FICTICIO-${String(i + 1).padStart(2, "0")}-${det}`,
        observed_at: observedAt,
        band: "FICTICIA-" + det,
        detector: det,
        image_url: image,
        metadata: { product_id: "fictício", timing_status: "teste de interface" },
      });
    }
  }
  list.push({ id: "FICTICIO-SEM-DATA", observed_at: null, band: null, detector: "D1",
              image_url: null, metadata: {} });
  return toFrames(list);
}

/* ---------- Visualizador ---------- */
function showFrame(i) {
  const f = state.frames[i];
  if (!f) return;
  state.index = i;
  if (f.imageUrl) el.img.src = f.imageUrl;
  else el.img.removeAttribute("src");
  el.img.alt = f.imageUrl
    ? `Região do céu observada em ${fmtDateTime(f.date)}, detector ${show(f.detector)}`
    : "Imagem indisponível para esta observação";
  el.legenda.textContent =
    `${fmtDateTime(f.date)} · detector ${show(f.detector)} · banda ${show(f.band)}` +
    ` — quadro ${i + 1} de ${state.frames.length}`;
  el.slider.value = i;
  el.slider.setAttribute("aria-valuetext", `${fmtDateTime(f.date)}, detector ${show(f.detector)}`);
  el.galeria.querySelectorAll("button").forEach((b, k) =>
    k === i ? b.setAttribute("aria-current", "true") : b.removeAttribute("aria-current"));

  const m = f.meta ?? {};
  const wl = m.wavelength_min_nm != null && m.wavelength_max_nm != null
    ? `${m.wavelength_min_nm}–${m.wavelength_max_nm} nm` : null;
  const rows = [
    ["Data da observação (UTC)", f.date],
    ["Origem da data", m.timing_status],
    ["Identificador", f.id],
    ["Produto no arquivo", m.product_id],
    ["Detector", f.detector],
    ["Banda", f.band],
    ["Comprimento de onda", wl],
    ["Tempo de exposição (s)", m.exposure_time_s],
    ["Data release", m.data_release],
    ["Normalização visual", m.visual_normalization],
    ["Fonte dos dados", state.isMock ? "Fictícia (teste)" : "SPHEREx / IRSA-IPAC"],
  ].map(([k, v]) => [k, show(v)]);
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
  el.galeriaAviso.hidden = true;
}

// Exibe no máximo CONFIG.GALLERY_MAX miniaturas (com loading="lazy") para não
// pedir centenas de imagens ao backend de uma vez.
function renderGallery(frames) {
  el.galeriaVazio.hidden = true;
  const shown = frames.slice(0, CONFIG.GALLERY_MAX);
  el.galeriaAviso.hidden = shown.length === frames.length;
  el.galeriaAviso.textContent =
    `Mostrando as ${shown.length} primeiras de ${frames.length} observações. ` +
    "Use o player ou o filtro por detector para ver as demais.";
  el.galeria.replaceChildren(
    ...shown.map((f, i) => {
      const li = document.createElement("li");
      const btn = document.createElement("button");
      btn.type = "button";
      const img = document.createElement("img");
      if (f.imageUrl) img.src = f.imageUrl;
      img.loading = "lazy";
      img.alt = "";
      const label = document.createElement("span");
      label.textContent = `${fmtDate(f.date)} · ${show(f.detector)}`;
      btn.setAttribute("aria-label", `Ver observação de ${fmtDateTime(f.date)}, detector ${show(f.detector)}`);
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

const detectorKey = (f) => f.detector ?? "—";

// Preenche o filtro com "Todos" + os detectores presentes na resposta.
function fillDetectorSelect(frames) {
  const dets = [...new Set(frames.map(detectorKey))].sort();
  el.detector.replaceChildren(
    new Option("Todos", ""),
    ...dets.map((d) => new Option(d === "—" ? "Sem detector" : d, d))
  );
  el.detector.value = "";
}

// Aplica o filtro por detector e reinicia o player na nova sequência.
function applyDetectorFilter() {
  stop();
  const det = el.detector.value;
  const frames = det ? state.allFrames.filter((f) => detectorKey(f) === det) : state.allFrames;
  state.frames = frames;
  el.slider.max = frames.length - 1;
  el.tIni.textContent = fmtDate(frames[0].date);
  el.tFim.textContent = fmtDate(frames.at(-1).date);
  renderGallery(frames);
  showFrame(0);

  const instants = new Set(frames.map((f) => f.date)).size;
  const nDets = new Set(frames.map(detectorKey)).size;
  let msg = `${frames.length} observações em ordem cronológica (${instants} instantes distintos).`;
  if (!det && nDets > 1) {
    msg += ` Atenção: ${nDets} detectores diferentes estão intercalados; quadros vizinhos podem ser` +
           " do mesmo instante em detectores distintos. Escolha um detector para ver uma sequência temporal.";
  }
  if (state.omitted) {
    msg += ` ${state.omitted} observação(ões) sem data de observação foram omitidas da sequência.`;
  }
  setStatus(msg);
}

function loadFrames({ frames, omitted }, isMock) {
  stop();
  state.allFrames = frames;
  state.omitted = omitted;
  state.isMock = isMock;
  el.avisoMock.hidden = !isMock;
  el.player.hidden = false;
  fillDetectorSelect(frames);
  applyDetectorFilter();
}

/* ---------- Fluxo de busca ---------- */
async function onSubmit(e) {
  e.preventDefault();
  const values = validate();
  if (!values) return;

  stop();
  el.player.hidden = true;
  clearGallery();
  el.buscar.disabled = true;
  setStatus("Buscando observações no arquivo SPHEREx… isso pode levar alguns segundos.", "carregando");

  try {
    const result = el.mock.checked ? mockObservations() : await fetchObservations(values);
    if (!result.frames.length) {
      setStatus(
        result.omitted
          ? `Foram encontradas ${result.omitted} observação(ões), mas nenhuma tem data de observação; não é possível montar a sequência temporal.`
          : "Nenhuma observação encontrada para essa região. Tente aumentar o tamanho da área (FOV) ou escolher outro ponto."
      );
      return;
    }
    loadFrames(result, el.mock.checked);
  } catch (err) {
    const timedOut = err === "timeout" || err?.name === "AbortError";
    if (timedOut && state.controller?.signal.reason !== "timeout") return; // busca substituída
    setStatus(
      timedOut
        ? "A busca demorou demais. Tente novamente em instantes."
        : errorMessage(err),
      err?.code === "NO_OBSERVATIONS_FOUND" ? "" : "erro"
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
el.detector.addEventListener("change", applyDetectorFilter);
el.slider.addEventListener("input", () => { stop(); showFrame(Number(el.slider.value)); });
el.img.addEventListener("error", () =>
  setStatus("Não foi possível carregar esta imagem. Tente outro quadro.", "erro"));

document.querySelectorAll(".chip").forEach((chip) =>
  chip.addEventListener("click", () => {
    el.ra.value = chip.dataset.ra;
    el.dec.value = chip.dataset.dec;
    el.fov.value = chip.dataset.fov;
    el.form.requestSubmit();
  })
);

// Atalhos de teclado no visualizador (fora de campos de texto)
document.addEventListener("keydown", (e) => {
  if (el.player.hidden || e.target.matches("input[inputmode], select")) return;
  if (e.key === "ArrowLeft") step(-1);
  else if (e.key === "ArrowRight") step(1);
});

// Destaca no menu lateral a seção visível
const navLinks = [...document.querySelectorAll(".sidebar a")];
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
