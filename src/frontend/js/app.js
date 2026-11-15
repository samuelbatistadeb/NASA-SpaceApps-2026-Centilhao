"use strict";

/* ============================================================
 * SPHEREx Explorer — frontend
 * Ajuste CONFIG e a função normalizeObservation() conforme
 * docs/architecture/api-contract.md.
 * ============================================================ */
const CONFIG = {
  API_BASE: "http://localhost:8000",
  OBSERVATIONS_PATH: "/api/observations", // GET ?ra_deg=&dec_deg=&fov_arcmin= (src/backend/app/api/observations.py)
  SPHEREX_HIPS_BASE: "https://alasky.cds.unistra.fr/SPHEREx/D", // + número do detector (1 a 6). Mapas HiPS do CDS, versão QR2: atualizar quando houver HiPS do DR1
  // Fontes do Aladin Lite, tentadas em ordem até uma funcionar. Versão fixa primeiro (mais previsível que "latest").
  // "script" = <script> clássico (define window.A); "module" = pacote npm (ES module) via import().
  ALADIN_SOURCES: [
    { type: "script", url: "https://aladin.cds.unistra.fr/AladinLite/api/v3/3.8.1/aladin.js" },
    { type: "script", url: "https://aladin.cds.unistra.fr/AladinLite/api/v3/latest/aladin.js" },
    { type: "module", url: "https://cdn.jsdelivr.net/npm/aladin-lite@3.8.1/dist/aladin.js" },
  ],
  SPECTRUM_PATH: "/api/spectrum", // ASSUMIDO: GET ?ra=&dec=&radius= (raio em segundos de arco)
  SPECTRUM_TIMEOUT_MS: 30000,
  IMAGE_EAST_LEFT: true, // ASSUMIDO: imagem com norte para cima e leste à esquerda (confirmar com o backend)
  TARGETS_PATH: "/api/targets", // GET → { targets: [{ name, ra, dec, fov, note }] }
  TIMEOUT_MS: 120000, // a primeira consulta ao IRSA pode levar dezenas de segundos
  EXTRA_PARAMS: {}, // parâmetros extras repassados ao backend
  FOV_MIN: 0.5,
  FOV_MAX: 30, // minutos de arco (o backend aceita 0,1 a 120)
  // Cada miniatura gera um recorte no IRSA (~10–15 s, sem cache): limitar evita sobrecarga.
  GALLERY_MAX: 24,
  // Miniaturas baixadas ao mesmo tempo (o IRSA responde 503 "Server busy" com muitos pedidos simultâneos).
  THUMB_CONCURRENCY: 2,
};

// Mensagens para os códigos de erro do backend (src/backend/app/api/errors.py).
const API_ERRORS = {
  NO_OBSERVATIONS_FOUND: "Nenhuma observação encontrada para essa região. Tente aumentar o tamanho da área (FOV) ou escolher outro ponto.",
  SOURCE_UNAVAILABLE: "O arquivo SPHEREx (IRSA) está indisponível ou ocupado no momento. Tente novamente em instantes.",
};

class ApiError extends Error {
  constructor(status, code, message) {
    super(message || `HTTP ${status}`);
    this.status = status;
    this.code = code;
  }
}

// Lê o envelope { error: { code, message } } do backend.
async function apiError(res) {
  const body = await res.json().catch(() => null);
  return new ApiError(res.status, body?.error?.code ?? null, body?.error?.message ?? null);
}

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
  visor: $("visor"), imgwrap: $("imgwrap"),
  ceuAbrir: $("ceu-abrir"), ceuTudo: $("ceu-tudo"), ceuFundo: $("ceu-fundo"), ceuGaia: $("ceu-gaia"), ceuWise: $("ceu-wise"),
  ceuMapa: $("ceu-mapa"), ceuStatus: $("ceu-status"),
  mapaGraf: $("mapa-grafico"), mapaVazio: $("mapa-vazio"), mapaMock: $("mapa-mock"),
  espStatus: $("esp-status"), espGraf: $("esp-grafico"), espTabBox: $("esp-tabela-box"),
  espTabela: $("esp-tabela"), raio: $("raio"), espCentro: $("esp-centro"), espLimpar: $("esp-limpar"), espCsv: $("esp-csv"), filtroVazio: $("filtro-vazio"), reset: $("filtro-reset"), galeria: $("galeria-lista"), galeriaVazio: $("galeria-vazio"), tIni: $("t-ini"), tFim: $("t-fim"), meta: $("meta"),
};

const state = { mapDots: new Map(), mapRing: null, pts: { A: null, B: null }, active: "A", specCtl: {}, rows: [], keys: [], values: null, all: [], wls: [], detectors: new Set(), frames: [], index: 0, timer: null, isMock: false, controller: null, omitted: 0 };

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

// Data e hora UTC: vários quadros podem cair no mesmo dia (exposições de ~2 min).
const fmtDateTime = (iso) =>
  new Date(iso).toLocaleString("pt-BR", { dateStyle: "long", timeStyle: "short", timeZone: "UTC" }) + " UTC";

function setStatus(msg, kind = "") {
  el.status.textContent = msg;
  el.status.className = "status " + kind;
}

/* ---------- Validação ---------- */
const RULES = {
  ra:  { min: 0,   max: 360, exclusiveMax: true, msg: "Informe graus (0 até menos de 360) ou h/m/s, ex.: 08h55m10.831s." },
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
    const ok = input.value.trim() !== "" && Number.isFinite(n) && n >= rule.min &&
      (rule.exclusiveMax ? n < rule.max : n <= rule.max);
    input.setAttribute("aria-invalid", String(!ok));
    $(name + "-erro").textContent = ok ? "" : rule.msg;
    if (!ok && !firstInvalid) firstInvalid = input;
    values[name] = Number(n.toFixed(6));
  }
  if (firstInvalid) { firstInvalid.focus(); return null; }
  return values;
}

/* ---------- API ---------- */
// Converte uma observação do backend (schemas/observation.py) para o formato interno.
// Cada observação é UMA exposição de UM detector. O comprimento de onda varia dentro
// da imagem (filtro linear variável), por isso guardamos a faixa, não um valor único.
function normalizeObservation(o) {
  const m = o.metadata ?? {};
  const img = o.image_url ?? "";
  const det = parseInt(String(o.detector ?? "").replace(/\D/g, ""), 10);
  const detOk = det >= 1 && det <= 6; // SPHEREx: seis detectores (D1 a D6)
  const nmToUm = (v) => (v === null || v === undefined || !Number.isFinite(Number(v)) ? null : Number(v) / 1000);
  const wlMin = nmToUm(m.wavelength_min_nm);
  const wlMax = nmToUm(m.wavelength_max_nm);
  return {
    id: o.id, // identificador interno da observação (usado em /api/images/{id})
    productId: m.product_id ?? "—",
    date: o.observed_at ?? null, // ISO 8601 UTC, vindo de t_min (MJD) do IRSA
    imageUrl: img ? (/^(https?:|data:)/.test(img) ? img : CONFIG.API_BASE + img) : "",
    detector: detOk ? det : null,
    detectorLabel: detOk ? "D" + det : String(o.detector ?? "—"),
    wavelength: null, // não há um único comprimento de onda por imagem
    wlRange: wlMin !== null && wlMax !== null ? [wlMin, wlMax] : null, // micrômetros
    band: o.band ?? "—",
    product: m.data_release ?? "—",
    exposure: m.exposure_time_s ?? null,
    cutout: m.cutout_strategy ?? null,
  };
}

async function fetchObservations({ ra, dec, fov }) {
  state.controller?.abort();
  const controller = (state.controller = new AbortController());
  const timeout = setTimeout(() => controller.abort("timeout"), CONFIG.TIMEOUT_MS);
  const url = new URL(CONFIG.OBSERVATIONS_PATH, CONFIG.API_BASE);
  url.search = new URLSearchParams({
    ra_deg: ra, dec_deg: dec, fov_arcmin: fov, ...CONFIG.EXTRA_PARAMS,
  }).toString();

  try {
    const res = await fetch(url, { signal: controller.signal });
    if (!res.ok) throw await apiError(res);
    const data = await res.json();
    const all = (data.observations ?? []).map(normalizeObservation);
    // Observações sem data resolvível ficam fora da sequência temporal (e são contadas).
    const frames = all
      .filter((f) => f.date && !Number.isNaN(Date.parse(f.date)))
      .sort((a, b) => Date.parse(a.date) - Date.parse(b.date));
    state.omitted = all.length - frames.length;
    return frames;
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
      productId: "FICTICIO-" + String(i + 1).padStart(2, "0"), wlRange: null, exposure: null, cutout: null,
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
  el.img.alt = `Região do céu observada em ${fmtDateTime(f.date)}, detector ${f.detectorLabel}`;
  el.legenda.textContent =
    `${fmtDateTime(f.date)} · detector ${f.detectorLabel} — quadro ${i + 1} de ${state.frames.length}`;
  el.slider.value = i;
  highlightMap(f.id);
  el.slider.setAttribute("aria-valuetext", fmtDateTime(f.date));
  el.galeria.querySelectorAll("button").forEach((b, k) =>
    k === i ? b.setAttribute("aria-current", "true") : b.removeAttribute("aria-current"));

  const wlText = f.wlRange
    ? `${fmtWl(f.wlRange[0])} a ${fmtWl(f.wlRange[1])} (varia ao longo da imagem)`
    : f.wavelength === null ? "—" : fmtWl(f.wavelength);
  const rows = [
    ["Data da observação", fmtDateTime(f.date)],
    ["Identificador do produto", f.productId],
    ["Detector", f.detectorLabel],
    ["Faixa espectral do detector", wlText],
    ["Tempo de exposição", f.exposure === null ? "—" : `${Math.round(f.exposure)} s`],
    ["Coleção", f.product],
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

/* ---------- Fila de miniaturas ----------
 * Cada miniatura real é um recorte pedido ao IRSA (~10–15 s). As <img> nascem sem src
 * (URL em data-src) e a fila atribui src a no máximo CONFIG.THUMB_CONCURRENCY por vez.
 * A fila não avança enquanto a imagem principal (#imagem) estiver carregando.
 * Cada renderGallery() abre uma nova geração: a fila anterior é descartada. */
const thumbs = { gen: 0, queue: [], active: new Set() };

const mainImageBusy = () => !!el.img.getAttribute("src") && !el.img.complete;

function setThumbState(img, st) {
  const tag = img.parentElement?.querySelector(".thumb-estado");
  if (!tag) return;
  tag.textContent = st === "carregando" ? "carregando…" : st === "falha" ? "falha ao carregar" : "";
  tag.hidden = !tag.textContent;
  if (st === "falha") {
    // Troca a <img> por um quadrado neutro (o navegador mostraria o ícone de imagem quebrada).
    const ph = document.createElement("div");
    ph.className = "thumb-falha";
    ph.style.cssText = "width:100%;aspect-ratio:1;background:#000;border-radius:4px;opacity:.4";
    img.replaceWith(ph);
  }
}

// Descarta as miniaturas que ainda não receberam src. As que já estão baixando continuam
// contando no limite até terminar: o recorte no servidor segue em andamento de qualquer forma.
function resetThumbQueue() {
  thumbs.gen++;
  thumbs.queue = [];
}

function pumpThumbs() {
  if (mainImageBusy()) return; // a principal tem prioridade; o evento load/error dela chama pumpThumbs
  while (thumbs.active.size < CONFIG.THUMB_CONCURRENCY && thumbs.queue.length) {
    const img = thumbs.queue.shift();
    if (!img.isConnected) continue;
    const gen = thumbs.gen;
    const done = (ok) => {
      img.onload = img.onerror = null;
      thumbs.active.delete(img);
      if (gen === thumbs.gen) setThumbState(img, ok ? "ok" : "falha"); // galeria descartada: nada a atualizar
      pumpThumbs();
    };
    img.onload = () => done(true);
    img.onerror = () => done(false);
    thumbs.active.add(img);
    img.src = img.dataset.src;
  }
}

el.img.addEventListener("load", pumpThumbs);
el.img.addEventListener("error", pumpThumbs);

function clearGallery() {
  resetThumbQueue();
  el.galeria.replaceChildren();
  el.galeriaVazio.hidden = false;
}

// Não inicia a fila: quem chama deve definir a imagem principal (showFrame) e depois chamar pumpThumbs().
function renderGallery(frames) {
  resetThumbQueue();
  el.galeriaVazio.hidden = true;
  // Mantém os índices: o botão i mostra state.frames[i].
  el.galeria.replaceChildren(
    ...frames.slice(0, CONFIG.GALLERY_MAX).map((f, i) => {
      const li = document.createElement("li");
      const btn = document.createElement("button");
      btn.type = "button";
      const img = document.createElement("img");
      img.alt = "";
      const estado = document.createElement("small");
      estado.className = "thumb-estado";
      estado.style.cssText = "font-size:.7rem;opacity:.75";
      const label = document.createElement("span");
      label.textContent = `${fmtDate(f.date)} · ${f.detectorLabel}`;
      btn.setAttribute("aria-label", `Ver observação de ${fmtDateTime(f.date)}, detector ${f.detectorLabel}`);
      btn.append(img, estado, label);
      if (f.imageUrl.startsWith("data:")) {
        img.src = f.imageUrl; // modo fictício: imagem local, sem rede
        estado.hidden = true;
      } else if (!f.imageUrl) {
        setThumbState(img, "falha");
      } else {
        img.dataset.src = f.imageUrl;
        setThumbState(img, "carregando");
        thumbs.queue.push(img);
      }
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
// Divisão das 102 bandas: 6 detectores x 17 bandas. Faixas em µm conforme a página da missão no IRSA;
// a numeração sequencial das bandas (1 a 102) é uma convenção deste projeto.
const BANDS_PER_DETECTOR = 17;
const DET_RANGES = [[0.75, 1.1], [1.1, 1.6], [1.6, 2.4], [2.4, 3.8], [3.8, 4.4], [4.4, 5.0]]; // página da missão no IRSA
const fmtRange = ([a, b]) => `${a.toFixed(2).replace(".", ",")}–${b.toFixed(2).replace(".", ",")} µm`;

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
      const first = (d - 1) * BANDS_PER_DETECTOR + 1;
      const rng = document.createElement("small");
      rng.className = "rng";
      rng.textContent = fmtRange(DET_RANGES[d - 1]);
      b.append(sw, document.createTextNode("Detector " + d), rng);
      b.dataset.info = `Bandas ${first} a ${first + BANDS_PER_DETECTOR - 1}`;
      b.disabled = !present.has(d);
      b.setAttribute("aria-pressed", String(present.has(d)));
      b.title = present.has(d) ? b.dataset.info : "Sem observações deste detector nesta busca";
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
  const instants = new Set(frames.map((f) => f.date)).size;
  const detsVisible = new Set(frames.map((f) => f.detector).filter(Boolean)).size;
  el.contagem.textContent =
    `Mostrando ${frames.length} de ${state.all.length} observações (${instants} instantes distintos).` +
    (detsVisible > 1
      ? " Atenção: há detectores diferentes intercalados; cada detector vê outra faixa do infravermelho. Para comparar épocas, deixe só um detector ativo."
      : "") +
    (frames.length > CONFIG.GALLERY_MAX ? ` A galeria mostra as ${CONFIG.GALLERY_MAX} primeiras.` : "") +
    (state.omitted ? ` ${state.omitted} observação(ões) sem data foram omitidas.` : "");

  stop();
  state.frames = frames;
  renderMap();
  el.visor.hidden = !frames.length;
  el.filtroVazio.hidden = !!frames.length;
  if (!frames.length) { clearGallery(); return; }

  el.slider.max = frames.length - 1;
  el.tIni.textContent = fmtDate(frames[0].date);
  el.tFim.textContent = fmtDate(frames.at(-1).date);
  renderGallery(frames);
  const idx = frames.findIndex((f) => f.id === keepId);
  showFrame(idx >= 0 ? idx : 0);
  pumpThumbs(); // só começa se a imagem principal já estiver pronta; senão, espera o load/error dela
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
  clearPoints();
  updateSky({ recenter: true });
  if (!el.mock.checked) updateUrl(values);

  stop();
  el.player.hidden = true;
  clearGallery();
  clearMap();
  el.buscar.disabled = true;
  setStatus("Buscando observações no arquivo SPHEREx… isso pode levar alguns segundos.", "carregando");

  try {
    state.omitted = 0;
    const frames = el.mock.checked ? mockObservations() : await fetchObservations(values);
    if (!frames.length) {
      setStatus(API_ERRORS.NO_OBSERVATIONS_FOUND);
      return;
    }
    loadFrames(frames, el.mock.checked);
    setStatus(`${frames.length} observações em ordem cronológica · RA ${values.ra}°, Dec ${values.dec}°, FOV ${values.fov}′.`);
  } catch (err) {
    const timedOut = err === "timeout" || err?.name === "AbortError";
    if (timedOut && state.controller?.signal.reason !== "timeout") return; // busca substituída
    if (err instanceof ApiError) {
      // NO_OBSERVATIONS_FOUND é um resultado válido, não uma falha.
      const kind = err.code === "NO_OBSERVATIONS_FOUND" ? "" : "erro";
      setStatus(API_ERRORS[err.code] ?? err.message, kind);
      return;
    }
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

/* ---------- Espectro de um ponto ---------- */
const SVG_NS = "http://www.w3.org/2000/svg";
const svgEl = (tag, attrs = {}, text) => {
  const n = document.createElementNS(SVG_NS, tag);
  for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
  if (text !== undefined) n.textContent = text;
  return n;
};
const fmtNum = (v) => v.toLocaleString("pt-BR", { maximumSignificantDigits: 4 });

function setEspStatus(msg, kind = "") {
  el.espStatus.textContent = msg;
  el.espStatus.className = "status " + kind;
}

const radius = () => {
  const v = Number(el.raio.value);
  return Number.isFinite(v) ? Math.min(60, Math.max(3, v)) : 12;
};

// Converte a posição na imagem (frações 0..1) em RA/Dec.
// Assume que a imagem mostra um quadrado de lado FOV centrado em (ra, dec).
function coordFromFrac(fx, fy) {
  const { ra, dec, fov } = state.values;
  const dx = (fx - 0.5) * fov * 60; // segundos de arco para a direita
  const dy = (0.5 - fy) * fov * 60; // segundos de arco para cima (norte)
  const sinal = CONFIG.IMAGE_EAST_LEFT ? -1 : 1;
  const raPt = ra + (sinal * dx) / 3600 / Math.cos((dec * Math.PI) / 180);
  return { ra: ((raPt % 360) + 360) % 360, dec: Math.max(-90, Math.min(90, dec + dy / 3600)) };
}

/* Marcadores sobre a imagem */
const markers = {};
for (const k of ["A", "B"]) {
  const m = document.createElement("div");
  m.className = "marker";
  m.dataset.k = k;
  m.hidden = true;
  el.imgwrap.append(m);
  markers[k] = m;
}

function renderMarkers() {
  const lado = state.values ? Math.max(4, ((2 * radius()) / (state.values.fov * 60)) * 100) : 6;
  for (const k of ["A", "B"]) {
    const p = state.pts[k];
    markers[k].hidden = !p;
    if (!p) continue;
    markers[k].style.left = p.fx * 100 + "%";
    markers[k].style.top = p.fy * 100 + "%";
    markers[k].style.width = `max(14px, ${lado}%)`;
  }
  scheduleSky();
}

function placePoint(key, fx, fy, { defer = false } = {}) {
  if (!state.values) return;
  fx = Math.min(1, Math.max(0, fx));
  fy = Math.min(1, Math.max(0, fy));
  const old = state.pts[key];
  const pt = { fx, fy, ...coordFromFrac(fx, fy), data: null, req: null, timer: null };
  clearTimeout(old?.timer);
  state.pts[key] = pt;
  renderMarkers();
  renderChart();
  if (defer) pt.timer = setTimeout(() => loadSpectrum(key), 400);
  else loadSpectrum(key);
}

function clearPoints() {
  for (const k of ["A", "B"]) {
    clearTimeout(state.pts[k]?.timer);
    state.specCtl[k]?.abort();
    state.pts[k] = null;
  }
  renderMarkers();
  renderChart();
  setEspStatus("Faça uma busca e marque um ponto na imagem.");
  if (state.values) setEspStatus("Clique na imagem para marcar o ponto A (alvo).");
}

/* Dados: API ou, no modo de teste, espectro fictício */
function normalizeSpectrum(data) {
  const list = Array.isArray(data) ? data : data.points ?? data.spectrum ?? [];
  const points = list
    .map((o) => {
      const det = parseInt(String(o.detector ?? o.detector_id ?? "").replace(/\D/g, ""), 10);
      return {
        wl: Number(o.wavelength_um ?? o.wavelength ?? o.wl),
        flux: Number(o.flux ?? o.brightness ?? o.value),
        err: o.flux_err ?? o.error ?? null,
        det: det >= 1 && det <= 6 ? det : null,
        band: o.band_index ?? o.band ?? null,
      };
    })
    .filter((p) => Number.isFinite(p.wl) && Number.isFinite(p.flux))
    .map((p) => ({ ...p, err: p.err === null || p.err === "" || !Number.isFinite(Number(p.err)) ? null : Number(p.err) }))
    .sort((a, b) => a.wl - b.wl);
  return { unit: data.unit ?? null, points };
}

async function fetchSpectrum(key, pt) {
  state.specCtl[key]?.abort();
  const ctl = (state.specCtl[key] = new AbortController());
  const timer = setTimeout(() => ctl.abort(), CONFIG.SPECTRUM_TIMEOUT_MS);
  try {
    const url = new URL(CONFIG.SPECTRUM_PATH, CONFIG.API_BASE);
    url.search = new URLSearchParams({
      ra: pt.ra.toFixed(6), dec: pt.dec.toFixed(6), radius: radius(), ...CONFIG.EXTRA_PARAMS,
    }).toString();
    const res = await fetch(url, { signal: ctl.signal });
    if (!res.ok) throw new Error("http-" + res.status);
    return normalizeSpectrum(await res.json());
  } finally {
    clearTimeout(timer);
  }
}

// Espectro inventado, só para testar a interface (o centro da imagem é mais brilhante).
function mockSpectrum(pt) {
  const r = Math.hypot(pt.fx - 0.5, pt.fy - 0.5);
  const ganho = 0.15 + 1.85 * Math.exp(-((r / 0.15) ** 2));
  const points = [];
  DET_RANGES.forEach(([lo, hi], d) => {
    for (let k = 0; k < BANDS_PER_DETECTOR; k++) {
      const wl = lo + ((hi - lo) * (k + 0.5)) / BANDS_PER_DETECTOR;
      const flux = (40 * Math.exp(-wl / 1.6) + 6 + 3 * Math.sin(wl * 5)) * ganho;
      points.push({ wl, flux, err: 0.06 * flux + 0.4, det: d + 1, band: d * BANDS_PER_DETECTOR + k + 1 });
    }
  });
  return { unit: "valor fictício", points };
}

async function loadSpectrum(key) {
  const pt = state.pts[key];
  if (!pt) return;
  const req = (pt.req = {});
  pt.data = null;
  renderChart();
  setEspStatus(`Calculando o espectro do ponto ${key}…`, "carregando");
  try {
    const data = state.isMock ? mockSpectrum(pt) : await fetchSpectrum(key, pt);
    if (pt.req !== req || state.pts[key] !== pt) return;
    if (!data.points.length) {
      setEspStatus(`Sem dados espectrais para o ponto ${key}. Tente aumentar o raio ou escolher outro ponto.`);
      return;
    }
    pt.data = data;
    renderChart();
    setEspStatus(
      `Ponto ${key}: ${data.points.length} bandas, raio de ${radius()}″, RA ${pt.ra.toFixed(4)}°, Dec ${pt.dec.toFixed(4)}°.` +
        (state.isMock ? " (dados fictícios)" : "")
    );
  } catch (err) {
    if (pt.req !== req || state.pts[key] !== pt) return;
    setEspStatus(
      err?.name === "AbortError"
        ? "O cálculo do espectro demorou demais. Tente novamente."
        : err?.message === "http-404"
          ? "O espectro de um ponto com dados reais ainda não está disponível no backend. Use os dados fictícios para testar esta seção."
          : "Não foi possível obter o espectro. Verifique se o backend está em execução.",
      "erro"
    );
  }
}

/* Gráfico (SVG) e tabela */
function niceStep(range, n = 5) {
  const raw = range / n;
  const p = 10 ** Math.floor(Math.log10(raw));
  const f = raw / p;
  return (f < 1.5 ? 1 : f < 3 ? 2 : f < 7 ? 5 : 10) * p;
}

function renderChart() {
  const series = ["A", "B"]
    .filter((k) => state.pts[k]?.data?.points.length)
    .map((k) => ({ key: k, pts: state.pts[k].data.points, unit: state.pts[k].data.unit }));
  el.espGraf.hidden = el.espTabBox.hidden = !series.length;
  if (!series.length) return;

  const W = 720, H = 360, m = { l: 64, r: 16, t: 16, b: 48 };
  const xmin = 0.7, xmax = 5.05;
  const all = series.flatMap((s) => s.pts);
  let ymin = Math.min(0, ...all.map((p) => p.flux - (p.err ?? 0)));
  let ymax = Math.max(...all.map((p) => p.flux + (p.err ?? 0)));
  if (ymax <= ymin) ymax = ymin + 1;
  const step = niceStep(ymax - ymin);
  ymin = Math.floor(ymin / step) * step;
  ymax = Math.ceil(ymax / step) * step;
  const X = (w) => m.l + ((w - xmin) / (xmax - xmin)) * (W - m.l - m.r);
  const Y = (v) => H - m.b - ((v - ymin) / (ymax - ymin)) * (H - m.t - m.b);
  const unit = series.find((s) => s.unit)?.unit ?? "unidades do backend";

  const svg = svgEl("svg", {
    viewBox: `0 0 ${W} ${H}`, role: "img",
    "aria-label": `Gráfico de brilho por comprimento de onda para ${series.map((s) => "o ponto " + s.key).join(" e ")}. Os mesmos dados estão na tabela abaixo.`,
  });

  DET_RANGES.forEach(([a, b], i) => {
    svg.append(svgEl("rect", { x: X(a), y: m.t, width: X(b) - X(a), height: H - m.t - m.b, fill: DET_COLORS[i], opacity: 0.12 }));
    svg.append(svgEl("text", { x: (X(a) + X(b)) / 2, y: m.t + 12, "text-anchor": "middle", fill: "var(--muted)", "font-size": 11 }, "D" + (i + 1)));
  });
  for (let w = 1; w <= 5; w++) {
    svg.append(svgEl("line", { x1: X(w), x2: X(w), y1: m.t, y2: H - m.b, stroke: "var(--line)" }));
    svg.append(svgEl("text", { x: X(w), y: H - m.b + 16, "text-anchor": "middle", fill: "var(--muted)", "font-size": 12 }, String(w)));
  }
  const n = Math.round((ymax - ymin) / step);
  for (let i = 0; i <= n; i++) {
    const v = ymin + i * step;
    svg.append(svgEl("line", { x1: m.l, x2: W - m.r, y1: Y(v), y2: Y(v), stroke: "var(--line)" }));
    svg.append(svgEl("text", { x: m.l - 8, y: Y(v) + 4, "text-anchor": "end", fill: "var(--muted)", "font-size": 12 }, fmtNum(v)));
  }
  svg.append(svgEl("text", { x: (m.l + W - m.r) / 2, y: H - 8, "text-anchor": "middle", fill: "var(--text)", "font-size": 13 }, "Comprimento de onda (µm)"));
  svg.append(svgEl("text", { transform: `translate(14 ${(m.t + H - m.b) / 2}) rotate(-90)`, "text-anchor": "middle", fill: "var(--text)", "font-size": 13 }, `Brilho (${unit})`));

  for (const s of series) {
    const cor = s.key === "A" ? "var(--ir)" : "var(--cool)";
    svg.append(svgEl("polyline", {
      points: s.pts.map((p) => `${X(p.wl)},${Y(p.flux)}`).join(" "),
      fill: "none", stroke: cor, "stroke-width": 1.5, opacity: 0.7,
      "stroke-dasharray": s.key === "B" ? "6 4" : "none",
    }));
    for (const p of s.pts) {
      const x = X(p.wl), y = Y(p.flux);
      const fill = p.det ? DET_COLORS[p.det - 1] : "#ffffff";
      if (p.err) svg.append(svgEl("line", { x1: x, x2: x, y1: Y(p.flux - p.err), y2: Y(p.flux + p.err), stroke: cor, opacity: 0.6 }));
      const forma = s.key === "A"
        ? svgEl("circle", { cx: x, cy: y, r: 3.5, fill, stroke: "#fff", "stroke-width": 0.8 })
        : svgEl("polygon", { points: `${x},${y - 4.5} ${x + 4.5},${y} ${x},${y + 4.5} ${x - 4.5},${y}`, fill, stroke: "#fff", "stroke-width": 0.8 });
      forma.append(svgEl("title", {}, `${s.key} · ${fmtNum(p.wl)} µm · ${p.det ? "D" + p.det : "detector ?"} · banda ${p.band ?? "?"} · brilho ${fmtNum(p.flux)}`));
      svg.append(forma);
    }
  }

  const legenda = document.createElement("ul");
  legenda.className = "legenda";
  const itens = DET_COLORS.map((c, i) => [c, `D${i + 1} (${fmtRange(DET_RANGES[i])})`]);
  for (const [c, texto] of itens) {
    const li = document.createElement("li");
    const sw = document.createElement("span");
    sw.className = "sw";
    sw.style.background = c;
    li.append(sw, texto);
    legenda.append(li);
  }
  for (const s of series) {
    const li = document.createElement("li");
    li.textContent = s.key === "A" ? "A: círculos, linha contínua" : "B: losangos, linha tracejada";
    legenda.append(li);
  }
  el.espGraf.replaceChildren(svg, legenda);
  renderTable(series);
}

function renderTable(series) {
  const rows = new Map();
  for (const s of series) {
    for (const p of s.pts) {
      const id = `${p.band ?? ""}|${p.wl.toFixed(4)}`;
      const r = rows.get(id) ?? { wl: p.wl, det: p.det, band: p.band };
      r[s.key] = p;
      rows.set(id, r);
    }
  }
  const keys = series.map((s) => s.key);
  const list = [...rows.values()].sort((a, b) => a.wl - b.wl);
  state.rows = list;
  state.keys = keys;

  const tr = (cells, tag = "td") => {
    const row = document.createElement("tr");
    for (const c of cells) {
      const cell = document.createElement(tag);
      if (tag === "th") cell.scope = "col";
      cell.textContent = c;
      row.append(cell);
    }
    return row;
  };
  const cap = document.createElement("caption");
  cap.textContent = "Brilho por comprimento de onda";
  const thead = document.createElement("thead");
  thead.append(tr(["Banda", "Detector", "Comprimento de onda (µm)", ...keys.map((k) => "Brilho " + k)], "th"));
  const tbody = document.createElement("tbody");
  for (const r of list) {
    tbody.append(tr([
      r.band ?? "—", r.det ? "D" + r.det : "—", fmtNum(r.wl),
      ...keys.map((k) => (r[k] ? fmtNum(r[k].flux) : "—")),
    ]));
  }
  el.espTabela.replaceChildren(cap, thead, tbody);
}

function downloadCsv() {
  const keys = state.keys;
  const linhas = [["banda", "detector", "comprimento_de_onda_um", ...keys.map((k) => "brilho_" + k), ...keys.map((k) => "erro_" + k)].join(",")];
  for (const r of state.rows) {
    linhas.push([
      r.band ?? "", r.det ?? "", r.wl,
      ...keys.map((k) => r[k]?.flux ?? ""),
      ...keys.map((k) => r[k]?.err ?? ""),
    ].join(","));
  }
  const url = URL.createObjectURL(new Blob([linhas.join("\n")], { type: "text/csv" }));
  const a = Object.assign(document.createElement("a"), { href: url, download: "espectro.csv" });
  a.click();
  URL.revokeObjectURL(url);
}

/* Eventos do espectro */
const activeKey = () => document.querySelector('input[name="ponto"]:checked').value;

el.imgwrap.addEventListener("click", (e) => {
  const r = el.imgwrap.getBoundingClientRect();
  placePoint(activeKey(), (e.clientX - r.left) / r.width, (e.clientY - r.top) / r.height);
});

el.imgwrap.addEventListener("keydown", (e) => {
  const key = activeKey();
  const passo = e.shiftKey ? 0.01 : 0.04;
  const p = state.pts[key] ?? { fx: 0.5, fy: 0.5 };
  const mov = { ArrowLeft: [-passo, 0], ArrowRight: [passo, 0], ArrowUp: [0, -passo], ArrowDown: [0, passo] }[e.key];
  if (mov) {
    e.preventDefault();
    placePoint(key, p.fx + mov[0], p.fy + mov[1], { defer: true });
  } else if (e.key === "Enter" || e.key === " ") {
    e.preventDefault();
    placePoint(key, p.fx, p.fy);
  } else if (e.key === "Escape" && state.pts[key]) {
    state.pts[key] = null;
    renderMarkers();
    renderChart();
  }
});

el.espCentro.addEventListener("click", () => placePoint(activeKey(), 0.5, 0.5));
el.espLimpar.addEventListener("click", clearPoints);
el.espCsv.addEventListener("click", downloadCsv);
el.raio.addEventListener("change", () => {
  renderMarkers();
  for (const k of ["A", "B"]) if (state.pts[k]) loadSpectrum(k);
});

/* ---------- Mapa de observações (plano cartesiano: data × comprimento de onda) ---------- */
const MAPA_VAZIO_PADRAO = "O mapa aparece depois de uma busca.";

function clearMap(msg = MAPA_VAZIO_PADRAO) {
  el.mapaGraf.replaceChildren();
  el.mapaGraf.hidden = true;
  el.mapaMock.hidden = true;
  el.mapaVazio.textContent = msg;
  el.mapaVazio.hidden = false;
  state.mapDots = new Map();
  state.mapRing = null;
}

function highlightMap(id) {
  const dot = state.mapDots.get(id);
  if (!state.mapRing) return;
  if (!dot) { state.mapRing.setAttribute("visibility", "hidden"); return; }
  state.mapRing.setAttribute("cx", dot.getAttribute("cx"));
  state.mapRing.setAttribute("cy", dot.getAttribute("cy"));
  state.mapRing.setAttribute("visibility", "visible");
}

function renderMap() {
  const all = state.all;
  const useWl = all.some((f) => f.wavelength !== null);
  const useDet = !useWl && all.some((f) => f.detector);
  const pts = all.filter((f) => (useWl ? f.wavelength !== null : useDet && f.detector));
  if (!pts.length) {
    clearMap("O mapa precisa do comprimento de onda ou do detector de cada observação, e esses dados não vieram na busca.");
    return;
  }

  const W = 720, H = 340, m = { l: 64, r: 16, t: 16, b: 48 };
  const ts = pts.map((f) => Date.parse(f.date));
  let t0 = Math.min(...ts), t1 = Math.max(...ts);
  if (t1 === t0) { t0 -= 15 * 864e5; t1 += 15 * 864e5; }
  else { const pad = (t1 - t0) * 0.04; t0 -= pad; t1 += pad; }
  const yMin = useWl ? 0.7 : 0.5, yMax = useWl ? 5.05 : 6.5;
  const X = (t) => m.l + ((t - t0) / (t1 - t0)) * (W - m.l - m.r);
  const Y = (v) => H - m.b - ((v - yMin) / (yMax - yMin)) * (H - m.t - m.b);
  const yOf = (f) => (useWl ? f.wavelength : f.detector);

  const svg = svgEl("svg", {
    viewBox: `0 0 ${W} ${H}`, role: "img",
    "aria-label": `Plano cartesiano com ${pts.length} observações: data na horizontal e ${useWl ? "comprimento de onda" : "detector"} na vertical, com uma cor por detector. Use a linha do tempo ou a galeria para navegar pelos mesmos quadros.`,
  });

  // eixo vertical
  if (useWl) {
    DET_RANGES.forEach(([a, b], i) => {
      svg.append(svgEl("rect", { x: m.l, y: Y(b), width: W - m.l - m.r, height: Y(a) - Y(b), fill: DET_COLORS[i], opacity: 0.1 }));
      svg.append(svgEl("text", { x: W - m.r - 4, y: Y(b) + 12, "text-anchor": "end", fill: "var(--muted)", "font-size": 11 }, "D" + (i + 1)));
    });
    for (let w = 1; w <= 5; w++) {
      svg.append(svgEl("line", { x1: m.l, x2: W - m.r, y1: Y(w), y2: Y(w), stroke: "var(--line)" }));
      svg.append(svgEl("text", { x: m.l - 8, y: Y(w) + 4, "text-anchor": "end", fill: "var(--muted)", "font-size": 12 }, String(w)));
    }
  } else {
    for (let d = 1; d <= 6; d++) {
      svg.append(svgEl("line", { x1: m.l, x2: W - m.r, y1: Y(d), y2: Y(d), stroke: "var(--line)" }));
      svg.append(svgEl("text", { x: m.l - 8, y: Y(d) + 4, "text-anchor": "end", fill: "var(--muted)", "font-size": 12 }, "D" + d));
    }
  }
  // eixo horizontal (datas)
  for (let i = 0; i <= 4; i++) {
    const t = t0 + ((t1 - t0) * i) / 4;
    svg.append(svgEl("line", { x1: X(t), x2: X(t), y1: m.t, y2: H - m.b, stroke: "var(--line)" }));
    svg.append(svgEl("text", { x: X(t), y: H - m.b + 16, "text-anchor": "middle", fill: "var(--muted)", "font-size": 12 },
      new Date(t).toLocaleDateString("pt-BR", { month: "short", year: "2-digit", timeZone: "UTC" })));
  }
  svg.append(svgEl("text", { x: (m.l + W - m.r) / 2, y: H - 8, "text-anchor": "middle", fill: "var(--text)", "font-size": 13 }, "Data da observação"));
  svg.append(svgEl("text", { transform: `translate(14 ${(m.t + H - m.b) / 2}) rotate(-90)`, "text-anchor": "middle", fill: "var(--text)", "font-size": 13 },
    useWl ? "Comprimento de onda (µm)" : "Detector"));

  // pontos
  const visiveis = new Set(state.frames.map((f) => f.id));
  state.mapDots = new Map();
  for (const f of pts) {
    const ok = visiveis.has(f.id);
    const c = svgEl("circle", {
      cx: X(Date.parse(f.date)), cy: Y(yOf(f)), r: 4.5,
      fill: f.detector ? DET_COLORS[f.detector - 1] : "#ffffff",
      stroke: "#fff", "stroke-width": 0.8, opacity: ok ? 0.95 : 0.15,
    });
    c.style.cursor = ok ? "pointer" : "default";
    c.append(svgEl("title", {}, `${fmtDate(f.date)} · ${f.detectorLabel} · ${f.wavelength === null ? "—" : fmtWl(f.wavelength)}${ok ? "" : " (oculta pelos filtros)"}`));
    c.addEventListener("click", () => {
      const i = state.frames.findIndex((x) => x.id === f.id);
      if (i >= 0) { stop(); showFrame(i); }
    });
    state.mapDots.set(f.id, c);
    svg.append(c);
  }
  state.mapRing = svgEl("circle", { r: 8, fill: "none", stroke: "#fff", "stroke-width": 2, "pointer-events": "none", visibility: "hidden" });
  svg.append(state.mapRing);

  const legenda = document.createElement("ul");
  legenda.className = "legenda";
  DET_COLORS.forEach((cor, i) => {
    const li = document.createElement("li");
    const sw = document.createElement("span");
    sw.className = "sw";
    sw.style.background = cor;
    li.append(sw, `D${i + 1} (${fmtRange(DET_RANGES[i])})`);
    legenda.append(li);
  });
  const atual = document.createElement("li");
  atual.textContent = "Anel branco: quadro em exibição";
  legenda.append(atual);

  el.mapaGraf.replaceChildren(svg, legenda);
  el.mapaGraf.hidden = false;
  el.mapaVazio.hidden = true;
  el.mapaMock.hidden = !state.isMock;
}

/* ---------- Mapa do céu (Aladin Lite, carregado só quando o usuário pede) ---------- */
const sky = { A: null, aladin: null, timer: null };

// Fundo do mapa: por padrão, os mapas HiPS da própria missão SPHEREx (um por detector)
(function preencherFundos() {
  const spherex = document.createElement("optgroup");
  spherex.label = "SPHEREx (dados da NASA)";
  DET_RANGES.forEach((r, i) =>
    spherex.append(new Option(`SPHEREx D${i + 1} · ${fmtRange(r)}`, CONFIG.SPHEREX_HIPS_BASE + (i + 1))));
  const outros = document.createElement("optgroup");
  outros.label = "Outros telescópios (comparação)";
  [["DSS2 (luz visível)", "P/DSS2/color"], ["2MASS (infravermelho próximo)", "P/2MASS/color"], ["AllWISE (infravermelho)", "P/allWISE/color"]]
    .forEach(([nome, id]) => outros.append(new Option(nome, id)));
  el.ceuFundo.replaceChildren(spherex, outros);
})();

function setCeuStatus(msg, kind = "") {
  el.ceuStatus.textContent = msg;
  el.ceuStatus.className = "status " + kind;
}

function loadScript(url) {
  return new Promise((resolve, reject) => {
    const el = document.createElement("script");
    el.src = url;
    el.onload = resolve;
    el.onerror = () => { el.remove(); reject(new Error("Falha ao baixar o script do Aladin Lite: " + url)); };
    document.head.append(el);
  });
}

async function loadAladin() {
  // Já carregado: só espera A.init (que rejeita, p.ex., sem WebGL2)
  if (window.A?.aladin) { await window.A.init; return window.A; }
  const falhas = [];
  for (const src of CONFIG.ALADIN_SOURCES) {
    try {
      if (src.type === "module") window.A = (await import(src.url)).default;
      else await loadScript(src.url);
      if (!window.A?.aladin) throw new Error("O código do Aladin carregou, mas window.A não existe: " + src.url);
      await window.A.init; // rejeita se o navegador não tiver WebGL2: não adianta tentar outra fonte
      return window.A;
    } catch (err) {
      if (/webgl/i.test(String(err))) throw err;
      console.warn("Mapa do céu: fonte falhou, tentando a próxima.", err);
      window.A = undefined;
      falhas.push(err);
    }
  }
  throw falhas.at(-1) ?? new Error("Nenhuma fonte do Aladin Lite configurada.");
}

const wrapRa = (ra) => ((ra % 360) + 360) % 360;

function drawSkyLayers() {
  const al = sky.aladin, A = sky.A, v = state.values;
  if (!al || !v) return;
  try {
    al.removeLayers();
    // retângulo da área pesquisada (coordenadas do céu: leste = RA crescente)
    const h = v.fov / 120; // meia largura, em graus
    const k = h / Math.cos((v.dec * Math.PI) / 180);
    const ov = A.graphicOverlay({ color: "#ff5c8a", lineWidth: 2 });
    al.addOverlay(ov);
    ov.addFootprints([A.polygon([
      [wrapRa(v.ra - k), v.dec - h], [wrapRa(v.ra + k), v.dec - h],
      [wrapRa(v.ra + k), v.dec + h], [wrapRa(v.ra - k), v.dec + h],
    ])]);

    const marca = (name, color, shape, size, list) => {
      if (!list.length) return;
      const cat = A.catalog({ name, shape, color, sourceSize: size, onClick: "showPopup" });
      al.addCatalog(cat);
      cat.addSources(list.map((s) => A.source(s.ra, s.dec, { nome: s.name })));
    };
    marca("Centro da busca", "#ffffff", "cross", 16, [{ ra: v.ra, dec: v.dec, name: "Centro da busca" }]);
    marca("Ponto A", "#ff5c8a", "circle", 14, state.pts.A ? [{ ra: state.pts.A.ra, dec: state.pts.A.dec, name: "Ponto A" }] : []);
    marca("Ponto B", "#7fd1ff", "square", 14, state.pts.B ? [{ ra: state.pts.B.ra, dec: state.pts.B.dec, name: "Ponto B" }] : []);

    const raio = Math.max((v.fov / 60) * 0.8, 0.02); // graus
    const alvo = `${v.ra} ${v.dec}`;
    if (el.ceuGaia.checked)
      al.addCatalog(A.catalogFromVizieR("I/355/gaiadr3", alvo, raio,
        { name: "Gaia DR3", shape: "circle", color: "#ffd98a", sourceSize: 8, onClick: "showTable", limit: 300 }));
    if (el.ceuWise.checked)
      al.addCatalog(A.catalogFromVizieR("II/328/allwise", alvo, raio,
        { name: "AllWISE", shape: "rhomb", color: "#9be28a", sourceSize: 9, onClick: "showTable", limit: 300 }));
  } catch (err) {
    console.error("Mapa do céu:", err);
    setCeuStatus("O mapa abriu, mas não foi possível desenhar todas as camadas.", "erro");
  }
}

function scheduleSky() {
  if (!sky.aladin) return;
  clearTimeout(sky.timer);
  sky.timer = setTimeout(drawSkyLayers, 500); // evita refazer a cada tecla
}

function updateSky({ recenter = false } = {}) {
  const v = state.values;
  if (!v) return;
  if (!sky.aladin) {
    setCeuStatus(`Mapa pronto para RA ${v.ra}°, Dec ${v.dec}°. Clique em “Carregar mapa interativo”.`);
    return;
  }
  if (recenter) {
    try {
      sky.aladin.gotoRaDec(v.ra, v.dec);
      sky.aladin.setFoV(Math.max(0.05, (v.fov / 60) * 4));
    } catch (err) { console.error("Mapa do céu:", err); }
    setCeuStatus(`Mapa centrado em RA ${v.ra}°, Dec ${v.dec}°.`);
  }
  scheduleSky();
}

// Clique no mapa -> preenche RA/Dec e faz a busca
function onSkyClick(e) {
  if (!e || e.isDragging) return;
  let { ra, dec } = e;
  if (!Number.isFinite(ra) || !Number.isFinite(dec)) {
    try { [ra, dec] = sky.aladin.pix2world(e.x, e.y); } catch { return; }
  }
  if (!Number.isFinite(ra) || !Number.isFinite(dec)) return;
  ra = wrapRa(ra);
  dec = Math.max(-90, Math.min(90, dec));
  el.ra.value = ra.toFixed(5);
  el.dec.value = dec.toFixed(5);
  if (!el.fov.value.trim()) el.fov.value = "3";
  setCeuStatus(`Ponto clicado: RA ${ra.toFixed(4)}°, Dec ${dec.toFixed(4)}°. Buscando observações… O resultado aparece na seção Observações.`, "carregando");
  el.form.requestSubmit();
}

el.ceuTudo.addEventListener("click", () => {
  if (!sky.aladin) { setCeuStatus("Carregue o mapa primeiro."); return; }
  try { sky.aladin.setFoV(360); } catch (err) { console.error("Mapa do céu:", err); }
});

el.ceuAbrir.addEventListener("click", async () => {
  const v = state.values;
  if (sky.aladin) {
    if (v) updateSky({ recenter: true });
    else setCeuStatus("Clique no mapa para escolher um ponto, ou faça uma busca.");
    return;
  }
  el.ceuAbrir.disabled = true;
  setCeuStatus("Carregando o mapa…", "carregando");
  try {
    sky.A = await loadAladin();
    el.ceuMapa.hidden = false;
    sky.aladin = sky.A.aladin("#ceu-mapa", {
      survey: el.ceuFundo.value, target: v ? `${v.ra} ${v.dec}` : "0 0",
      fov: 360, projection: "AIT", showCooGrid: true, showFullscreenControl: true, // AIT: céu inteiro numa elipse
    });
    sky.aladin.on("click", onSkyClick);
    el.ceuAbrir.textContent = "Recentrar na busca";
    el.ceuAbrir.disabled = false;
    setCeuStatus("Céu inteiro, com mapas do SPHEREx. Clique num ponto para pesquisar aquelas coordenadas.");
    drawSkyLayers();
  } catch (err) {
    console.error("Mapa do céu:", err);
    sky.aladin = null;
    el.ceuMapa.hidden = true;
    el.ceuAbrir.disabled = false;
    setCeuStatus(
      /webgl/i.test(String(err))
        ? "O mapa precisa de WebGL2, que está indisponível neste navegador. Ative a aceleração de hardware nas configurações do navegador ou tente outro navegador."
        : "Não foi possível carregar o mapa. Verifique a conexão com a internet e tente de novo (detalhes no console do navegador, tecla F12).",
      "erro"
    );
  }
});

el.ceuFundo.addEventListener("change", () => {
  if (!sky.aladin) return;
  try { (sky.aladin.setBaseImageLayer ?? sky.aladin.setImageSurvey).call(sky.aladin, el.ceuFundo.value); }
  catch (err) { console.error("Mapa do céu:", err); }
});
el.ceuGaia.addEventListener("change", scheduleSky);
el.ceuWise.addEventListener("change", scheduleSky);

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
  if (el.player.hidden || e.target.matches("input, select, textarea") || e.target.closest("#imgwrap")) return;
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
