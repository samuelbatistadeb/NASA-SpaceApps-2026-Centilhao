"use strict";

/* ============================================================
 * SPHEREx Explorer — frontend
 * Ajuste CONFIG e a função normalizeObservation() conforme
 * docs/architecture/api-contract.md.
 * ============================================================ */
const CONFIG = {
  API_BASE: "http://localhost:8000",
  OBSERVATIONS_PATH: "/api/observations", // ASSUMIDO: GET ?ra=&dec=&fov=
  TIMEOUT_MS: 30000,
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
  slider: $("slider"), galeria: $("galeria-lista"), galeriaVazio: $("galeria-vazio"), tIni: $("t-ini"), tFim: $("t-fim"), meta: $("meta"),
};

const state = { frames: [], index: 0, timer: null, isMock: false, controller: null };

/* ---------- Utilitários ---------- */
const parseNum = (v) => Number(String(v).trim().replace(",", "."));

const fmtDate = (iso) =>
  new Date(iso).toLocaleDateString("pt-BR", { dateStyle: "long", timeZone: "UTC" });

function setStatus(msg, kind = "") {
  el.status.textContent = msg;
  el.status.className = "status " + kind;
}

/* ---------- Validação ---------- */
const RULES = {
  ra:  { min: 0,   max: 360, msg: "Informe um número entre 0 e 360." },
  dec: { min: -90, max: 90,  msg: "Informe um número entre −90 e 90." },
  fov: { min: CONFIG.FOV_MIN, max: CONFIG.FOV_MAX,
         msg: `Informe um número entre ${CONFIG.FOV_MIN} e ${CONFIG.FOV_MAX}.` },
};

function validate() {
  const values = {};
  let firstInvalid = null;
  for (const [name, rule] of Object.entries(RULES)) {
    const input = el[name];
    const n = parseNum(input.value);
    const ok = input.value.trim() !== "" && Number.isFinite(n) && n >= rule.min && n <= rule.max;
    input.setAttribute("aria-invalid", String(!ok));
    $(name + "-erro").textContent = ok ? "" : rule.msg;
    if (!ok && !firstInvalid) firstInvalid = input;
    values[name] = n;
  }
  if (firstInvalid) { firstInvalid.focus(); return null; }
  return values;
}

/* ---------- API ---------- */
// Converte a resposta do backend para o formato interno.
function normalizeObservation(o) {
  const img = o.image_url ?? o.imageUrl ?? o.image ?? "";
  return {
    id: o.product_id ?? o.id ?? "—",
    date: o.obs_date ?? o.date ?? o.epoch ?? null, // ISO 8601
    imageUrl: /^(https?:|data:)/.test(img) ? img : CONFIG.API_BASE + img,
    detector: o.detector ?? "—",
    band: o.band ?? o.wavelength ?? "—",
    product: o.product_type ?? o.product ?? "—",
  };
}

async function fetchObservations({ ra, dec, fov }) {
  state.controller?.abort();
  const controller = (state.controller = new AbortController());
  const timeout = setTimeout(() => controller.abort("timeout"), CONFIG.TIMEOUT_MS);
  const url = new URL(CONFIG.OBSERVATIONS_PATH, CONFIG.API_BASE);
  url.search = new URLSearchParams({ ra, dec, fov }).toString();

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
      detector: "fictício", band: "fictícia", product: "teste de interface",
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
    ["Detector", f.detector],
    ["Banda", f.band],
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

function loadFrames(frames, isMock) {
  stop();
  state.frames = frames;
  state.isMock = isMock;
  el.avisoMock.hidden = !isMock;
  el.slider.max = frames.length - 1;
  el.tIni.textContent = fmtDate(frames[0].date);
  el.tFim.textContent = fmtDate(frames.at(-1).date);
  el.player.hidden = false;
  renderGallery(frames);
  showFrame(0);
  setStatus(`${frames.length} observações em ordem cronológica.`);
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
    const frames = el.mock.checked ? mockObservations() : await fetchObservations(values);
    if (!frames.length) {
      setStatus("Nenhuma observação encontrada para essa região. Tente aumentar o tamanho da área (FOV) ou escolher outro ponto.");
      return;
    }
    loadFrames(frames, el.mock.checked);
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
