"use strict";

/* ============================================================
 * SPHEREx Explorer — frontend
 * Ajuste CONFIG e a função normalizeObservation() conforme
 * docs/architecture/api-contract.md.
 * ============================================================ */
const CONFIG = {
  API_BASE: "http://localhost:8000",
  OBSERVATIONS_PATH: "/api/observations", // GET ?ra_deg=&dec_deg=&fov_arcmin= (src/backend/app/api/observations.py)
  // Mapas HiPS do SPHEREx no CDS (versão QR2), + número do detector (1 a 6), em ordem de preferência.
  // IDs CDS/P/SPHEREx/QR2/D1..D6 no MocServer. Atualizar quando houver HiPS do DR1.
  SPHEREX_HIPS_MIRRORS: ["https://alasky.cds.unistra.fr/SPHEREx/D", "https://alaskybis.cds.unistra.fr/SPHEREx/D"],
  // Fundos do mapa do céu usados quando o SPHEREx não responde, em ordem de preferência. Antes de usar
  // qualquer fundo o app baixa o arquivo "properties" do HiPS (com tempo limite) e pula os indisponíveis.
  // Espelhos do IRSA (NASA) dos HiPS do CDS.
  HIPS_FALLBACK: [
    { name: "AllWISE (WISE)", why: "também infravermelho", url: "https://irsa.ipac.caltech.edu/data/hips/CDS/AllWISE/RGB-W4-W2-W1" },
    { name: "2MASS", why: "infravermelho próximo", url: "https://irsa.ipac.caltech.edu/data/hips/CDS/2MASS/Color" },
    { name: "DSS2", why: "luz visível", url: "https://irsa.ipac.caltech.edu/data/hips/CDS/DSS2/color" },
  ],
  HIPS_PROBE_TIMEOUT_MS: 6000,
  // Fontes do Aladin Lite, tentadas em ordem, cada uma com tempo limite curto. jsdelivr primeiro:
  // em 2026-11-15 o aladin.cds.unistra.fr falhava devagar (ERR_NAME_NOT_RESOLVED / indisponível).
  // "script" = <script> clássico (define window.A); "module" = pacote npm (ES module) via import().
  ALADIN_SOURCES: [
    { type: "module", url: "https://cdn.jsdelivr.net/npm/aladin-lite@3.8.1/dist/aladin.js" },
    { type: "module", url: "https://unpkg.com/aladin-lite@3.8.1/dist/aladin.js" },
    { type: "script", url: "https://aladin.cds.unistra.fr/AladinLite/api/v3/3.8.1/aladin.js" },
    { type: "script", url: "https://aladin.cds.unistra.fr/AladinLite/api/v3/latest/aladin.js" },
  ],
  ALADIN_SOURCE_TIMEOUT_MS: 8000, // por fonte (download do código)
  ALADIN_INIT_TIMEOUT_MS: 25000, // inicialização (WebAssembly) depois do download
  // Modo demonstração: dados reais pré-gerados, servidos como arquivos estáticos (sem backend).
  DEMO_MANIFEST: "demo/manifest.json",
  // Nova tentativa automática da busca (SOURCE_UNAVAILABLE / falha de rede): esperas, em segundos.
  RETRY_DELAYS_S: [10, 20, 40, 60, 60],
  // Espelhos do VizieR (catálogos Gaia/AllWISE no mapa do céu), tentados em ordem. O da CfA tem CORS liberado.
  VIZIER_HOSTS: ["https://vizier.cds.unistra.fr", "https://vizier.cfa.harvard.edu"],
  // GET ?ra_deg=&dec_deg=[&pm_ra_cosdec_masyr=&pm_dec_masyr=&ref_epoch_jyear=][&aperture_arcsec=][&max_exposures=]
  // → { unit, points: [{ wavelength_um, bandwidth_um, flux, flux_err, detector, observed_at, observation_id, flagged, flags }], ... }
  SPECTRUM_PATH: "/api/spectrum",
  SPECTRUM_TIMEOUT_MS: 240000, // sem cache: ~1–2 s por exposição, até max_exposures
  SPECTRUM_MAX_EXPOSURES: 60,
  APERTURE_MIN: 3, APERTURE_MAX: 30, APERTURE_DEFAULT: 9, // segundos de arco
  // GET /api/observations/{id}/quality (depois que a imagem do quadro foi gerada)
  QUALITY_PATH: (id) => `/api/observations/${encodeURIComponent(id)}/quality`,
  TARGETS_PATH: "/api/targets", // GET → { targets: [{ name, ra, dec, fov, note }] }
  TIMEOUT_MS: 120000, // a primeira consulta ao IRSA pode levar dezenas de segundos
  EXTRA_PARAMS: {}, // parâmetros extras repassados ao backend
  FOV_MIN: 0.5,
  FOV_MAX: 30, // minutos de arco (o backend aceita 0,1 a 120)
  // Cada miniatura gera um recorte no IRSA (~10–15 s, sem cache): limitar evita sobrecarga.
  GALLERY_MAX: 24,
  // Miniaturas baixadas ao mesmo tempo (o IRSA responde 503 "Server busy" com muitos pedidos simultâneos).
  THUMB_CONCURRENCY: 2,
  // GET ?ra_deg=&dec_deg=[&pm_ra_cosdec_masyr=&pm_dec_masyr=&ref_epoch_jyear=] → { fovs: [...], recommended_fov_arcmin, ... }
  COVERAGE_PATH: "/api/coverage",
  COVERAGE_DEBOUNCE_MS: 600,
  COVERAGE_TIMEOUT_MS: 30000,
  PIXEL_SCALE_ARCSEC: 6.15, // pixel SPHEREx (o backend pode informar outro valor em pixel_scale_arcsec)
  MOON_DIAMETER_ARCMIN: 31, // diâmetro aparente médio da Lua, ~31′
  COMPLETE_COVERAGE: 0.999, // mesmo limiar do backend para "quadro completo"
  // GET ?op=mean&a=ids | ?op=diff&a=ids&b=ids → PNG (mesmo detector; máx. 40 ids no total)
  COMPOSITE_PATH: "/api/composite",
  COMPOSITE_MAX: 40,
  COMPOSITE_TIMEOUT_MS: 180000, // sem cache: ~1–2 s por observação
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
  espTabela: $("esp-tabela"), raio: $("raio"), espCentro: $("esp-centro"), espAlvo: $("esp-alvo"),
  espOcultar: $("esp-ocultar"), espProgresso: $("esp-progresso"), espNota: $("esp-nota"), espLimpar: $("esp-limpar"), espCsv: $("esp-csv"), filtroVazio: $("filtro-vazio"), reset: $("filtro-reset"), galeria: $("galeria-lista"), galeriaVazio: $("galeria-vazio"), tIni: $("t-ini"), tFim: $("t-fim"), meta: $("meta"),
  fovRegua: $("fov-regua"), fovParadas: $("fov-paradas"), fovInfo: $("fov-info"),
  seguirBox: $("seguir-box"), seguir: $("seguir"),
  soCompletos: $("so-completos"), soCompletosBox: $("so-completos-box"), soCompletosInfo: $("so-completos-info"),
  combGerar: $("comb-gerar"), combSelecao: $("comb-selecao"), combStatus: $("comb-status"),
  combResultado: $("comb-resultado"), combImg: $("comb-img"), combLegenda: $("comb-legenda"),
  detModo: $("det-modo"), detSomar: $("det-somar"),
  imgFalha: $("img-falha"), imgFalhaMsg: $("img-falha-msg"), imgRetry: $("img-retry"), imgProx: $("img-prox"),
  alt: $("alternativas"), altTitulo: $("alt-titulo"), altMsg: $("alt-msg"), altDemo: $("alt-demo"),
  altDemoLista: $("alt-demo-lista"), altRetry: $("alt-retry"), altCancelar: $("alt-cancelar"),
  altContagem: $("alt-contagem"), altMapa: $("alt-mapa"), altMock: $("alt-mock"), altOutras: $("alt-outras"),
  avisoDemo: $("aviso-demo"), demoSair: $("demo-sair"),
  ceuCentro: $("ceu-centro"), ceuFundoInfo: $("ceu-fundo-info"),
  espAcoes: $("esp-acoes"), espRetry: $("esp-retry"),
  cmp: $("comparar"), cmpA: $("cmp-a"), cmpB: $("cmp-b"), cmpStage: $("cmp-stage"), cmpImgA: $("cmp-img-a"),
  cmpImgB: $("cmp-img-b"), cmpDivisor: $("cmp-divisor"), cmpRotulo: $("cmp-rotulo"),
  cmpPiscar: $("cmp-piscar"), cmpTrocar: $("cmp-trocar"), cmpAviso: $("cmp-aviso"),
};

const state = { mapDots: new Map(), mapRing: null, pts: { A: null, B: null }, active: "A", specCtl: {}, rows: [], keys: [], values: null, all: [], wls: [], detectors: new Set(), frames: [], index: 0, timer: null, isMock: false, controller: null, omitted: 0,
  // Movimento próprio do alvo de exemplo selecionado: { pmRa, pmDec, refEpoch, name } ou null.
  // Só vale para as coordenadas exatas do alvo; qualquer outra mudança de RA/Dec o descarta.
  motion: null,
  // Última resposta válida de /api/coverage para as coordenadas atuais (ou null).
  coverage: null, coverageLoading: false,
  // Qualidade por observação (/api/observations/{id}/quality): id → resposta normalizada.
  quality: new Map(), qualityReq: new Set(),
  // Detectores presentes na busca e estatísticas por detector (contagem, faixa real).
  detPresent: new Set(), detStats: new Map(),
  // Modo demonstração (dados reais salvos, arquivos estáticos) ou null.
  demo: null };

// Movimento efetivamente enviado ao backend: só quando o usuário escolhe seguir o alvo.
const activeMotion = () => (state.motion && el.seguir.checked ? state.motion : null);

// Fração do quadro dentro do detector; null quando o backend não informa.
const isPartial = (f) => f.coverage !== null && f.coverage !== undefined && f.coverage < CONFIG.COMPLETE_COVERAGE;
const fmtPct = (c) => `${Math.floor(c * 100)}%`;

// Lê o movimento próprio (mas/ano) e a época de referência (ano juliano). Retorna null se faltar algum.
function parseMotion(pmRa, pmDec, refEpoch, name = "") {
  const vals = [pmRa, pmDec, refEpoch].map((v) => (v === null || v === undefined || v === "" ? NaN : Number(v)));
  if (!vals.every(Number.isFinite)) return null;
  return { pmRa: vals[0], pmDec: vals[1], refEpoch: vals[2], name: String(name ?? "") };
}

// Parâmetros do contrato /api/observations (os três juntos ou nenhum).
const motionParams = (m) =>
  m ? { pm_ra_cosdec_masyr: m.pmRa, pm_dec_masyr: m.pmDec, ref_epoch_jyear: m.refEpoch } : {};

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
    // "/api/..." vem do backend; caminhos relativos ("demo/...") são arquivos estáticos do próprio site.
    imageUrl: img ? (/^(https?:|data:|blob:)/.test(img) ? img : img.startsWith("/") ? CONFIG.API_BASE + img : img) : "",
    detector: detOk ? det : null,
    detectorLabel: detOk ? "D" + det : String(o.detector ?? "—"),
    wavelength: null, // não há um único comprimento de onda por imagem
    wlRange: wlMin !== null && wlMax !== null ? [wlMin, wlMax] : null, // micrômetros
    band: o.band ?? "—",
    product: m.data_release ?? "—",
    exposure: m.exposure_time_s ?? null,
    cutout: m.cutout_strategy ?? null,
    // Centro real do recorte (pode diferir do pedido quando o backend propaga o movimento próprio).
    cutoutCenter: Number.isFinite(m.cutout_center_ra_deg) && Number.isFinite(m.cutout_center_dec_deg)
      ? { ra: m.cutout_center_ra_deg, dec: m.cutout_center_dec_deg } : null,
    positionSource: m.position_source ?? null, // "requested" | "proper_motion"
    // Fração do quadro dentro do detector (0–1), prevista pelo polígono do detector; null se ausente.
    coverage: typeof m.coverage_fraction === "number" && Number.isFinite(m.coverage_fraction)
      ? Math.min(1, Math.max(0, m.coverage_fraction)) : null,
    frame: m.frame ?? null, // "common_north_up"
  };
}

async function fetchObservations({ ra, dec, fov }, motion = null) {
  state.controller?.abort();
  const controller = (state.controller = new AbortController());
  const timeout = setTimeout(() => controller.abort("timeout"), CONFIG.TIMEOUT_MS);
  const url = new URL(CONFIG.OBSERVATIONS_PATH, CONFIG.API_BASE);
  url.search = new URLSearchParams({
    ra_deg: ra, dec_deg: dec, fov_arcmin: fov, ...motionParams(motion), ...CONFIG.EXTRA_PARAMS,
  }).toString();

  try {
    const res = await fetch(url, { signal: controller.signal });
    if (!res.ok) throw await apiError(res);
    return parseObservations(await res.json());
  } finally {
    clearTimeout(timeout);
  }
}

// Resposta de GET /api/observations (ou o observations.json do modo demonstração) → quadros ordenados.
function parseObservations(data) {
  const all = (data.observations ?? []).map(normalizeObservation);
  // Observações sem data resolvível ficam fora da sequência temporal (e são contadas).
  const frames = all
    .filter((f) => f.date && !Number.isNaN(Date.parse(f.date)))
    .sort((a, b) => Date.parse(a.date) - Date.parse(b.date));
  state.omitted = all.length - frames.length;
  // "stale_cache": o IRSA estava indisponível e o backend usou a última resposta salva.
  // "demo_snapshot": arquivo estático do modo demonstração.
  state.dataSource = { status: data.data_source ?? null, cachedAt: data.data_cached_at ?? null };
  return frames;
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
    // Dois quadros parciais (fictícios): a parte fora do "detector" fica transparente, como no backend.
    const coverage = i === 3 ? 0.72 : i === 7 ? 0.45 : 1;
    if (i === 3) g.clearRect(Math.round(128 * 0.72), 0, 128, 128);
    if (i === 7) g.clearRect(0, Math.round(128 * 0.45), 128, 128);
    frames.push({
      coverage, frame: "common_north_up",
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
  el.imgFalha.hidden = true;
  if (el.img.getAttribute("src") !== f.imageUrl) el.img.src = f.imageUrl;
  el.img.alt = `Região do céu observada em ${fmtDateTime(f.date)}, detector ${f.detectorLabel}`;
  el.legenda.textContent =
    `${fmtDateTime(f.date)} · detector ${f.detectorLabel} — quadro ${i + 1} de ${state.frames.length}` +
    (isPartial(f) ? ` · Cobertura do quadro: ${fmtPct(f.coverage)}` : "");
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
    ...(f.cutoutCenter
      ? [["Centro do recorte",
          `RA ${f.cutoutCenter.ra.toFixed(4)}°, Dec ${f.cutoutCenter.dec.toFixed(4)}°` +
            (f.positionSource === "proper_motion" ? " (propagado pelo movimento próprio)" : "")]]
      : []),
    ...(f.coverage !== null && f.coverage !== undefined
      ? [["Cobertura do quadro", isPartial(f)
          ? `${fmtPct(f.coverage)} (o restante fica fora do detector, sem dados)` : "Completa"]]
      : []),
    ...(state.quality.has(f.id) ? [["Contaminação no alvo", qualityText(state.quality.get(f.id))]] : []),
    ["Coleção", f.product],
    ["Fonte dos dados", state.isMock ? "Fictícia (teste)"
      : state.demo ? `SPHEREx / IRSA-IPAC (exemplo real salvo${state.demo.cachedAt ? " em " + fmtDateTime(state.demo.cachedAt) : ""})`
      : "SPHEREx / IRSA-IPAC"],
  ];
  el.meta.replaceChildren(
    ...rows.flatMap(([k, v]) => {
      const dt = document.createElement("dt"); dt.textContent = k;
      const dd = document.createElement("dd");
      if (typeof v === "string") dd.textContent = v;
      else { dd.textContent = v.text; if (v.title) dd.title = v.title; }
      return [dt, dd];
    })
  );
  positionMarkers();
  scheduleSkyFrame(); // marcador do alvo e FOV no mapa do céu acompanham o quadro
  // Visor (js/cinema.js): sobreposição com data/detector, bolha da linha do tempo e tira de miniaturas.
  document.dispatchEvent(new CustomEvent("visor:quadro", { detail: { index: i, frame: f } }));
}

/* ---------- Qualidade do quadro (máscara de flags do SPHEREx) ---------- */
// Nomes das flags (bits da extensão FLAGS) em português; a descrição do backend vai na dica (title).
const FLAG_NAMES = {
  TRANSIENT: "raio cósmico/transiente", OVERFLOW: "saturação", NONFUNC: "pixel morto",
  HOT: "pixel quente", COLD: "pixel frio", PERSIST: "persistência", OUTLIER: "valor anômalo",
  CROSSTALK: "diafonia", STREAK: "rastro de satélite", BLOOM: "transbordamento de fonte",
  SNOWBALL: "snowball", HALO: "halo de transiente", MISSING_DATA: "dado perdido",
  NONLINEAR: "não linearidade", SUR_ERROR: "erro de leitura a bordo",
  DICHROIC: "baixa eficiência (dicroico)", PHANMISS: "correção de pixel fantasma ausente",
};
const flagName = (n) => {
  const s = String(n ?? "").toUpperCase();
  return FLAG_NAMES[s] ?? (s.startsWith("GHOST") ? "reflexo (ghost)" : s || "?");
};

function normalizeQuality(d) {
  const info = new Set((d?.informational ?? []).map((s) => String(s).toUpperCase()));
  // "SOURCE" (pixel de fonte conhecida) é informativo, não contaminação.
  const flags = (d?.flags_at_target ?? [])
    .filter((f) => f && !info.has(String(f.name).toUpperCase()))
    .map((f) => ({ name: String(f.name), label: flagName(f.name), description: f.description ?? "" }));
  return { contaminated: Boolean(d?.contaminated_at_target) && flags.length > 0, flags,
           frameFraction: d?.frame_flagged_fraction ?? {} };
}

function qualityText(q) {
  const frac = Object.entries(q.frameFraction)
    .filter(([, v]) => Number.isFinite(v) && v > 0)
    .sort((a, b) => b[1] - a[1]).slice(0, 4)
    .map(([k, v]) => `${flagName(k)} ${(v * 100).toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`);
  const fracTxt = frac.length ? `Pixels sinalizados no quadro inteiro: ${frac.join(", ")}.` : "";
  if (!q.contaminated) return { text: "nenhuma", title: fracTxt };
  const labels = [...new Set(q.flags.map((f) => f.label))];
  const desc = q.flags.map((f) => `${f.name}: ${f.description || f.label}`).join("\n");
  return { text: labels.join(", "), title: [desc, fracTxt].filter(Boolean).join("\n") };
}

// Pedida depois que a imagem principal carregou (o backend só tem a máscara após gerar a imagem).
// Sem bloquear: erros e 404 são ignorados (a linha simplesmente não aparece).
async function fetchQuality(f) {
  if (state.isMock || state.demo || !f?.id || state.quality.has(f.id) || state.qualityReq.has(f.id)) return;
  state.qualityReq.add(f.id);
  try {
    const res = await fetch(new URL(CONFIG.QUALITY_PATH(f.id), CONFIG.API_BASE), { signal: AbortSignal.timeout(30000) });
    if (!res.ok) return;
    state.quality.set(f.id, normalizeQuality(await res.json()));
    if (state.frames[state.index]?.id === f.id) showFrame(state.index);
  } catch { /* ignorado */ } finally {
    state.qualityReq.delete(f.id);
  }
}
el.img.addEventListener("load", () => fetchQuality(state.frames[state.index]));

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
      btn.setAttribute("aria-label", `Ver observação de ${fmtDateTime(f.date)}, detector ${f.detectorLabel}` +
        (isPartial(f) ? `, quadro parcial (${fmtPct(f.coverage)} dentro do detector)` : ""));
      btn.append(img, estado, label);
      if (isPartial(f)) {
        btn.classList.add("parcial");
        const selo = document.createElement("span");
        selo.className = "selo-parcial";
        selo.setAttribute("aria-hidden", "true");
        selo.textContent = `parcial · ${fmtPct(f.coverage)}`;
        btn.title = "Parte deste quadro fica fora do detector (área hachurada, sem dados).";
        btn.append(selo);
      }
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
  setPlayLabel(false);
}

// O botão tem ícone (CSS, pelo aria-pressed) e texto; só o texto muda aqui.
function setPlayLabel(playing) {
  (el.play.querySelector(".txt") ?? el.play).textContent = playing ? "Pausar" : "Reproduzir";
  el.play.setAttribute("aria-pressed", String(playing));
}

function start() {
  if (state.frames.length < 2) return;
  stop();
  setPlayLabel(true);
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

/* Faixa espectral REAL de cada detector nesta busca: mínimo e máximo de metadata.wavelength_*_nm
 * (em µm). Sem esses metadados, cai para DET_RANGES, marcada como aproximada. */
function detectorStats(frames) {
  const st = new Map();
  for (let d = 1; d <= 6; d++) st.set(d, { n: 0, lo: Infinity, hi: -Infinity });
  for (const f of frames) {
    const s = st.get(f.detector);
    if (!s) continue;
    s.n++;
    if (f.wlRange) { s.lo = Math.min(s.lo, f.wlRange[0]); s.hi = Math.max(s.hi, f.wlRange[1]); }
  }
  for (const [d, s] of st) {
    s.real = Number.isFinite(s.lo) && Number.isFinite(s.hi);
    s.range = s.real ? [s.lo, s.hi] : DET_RANGES[d - 1];
  }
  return st;
}

// Clique simples = só aquele detector; Ctrl/⌘/Shift+clique ou o modo "combinar" = adiciona/remove.
function pickDetector(d, additive) {
  const present = state.detPresent;
  if (d === "all") state.detectors = new Set(present);
  else if (additive) {
    const s = new Set(state.detectors);
    s.has(d) ? s.delete(d) : s.add(d);
    state.detectors = s.size ? s : new Set([d]); // nunca deixa nenhum ativo
  } else state.detectors = new Set([d]);
  syncDetectorButtons();
  applyFilters();
}

function syncDetectorButtons() {
  const all = state.detPresent.size > 0 && [...state.detPresent].every((d) => state.detectors.has(d));
  for (const b of el.detBox.querySelectorAll("button.det")) {
    const d = b.dataset.det;
    b.setAttribute("aria-pressed", String(d === "all" ? all : !all && state.detectors.has(Number(d))));
  }
}

function setupFilters(frames) {
  const present = new Set(frames.map((f) => f.detector).filter(Boolean));
  const stats = detectorStats(frames);
  state.detPresent = present;
  state.detStats = stats;
  state.detectors = new Set(present);
  el.detBox.hidden = present.size === 0;
  el.detModo.hidden = present.size < 2;
  const mk = (d) => {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "det";
    b.dataset.det = d;
    if (d === "all") {
      b.classList.add("det-todos");
      const n = document.createElement("small");
      n.className = "cnt";
      n.textContent = String(frames.filter((f) => f.detector).length);
      b.append(document.createTextNode("Todos"), n);
      b.title = "Mostrar as observações de todos os detectores (faixas diferentes do infravermelho intercaladas)";
      b.setAttribute("aria-label", `Todos os detectores, ${n.textContent} observações`);
    } else {
      const s = stats.get(d);
      b.style.setProperty("--det", DET_COLORS[d - 1]);
      const sw = document.createElement("span");
      sw.className = "sw";
      sw.setAttribute("aria-hidden", "true");
      const nome = document.createElement("strong");
      nome.textContent = "D" + d;
      const cnt = document.createElement("small");
      cnt.className = "cnt";
      cnt.textContent = String(s.n);
      const rng = document.createElement("small");
      rng.className = "rng";
      rng.textContent = (s.real ? "" : "≈ ") + fmtRange(s.range);
      b.append(sw, nome, cnt, rng);
      const first = (d - 1) * BANDS_PER_DETECTOR + 1;
      b.disabled = !present.has(d);
      b.title = present.has(d)
        ? `Detector ${d}: ${s.n} observações · ${fmtRange(s.range)}` +
          (s.real ? " (faixa dos metadados destas observações)" : " (faixa aproximada, da página da missão)") +
          ` · bandas ${first} a ${first + BANDS_PER_DETECTOR - 1}. Clique: só este detector. Ctrl/⌘/Shift+clique: somar.`
        : "Sem observações deste detector nesta busca";
      b.setAttribute("aria-label", `Detector ${d}, ${s.n} observações, ${s.real ? "" : "aproximadamente "}${fmtRange(s.range).replace("–", " a ")}`);
    }
    b.addEventListener("click", (e) =>
      pickDetector(d, d !== "all" && (e.ctrlKey || e.metaKey || e.shiftKey || el.detSomar.checked)));
    return b;
  };
  el.detBox.replaceChildren(mk("all"), ...[1, 2, 3, 4, 5, 6].map(mk));
  syncDetectorButtons();

  state.wls = [...new Set(frames.map((f) => f.wavelength).filter((w) => w !== null))].sort((a, b) => a - b);
  const last = Math.max(state.wls.length - 1, 0);
  el.faixa.hidden = state.wls.length < 2;
  el.wlMin.max = el.wlMax.max = last;
  el.wlMin.value = 0;
  el.wlMax.value = last;

  // "Só quadros completos": desligado a cada nova busca; só aparece se o backend informar a cobertura.
  const partials = frames.filter(isPartial).length;
  el.soCompletos.checked = false;
  el.soCompletosBox.hidden = !frames.some((f) => f.coverage !== null && f.coverage !== undefined);
  el.soCompletosInfo.textContent = partials
    ? `(esconde ${partials} quadro${partials > 1 ? "s" : ""} parcia${partials > 1 ? "is" : "l"})`
    : "(nenhum quadro parcial nesta busca)";
}

function isVisible(f) {
  if (f.detector && !state.detectors.has(f.detector)) return false;
  if (el.soCompletos.checked && isPartial(f)) return false;
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
  const partialsVisible = frames.filter(isPartial).length;
  el.contagem.textContent =
    `Mostrando ${frames.length} de ${state.all.length} observações (${instants} instantes distintos).` +
    (partialsVisible ? ` ${partialsVisible} com quadro parcial (marcadas na galeria).` : "") +
    (detsVisible > 1
      ? " Atenção: há detectores diferentes intercalados; cada detector vê outra faixa do infravermelho. Para comparar épocas, deixe só um detector ativo."
      : "") +
    (frames.length > CONFIG.GALLERY_MAX ? ` A galeria mostra as ${CONFIG.GALLERY_MAX} primeiras.` : "") +
    (state.omitted ? ` ${state.omitted} observação(ões) sem data foram omitidas.` : "");

  stop();
  state.frames = frames;
  resetComposite(); // a seleção mudou: o resultado combinado anterior deixa de valer
  renderMap();
  el.visor.hidden = !frames.length;
  el.filtroVazio.hidden = !!frames.length;
  // Visor (js/cinema.js): marcas da linha do tempo, abas e tira de miniaturas da nova seleção.
  document.dispatchEvent(new CustomEvent("visor:quadros", { detail: { frames } }));
  if (!frames.length) { clearGallery(); resetCompare(); return; }

  el.slider.max = frames.length - 1;
  el.tIni.textContent = fmtDate(frames[0].date);
  el.tFim.textContent = fmtDate(frames.at(-1).date);
  renderGallery(frames);
  const idx = frames.findIndex((f) => f.id === keepId);
  showFrame(idx >= 0 ? idx : 0);
  pumpThumbs(); // só começa se a imagem principal já estiver pronta; senão, espera o load/error dela
  // Mudou o detector: A/B voltam para a primeira e a última dele; senão, mantém a escolha.
  resetCompare({ keep: state.cmpDetKey === [...state.detectors].join() });
  state.cmpDetKey = [...state.detectors].join();
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

/* ---------- Combinar épocas (/api/composite) ----------
 * Só com UM detector ativo (o backend recusa misturar detectores). Usa as observações visíveis
 * (já filtradas). Nunca pede composição no modo de dados fictícios. */
const comb = { ctl: null, url: null };
const combMode = () => document.querySelector('input[name="comb-modo"]:checked').value;
const fmtSpan = (fs) => (fs.length ? `${fmtDate(fs[0].date)} a ${fmtDate(fs.at(-1).date)}` : "—");

function compositeSelection() {
  const det = state.detectors.size === 1 ? [...state.detectors][0] : null;
  if (state.isMock) return { erro: "Combinar épocas não está disponível com dados fictícios: a combinação é feita pelo servidor com observações reais." };
  if (det === null) return { erro: "Escolha um detector para combinar épocas (deixe só um ativo no filtro acima)." };
  const frames = state.frames.filter((f) => f.detector === det); // já em ordem cronológica
  if (combMode() === "mean") {
    if (!frames.length) return { erro: "Nenhuma observação visível deste detector." };
    // Mais de 40: prioriza quadros completos / de maior cobertura (cobertura desconhecida conta como completa).
    const a = [...frames].sort((x, y) => (y.coverage ?? 1) - (x.coverage ?? 1)).slice(0, CONFIG.COMPOSITE_MAX)
      .sort((x, y) => Date.parse(x.date) - Date.parse(y.date));
    return { det, op: "mean", a, b: [], total: frames.length };
  }
  if (frames.length < 2) return { erro: "A diferença precisa de pelo menos duas observações visíveis deste detector." };
  const half = Math.min(Math.floor(frames.length / 2), CONFIG.COMPOSITE_MAX / 2);
  return { det, op: "diff", b: frames.slice(0, half), a: frames.slice(-half), total: frames.length };
}

// Modo demonstração: só há as combinações pré-geradas listadas no manifest.
const OP_NAMES = { mean: "soma de épocas", diff: "diferença entre épocas" };
function demoComposite() {
  const det = state.detectors.size === 1 ? [...state.detectors][0] : null;
  const list = state.demo?.composites ?? [];
  const disp = list.length
    ? `Pré-calculadas neste exemplo: ${list.map((c) => `${c.detector} (${OP_NAMES[c.op] ?? c.op})`).join(", ")}.`
    : "Este exemplo salvo não traz combinações pré-calculadas.";
  if (det === null) return { erro: `Escolha um detector para combinar épocas. ${disp}` };
  const c = list.find((x) => x.detector === "D" + det && x.op === combMode());
  if (!c) return { erro: `Sem o servidor, só dá para ver combinações já calculadas. ${disp}` };
  return { demo: c, det };
}

function renderCompositeUi() {
  if (state.demo) {
    const d = demoComposite();
    el.combGerar.disabled = !!d.erro;
    el.combSelecao.textContent = d.erro ?? `Exemplo salvo: ${d.demo.description || `${d.demo.detector}, ${OP_NAMES[d.demo.op] ?? d.demo.op}`}`;
    return;
  }
  const s = compositeSelection();
  el.combGerar.disabled = !!s.erro;
  if (s.erro) { el.combSelecao.textContent = s.erro; return; }
  el.combSelecao.textContent = s.op === "mean"
    ? `D${s.det}: ${s.a.length} observações` + (s.total > s.a.length ? ` (das ${s.total} visíveis, as de maior cobertura)` : "") + ` · ${fmtSpan(s.a)}`
    : `D${s.det}: A = ${s.a.length} mais recentes (${fmtSpan(s.a)}) · B = ${s.b.length} mais antigas (${fmtSpan(s.b)})`;
}

function setCombStatus(msg, kind = "") {
  el.combStatus.hidden = !msg;
  el.combStatus.textContent = msg;
  el.combStatus.className = "status " + kind;
}

// Nova seleção (filtros, nova busca): cancela o pedido e descarta o resultado anterior.
function resetComposite() {
  comb.ctl?.abort();
  comb.ctl = null;
  if (comb.url) URL.revokeObjectURL(comb.url);
  comb.url = null;
  el.combResultado.hidden = true;
  el.combImg.onerror = null;
  el.combImg.removeAttribute("src");
  setCombStatus("");
  renderCompositeUi();
}

function showDemoComposite() {
  const d = demoComposite();
  if (d.erro) { setCombStatus(d.erro); return; }
  resetComposite();
  el.combImg.onerror = () => { el.combResultado.hidden = true; setCombStatus("Não foi possível abrir a imagem pré-calculada deste exemplo.", "erro"); };
  el.combImg.src = d.demo.file;
  el.combImg.alt = `${OP_NAMES[d.demo.op] ?? d.demo.op}, detector ${d.demo.detector} (pré-calculada)`;
  el.combLegenda.textContent = `${(d.demo.description || "").replace(/([^.])$/, "$1.")} Imagem pré-calculada pelo servidor quando o exemplo foi salvo` +
    (state.demo.cachedAt ? ` (${fmtDateTime(state.demo.cachedAt)})` : "") + "." +
    (d.demo.op === "diff" ? " Claro = mais brilho nas épocas recentes; escuro = nas antigas; cinza médio = sem mudança." : "");
  el.combResultado.hidden = false;
}

async function runComposite() {
  if (state.demo) { showDemoComposite(); return; }
  const s = compositeSelection();
  if (s.erro) { setCombStatus(s.erro); return; }
  resetComposite();
  const ctl = (comb.ctl = new AbortController());
  const timer = setTimeout(() => ctl.abort("timeout"), CONFIG.COMPOSITE_TIMEOUT_MS);
  const n = s.a.length + s.b.length;
  el.combGerar.disabled = true;
  setCombStatus(`Combinando ${n} observações no servidor… pode levar até ~${Math.max(5, n * 2)} s na primeira vez.`, "carregando");
  try {
    const url = new URL(CONFIG.COMPOSITE_PATH, CONFIG.API_BASE);
    url.search = new URLSearchParams({
      op: s.op, a: s.a.map((f) => f.id).join(","), ...(s.op === "diff" ? { b: s.b.map((f) => f.id).join(",") } : {}),
      ...CONFIG.EXTRA_PARAMS,
    }).toString();
    const res = await fetch(url, { signal: ctl.signal });
    if (!res.ok) throw await apiError(res);
    const blob = await res.blob();
    if (comb.ctl !== ctl) return;
    comb.url = URL.createObjectURL(blob);
    el.combImg.src = comb.url;
    // Cabeçalhos de metadados: só usados se o navegador os expuser (CORS); a legenda não depende deles.
    const hdrDet = res.headers.get("X-SpherEx-Detector");
    const detTxt = `detector D${s.det}` + (hdrDet && !String(hdrDet).includes(String(s.det)) ? ` (servidor informou ${hdrDet})` : "");
    if (s.op === "mean") {
      el.combImg.alt = `Média de ${s.a.length} observações do ${detTxt}`;
      el.combLegenda.textContent = `Média de ${s.a.length} observações · ${detTxt} · ${fmtSpan(s.a)}. Mais quadros = menos ruído; objetos fracos ficam mais visíveis.`;
    } else {
      el.combImg.alt = `Diferença entre épocas do ${detTxt}`;
      el.combLegenda.textContent = `Diferença média(A) − média(B) · ${detTxt}. Claro = mais brilho em A (${s.a.length} recentes: ${fmtSpan(s.a)}); escuro = mais brilho em B (${s.b.length} antigas: ${fmtSpan(s.b)}); cinza médio = sem mudança.`;
    }
    el.combResultado.hidden = false;
    setCombStatus("");
  } catch (err) {
    if (comb.ctl !== ctl) return; // substituído ou descartado
    if (err instanceof ApiError) {
      setCombStatus(err.code === "INVALID_PARAMETERS"
        ? `O servidor recusou a combinação: ${err.message}`
        : API_ERRORS[err.code] ?? `Não foi possível combinar as épocas: ${err.message}`, "erro");
    } else {
      setCombStatus(ctl.signal.reason === "timeout"
        ? "A combinação demorou demais. Tente com menos observações (filtre por comprimento de onda ou só quadros completos)."
        : "O servidor de cálculo não está disponível agora, e a combinação de épocas precisa dele. " +
          "Tente de novo daqui a pouco ou abra um exemplo real salvo, que já traz combinações prontas.", "info");
    }
  } finally {
    clearTimeout(timer);
    if (comb.ctl === ctl) { comb.ctl = null; el.combGerar.disabled = !!compositeSelection().erro; }
  }
}

el.combGerar.addEventListener("click", runComposite);
document.querySelectorAll('input[name="comb-modo"]').forEach((r) => r.addEventListener("change", resetComposite));
el.soCompletos.addEventListener("change", applyFilters);

function loadFrames(frames, isMock) {
  stop();
  state.all = frames;
  state.isMock = isMock;
  el.avisoMock.hidden = !isMock;
  el.avisoDemo.hidden = !state.demo;
  if (state.demo) {
    el.avisoDemo.querySelector("span").textContent =
      `Exemplo real salvo${state.demo.cachedAt ? " em " + fmtDateTime(state.demo.cachedAt) : ""}` +
      ` (${state.demo.target.name}) — o arquivo IRSA ou o servidor do SPHEREx Explorer está indisponível agora. ` +
      "Imagens, linha do tempo, filtros e cobertura vêm de arquivos salvos; nada é calculado ao vivo.";
    // Atalho para a imagem de diferença pré-calculada (o jeito mais rápido de "ver o que mudou").
    el.avisoDemo.querySelector(".demo-diff")?.remove();
    const diff = state.demo.composites.find((c) => c.op === "diff" && c.detector === "D1") ??
      state.demo.composites.find((c) => c.op === "diff");
    const det = diff ? parseInt(diff.detector.replace(/\D/g, ""), 10) : NaN;
    if (diff && frames.some((f) => f.detector === det)) {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "chip demo-diff";
      b.textContent = `Ver o que mudou (diferença ${diff.detector})`;
      b.addEventListener("click", () => {
        pickDetector(det, false);
        document.querySelector('input[name="comb-modo"][value="diff"]').checked = true;
        window.visorAba?.("combinar"); // aba "Combinar" do visor (js/cinema.js)
        showDemoComposite();
        el.visor.scrollIntoView({ behavior: "smooth", block: "start" });
      });
      el.demoSair.before(b);
    }
  }
  setupFilters(frames);
  el.player.hidden = false;
  state.cmpDetKey = null; // nova busca: comparador volta ao padrão
  applyFilters();
}

/* ---------- Alternativas quando a busca falha ----------
 * Em vez de só uma mensagem de erro: exemplo real salvo (modo demonstração), nova tentativa
 * automática com contagem regressiva (cancelável), ir ao mapa do céu, ou dados fictícios. */
const retry = { attempt: 0, timer: null, until: 0, auto: false };

function cancelRetry() {
  clearInterval(retry.timer);
  retry.timer = null;
  el.altContagem.textContent = "";
  el.altCancelar.hidden = true;
}

function hideAlternatives() {
  cancelRetry();
  el.alt.hidden = true;
}

function scheduleRetry() {
  cancelRetry();
  const delays = CONFIG.RETRY_DELAYS_S;
  if (retry.attempt >= delays.length) {
    el.altContagem.textContent = `Já foram ${retry.attempt} novas tentativas automáticas. Use “Tentar de novo” quando quiser.`;
    return;
  }
  retry.until = Date.now() + delays[retry.attempt] * 1000;
  el.altCancelar.hidden = false;
  const tick = () => {
    const s = Math.max(0, Math.ceil((retry.until - Date.now()) / 1000));
    el.altContagem.textContent = `Nova tentativa automática em ${s} s (tentativa ${retry.attempt + 1} de ${delays.length}).`;
    if (s <= 0) { cancelRetry(); retry.attempt++; retry.auto = true; el.form.requestSubmit(); }
  };
  tick();
  retry.timer = setInterval(tick, 1000);
}

/** kind: "source" (IRSA indisponível), "network" (servidor inacessível), "timeout". */
function showAlternatives(kind, detail = "", { autoRetry = true } = {}) {
  const titulos = {
    source: "O arquivo da NASA (IRSA) está ocupado agora",
    network: "Observações ao vivo indisponíveis no momento",
    timeout: "A busca está demorando mais que o normal",
  };
  el.altTitulo.textContent = titulos[kind] ?? "Outras formas de explorar esta região";
  el.altMsg.textContent = (detail ? detail + " " : "") + ({
    source: "Isso costuma ser passageiro. Enquanto isso, você pode ver um exemplo real salvo, a mesma região em outras bases de imagens do céu ou o mapa interativo.",
    network: "Tudo bem: um exemplo real salvo do SPHEREx funciona sem o servidor, e você pode ver esta região em outras bases de imagens do céu (WISE, 2MASS, DSS2) ou no mapa interativo.",
    timeout: "O arquivo da NASA pode estar lento. Tente de novo, veja um exemplo real salvo ou explore esta região em outras bases de imagens do céu.",
  }[kind] ?? "");
  el.altOutras.hidden = !state.values; // precisa de coordenadas para mostrar a região
  renderDemoOptions();
  el.alt.hidden = false;
  el.altRetry.hidden = !state.values; // sem coordenadas ainda, não há o que tentar de novo
  if (autoRetry && state.values) scheduleRetry();
  else cancelRetry();
  // js/refimages.js mostra as imagens salvas desta região (ou dos alvos de exemplo).
  document.dispatchEvent(new CustomEvent("spx:alternativas", { detail: { kind, values: state.values ?? null } }));
}

/* ---------- Fluxo de busca ---------- */
async function onSubmit(e) {
  e.preventDefault();
  if (!retry.auto) retry.attempt = 0; // busca pedida pelo usuário: recomeça a contagem
  retry.auto = false;
  hideAlternatives();
  // Nome do objeto (opcional, js/surveys.js): resolvido pelo Sesame (CDS) antes de validar RA/Dec.
  if (window.Surveys && !(await window.Surveys.resolveNameIfNeeded())) return;
  const values = validate();
  if (!values) {
    if (document.body.classList.contains("embed")) setStatus("Coordenadas inválidas na URL.", "erro");
    return;
  }
  // Outra base de dados (WISE, 2MASS, DSS2): imagens de outros telescópios, sem o servidor.
  if (window.Surveys && !el.mock.checked && window.Surveys.selected() !== "spherex") {
    window.Surveys.show(values);
    return;
  }
  window.Surveys?.hide();
  leaveDemo();
  state.values = values;
  // Dados fictícios não usam movimento próprio; sem "seguir o alvo", o quadro fica fixo no céu.
  const motion = el.mock.checked ? null : activeMotion();
  renderFovUi();
  scheduleCoverage();
  clearPoints();
  updateSky({ recenter: true });
  if (!el.mock.checked) updateUrl(values, state.motion);

  stop();
  el.player.hidden = true;
  clearGallery();
  clearMap();
  el.buscar.disabled = true;
  setStatus("Buscando observações no arquivo SPHEREx… isso pode levar alguns segundos.", "carregando");

  try {
    state.omitted = 0;
    const frames = el.mock.checked ? mockObservations() : await fetchObservations(values, motion);
    if (!frames.length) {
      setStatus(API_ERRORS.NO_OBSERVATIONS_FOUND);
      return;
    }
    loadFrames(frames, el.mock.checked);
    setStatus(`${frames.length} observações em ordem cronológica · RA ${values.ra}°, Dec ${values.dec}°, FOV ${values.fov}′.` +
      // Só afirma a correção se o backend confirmar (um backend antigo ignora os parâmetros).
      (motion && frames.some((f) => f.positionSource === "proper_motion")
        ? ` Posição corrigida pelo movimento próprio${motion.name ? " de " + motion.name : ""} em cada data.` : "") +
      (!el.mock.checked && state.motion && !motion
        ? ` Quadro fixo no céu: ${state.motion.name || "o alvo"} pode aparecer deslocado entre as datas.` : "") +
      (!el.mock.checked && state.dataSource?.status === "stale_cache"
        ? ` Atenção: o arquivo IRSA está indisponível; exibindo a lista salva em ${
            state.dataSource.cachedAt ? fmtDateTime(state.dataSource.cachedAt) : "uma consulta anterior"
          } (pode não incluir dados mais recentes).` : ""),
      !el.mock.checked && state.dataSource?.status === "stale_cache" ? "aviso" : "");
  } catch (err) {
    const timedOut = err === "timeout" || err?.name === "AbortError";
    if (timedOut && state.controller?.signal.reason !== "timeout") return; // busca substituída
    if (err instanceof ApiError) {
      // NO_OBSERVATIONS_FOUND é um resultado válido, não uma falha.
      if (err.code === "NO_OBSERVATIONS_FOUND") { setStatus(API_ERRORS.NO_OBSERVATIONS_FOUND); return; }
      if (err.code === "SOURCE_UNAVAILABLE" || err.status >= 502) {
        setStatus(API_ERRORS.SOURCE_UNAVAILABLE, "aviso");
        showAlternatives("source");
        return;
      }
      setStatus(API_ERRORS[err.code] ?? err.message, "erro");
      return;
    }
    if (timedOut) {
      setStatus("A busca está demorando mais que o normal. Você pode tentar de novo, ver um exemplo real salvo ou explorar outras bases de imagens do céu.", "aviso");
      showAlternatives("timeout");
    } else {
      state.backendDown = true;
      // Sem tom de erro: o site continua útil sem o servidor (exemplos salvos e outras bases).
      setStatus("O servidor de observações ao vivo não está disponível agora. Você pode ver um exemplo real salvo, " +
        "explorar esta região em outras bases de imagens do céu (WISE, 2MASS, DSS2) ou tentar de novo daqui a pouco.", "info");
      showAlternatives("network");
    }
  } finally {
    el.buscar.disabled = false;
  }
}

el.altRetry.addEventListener("click", () => { cancelRetry(); retry.auto = true; retry.attempt++; el.form.requestSubmit(); });
el.altCancelar.addEventListener("click", () => {
  cancelRetry();
  el.altContagem.textContent = "Nova tentativa automática cancelada.";
});
el.altMapa.addEventListener("click", () => {
  cancelRetry();
  $("ceu").scrollIntoView({ behavior: "smooth", block: "start" });
  openSky();
});
el.altOutras.addEventListener("click", () => {
  cancelRetry();
  $("base").value = "wise";
  $("base").dispatchEvent(new Event("change"));
  el.mock.checked = false;
  el.form.requestSubmit();
});
el.altMock.addEventListener("click", () => {
  hideAlternatives();
  el.mock.checked = true;
  if (!validate()) { el.ra.value = el.ra.value || "0"; el.dec.value = el.dec.value || "0"; }
  el.form.requestSubmit();
});

/* ---------- Modo demonstração (exemplo real salvo, arquivos estáticos) ----------
 * Contrato: src/frontend/demo/manifest.json lista alvos; cada um aponta para observations.json
 * (formato de GET /api/observations, image_url relativo ao site), coverage.json, spectrum.json
 * e composites pré-gerados. Nada aqui é calculado: só exibe o que foi salvo. */
let demoManifestPromise = null;
function loadDemoManifest() {
  demoManifestPromise ??= fetch(CONFIG.DEMO_MANIFEST, { signal: AbortSignal.timeout(10000) })
    .then((r) => (r.ok ? r.json() : null))
    .then((m) => {
      const targets = (m?.targets ?? []).filter((t) => t && t.id && t.observations);
      return targets.length ? { ...m, targets } : null;
    })
    .catch(() => null);
  return demoManifestPromise;
}

async function renderDemoOptions() {
  const m = await loadDemoManifest();
  el.altDemo.hidden = !m;
  if (!m) return;
  el.altDemoLista.replaceChildren(...m.targets.map((t) => {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "primary";
    b.textContent = m.targets.length > 1 ? `Ver exemplo real salvo: ${t.name ?? t.id}` : `Ver um exemplo real salvo (${t.name ?? t.id})`;
    b.addEventListener("click", () => enterDemo(t.id));
    return b;
  }));
  const quando = m.generated_at ? ` Salvo em ${fmtDateTime(m.generated_at)}.` : "";
  el.altDemo.querySelector("small").textContent = (m.note ? m.note + " " : "") +
    "Imagens reais do SPHEREx baixadas anteriormente do IRSA; funciona sem o servidor." + quando;
}

const fetchJson = async (url) => {
  const r = await fetch(url, { signal: AbortSignal.timeout(20000) });
  if (!r.ok) throw new Error(`HTTP ${r.status} em ${url}`);
  return r.json();
};

async function enterDemo(id) {
  const m = await loadDemoManifest();
  const t = m?.targets.find((x) => x.id === id);
  if (!t) { setStatus("Exemplo salvo não encontrado.", "erro"); return; }
  hideAlternatives();
  stop();
  state.controller?.abort();
  setStatus(`Abrindo o exemplo real salvo de ${t.name ?? t.id}…`, "carregando");
  try {
    const data = await fetchJson(t.observations);
    const frames = parseObservations(data);
    if (!frames.length) throw new Error("observations.json sem observações");
    const motion = t.motion
      ? parseMotion(t.motion.pm_ra_cosdec_masyr, t.motion.pm_dec_masyr, t.motion.ref_epoch_jyear, t.name ?? t.id) : null;
    el.mock.checked = false;
    el.ra.value = t.ra; el.dec.value = t.dec; el.fov.value = t.fov ?? 3;
    el.seguir.checked = true;
    state.values = { ra: Number(t.ra), dec: Number(t.dec), fov: Number(t.fov ?? 3) };
    state.demo = {
      target: t, cachedAt: data.data_cached_at ?? m.generated_at ?? null,
      composites: Array.isArray(t.composites) ? t.composites.filter((c) => c?.file && c?.detector && c?.op) : [],
      spectrum: null, coverage: null,
    };
    setMotion(motion); // depois de state.demo: a cobertura não é pedida ao servidor
    el.seguirBox.hidden = true; // o exemplo foi salvo de um jeito só; mudar exigiria o servidor
    try { history.replaceState(null, "", "?demo=" + encodeURIComponent(t.id)); } catch { /* file:// */ }
    clearPoints();
    loadFrames(frames, false);
    renderFovUi();
    if (t.coverage) {
      fetchJson(t.coverage).then((c) => {
        if (state.demo?.target !== t) return;
        state.demo.coverage = normalizeCoverage(c);
        state.coverage = state.demo.coverage.fovs.length ? state.demo.coverage : null;
        renderFovUi();
      }).catch((err) => console.debug("Exemplo salvo sem cobertura:", err));
    }
    if (t.quality) {
      // quality.json: mapa id → resposta de /api/observations/{id}/quality, salva com o exemplo.
      fetchJson(t.quality).then((q) => {
        if (state.demo?.target !== t || !q || typeof q !== "object") return;
        for (const [id, resp] of Object.entries(q)) if (resp) state.quality.set(id, normalizeQuality(resp));
        if (state.frames.length) showFrame(state.index);
      }).catch((err) => console.debug("Exemplo salvo sem qualidade:", err));
    }
    updateSky({ recenter: true });
    setStatus(`${frames.length} observações reais (exemplo salvo) · ${t.name ?? t.id} · RA ${t.ra}°, Dec ${t.dec}°, FOV ${t.fov ?? 3}′.`, "aviso");
    setEspStatus(t.spectrum
      ? "Exemplo salvo: use “Espectro do alvo” para ver o espectro medido quando o exemplo foi gerado."
      : "Este exemplo salvo não traz espectro; o espectro precisa do servidor.");
  } catch (err) {
    console.error("Modo demonstração:", err);
    state.demo = null;
    setStatus("Não foi possível abrir o exemplo salvo.", "erro");
  }
}

window.spxEnterDemo = enterDemo; // usado por js/refimages.js

// Qualquer busca nova sai do modo demonstração.
function leaveDemo() {
  if (!state.demo) return;
  state.demo = null;
  el.avisoDemo.hidden = true;
  state.coverage = null;
  cov.key = "";
  if (state.motion) el.seguirBox.hidden = false;
}
el.demoSair.addEventListener("click", () => {
  leaveDemo();
  el.form.requestSubmit(); // tenta a busca ao vivo com as mesmas coordenadas
});

/* ---------- Eventos ---------- */
el.form.addEventListener("submit", onSubmit);
el.prev.addEventListener("click", () => step(-1));
el.next.addEventListener("click", () => step(1));
el.play.addEventListener("click", () => (state.timer ? stop() : start()));
el.speed.addEventListener("change", () => state.timer && start());
el.slider.addEventListener("input", () => { stop(); showFrame(Number(el.slider.value)); });
// Falha da imagem: painel sobre o quadro com "Tentar de novo" e "Próxima observação".
el.img.addEventListener("error", () => {
  if (!el.img.getAttribute("src")) return;
  const f = state.frames[state.index];
  el.imgFalhaMsg.textContent = state.demo
    ? "A imagem desta observação não está no exemplo salvo."
    : `Não foi possível carregar a imagem de ${f ? fmtDateTime(f.date) : "esta observação"}. ` +
      "O recorte é feito no IRSA na hora e às vezes falha ou demora.";
  el.imgProx.hidden = state.frames.length < 2;
  el.imgFalha.hidden = false;
});
el.img.addEventListener("load", () => { el.imgFalha.hidden = true; });
el.imgRetry.addEventListener("click", () => {
  const f = state.frames[state.index];
  if (!f?.imageUrl || f.imageUrl.startsWith("data:")) return;
  el.imgFalha.hidden = true;
  const u = f.imageUrl + (f.imageUrl.includes("?") ? "&" : "?") + "tentativa=" + Date.now();
  el.img.src = u;
});
el.imgProx.addEventListener("click", () => step(1));
// Edição manual de RA/Dec: o movimento próprio do alvo deixa de valer (mudar só o FOV não afeta).
el.ra.addEventListener("input", () => setMotion(null));
el.dec.addEventListener("input", () => setMotion(null));

/* ---------- Seletor de FOV com significado ----------
 * Régua logarítmica de CONFIG.FOV_MIN a CONFIG.FOV_MAX, sincronizada com o campo numérico #fov
 * (que continua sendo a fonte do valor e passa pela validação de sempre no envio).
 * Os números de cobertura vêm de /api/coverage; sem essa resposta o seletor funciona igual. */
const FOV_STOPS = [
  { fov: 1, name: "Detalhe" }, { fov: 3, name: "Objeto" }, { fov: 5, name: "Vizinhança" },
  { fov: 10, name: "Região" }, { fov: 30, name: "Campo amplo" },
];
const FOV_SPAN = Math.log(CONFIG.FOV_MAX / CONFIG.FOV_MIN);
const FOV_POS_MAX = Number(el.fovRegua.max);
const fovToPos = (f) => Math.round((Math.log(f / CONFIG.FOV_MIN) / FOV_SPAN) * FOV_POS_MAX);

// Arredonda para valores "limpos": 0,1′ abaixo de 2′, 0,5′ até 10′, 1′ acima.
function niceFov(x) {
  const s = x < 2 ? 0.1 : x < 10 ? 0.5 : 1;
  return Math.min(CONFIG.FOV_MAX, Math.max(CONFIG.FOV_MIN, Number((Math.round(x / s) * s).toFixed(1))));
}

function posToFov(p) {
  for (const s of FOV_STOPS) if (Math.abs(fovToPos(s.fov) - p) <= 15) return s.fov; // "ímã" nas paradas
  return niceFov(CONFIG.FOV_MIN * Math.exp((p / FOV_POS_MAX) * FOV_SPAN));
}

// FOV do campo numérico, se válido (sem marcar erro: a validação visível fica para o envio).
function readFov() {
  const n = parseNum(el.fov.value);
  return el.fov.value.trim() !== "" && Number.isFinite(n) && n >= RULES.fov.min && n <= RULES.fov.max ? n : null;
}

const fmtArcmin = (f) => `${String(Number(f.toFixed(2))).replace(".", ",")}′`;
const pixelScale = () => state.coverage?.pixelScale ?? CONFIG.PIXEL_SCALE_ARCSEC;
const spherexPixels = (f) => Math.round((f * 60) / pixelScale());

function moonText(f) {
  const r = CONFIG.MOON_DIAMETER_ARCMIN / f;
  return r >= 1.5 ? `≈ 1/${Math.round(r)} do diâmetro da Lua` : `≈ ${Math.round(100 / r)}% do diâmetro da Lua`;
}

const coverageEntry = (f) => state.coverage?.fovs.find((e) => Math.abs(e.fov - f) < 1e-6) ?? null;

// Custo por imagem: valor do backend para o FOV exato; para outros FOV, escala o mais próximo
// pela área em pixels (estimativa, marcada com "≈").
function kbText(f) {
  const exact = coverageEntry(f);
  if (exact?.kb !== null && exact?.kb !== undefined) return `~${fmtNum(exact.kb)} kB por imagem`;
  const ref = state.coverage?.fovs
    .filter((e) => e.kb !== null && e.pixels > 0)
    .sort((a, b) => Math.abs(Math.log(a.fov / f)) - Math.abs(Math.log(b.fov / f)))[0];
  if (!ref) return null;
  const kb = ref.kb * (spherexPixels(f) / ref.pixels) ** 2;
  return `≈ ${fmtNum(Math.max(1, Math.round(kb)))} kB por imagem (estimado a partir de ${fmtArcmin(ref.fov)})`;
}

function coverageText(e) {
  return `${e.observations} observações: ${e.complete} com quadro completo, ${e.partial} parcia${e.partial === 1 ? "l" : "is"}`;
}

(function buildFovStops() {
  el.fovParadas.replaceChildren(...FOV_STOPS.map((s) => {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "fov-parada";
    b.dataset.fov = s.fov;
    const top = document.createElement("strong");
    top.textContent = `${fmtArcmin(s.fov)} ${s.name}`;
    const sub = document.createElement("small"); // contagem de cobertura (preenchida quando houver)
    b.append(top, sub);
    b.addEventListener("click", () => { el.fov.value = String(s.fov); onFovChange(); });
    return b;
  }));
})();

function renderFovUi({ fromSlider = false } = {}) {
  const f = readFov();
  const rec = state.coverage?.recommended ?? null;
  for (const b of el.fovParadas.children) {
    const sf = Number(b.dataset.fov);
    const e = coverageEntry(sf);
    b.setAttribute("aria-pressed", String(f !== null && Math.abs(sf - f) < 1e-6));
    b.classList.toggle("recomendado", rec !== null && Math.abs(sf - rec) < 1e-6);
    b.querySelector("small").textContent =
      `${spherexPixels(sf)} px` + (e ? ` · ${e.complete}/${e.observations} completos` : "") +
      (rec !== null && Math.abs(sf - rec) < 1e-6 ? " · ★ recomendado" : "");
    b.title = `${fmtArcmin(sf)}: ${spherexPixels(sf)} × ${spherexPixels(sf)} pixels SPHEREx, ${moonText(sf)}` +
      (e ? `. ${coverageText(e)}.` : "");
  }
  if (f === null) {
    el.fovInfo.textContent = `Informe um FOV entre ${fmtArcmin(CONFIG.FOV_MIN)} e ${fmtArcmin(CONFIG.FOV_MAX)}.`;
    return;
  }
  if (!fromSlider) el.fovRegua.value = fovToPos(f);
  el.fovRegua.setAttribute("aria-valuetext", `${fmtArcmin(f)}, ${spherexPixels(f)} pixels SPHEREx de lado`);

  const parts = [
    `${fmtArcmin(f)} = ${spherexPixels(f)} × ${spherexPixels(f)} pixels SPHEREx (${fmtNum(pixelScale())}″ cada)`,
    moonText(f),
  ];
  const kb = kbText(f);
  if (kb) parts.push(kb);
  const e = coverageEntry(f);
  if (e) parts.push(coverageText(e));
  else if (state.coverage?.fovs.length) parts.push(`contagem de cobertura disponível para ${state.coverage.fovs.map((x) => fmtArcmin(x.fov)).join(", ")}`);
  else if (state.coverageLoading) parts.push("consultando a cobertura destas coordenadas");
  if (rec !== null) parts.push(Math.abs(rec - f) < 1e-6 ? "★ FOV recomendado para estas coordenadas" : `recomendado aqui: ${fmtArcmin(rec)}`);
  const mv = state.coverage?.motion;
  if (mv !== null && mv !== undefined) {
    const px = (mv / pixelScale()).toLocaleString("pt-BR", { maximumFractionDigits: 1 });
    parts.push(`o alvo se desloca ${fmtNum(mv)}″ (≈ ${px} px) nas datas disponíveis`);
  }
  el.fovInfo.textContent = parts.join(" · ") + ".";
}

function onFovChange(opts) {
  renderFovUi(opts);
  scheduleSky(); // o retângulo do FOV no mapa do céu acompanha o seletor
}

el.fovRegua.addEventListener("input", () => {
  el.fov.value = String(posToFov(Number(el.fovRegua.value)));
  el.fov.setAttribute("aria-invalid", "false");
  $("fov-erro").textContent = "";
  onFovChange({ fromSlider: true });
});
el.fov.addEventListener("input", () => onFovChange());

/* Cobertura por FOV (/api/coverage): debounce, cancela pedidos antigos, falha em silêncio. */
const cov = { timer: null, ctl: null, key: "" };

function coordsFromInputs() {
  const ra = parseCoord(el.ra.value, "ra"), dec = parseCoord(el.dec.value, "dec");
  const ok = Number.isFinite(ra) && Number.isFinite(dec) && ra >= 0 && ra < 360 && dec >= -90 && dec <= 90;
  return ok ? { ra: Number(ra.toFixed(6)), dec: Number(dec.toFixed(6)) } : null;
}

function normalizeCoverage(d) {
  const num = (v) => (typeof v === "number" && Number.isFinite(v) ? v : null);
  const fovs = (Array.isArray(d?.fovs) ? d.fovs : [])
    .map((e) => ({
      fov: num(e.fov_arcmin), pixels: num(e.pixels), observations: num(e.observations),
      complete: num(e.complete), partial: num(e.partial), kb: num(e.estimated_kb_per_image),
    }))
    .filter((e) => e.fov !== null && e.observations !== null && e.complete !== null && e.partial !== null);
  return {
    fovs, recommended: num(d?.recommended_fov_arcmin),
    motion: num(d?.motion_arcsec_over_survey), pixelScale: num(d?.pixel_scale_arcsec),
  };
}

function scheduleCoverage() {
  const c = coordsFromInputs();
  const motion = activeMotion();
  const key = c ? JSON.stringify([c.ra, c.dec, motionParams(motion)]) : "";
  if (state.demo) { // exemplo salvo: cobertura vem do coverage.json, nunca do servidor
    clearTimeout(cov.timer);
    cov.ctl?.abort();
    const t = state.demo.target;
    const same = c && Math.abs(c.ra - t.ra) < 1e-5 && Math.abs(c.dec - t.dec) < 1e-5;
    state.coverage = same && state.demo.coverage?.fovs.length ? state.demo.coverage : null;
    state.coverageLoading = false;
    renderFovUi();
    return;
  }
  if (key === cov.key) return; // mesmo pedido já feito ou em andamento
  clearTimeout(cov.timer);
  cov.ctl?.abort();
  cov.key = key;
  state.coverage = null;
  state.coverageLoading = !!c;
  renderFovUi();
  if (c) cov.timer = setTimeout(() => fetchCoverage(c, motion, key), CONFIG.COVERAGE_DEBOUNCE_MS);
}

async function fetchCoverage({ ra, dec }, motion, key) {
  const ctl = (cov.ctl = new AbortController());
  const timer = setTimeout(() => ctl.abort(), CONFIG.COVERAGE_TIMEOUT_MS);
  try {
    const url = new URL(CONFIG.COVERAGE_PATH, CONFIG.API_BASE);
    url.search = new URLSearchParams({ ra_deg: ra, dec_deg: dec, ...motionParams(motion), ...CONFIG.EXTRA_PARAMS }).toString();
    const res = await fetch(url, { signal: ctl.signal });
    if (!res.ok) throw new Error("http-" + res.status);
    const data = normalizeCoverage(await res.json());
    if (cov.key !== key) return;
    state.coverage = data.fovs.length ? data : null;
  } catch (err) {
    if (cov.key !== key) return; // pedido substituído
    console.debug("Cobertura por FOV indisponível:", err);
    cov.key = ""; // permite tentar de novo na próxima busca
  } finally {
    clearTimeout(timer);
    if (cov.key === key || cov.key === "") { state.coverageLoading = false; renderFovUi(); }
  }
}

/* "Seguir o alvo": só aparece quando há movimento próprio (alvo de exemplo ou link compartilhado). */
function setMotion(m) {
  state.motion = m;
  el.seguirBox.hidden = !m;
  scheduleCoverage();
}

el.seguir.addEventListener("change", () => {
  scheduleCoverage();
  if (state.values && !el.mock.checked) el.form.requestSubmit(); // refaz a busca com/sem correção
});

// Alvos de exemplo: nomes e coordenadas vêm do backend (o frontend não guarda coordenadas).
// Formato esperado: [{ name, ra, dec, fov?, note? }] ou { targets: [...] }, RA/Dec em graus.
function normalizeTarget(t) {
  return {
    name: String(t.name ?? t.id ?? ""),
    ra: Number(t.ra), dec: Number(t.dec),
    fov: Number(t.fov ?? t.default_fov ?? 3),
    note: t.note ?? t.description ?? "",
    // ra/dec estão na época ref_epoch_jyear; null se o alvo não tiver movimento próprio conhecido.
    motion: parseMotion(t.pm_ra_cosdec_masyr, t.pm_dec_masyr, t.ref_epoch_jyear, t.name ?? t.id),
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
        setMotion(t.motion);
        el.form.requestSubmit();
      });
      box.append(b);
    }
  } catch (err) {
    box.querySelector("span").textContent = "Alvos de exemplo indisponíveis no momento. Informe as coordenadas manualmente.";
    // Servidor inacessível (ex.: site publicado só com arquivos estáticos): oferece os exemplos salvos.
    if (err instanceof TypeError || err?.name === "TimeoutError") {
      state.backendDown = true;
      const m = await loadDemoManifest();
      if (!m) return;
      box.querySelector("span").textContent = "Observações ao vivo fora do ar agora. Exemplos reais salvos:";
      for (const t of m.targets) {
        const b = document.createElement("button");
        b.type = "button";
        b.className = "chip";
        b.textContent = `${t.name ?? t.id} (exemplo salvo)`;
        b.addEventListener("click", () => enterDemo(t.id));
        box.append(b);
      }
      // Sem busca em andamento nem exemplo aberto: mostra a oferta no lugar da mensagem inicial.
      if (!state.values && !state.demo && el.alt.hidden) showAlternatives("network", "", { autoRetry: false });
    }
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

// Raio da abertura (aperture_arcsec do backend), limitado a CONFIG.APERTURE_MIN..MAX.
const radius = () => {
  const v = Number(String(el.raio.value).replace(",", "."));
  return Number.isFinite(v) && v > 0
    ? Math.min(CONFIG.APERTURE_MAX, Math.max(CONFIG.APERTURE_MIN, v)) : CONFIG.APERTURE_DEFAULT;
};

/* Geometria do quadro comum (backend: services/common_frame.py): projeção TAN, norte para cima,
 * leste à esquerda, lado = FOV, centrado em metadata.cutout_center_* (posição propagada pelo
 * movimento próprio quando "Seguir" está ativo). Para campos de poucos minutos de arco a
 * aproximação plana abaixo difere da TAN exata por muito menos que um pixel (6,15″). */
const frameCenter = () => state.frames[state.index]?.cutoutCenter ?? { ra: state.values.ra, dec: state.values.dec };
const pixelFrac = () => pixelScale() / (state.values.fov * 60); // 1 pixel em fração do lado

function coordFromFrac(fx, fy) {
  const c = frameCenter();
  const lado = state.values.fov * 60; // segundos de arco
  const leste = (0.5 - fx) * lado; // leste à esquerda
  const norte = (0.5 - fy) * lado; // norte para cima
  const dec = Math.max(-90, Math.min(90, c.dec + norte / 3600));
  const ra = c.ra + leste / 3600 / Math.cos((c.dec * Math.PI) / 180);
  return { ra: ((ra % 360) + 360) % 360, dec };
}

function fracFromCoord(ra, dec) {
  const c = frameCenter();
  const lado = state.values.fov * 60;
  let dra = ra - c.ra;
  if (dra > 180) dra -= 360;
  if (dra < -180) dra += 360;
  const leste = dra * 3600 * Math.cos((c.dec * Math.PI) / 180);
  return { fx: 0.5 - leste / lado, fy: 0.5 - ((dec - c.dec) * 3600) / lado };
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

// Posição do marcador no quadro em exibição. O alvo com movimento fica no centro de cada quadro
// (o backend recentra nele); os demais pontos são fixos no céu e são reprojetados por quadro.
function markerFrac(p) {
  if (p.target && p.motion && activeMotion()) return { fx: 0.5, fy: 0.5 };
  if (state.isMock || !state.frames.length) return { fx: p.fx, fy: p.fy };
  return fracFromCoord(p.ra, p.dec);
}

function positionMarkers() {
  const lado = state.values ? Math.max(4, ((2 * radius()) / (state.values.fov * 60)) * 100) : 6;
  for (const k of ["A", "B"]) {
    const p = state.pts[k];
    markers[k].hidden = !p;
    if (!p) continue;
    const { fx, fy } = markerFrac(p);
    const fora = fx < 0 || fx > 1 || fy < 0 || fy > 1;
    markers[k].hidden = fora;
    markers[k].style.left = fx * 100 + "%";
    markers[k].style.top = fy * 100 + "%";
    markers[k].style.width = `max(14px, ${lado}%)`;
  }
}

function renderMarkers() {
  positionMarkers();
  scheduleSky();
}

// Marca um ponto. Um clique a ≤ 1 pixel do centro com "Seguir" ativo (ou o botão
// "Espectro do alvo") é o próprio alvo: envia também o movimento próprio ao backend.
function placePoint(key, fx, fy, { defer = false, target = false } = {}) {
  if (!state.values) return;
  fx = Math.min(1, Math.max(0, fx));
  fy = Math.min(1, Math.max(0, fy));
  const motion = state.isMock ? null : activeMotion();
  const noCentro = Math.hypot(fx - 0.5, fy - 0.5) <= pixelFrac();
  const isTarget = target || (motion !== null && noCentro);
  const old = state.pts[key];
  // O alvo usa as coordenadas informadas (época ref_epoch_jyear); o backend propaga para cada exposição.
  const coords = isTarget ? { ra: state.values.ra, dec: state.values.dec } : coordFromFrac(fx, fy);
  const pt = { fx: isTarget ? 0.5 : fx, fy: isTarget ? 0.5 : fy, ...coords,
               target: isTarget, motion: isTarget ? motion : null, data: null, req: null, timer: null };
  clearTimeout(old?.timer);
  state.specCtl[key]?.abort();
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
  el.espAcoes.hidden = true;
  updateProgress();
  renderMarkers();
  renderChart();
  setEspStatus("Faça uma busca e marque um ponto na imagem.");
  if (state.values) setEspStatus("Clique na imagem para marcar o ponto A, ou use “Espectro do alvo”.");
}

/* Dados: API ou, no modo de teste, espectro fictício */
function normalizeSpectrum(data) {
  const num = (v) => (v === null || v === undefined || v === "" || !Number.isFinite(Number(v)) ? null : Number(v));
  const points = (data?.points ?? [])
    .map((o) => {
      const det = parseInt(String(o.detector ?? "").replace(/\D/g, ""), 10);
      const flags = Array.isArray(o.flags) ? o.flags.map(String) : [];
      return {
        wl: num(o.wavelength_um), bw: num(o.bandwidth_um),
        flux: num(o.flux), err: num(o.flux_err),
        det: det >= 1 && det <= 6 ? det : null,
        date: o.observed_at ?? null, obsId: o.observation_id ?? null,
        flagged: Boolean(o.flagged), flags,
      };
    })
    .filter((p) => p.wl !== null && p.flux !== null)
    .sort((a, b) => a.wl - b.wl);
  return {
    unit: data?.unit ?? null, points,
    nExposures: num(data?.n_exposures), aperture: num(data?.aperture_arcsec),
    wlSource: data?.wavelength_source ?? null, dataSource: data?.data_source ?? null,
  };
}

async function fetchSpectrum(key, pt) {
  state.specCtl[key]?.abort();
  const ctl = (state.specCtl[key] = new AbortController());
  const timer = setTimeout(() => ctl.abort("timeout"), CONFIG.SPECTRUM_TIMEOUT_MS);
  try {
    const url = new URL(CONFIG.SPECTRUM_PATH, CONFIG.API_BASE);
    url.search = new URLSearchParams({
      ra_deg: pt.ra.toFixed(6), dec_deg: pt.dec.toFixed(6),
      ...motionParams(pt.motion), // só para o próprio alvo; pontos do fundo do céu são fixos
      aperture_arcsec: radius(), max_exposures: CONFIG.SPECTRUM_MAX_EXPOSURES,
      ...CONFIG.EXTRA_PARAMS,
    }).toString();
    const res = await fetch(url, { signal: ctl.signal });
    if (!res.ok) throw await apiError(res);
    return normalizeSpectrum(await res.json());
  } finally {
    clearTimeout(timer);
  }
}

// Espectro inventado, só para testar a interface (o centro da imagem é mais brilhante).
// Mesmo formato do backend: um ponto por exposição, alguns marcados como contaminados.
function mockSpectrum(pt) {
  const r = Math.hypot(pt.fx - 0.5, pt.fy - 0.5);
  const ganho = 0.15 + 1.85 * Math.exp(-((r / 0.15) ** 2));
  const points = [];
  const n = 54, inicio = Date.UTC(2025, 4, 1);
  for (let i = 0; i < n; i++) {
    const wl = 0.75 + (4.25 * (i + 0.5)) / n;
    const d = DET_RANGES.findIndex(([lo, hi]) => wl >= lo && wl < hi);
    const flux = (40 * Math.exp(-wl / 1.6) + 6 + 3 * Math.sin(wl * 5)) * ganho;
    const flagged = i % 11 === 4;
    points.push({
      wavelength_um: wl, bandwidth_um: wl / (d >= 4 ? 120 : 40), // R aproximado, valor fictício
      flux: flagged ? flux * 1.8 : flux, flux_err: 0.06 * flux + 0.4,
      detector: "D" + (d + 1), observed_at: new Date(inicio + i * 3 * 864e5).toISOString(),
      observation_id: "FICTICIO-" + String(i + 1).padStart(2, "0"),
      flagged, flags: flagged ? ["TRANSIENT"] : [],
    });
  }
  return normalizeSpectrum({ unit: "valor fictício", points, n_exposures: n, aperture_arcsec: radius(),
    wavelength_source: "fictício (teste de interface)", data_source: "mock" });
}

// Modo demonstração: só o espectro do alvo, medido quando o exemplo foi salvo (spectrum.json).
async function demoSpectrum(pt) {
  const t = state.demo.target;
  const noAlvo = pt.target || Math.hypot(pt.fx - 0.5, pt.fy - 0.5) <= 2 * pixelFrac();
  const falha = (message) => Object.assign(new Error(message), { demo: true });
  if (!t.spectrum) throw falha("Este exemplo salvo não traz espectro. O espectro de um ponto precisa do servidor.");
  if (!noAlvo) throw falha("No exemplo salvo só há o espectro do alvo (centro do quadro). Para outros pontos é preciso o servidor; use “Espectro do alvo”.");
  state.demo.spectrum ??= await fetchJson(t.spectrum);
  pt.target = true; // o espectro salvo é o do alvo
  return normalizeSpectrum(state.demo.spectrum);
}

el.espRetry.addEventListener("click", () => {
  const k = el.espRetry.dataset.key;
  el.espAcoes.hidden = true;
  if (k && state.pts[k]) loadSpectrum(k);
});

// Barra de progresso indeterminada enquanto algum ponto espera o backend.
const updateProgress = () => { el.espProgresso.hidden = !["A", "B"].some((k) => state.pts[k]?.loading); };

const ptLabel = (key, pt) => `ponto ${key}${pt.target ? " (alvo" + (pt.motion ? ", seguindo o movimento próprio)" : ")") : ""}`;

async function loadSpectrum(key) {
  const pt = state.pts[key];
  if (!pt) return;
  const req = (pt.req = {});
  pt.data = null;
  pt.loading = !state.isMock;
  renderChart();
  updateProgress();
  setEspStatus(state.isMock
    ? `Calculando o espectro do ${ptLabel(key, pt)}…`
    : `Medindo o ${ptLabel(key, pt)} em até ${CONFIG.SPECTRUM_MAX_EXPOSURES} exposições… A primeira vez é lenta ` +
      "(cerca de 1–2 s por exposição, podendo passar de um minuto); depois o resultado fica em cache.", "carregando");
  el.espAcoes.hidden = true;
  try {
    const data = state.isMock ? mockSpectrum(pt) : state.demo ? await demoSpectrum(pt) : await fetchSpectrum(key, pt);
    if (pt.req !== req || state.pts[key] !== pt) return;
    if (!data.points.length) {
      setEspStatus(`Sem medidas para o ponto ${key}: nenhuma exposição cobre esse ponto. Tente outro ponto.`);
      return;
    }
    pt.data = data;
    renderChart();
    const nFlag = data.points.filter((p) => p.flagged).length;
    if (nFlag === data.points.length) {
      // Ex.: Estrela de Barnard satura o SPHEREx: todas as medidas sinalizadas. Não apresentar como espectro.
      setEspStatus(`Espectro inválido para o ${ptLabel(key, pt)}: todas as ${nFlag} medidas estão sinalizadas como contaminadas ` +
        `(${[...new Set(data.points.flatMap((p) => p.flags))].map(flagName).join(", ") || "flags do SPHEREx"}). ` +
        "Para uma fonte muito brilhante isso indica saturação do detector; os valores no gráfico não representam o brilho real." +
        (state.demo ? " (exemplo real salvo)" : ""), "aviso");
      return;
    }
    setEspStatus(
      `${ptLabel(key, pt).replace(/^p/, "P")}: ${data.points.length} medidas` +
        (data.nExposures !== null ? ` de ${data.nExposures} exposições` : "") +
        `, abertura de ${data.aperture ?? radius()}″, RA ${pt.ra.toFixed(4)}°, Dec ${pt.dec.toFixed(4)}°.` +
        (nFlag ? ` ${nFlag} com contaminação na abertura (símbolo vazado).` : "") +
        (data.dataSource === "stale_cache" ? " Atenção: IRSA indisponível, usando resultado salvo." : "") +
        (state.isMock ? " (dados fictícios)" : "") +
        (state.demo ? " (exemplo real salvo; medido quando o exemplo foi gerado)" : ""),
      data.dataSource === "stale_cache" ? "aviso" : ""
    );
  } catch (err) {
    if (pt.req !== req || state.pts[key] !== pt) return;
    const timedOut = err === "timeout" || err?.name === "AbortError";
    if (timedOut && state.specCtl[key]?.signal.reason !== "timeout") return; // pedido substituído
    if (err?.demo) { setEspStatus(err.message); return; }
    el.espRetry.dataset.key = key;
    el.espRetry.textContent = `Tentar de novo (ponto ${key})`;
    el.espAcoes.hidden = false;
    setEspStatus(
      timedOut
        ? "O cálculo do espectro demorou demais. Tente novamente: as exposições já processadas ficam em cache."
        : err instanceof ApiError
          ? (err.status === 404 && !err.code
              ? "O espectro de um ponto ainda não está disponível neste backend. Use os dados fictícios para testar esta seção."
              : API_ERRORS[err.code] ?? err.message)
          : "Não foi possível obter o espectro. Verifique se o backend está em execução.",
      "erro"
    );
  } finally {
    if (pt.req === req) pt.loading = false;
    updateProgress();
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
  const ocultar = el.espOcultar.checked;
  const series = ["A", "B"]
    .filter((k) => state.pts[k]?.data?.points.length)
    .map((k) => ({ key: k, all: state.pts[k].data.points, unit: state.pts[k].data.unit, data: state.pts[k].data }))
    .map((s) => ({ ...s, pts: ocultar ? s.all.filter((p) => !p.flagged) : s.all }));
  el.espGraf.hidden = el.espTabBox.hidden = !series.length;
  const fontes = [...new Set(series.map((s) => s.data.wlSource).filter(Boolean))];
  el.espNota.hidden = !series.length;
  el.espNota.textContent = series.length
    ? "Cada ponto é uma exposição: o SPHEREx mede o espectro porque o ponto cai em posições diferentes do detector " +
      "(filtro linear variável). Fluxo = média na abertura menos o fundo local (anel). " +
      `Comprimento de onda: ${fontes.join("; ") || "fonte não informada"}.`
    : "";
  if (!series.length) return;

  const W = 720, H = 360, m = { l: 64, r: 16, t: 16, b: 48 };
  const xmin = 0.7, xmax = 5.05;
  const all = series.flatMap((s) => s.pts);
  if (!all.length) {
    el.espGraf.replaceChildren(Object.assign(document.createElement("p"), {
      className: "placeholder", textContent: "Todas as medidas estão marcadas como contaminadas. Desmarque “Ocultar contaminados” para vê-las." }));
    renderTable(series);
    return;
  }
  let ymin = Math.min(0, ...all.map((p) => p.flux - (p.err ?? 0)));
  let ymax = Math.max(...all.map((p) => p.flux + (p.err ?? 0)));
  if (ymax <= ymin) ymax = ymin + 1;
  const step = niceStep(ymax - ymin);
  ymin = Math.floor(ymin / step) * step;
  ymax = Math.ceil(ymax / step) * step;
  const X = (w) => m.l + ((Math.min(xmax, Math.max(xmin, w)) - xmin) / (xmax - xmin)) * (W - m.l - m.r);
  const Y = (v) => H - m.b - ((v - ymin) / (ymax - ymin)) * (H - m.t - m.b);
  const unit = series.find((s) => s.unit)?.unit ?? "unidades do backend";

  const svg = svgEl("svg", {
    viewBox: `0 0 ${W} ${H}`, role: "img",
    "aria-label": `Gráfico de fluxo por comprimento de onda para ${series.map((s) => "o ponto " + s.key).join(" e ")}. Os mesmos dados estão na tabela abaixo.`,
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
  svg.append(svgEl("text", { x: (m.l + W - m.r) / 2, y: H - 8, "text-anchor": "middle", fill: "var(--text)", "font-size": 13 }, "Comprimento de onda λ (µm)"));
  svg.append(svgEl("text", { transform: `translate(14 ${(m.t + H - m.b) / 2}) rotate(-90)`, "text-anchor": "middle", fill: "var(--text)", "font-size": 13 }, `Fluxo (${unit})`));

  for (const s of series) {
    const cor = s.key === "A" ? "var(--ir)" : "var(--cool)";
    const limpos = s.pts.filter((p) => !p.flagged); // a linha liga só as medidas sem contaminação
    if (limpos.length > 1) svg.append(svgEl("polyline", {
      points: limpos.map((p) => `${X(p.wl)},${Y(p.flux)}`).join(" "),
      fill: "none", stroke: cor, "stroke-width": 1.2, opacity: 0.5,
      "stroke-dasharray": s.key === "B" ? "6 4" : "none",
    }));
    for (const p of s.pts) {
      const x = X(p.wl), y = Y(p.flux);
      const corDet = p.det ? DET_COLORS[p.det - 1] : "#ffffff";
      if (p.err) svg.append(svgEl("line", { x1: x, x2: x, y1: Y(p.flux - p.err), y2: Y(p.flux + p.err), stroke: cor, opacity: 0.6 }));
      // Contaminado: símbolo vazado (só contorno, na cor do detector).
      const estilo = p.flagged
        ? { fill: "none", stroke: corDet, "stroke-width": 1.6 }
        : { fill: corDet, stroke: "#fff", "stroke-width": 0.8 };
      const forma = s.key === "A"
        ? svgEl("circle", { cx: x, cy: y, r: 3.5, ...estilo })
        : svgEl("polygon", { points: `${x},${y - 4.5} ${x + 4.5},${y} ${x},${y + 4.5} ${x - 4.5},${y}`, ...estilo });
      forma.append(svgEl("title", {},
        `${s.key} · λ ${fmtNum(p.wl)} µm` + (p.bw !== null ? ` (largura ${fmtNum(p.bw)} µm)` : "") +
        ` · ${p.det ? "D" + p.det : "detector ?"} · fluxo ${fmtNum(p.flux)}` + (p.err !== null ? ` ± ${fmtNum(p.err)}` : "") +
        ` ${unit}` + (p.date ? ` · ${fmtDateTime(p.date)}` : "") +
        (p.flagged ? ` · contaminado: ${p.flags.map(flagName).join(", ") || "sim"}` : "")));
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
  if (series.some((s) => s.pts.some((p) => p.flagged))) {
    const li = document.createElement("li");
    const sw = document.createElement("span");
    sw.className = "sw sw-vazado";
    li.append(sw, "contaminado (símbolo vazado)");
    legenda.append(li);
  }
  el.espGraf.replaceChildren(svg, legenda);
  renderTable(series);
}

// Uma linha por medida (exposição); A e B vêm de exposições diferentes, então não são pareados.
function renderTable(series) {
  const list = series.flatMap((s) => s.all.map((p) => ({ key: s.key, unit: s.unit, pt: state.pts[s.key], ...p })))
    .sort((a, b) => a.key.localeCompare(b.key) || a.wl - b.wl);
  state.rows = list;
  state.keys = series.map((s) => s.key);

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
  cap.textContent = `Fluxo por comprimento de onda (${series.find((s) => s.unit)?.unit ?? "unidades do backend"})`;
  const thead = document.createElement("thead");
  thead.append(tr(["Ponto", "λ (µm)", "Largura (µm)", "Detector", "Fluxo", "Erro", "Data (UTC)", "Contaminação"], "th"));
  const tbody = document.createElement("tbody");
  for (const r of list) {
    tbody.append(tr([
      r.key, fmtNum(r.wl), r.bw === null ? "—" : fmtNum(r.bw), r.det ? "D" + r.det : "—",
      fmtNum(r.flux), r.err === null ? "—" : fmtNum(r.err), r.date ? fmtDateTime(r.date) : "—",
      r.flagged ? r.flags.map(flagName).join(", ") || "sim" : "não",
    ]));
  }
  el.espTabela.replaceChildren(cap, thead, tbody);
}

function downloadCsv() {
  const q = (v) => (/[",\n]/.test(String(v)) ? `"${String(v).replace(/"/g, '""')}"` : String(v));
  const linhas = [["ponto", "ra_deg", "dec_deg", "abertura_arcsec", "comprimento_de_onda_um", "largura_banda_um",
    "detector", "fluxo", "erro_fluxo", "unidade", "observado_em", "observation_id", "contaminado", "flags"].join(",")];
  for (const r of state.rows) {
    linhas.push([
      r.key, r.pt?.ra ?? "", r.pt?.dec ?? "", r.pt?.data?.aperture ?? "", r.wl, r.bw ?? "",
      r.det ? "D" + r.det : "", r.flux, r.err ?? "", r.unit ?? "", r.date ?? "", r.obsId ?? "",
      r.flagged, r.flags.join(";"),
    ].map(q).join(","));
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
  const p = state.pts[key] ? markerFrac(state.pts[key]) : { fx: 0.5, fy: 0.5 };
  const mov = { ArrowLeft: [-passo, 0], ArrowRight: [passo, 0], ArrowUp: [0, -passo], ArrowDown: [0, passo] }[e.key];
  if (mov) {
    e.preventDefault();
    placePoint(key, p.fx + mov[0], p.fy + mov[1], { defer: true });
  } else if (e.key === "Enter" || e.key === " ") {
    e.preventDefault();
    placePoint(key, p.fx, p.fy);
  } else if (e.key === "Escape" && state.pts[key]) {
    state.specCtl[key]?.abort();
    state.pts[key] = null;
    updateProgress();
    renderMarkers();
    renderChart();
  }
});

el.espCentro.addEventListener("click", () => placePoint(activeKey(), 0.5, 0.5));
el.espAlvo.addEventListener("click", () => {
  if (!state.values) { setEspStatus("Faça uma busca primeiro."); return; }
  document.querySelector('input[name="ponto"][value="A"]').checked = true;
  placePoint("A", 0.5, 0.5, { target: true });
});
el.espLimpar.addEventListener("click", clearPoints);
el.espCsv.addEventListener("click", downloadCsv);
el.espOcultar.addEventListener("change", renderChart);
el.raio.addEventListener("change", () => {
  el.raio.value = radius();
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

/* ---------- Mapa do céu (Aladin Lite) ----------
 * Carregado quando a seção aparece na tela (ou pelo botão). O código do Aladin vem da primeira
 * fonte que responder dentro do tempo limite; o fundo (HiPS) só é usado depois de verificado. */
const sky = { A: null, aladin: null, timer: null, frameTimer: null, drawGen: 0, opening: null,
              dyn: null, alvo: null, bgSeq: 0, timing: null };

const SPHEREX_PREFIX = "spherex:"; // valor das opções SPHEREx no <select>: "spherex:<detector>"

(function preencherFundos() {
  const spherex = document.createElement("optgroup");
  spherex.label = "SPHEREx (dados da NASA)";
  DET_RANGES.forEach((r, i) =>
    spherex.append(new Option(`SPHEREx D${i + 1} · ≈ ${fmtRange(r)}`, SPHEREX_PREFIX + (i + 1))));
  const outros = document.createElement("optgroup");
  outros.label = "Outros telescópios (comparação)";
  // Em 2026-11-15 o alasky/alaskybis não respondia para alguns HiPS e o Aladin, com os IDs "P/...",
  // escolhia o alaskybis: o fundo ficava cinza. Por isso usamos URLs explícitas dos espelhos do IRSA.
  CONFIG.HIPS_FALLBACK.forEach((h) => outros.append(new Option(`${h.name} (${h.why})`, h.url)));
  el.ceuFundo.replaceChildren(spherex, outros);
})();

// O CDS publica cada mapa HiPS em dois espelhos (alasky e alaskybis). Em algumas regiões/redes um deles
// responde 404; então testamos o arquivo "properties" de cada um e usamos o primeiro que responder.
const HIPS_MIRRORS = ["https://alasky.cds.unistra.fr", "https://alaskybis.cds.unistra.fr"];
// Servidores alternativos (fora do CDS) indicados pelo próprio CDS em cds.unistra.fr durante o incidente de nov/2026.
// O SPHEREx só é publicado pelo CDS: não há alternativa confirmada para ele.
const HIPS_ALT = {
  "P/DSS2/color": ["https://skies.esac.esa.int/DSSColor"],
  "P/2MASS/color": ["https://skies.esac.esa.int/2MASSColor"],
  "P/allWISE/color": ["https://skies.esac.esa.int/AllWISEColor"],
};
const hipsCache = new Map();
async function hipsOk(base) {
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), 8000);
  try {
    const r = await fetch(`${base}/properties`, { signal: ctl.signal });
    if (r.ok) return true;
    console.warn(`Mapa do céu: ${base} respondeu ${r.status}.`);
  } catch (err) {
    console.warn(`Mapa do céu: não consegui falar com ${base}.`, err);
  } finally { clearTimeout(timer); }
  return false;
}
async function resolveSurvey(value) {
  if (hipsCache.has(value)) return hipsCache.get(value);
  let candidatos;
  if (/^https?:\/\//.test(value)) {
    const path = new URL(value).pathname;
    candidatos = HIPS_MIRRORS.map((m) => m + path);
  } else {
    // ID (ex.: P/DSS2/color): tenta os servidores alternativos; se nenhum responder, deixa o Aladin usar o CDS
    candidatos = HIPS_ALT[value] ?? [];
    for (const c of candidatos) if (await hipsOk(c)) { hipsCache.set(value, c); return c; }
    return value;
  }
  for (const c of candidatos) if (await hipsOk(c)) { hipsCache.set(value, c); return c; }
  return null;
}

function setCeuStatus(msg, kind = "") {
  el.ceuStatus.textContent = msg;
  el.ceuStatus.className = "status " + kind;
}

function setFundoInfo(msg, kind = "") {
  el.ceuFundoInfo.textContent = msg;
  el.ceuFundoInfo.className = "note " + kind;
}

const withTimeout = (p, ms, msg) => {
  let t;
  return Promise.race([p, new Promise((_, rej) => { t = setTimeout(() => rej(new Error(msg)), ms); })])
    .finally(() => clearTimeout(t));
};

function loadScript(url) {
  return new Promise((resolve, reject) => {
    const s = document.createElement("script");
    s.src = url;
    s.onload = resolve;
    s.onerror = () => { s.remove(); reject(new Error("Falha ao baixar o script do Aladin Lite: " + url)); };
    document.head.append(s);
  });
}

async function loadAladin() {
  if (sky.A) return sky.A;
  const falhas = [];
  for (const src of CONFIG.ALADIN_SOURCES) {
    const t0 = performance.now();
    try {
      let A;
      if (src.type === "module") {
        A = (await withTimeout(import(src.url), CONFIG.ALADIN_SOURCE_TIMEOUT_MS, "tempo esgotado: " + src.url)).default;
      } else {
        await withTimeout(loadScript(src.url), CONFIG.ALADIN_SOURCE_TIMEOUT_MS, "tempo esgotado: " + src.url);
        A = window.A;
      }
      if (!A?.aladin) throw new Error("O código do Aladin carregou, mas não expôs A.aladin: " + src.url);
      // Rejeita sem WebGL2: aí não adianta tentar outra fonte.
      await withTimeout(A.init, CONFIG.ALADIN_INIT_TIMEOUT_MS, "inicialização do Aladin demorou demais");
      console.info(`Mapa do céu: Aladin Lite de ${src.url} em ${((performance.now() - t0) / 1000).toFixed(1)} s`);
      sky.source = src.url;
      return (sky.A = A);
    } catch (err) {
      if (/webgl/i.test(String(err))) throw err;
      console.warn(`Mapa do céu: fonte falhou após ${((performance.now() - t0) / 1000).toFixed(1)} s, tentando a próxima.`, err);
      falhas.push(err);
    }
  }
  throw falhas.at(-1) ?? new Error("Nenhuma fonte do Aladin Lite configurada.");
}

/* Disponibilidade de um HiPS: o arquivo "properties" precisa responder (com tempo limite).
 * Resultado ("ok" | "missing" = o servidor respondeu sem o HiPS | "down" = sem resposta),
 * guardado por URL durante a sessão. */
const hipsProbe = new Map();
function probeHipsState(url) {
  if (!hipsProbe.has(url)) {
    hipsProbe.set(url, fetch(url + "/properties", { signal: AbortSignal.timeout(CONFIG.HIPS_PROBE_TIMEOUT_MS) })
      .then(async (r) => (r.ok && /hips_|obs_title|creator_did/i.test(await r.text()) ? "ok" : "missing"))
      .catch(() => "down"));
  }
  return hipsProbe.get(url);
}
const probeHips = async (url) => (await probeHipsState(url)) === "ok";

// Espelhos (mesmo conteúdo): o primeiro "ok" vence; se o principal RESPONDER que não tem o HiPS,
// não vale esperar o tempo limite dos espelhos (em 2026-11-15: alasky 404 rápido, alaskybis sem resposta).
function firstMirror(urls) {
  return new Promise((resolve) => {
    let pend = urls.length;
    urls.forEach((u, i) => probeHipsState(u).then((st) => {
      if (st === "ok") resolve(i);
      else if (i === 0 && st === "missing") resolve(-1);
      if (--pend === 0) resolve(-1);
    }));
  });
}

/* Resolve o fundo pedido. SPHEREx: tenta os espelhos do CDS; se nenhum responder, usa a cadeia
 * CONFIG.HIPS_FALLBACK (AllWISE → 2MASS → DSS2). As verificações rodam em paralelo. */
async function resolveBackground(value) {
  const isSpherex = value.startsWith(SPHEREX_PREFIX);
  const det = isSpherex ? value.slice(SPHEREX_PREFIX.length) : null;
  const pedidos = isSpherex
    ? CONFIG.SPHEREX_HIPS_MIRRORS.map((m) => ({ url: m + det, name: `SPHEREx D${det}`, spherex: true }))
    : CONFIG.HIPS_FALLBACK.filter((h) => h.url === value).map((h) => ({ ...h }));
  if (!pedidos.length) pedidos.push({ url: value, name: "fundo escolhido" });
  const reservas = CONFIG.HIPS_FALLBACK.filter((h) => !pedidos.some((p) => p.url === h.url));
  const okR = reservas.map((h) => probeHips(h.url)); // em paralelo com a verificação do pedido
  const i = await firstMirror(pedidos.map((p) => p.url));
  if (i >= 0) return { ...pedidos[i], value };
  const ok2 = await Promise.all(okR);
  const j = ok2.indexOf(true);
  const pedidoNome = pedidos[0].name;
  if (j >= 0) return { ...reservas[j], value: reservas[j].url, fallbackFrom: pedidoNome, wasSpherex: isSpherex };
  return { ...pedidos[0], value, unverified: true };
}

function backgroundText(bg) {
  if (bg.unverified) return `Nenhum fundo respondeu à verificação agora; tentando mesmo assim ${bg.name}. Se o mapa ficar vazio, o serviço de imagens está fora do ar.`;
  if (bg.fallbackFrom) {
    return `${bg.wasSpherex ? "Mapa SPHEREx indisponível no CDS agora" : `${bg.fallbackFrom} indisponível agora`}; ` +
      `mostrando ${bg.name}${bg.why ? ", " + bg.why : ""} (outro telescópio, só para comparação). As imagens da seção Observações continuam sendo do SPHEREx.`;
  }
  return bg.spherex
    ? `Fundo: mapa da própria missão SPHEREx, detector ${bg.name.slice(-2)} (HiPS do CDS, versão QR2). Regiões ainda não observadas aparecem vazias.`
    : `Fundo: ${bg.name}${bg.why ? ", " + bg.why : ""} (outro telescópio, só para comparação).`;
}

async function applyBackground(value) {
  const seq = ++sky.bgSeq;
  setFundoInfo("Verificando se o fundo escolhido está disponível…", "carregando");
  const bg = await resolveBackground(value);
  if (seq !== sky.bgSeq) return bg;
  if (bg.value !== el.ceuFundo.value && [...el.ceuFundo.options].some((o) => o.value === bg.value)) el.ceuFundo.value = bg.value;
  setFundoInfo(backgroundText(bg), bg.fallbackFrom || bg.unverified ? "aviso" : "");
  if (sky.aladin) {
    try { (sky.aladin.setBaseImageLayer ?? sky.aladin.setImageSurvey).call(sky.aladin, bg.url); }
    catch (err) { console.error("Mapa do céu:", err); }
  }
  return bg;
}

const wrapRa = (ra) => ((ra % 360) + 360) % 360;

// Centro do quadro em exibição (propagado pelo movimento próprio quando "Seguir" está ativo).
const skyTarget = () => state.frames[state.index]?.cutoutCenter ?? (state.values ? { ra: state.values.ra, dec: state.values.dec } : null);

function fovPolygon(A, c, fov) {
  const h = fov / 120; // meia largura, em graus
  const k = h / Math.cos((c.dec * Math.PI) / 180);
  return A.polygon([
    [wrapRa(c.ra - k), c.dec - h], [wrapRa(c.ra + k), c.dec - h],
    [wrapRa(c.ra + k), c.dec + h], [wrapRa(c.ra - k), c.dec + h],
  ]);
}

function drawSkyLayers() {
  const al = sky.aladin, A = sky.A, v = state.values;
  if (!al || !v) return;
  try {
    al.removeLayers();
    sky.drawGen++; // descarta catálogos assíncronos de desenhos anteriores
    // Camadas dinâmicas: retângulo do FOV e alvo no quadro atual (atualizadas a cada quadro).
    sky.dyn = A.graphicOverlay({ color: "#ff5c8a", lineWidth: 2 });
    al.addOverlay(sky.dyn);
    sky.alvo = A.catalog({ name: "Alvo no quadro atual", shape: "circle", color: "#ff5c8a", sourceSize: 18, onClick: "showPopup" });
    al.addCatalog(sky.alvo);

    const fov = readFov() ?? v.fov;
    const marca = (name, color, shape, size, list) => {
      if (!list.length) return;
      const cat = A.catalog({ name, shape, color, sourceSize: size, onClick: "showPopup" });
      al.addCatalog(cat);
      cat.addSources(list.map((s) => A.source(s.ra, s.dec, { nome: s.name })));
    };
    marca("Centro da busca", "#ffffff", "cross", 16, [{ ra: v.ra, dec: v.dec, name: "Centro da busca" }]);
    marca("Ponto A", "#ff5c8a", "circle", 14, state.pts.A ? [{ ra: state.pts.A.ra, dec: state.pts.A.dec, name: "Ponto A" }] : []);
    marca("Ponto B", "#7fd1ff", "square", 14, state.pts.B ? [{ ra: state.pts.B.ra, dec: state.pts.B.dec, name: "Ponto B" }] : []);

    const raio = Math.max((fov / 60) * 0.8, 0.02); // graus
    const pedidos = [
      el.ceuGaia.checked && { table: "I/355/gaiadr3", opts: { name: "Gaia DR3", shape: "circle", color: "#ffd98a", sourceSize: 8, onClick: "showTable" } },
      el.ceuWise.checked && { table: "II/328/allwise", opts: { name: "AllWISE", shape: "rhomb", color: "#9be28a", sourceSize: 9, onClick: "showTable" } },
    ].filter(Boolean);
    if (pedidos.length) addVizierCatalogs(pedidos, v, raio, sky.drawGen);
    updateSkyFrame();
    window.Surveys?.drawSkyMark(); // região vista em outra base (removeLayers apagou a marca)
  } catch (err) {
    console.error("Mapa do céu:", err);
    setCeuStatus("O mapa abriu, mas não foi possível desenhar todas as camadas.", "erro");
  }
}

// Só as camadas que mudam com o quadro: retângulo do FOV e marcador do alvo.
function updateSkyFrame() {
  const A = sky.A, c = skyTarget();
  if (!sky.aladin || !sky.dyn || !c) return;
  try {
    const fov = readFov() ?? state.values.fov;
    const f = state.frames[state.index];
    sky.dyn.removeAll();
    sky.dyn.addFootprints([fovPolygon(A, c, fov)]);
    sky.alvo.removeAll();
    sky.alvo.addSources([A.source(c.ra, c.dec, {
      nome: f ? `Centro do quadro de ${fmtDateTime(f.date)} (${f.detectorLabel})` : "Centro da busca",
    })]);
  } catch (err) {
    console.error("Mapa do céu (quadro):", err);
  }
}

/* Catálogos Gaia/AllWISE via VizieR.
 * Não usamos A.catalogFromVizieR: o Aladin Lite 3.8.1 monta a URL em vizier.unistra.fr, domínio que
 * não resolve no DNS (testado em 2026-11-15), então as camadas vinham sempre vazias. Montamos a
 * consulta VOTable e tentamos os espelhos em ordem, guardando o primeiro que responder. */
let vizierHostPromise = null;
function vizierHost() {
  vizierHostPromise ??= (async () => {
    for (const host of CONFIG.VIZIER_HOSTS) {
      try {
        const res = await fetch(`${host}/viz-bin/votable?-source=I/355/gaiadr3&-c=0%200&-c.rd=0.01&-out.max=1`,
          { signal: AbortSignal.timeout(10000) });
        if (res.ok && /<VOTABLE/i.test(await res.text())) return host;
      } catch { /* tenta o próximo espelho */ }
    }
    vizierHostPromise = null; // nenhum respondeu: tenta de novo no próximo desenho
    throw new Error("Nenhum espelho do VizieR respondeu.");
  })();
  return vizierHostPromise;
}

async function addVizierCatalogs(pedidos, v, raio, gen) {
  try {
    const host = await vizierHost();
    if (gen !== sky.drawGen) return; // camadas redesenhadas enquanto esperava
    for (const { table, opts } of pedidos) {
      const q = new URLSearchParams({ "-source": table, "-c": `${v.ra} ${v.dec}`, "-c.rd": raio.toFixed(4), "-out.max": 300 });
      const cat = sky.A.catalogFromURL(`${host}/viz-bin/votable?${q}`, opts, undefined,
        () => setCeuStatus(`Não foi possível carregar o catálogo ${opts.name}.`, "erro"));
      sky.aladin.addCatalog(cat);
    }
  } catch (err) {
    console.error("Mapa do céu:", err);
    if (gen === sky.drawGen) setCeuStatus("Catálogos Gaia/WISE indisponíveis: o serviço VizieR não respondeu. Tente de novo mais tarde.", "erro");
  }
}

function scheduleSky() {
  if (!sky.aladin) return;
  clearTimeout(sky.timer);
  sky.timer = setTimeout(drawSkyLayers, 500); // evita refazer a cada tecla
}

// Limitado a ~4 por segundo (a reprodução troca de quadro a cada 350 ms ou mais).
function scheduleSkyFrame() {
  if (!sky.aladin || sky.frameTimer) return;
  sky.frameTimer = setTimeout(() => { sky.frameTimer = null; updateSkyFrame(); }, 250);
}

function centerSky(c, fov) {
  try {
    sky.aladin.gotoRaDec(c.ra, c.dec);
    sky.aladin.setFoV(Math.max(0.05, (fov / 60) * 4));
  } catch (err) { console.error("Mapa do céu:", err); }
}

function updateSky({ recenter = false } = {}) {
  const v = state.values;
  if (!v) return;
  if (!sky.aladin) {
    if (!sky.opening) setCeuStatus(`Mapa pronto para RA ${v.ra}°, Dec ${v.dec}°. Ele abre sozinho quando esta seção aparece na tela, ou clique em “Carregar mapa interativo”.`);
    return;
  }
  if (recenter) {
    centerSky(v, v.fov);
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
  setMotion(null); // ponto arbitrário do céu: sem movimento próprio
  window.Surveys?.clearName(); // o nome digitado não vale mais para o ponto clicado
  if (!el.fov.value.trim()) el.fov.value = "3";
  const outra = window.Surveys && window.Surveys.selected() !== "spherex";
  setCeuStatus(`Ponto clicado: RA ${ra.toFixed(4)}°, Dec ${dec.toFixed(4)}°. ` +
    (outra ? "Mostrando a região na base escolhida, na seção de busca." : "Buscando observações… O resultado aparece na seção Observações."), "carregando");
  el.form.requestSubmit();
}

el.ceuTudo.addEventListener("click", () => {
  if (!sky.aladin) { openSky(); return; }
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
    let fundo = await resolveSurvey(el.ceuFundo.value);
    let aviso = "";
    if (!fundo) {
      // Nenhum espelho tem o mapa escolhido: abre com DSS2 (luz visível) para o mapa não ficar vazio
      console.error("Mapa do céu: nenhum espelho do CDS tem", el.ceuFundo.value);
      el.ceuFundo.value = "P/DSS2/color";
      fundo = await resolveSurvey("P/DSS2/color");
      aviso = " Os mapas do SPHEREx ficam nos servidores do CDS (Estrasburgo), que estão instáveis (incidente de segurança informado por eles em 09/11/2026). Mostrando DSS2 no lugar; tente de novo mais tarde.";
    }
    el.ceuMapa.hidden = false;
    sky.aladin = sky.A.aladin("#ceu-mapa", {
      survey: fundo, target: v ? `${v.ra} ${v.dec}` : "0 0",
      fov: 360, projection: "AIT", showCooGrid: true, showFullscreenControl: true, // AIT: céu inteiro numa elipse
    });
    sky.aladin.on("click", onSkyClick);
    el.ceuAbrir.textContent = "Recentrar na busca";
    el.ceuAbrir.disabled = false;
    setCeuStatus("Céu inteiro. Clique num ponto para pesquisar aquelas coordenadas." + aviso, aviso ? "erro" : "");
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

el.ceuFundo.addEventListener("change", async () => {
  if (!sky.aladin) return;
  try {
    const fundo = await resolveSurvey(el.ceuFundo.value);
    if (!fundo) { setCeuStatus("Esse mapa não está disponível nos servidores do CDS agora. Tente outro fundo.", "erro"); return; }
    setCeuStatus("Céu inteiro. Clique num ponto para pesquisar aquelas coordenadas.");
    (sky.aladin.setBaseImageLayer ?? sky.aladin.setImageSurvey).call(sky.aladin, fundo);
  } catch (err) { console.error("Mapa do céu:", err); }
});

// Abre sozinho quando a seção entra na tela (uma vez).
if ("IntersectionObserver" in window) {
  const ceuObs = new IntersectionObserver((entries) => {
    if (!entries.some((en) => en.isIntersecting)) return;
    ceuObs.disconnect();
    openSky();
  }, { rootMargin: "150px 0px" });
  ceuObs.observe($("ceu"));
}

el.ceuFundo.addEventListener("change", () => applyBackground(el.ceuFundo.value));
el.ceuGaia.addEventListener("change", scheduleSky);
el.ceuWise.addEventListener("change", scheduleSky);

/* ---------- Comparar duas datas (cortina deslizante ou piscar) ----------
 * Os quadros estão no mesmo referencial (norte para cima, mesmo FOV), então A e B se sobrepõem
 * pixel a pixel. Padrão: primeira e última observação do detector selecionado (ou do quadro atual). */
const cmp = { timer: null, showA: true };
const cmpMode = () => document.querySelector('input[name="cmp-modo"]:checked').value;
const cmpFrame = (sel) => state.frames.find((f) => f.id === sel.value) ?? null;
const reduzMovimento = () => window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

function stopBlink() {
  clearInterval(cmp.timer);
  cmp.timer = null;
  el.cmpPiscar.textContent = "Piscar";
  el.cmpPiscar.setAttribute("aria-pressed", "false");
}

function startBlink() {
  stopBlink();
  el.cmpPiscar.textContent = "Pausar";
  el.cmpPiscar.setAttribute("aria-pressed", "true");
  cmp.timer = setInterval(() => { cmp.showA = !cmp.showA; paintCompare(); }, 500); // A/B a ~1 Hz
}

// Preenche as listas A/B. keep = mantém a escolha anterior quando ainda visível.
function resetCompare({ keep = false } = {}) {
  stopBlink();
  const frames = state.frames;
  if (frames.length < 2) return; // a aba "Comparar" fica desativada (js/cinema.js)
  const prevA = el.cmpA.value, prevB = el.cmpB.value;
  const det = state.detectors.size === 1 ? [...state.detectors][0] : frames[state.index]?.detector ?? null;
  const doDet = frames.filter((f) => f.detector === det);
  const base = doDet.length >= 2 ? doDet : frames;
  const opts = () => frames.map((f) => new Option(`${fmtDateTime(f.date)} · ${f.detectorLabel}`, f.id));
  el.cmpA.replaceChildren(...opts());
  el.cmpB.replaceChildren(...opts());
  const has = (id) => frames.some((f) => f.id === id);
  el.cmpA.value = keep && has(prevA) ? prevA : base[0].id;
  el.cmpB.value = keep && has(prevB) ? prevB : base.at(-1).id;
  renderCompare();
}

// el.cmp é o painel da aba "Comparar": escondido = outra aba ativa (não baixa imagens nem pisca).
function renderCompare() {
  if (el.cmp.hidden || state.frames.length < 2) { stopBlink(); return; }
  const a = cmpFrame(el.cmpA), b = cmpFrame(el.cmpB);
  if (!a || !b) return;
  if (el.cmpImgA.getAttribute("src") !== a.imageUrl) el.cmpImgA.src = a.imageUrl;
  if (el.cmpImgB.getAttribute("src") !== b.imageUrl) el.cmpImgB.src = b.imageUrl;
  el.cmpImgA.alt = `Data A: ${fmtDateTime(a.date)}, detector ${a.detectorLabel}`;
  el.cmpImgB.alt = `Data B: ${fmtDateTime(b.date)}, detector ${b.detectorLabel}`;
  const dias = Math.abs(Date.parse(b.date) - Date.parse(a.date)) / 864e5;
  const avisos = [`Intervalo entre A e B: ${dias < 1 ? (dias * 24).toFixed(1).replace(".", ",") + " h" : Math.round(dias) + " dias"}.`];
  if (a.id === b.id) avisos.push("A e B são o mesmo quadro: escolha datas diferentes.");
  if (a.detector !== b.detector) avisos.push(`Atenção: detectores diferentes (${a.detectorLabel} × ${b.detectorLabel}) veem faixas diferentes do infravermelho; a diferença pode não ser mudança no tempo.`);
  if (isPartial(a) || isPartial(b)) avisos.push("Um dos quadros é parcial: a área hachurada não tem dados.");
  el.cmpAviso.textContent = avisos.join(" ");
  const modo = cmpMode();
  el.cmpStage.dataset.modo = modo;
  el.cmpPiscar.hidden = modo !== "piscar";
  el.cmpDivisor.hidden = modo !== "cortina";
  if (modo === "piscar") {
    if (!cmp.timer && !reduzMovimento() && el.cmpPiscar.dataset.pausado !== "1") startBlink();
  } else stopBlink();
  paintCompare();
}

function paintCompare() {
  const a = cmpFrame(el.cmpA), b = cmpFrame(el.cmpB);
  if (!a || !b) return;
  if (cmpMode() === "piscar") {
    el.cmpStage.style.setProperty("--pos", cmp.showA ? "100%" : "0%");
    el.cmpRotulo.textContent = cmp.showA ? `Mostrando A: ${fmtDateTime(a.date)} · ${a.detectorLabel}` : `Mostrando B: ${fmtDateTime(b.date)} · ${b.detectorLabel}`;
  } else {
    el.cmpStage.style.setProperty("--pos", el.cmpDivisor.value + "%");
    el.cmpRotulo.textContent = `◀ A: ${fmtDateTime(a.date)} · ${a.detectorLabel}   |   B: ${fmtDateTime(b.date)} · ${b.detectorLabel} ▶ — arraste a cortina`;
    el.cmpDivisor.setAttribute("aria-valuetext", `${el.cmpDivisor.value}% da largura mostra a data A`);
  }
}

el.cmpA.addEventListener("change", renderCompare);
el.cmpB.addEventListener("change", renderCompare);
el.cmpDivisor.addEventListener("input", paintCompare);
document.querySelectorAll('input[name="cmp-modo"]').forEach((r) => r.addEventListener("change", () => {
  el.cmpPiscar.dataset.pausado = "";
  cmp.showA = true;
  renderCompare();
}));
el.cmpTrocar.addEventListener("click", () => {
  [el.cmpA.value, el.cmpB.value] = [el.cmpB.value, el.cmpA.value];
  renderCompare();
});
el.cmpPiscar.addEventListener("click", () => {
  if (cmp.timer) { stopBlink(); el.cmpPiscar.dataset.pausado = "1"; }
  else { el.cmpPiscar.dataset.pausado = ""; startBlink(); }
});

/* ---------- URL, compartilhamento e modo incorporado ---------- */
// Movimento próprio na URL: mesmos nomes do backend, mais "alvo" (nome exibido na mensagem).
const MOTION_URL_KEYS = ["pm_ra_cosdec_masyr", "pm_dec_masyr", "ref_epoch_jyear", "alvo", "seguir"];
const motionUrlParams = (m) => (m
  ? { ...motionParams(m), ...(m.name ? { alvo: m.name } : {}), ...(el.seguir.checked ? {} : { seguir: 0 }) }
  : {});

function updateUrl({ ra, dec, fov }, motion = null) {
  const q = new URLSearchParams(location.search);
  q.set("ra", ra); q.set("dec", dec); q.set("fov", fov);
  MOTION_URL_KEYS.forEach((k) => q.delete(k));
  for (const [k, v] of Object.entries(motionUrlParams(motion))) q.set(k, v);
  try { history.replaceState(null, "", "?" + q); } catch { /* ex.: file:// */ }
}

function shareUrl(embed) {
  const { ra, dec, fov } = state.values;
  const u = new URL(location.href);
  u.hash = "";
  u.search = new URLSearchParams(state.demo
    ? { demo: state.demo.target.id, ...(embed ? { embed: 1 } : {}) }
    : { ra, dec, fov, ...motionUrlParams(state.motion), ...(embed ? { embed: 1 } : {}) });
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
  copy(`<iframe src="${shareUrl(true)}" width="100%" height="640" style="border:0" title="SPHEREx Explorer" loading="lazy" allow="fullscreen"></iframe>`,
       "Código copiado."));

renderFovUi(); // estado inicial do seletor de FOV (depois de todas as funções auxiliares existirem)

(function initFromUrl() {
  const q = new URLSearchParams(location.search);
  if (q.get("embed") === "1") document.body.classList.add("embed");
  if (q.has("demo")) { enterDemo(q.get("demo")); return; }
  if (q.has("ra") && q.has("dec")) {
    el.ra.value = q.get("ra");
    el.dec.value = q.get("dec");
    if (q.has("fov")) el.fov.value = q.get("fov");
    // Restaura o movimento próprio só se os três parâmetros vierem válidos; senão, nenhum.
    if (q.get("seguir") === "0") el.seguir.checked = false;
    setMotion(parseMotion(q.get("pm_ra_cosdec_masyr"), q.get("pm_dec_masyr"), q.get("ref_epoch_jyear"), q.get("alvo") ?? ""));
    el.form.requestSubmit();
  }
})();

// Atalhos de teclado na linha do tempo: ←/→ trocam o quadro, espaço reproduz/pausa.
// Ignorados em campos de formulário, na imagem (que usa as setas para mover o ponto) e com modificadores.
document.addEventListener("keydown", (e) => {
  const t = e.target;
  if (el.player.hidden || el.visor.hidden || e.defaultPrevented || e.ctrlKey || e.metaKey || e.altKey) return;
  if (t.isContentEditable || t.matches?.("input, select, textarea") || t.closest?.("#imgwrap, #ceu-mapa")) return;
  if (e.key === "ArrowLeft") { e.preventDefault(); step(-1); }
  else if (e.key === "ArrowRight") { e.preventDefault(); step(1); }
  else if (e.key === " " && !t.matches?.("button, a, summary, [role='button']") &&
           (t === document.body || t.closest?.("#observacoes"))) {
    e.preventDefault();
    state.timer ? stop() : start();
  }
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


/* ---------- Ícone SPHEREx: 1º clique = barra de coordenadas, 2º = + menu lateral (a barra continua aberta), 3º = fecha tudo ---------- */
(function iconeSpherex() {
  const btn = $("spx-btn"), barra = $("barra-coord"), menu = $("menu-lateral"), scrim = $("scrim");
  const bRa = $("barra-ra"), bDec = $("barra-dec"), bFov = $("barra-fov"), msg = $("barra-msg");
  const ROTULOS = ["Abrir a busca por coordenadas", "Abrir o menu lateral", "Fechar a busca e o menu lateral"];
  const ERROS = ["ra-erro", "dec-erro", "fov-erro"];
  let estado = 0; // 0 fechado · 1 barra de coordenadas · 2 barra + menu lateral

  const syncBarra = () => { bRa.value = el.ra.value; bDec.value = el.dec.value; bFov.value = el.fov.value; };
  // O menu lateral e o fundo escurecido começam logo abaixo da barra, que pode mudar de altura (quebra de linha)
  const medeBarra = () =>
    document.documentElement.style.setProperty("--barra-h", barra.hidden ? "0px" : barra.offsetHeight + "px");
  const atualizaMsg = () => {
    const erro = ERROS.map((id) => $(id).textContent.trim()).find(Boolean);
    msg.textContent = erro || el.status.textContent.trim();
    msg.classList.toggle("erro", Boolean(erro) || el.status.classList.contains("erro"));
    medeBarra();
  };

  function ir(novo) {
    const antes = estado;
    estado = novo;
    barra.hidden = estado === 0;
    scrim.hidden = estado !== 2;
    document.body.classList.toggle("barra-aberta", estado >= 1);
    document.body.classList.toggle("menu-aberto", estado === 2);
    btn.setAttribute("aria-expanded", String(estado !== 0));
    btn.setAttribute("aria-label", ROTULOS[estado]);
    btn.title = ROTULOS[estado];
    if (antes === 0 && estado === 1) { syncBarra(); atualizaMsg(); bRa.focus(); }
    medeBarra();
    if (estado === 2) menu.querySelector("a")?.focus();
  }

  btn.addEventListener("click", () => ir((estado + 1) % 3));
  scrim.addEventListener("click", () => ir(1));                       // fecha só o menu; a barra continua
  menu.addEventListener("click", (e) => { if (e.target.closest("a")) ir(1); });
  document.addEventListener("keydown", (e) => {
    if (e.key !== "Escape" || estado === 0) return;
    ir(estado - 1);                                                   // Esc fecha uma camada por vez
    btn.focus();
  });
  if (typeof ResizeObserver !== "undefined") new ResizeObserver(medeBarra).observe(barra);

  // A barra usa o mesmo formulário e a mesma validação da pesquisa principal
  barra.addEventListener("submit", (e) => {
    e.preventDefault();
    el.ra.value = bRa.value; el.dec.value = bDec.value; el.fov.value = bFov.value;
    el.form.requestSubmit();
    if (!ERROS.some((id) => $(id).textContent.trim())) $("observacoes").scrollIntoView();
  });
  // Cliques no mapa do céu, alvos de exemplo etc. também enviam o formulário: mantém a barra em dia
  el.form.addEventListener("submit", () => { if (estado >= 1) syncBarra(); });
  const mo = new MutationObserver(atualizaMsg);
  [...ERROS, "status"].forEach((id) =>
    mo.observe($(id), { childList: true, characterData: true, subtree: true, attributes: true, attributeFilter: ["class"] }));
})();
