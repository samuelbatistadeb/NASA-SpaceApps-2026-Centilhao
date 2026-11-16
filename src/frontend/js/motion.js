"use strict";

/* ============================================================
 * "Décadas": o mesmo pedaço FIXO do céu ao longo de ~75 anos, para ver a estrela se mover.
 * Dados estáticos gerados por data/scripts/19_motion_timeline.py (demo/motion.json e
 * demo/<id>/motion.json): placas DSS, 2MASS e WISE (IRSA Finder Chart) + exposições SPHEREx
 * D1–D6 recortadas de novo (IBE) no mesmo centro e FOV. Nada é medido aqui: a marca é a
 * posição PREVISTA pelo movimento próprio do catálogo, calculada no script.
 *
 * API: window.SpxMotion = { index(), near(ra, dec), load(id), mount(container, data, opts) }.
 * ============================================================ */
(() => {
  const INDEX = "demo/motion.json";
  const NEAR_ARCMIN = 10;
  const DETS = ["D1", "D2", "D3", "D4", "D5", "D6"];
  let indexPromise = null;
  const cache = new Map();

  const index = () => {
    indexPromise ??= fetch(INDEX, { signal: AbortSignal.timeout(10000) })
      .then((r) => (r.ok ? r.json() : null))
      .then((m) => ((m?.targets ?? []).filter((t) => t.frames > 0)))
      .catch(() => []);
    return indexPromise;
  };
  const load = (id) => {
    if (!cache.has(id)) {
      cache.set(id, index().then((ts) => {
        const t = ts.find((x) => x.id === id);
        if (!t) return null;
        return fetch(t.file, { signal: AbortSignal.timeout(15000) }).then((r) => (r.ok ? r.json() : null));
      }).catch(() => null));
    }
    return cache.get(id);
  };
  const rad = (d) => (d * Math.PI) / 180;
  const sep = (ra1, de1, ra2, de2) => {
    const c = Math.sin(rad(de1)) * Math.sin(rad(de2)) + Math.cos(rad(de1)) * Math.cos(rad(de2)) * Math.cos(rad(ra1 - ra2));
    return (Math.acos(Math.min(1, Math.max(-1, c))) * 180 / Math.PI) * 60;
  };
  async function near(ra, dec) {
    if (!Number.isFinite(ra) || !Number.isFinite(dec)) return null;
    const best = (await index()).map((t) => ({ t, d: sep(ra, dec, t.ra, t.dec) })).sort((a, b) => a.d - b.d)[0];
    return best && best.d <= NEAR_ARCMIN ? best.t : null;
  }

  const h = (tag, props = {}, ...kids) => {
    const n = Object.assign(document.createElement(tag), props);
    n.append(...kids.filter((k) => k != null));
    return n;
  };
  const svg = (tag, attrs = {}) => {
    const n = document.createElementNS("http://www.w3.org/2000/svg", tag);
    for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
    return n;
  };
  const fmtData = (iso) => { const [y, m, d] = iso.split("-"); return `${d}/${m}/${y}`; };
  const grupo = (f) => (f.kind === "spherex" ? f.detector : "outros");

  /** Monta o player em `container`. opts.onSpherex: ação do botão "sequência SPHEREx completa". */
  function mount(container, data, opts = {}) {
    container.replaceChildren();
    const frames = data.frames;
    if (!frames?.length) return;
    const anos = Math.round(data.span_years[1] - data.span_years[0]);
    const pm = data.pm_total_arcsec_per_year;
    const temMov = pm >= 0.5; // abaixo disso o deslocamento não aparece nas imagens

    const st = { on: new Set(["outros", ...DETS]), vis: [], i: 0, timer: 0, piscar: 0, trajeto: true };

    // ---------- Cabeçalho ----------
    const head = h("div", { className: "mv-head" },
      h("h3", { className: "mv-titulo", textContent: `${data.name}: ${anos} anos no mesmo pedaço do céu` }),
      h("p", { className: "dica", textContent: temMov
        ? `Todas as imagens mostram o mesmo campo de ${data.fov_arcmin}′ (norte para cima). A estrela se move ~${pm.toFixed(1).replace(".", ",")}″ por ano: ` +
          `${data.track_extent_arcmin.toFixed(1).replace(".", ",")}′ desde a imagem mais antiga, enquanto as estrelas de fundo ficam paradas. ` +
          "O círculo laranja é a posição prevista pelo catálogo em cada data; a linha tracejada é o trajeto previsto."
        : `Todas as imagens mostram o mesmo campo de ${data.fov_arcmin}′. O movimento próprio deste alvo é pequeno ` +
          `(${pm.toFixed(3).replace(".", ",")}″/ano) e não aparece nas imagens: aqui a mudança vem do brilho, não da posição.` }));

    // ---------- Filtros: outros telescópios + D1–D6 ----------
    const conta = (g) => frames.filter((f) => grupo(f) === g).length;
    const chips = h("div", { className: "mv-chips", role: "group", ariaLabel: "Filtrar imagens: outros telescópios e detectores SPHEREx" });
    const todos = h("button", { type: "button", className: "mv-chip", textContent: "Todos" });
    chips.append(todos);
    const botoes = {};
    for (const g of ["outros", ...DETS]) {
      const n = conta(g);
      if (!n) continue;
      const b = h("button", { type: "button", className: `mv-chip ${g === "outros" ? "mv-outros" : "mv-spx"}`, title: g === "outros"
        ? "DSS, 2MASS e WISE: outras missões, para as décadas anteriores" : `SPHEREx, detector ${g}` },
        g === "outros" ? "Outros telescópios" : g, h("small", { textContent: ` ${n}` }));
      b.addEventListener("click", (e) => {
        const somar = e.ctrlKey || e.metaKey || e.shiftKey;
        if (somar) { st.on.has(g) ? st.on.delete(g) : st.on.add(g); if (!st.on.size) st.on.add(g); }
        else st.on = st.on.size === 1 && st.on.has(g) ? new Set(Object.keys(botoes)) : new Set([g]);
        filtrar();
      });
      botoes[g] = b;
      chips.append(b);
    }
    todos.addEventListener("click", () => { st.on = new Set(Object.keys(botoes)); filtrar(); });
    const dicaChips = h("small", { className: "mv-dica-chips", textContent: "Clique para ver só um grupo; Ctrl/⌘/Shift + clique soma." });

    // ---------- Palco ----------
    const imgs = frames.map((f) => h("img", { src: f.file, alt: "", loading: "eager", decoding: "async", className: "mv-img" }));
    const over = svg("svg", { viewBox: "0 0 100 100", class: "mv-over", "aria-hidden": "true", preserveAspectRatio: "none" });
    const trilha = svg("polyline", { class: "mv-trilha", points: data.track.map(([x, y]) => `${x * 100},${y * 100}`).join(" ") });
    const pegadas = svg("g", { class: "mv-pegadas" });
    const alvo = svg("circle", { class: "mv-alvo", r: "3.2" });
    over.append(trilha, pegadas, alvo);
    const ano = h("div", { className: "mv-ano", ariaHidden: "true" });
    const selo = h("div", { className: "mv-selo" });
    const palco = h("div", { className: "mv-palco", tabIndex: 0, role: "img" }, ...imgs, over, ano, selo);

    // ---------- Eixo do tempo (proporcional aos anos) ----------
    const y0 = Math.floor(Math.min(...frames.map((f) => f.jyear)) / 10) * 10;
    const y1 = Math.ceil(data.span_years[1]);
    const pos = (y) => ((y - y0) / (y1 - y0)) * 100;
    const eixo = h("div", { className: "mv-eixo" });
    for (let d = y0; d <= y1; d += 10) eixo.append(h("span", { className: "mv-dec", textContent: String(d), style: `left:${pos(d)}%` }));
    const pontos = frames.map((f, k) => {
      const p = h("button", { type: "button", className: `mv-pt ${f.kind === "spherex" ? "spx" : "out"}`, style: `left:${pos(f.jyear)}%`,
        title: `${f.label} · ${fmtData(f.date)}`, ariaLabel: `${f.label}, ${fmtData(f.date)}` });
      p.addEventListener("click", () => { pausar(); ir(st.vis.indexOf(k)); });
      eixo.append(p);
      return p;
    });
    const cursor = h("div", { className: "mv-cursor" });
    eixo.append(cursor);

    // ---------- Controles ----------
    const prev = h("button", { type: "button", className: "mv-btn", ariaLabel: "Imagem anterior", textContent: "◀" });
    const play = h("button", { type: "button", className: "mv-btn mv-play", ariaPressed: "false", textContent: "▶ Reproduzir" });
    const next = h("button", { type: "button", className: "mv-btn", ariaLabel: "Próxima imagem", textContent: "▶" });
    const piscar = h("button", { type: "button", className: "mv-btn", ariaPressed: "false", textContent: "Piscar 1ª ↔ última" });
    const slider = h("input", { type: "range", min: 0, max: 0, value: 0, className: "mv-slider", ariaLabel: "Imagem na sequência" });
    const chkTraj = h("input", { type: "checkbox", checked: true });
    const traj = h("label", { className: "check vis mv-check" }, chkTraj, " Trajeto previsto");
    const ctrls = h("div", { className: "mv-ctrls" }, prev, play, next, piscar, traj);
    const legenda = h("p", { className: "mv-legenda", ariaLive: "polite" });
    const credito = h("p", { className: "note mv-credito" });
    const pulados = data.skipped?.length
      ? h("details", { className: "mv-pulados" }, h("summary", { textContent: `Imagens não incluídas (${data.skipped.length})` }),
        h("ul", {}, ...data.skipped.map((s) => h("li", { textContent: s }))))
      : null;
    const acoes = h("div", { className: "alt-botoes" });
    if (opts.onSpherex) {
      const b = h("button", { type: "button", className: "primary", textContent: opts.spherexLabel ?? "Ver a sequência SPHEREx completa (mês a mês)" });
      b.addEventListener("click", () => { pausar(); opts.onSpherex(); });
      acoes.append(b);
    }

    container.append(h("div", { className: "mv" }, head, chips, dicaChips, palco, eixo, slider, ctrls, legenda, acoes, credito, pulados));

    // ---------- Lógica ----------
    function filtrar() {
      pausar();
      const atual = st.vis[st.i];
      st.vis = frames.map((f, k) => (st.on.has(grupo(f)) ? k : -1)).filter((k) => k >= 0);
      for (const [g, b] of Object.entries(botoes)) b.setAttribute("aria-pressed", String(st.on.has(g)));
      todos.setAttribute("aria-pressed", String(st.on.size === Object.keys(botoes).length));
      pontos.forEach((p, k) => p.classList.toggle("off", !st.vis.includes(k)));
      slider.max = Math.max(0, st.vis.length - 1);
      const j = st.vis.indexOf(atual);
      ir(j >= 0 ? j : st.vis.length - 1);
    }

    function ir(j) {
      if (!st.vis.length) return;
      st.i = Math.max(0, Math.min(st.vis.length - 1, j));
      const k = st.vis[st.i], f = frames[k];
      imgs.forEach((im, n) => im.classList.toggle("on", n === k));
      alvo.setAttribute("cx", f.target_xy[0] * 100);
      alvo.setAttribute("cy", f.target_xy[1] * 100);
      alvo.classList.toggle("off", !temMov);
      // Pegadas: posições previstas das imagens já vistas (visíveis) até esta.
      pegadas.replaceChildren(...st.vis.slice(0, st.i).map((n) => svg("circle", {
        cx: frames[n].target_xy[0] * 100, cy: frames[n].target_xy[1] * 100, r: "0.9" })));
      trilha.classList.toggle("off", !st.trajeto || !temMov);
      pegadas.classList.toggle("off", !st.trajeto || !temMov);
      ano.textContent = f.date.slice(0, 4);
      selo.replaceChildren(h("strong", { textContent: f.label }), ` · ${f.wavelength}`);
      selo.className = `mv-selo ${f.kind === "spherex" ? "spx" : "out"}`;
      palco.setAttribute("aria-label", `${data.name}: ${f.label}, ${fmtData(f.date)}. Imagem ${st.i + 1} de ${st.vis.length}.`);
      slider.value = st.i;
      cursor.style.left = `${pos(f.jyear)}%`;
      pontos.forEach((p, n) => p.classList.toggle("atual", n === k));
      legenda.textContent = `${st.i + 1} de ${st.vis.length} · ${f.label} (${f.wavelength}) · ${fmtData(f.date)}` +
        (f.kind === "spherex" ? " · SPHEREx, recortado de novo no mesmo campo" : " · outra missão, para comparação");
      credito.textContent = `${f.credit}. ${data.note}`;
    }

    function pausar() {
      clearInterval(st.timer); st.timer = 0;
      clearInterval(st.piscar); st.piscar = 0;
      play.setAttribute("aria-pressed", "false"); play.textContent = "▶ Reproduzir";
      piscar.setAttribute("aria-pressed", "false");
    }
    function reproduzir() {
      if (st.timer) { pausar(); return; }
      pausar();
      if (st.i >= st.vis.length - 1) ir(0);
      play.setAttribute("aria-pressed", "true"); play.textContent = "⏸ Pausar";
      st.timer = setInterval(() => { if (st.i >= st.vis.length - 1) pausar(); else ir(st.i + 1); }, 900);
    }
    function alternarPiscar() {
      if (st.piscar) { pausar(); return; }
      pausar();
      piscar.setAttribute("aria-pressed", "true");
      let lado = 0;
      ir(0);
      st.piscar = setInterval(() => { lado ^= 1; ir(lado ? st.vis.length - 1 : 0); }, 700);
    }

    prev.addEventListener("click", () => { pausar(); ir(st.i - 1); });
    next.addEventListener("click", () => { pausar(); ir(st.i + 1); });
    play.addEventListener("click", reproduzir);
    piscar.addEventListener("click", alternarPiscar);
    slider.addEventListener("input", () => { pausar(); ir(Number(slider.value)); });
    chkTraj.addEventListener("change", () => { st.trajeto = chkTraj.checked; ir(st.i); });
    container.addEventListener("keydown", (e) => {
      if (e.target.matches?.("input[type=range], select, textarea, input[type=text]")) return;
      if (e.key === "ArrowLeft" || e.key === "ArrowRight") {
        e.preventDefault(); e.stopPropagation(); pausar(); ir(st.i + (e.key === "ArrowRight" ? 1 : -1));
      } else if (e.key === " " && !e.target.matches?.("button")) {
        e.preventDefault(); e.stopPropagation(); reproduzir();
      }
    });

    filtrar();
    ir(0);
    return { pausar };
  }

  window.SpxMotion = { index, near, load, mount };

  /* ---------- Aba "Décadas" no visor de Observações ----------
   * Aparece só quando a região em exibição é um dos alvos com linha do tempo salva. */
  const aba = document.getElementById("aba-decadas");
  const painel = document.getElementById("painel-decadas");
  if (!aba || !painel) return;
  let atualId = null, montado = null, player = null;

  async function checar() {
    const v = typeof state !== "undefined" ? state.values : null;
    const t = v ? await near(Number(v.ra), Number(v.dec)) : null;
    if ((t?.id ?? null) === atualId) return;
    atualId = t?.id ?? null;
    player?.pausar(); player = null; montado = null;
    painel.replaceChildren();
    aba.hidden = !t;
    aba.disabled = !t; // fora da navegação por setas entre as abas
    if (!t && aba.getAttribute("aria-selected") === "true") window.visorAba?.("seq");
  }
  async function montar() {
    if (!atualId || montado === atualId) return;
    montado = atualId;
    painel.replaceChildren(h("p", { className: "status carregando", textContent: "Carregando as imagens de décadas…" }));
    const data = await load(atualId);
    if (montado !== atualId) return;
    if (!data) { painel.replaceChildren(h("p", { className: "status aviso", textContent: "As imagens de décadas não puderam ser carregadas." })); return; }
    player = mount(painel, data, { onSpherex: () => window.visorAba?.("seq"), spherexLabel: "Voltar à sequência SPHEREx (mês a mês)" });
  }
  document.addEventListener("visor:quadros", () => { checar(); });
  aba.addEventListener("click", montar);
  aba.addEventListener("focus", montar);
  // Saiu da aba: pausa a animação (o painel fica escondido).
  new MutationObserver(() => { if (painel.hidden) player?.pausar(); })
    .observe(painel, { attributes: true, attributeFilter: ["hidden"] });
})();
