/* SPHEREx Explorer — visor das observações ("modo cinema").
 *
 * Complementa js/app.js (carregado antes, também com defer) sem duplicar a lógica do player:
 * usa as funções e o estado globais de app.js (state, el, showFrame, stop, renderCompare,
 * fmtDate, fmtDateTime, isPartial, fmtPct, DET_COLORS) e ouve dois eventos que app.js emite:
 *   - "visor:quadros" (applyFilters): nova seleção de quadros → marcas da linha do tempo, abas;
 *   - "visor:quadro"  (showFrame): quadro exibido → data/detector sobre a imagem, bolha, tira.
 *
 * Recursos: abas Sequência | Comparar | Combinar; modo cinema (Fullscreen API, com recurso a
 * uma camada fixa de tela inteira quando a API não existe ou é recusada) com barra de controles
 * que some sem movimento do mouse; zoom (Ctrl + roda, roda no cinema, pinça) e arrastar; marcas
 * dos meses sobre a linha do tempo; tira de miniaturas que só reaproveita imagens já baixadas.
 */
"use strict";

(() => {
  const $c = (id) => document.getElementById(id);
  const v = {
    visor: $c("visor"), palco: $c("cine-palco"), vista: $c("cine-vista"), wrap: $c("imgwrap"), img: $c("imagem"),
    data: $c("cine-data"), det: $c("cine-det"), cont: $c("cine-cont"), parcial: $c("cine-parcial"),
    barra: $c("cine-barra"), trilho: $c("cine-trilho"), bolha: $c("cine-bolha"), marcas: $c("cine-marcas"),
    slider: $c("slider"), tira: $c("cine-tira"), btn: $c("cine-btn"), sair: $c("cine-sair"),
    zoomMais: $c("zoom-mais"), zoomMenos: $c("zoom-menos"), ajustar: $c("zoom-ajustar"),
  };
  if (!v.visor || !v.palco || typeof showFrame !== "function") return; // página sem o visor

  /* ---------- Abas: Sequência | Comparar | Combinar ---------- */
  const abas = [...v.visor.querySelectorAll('.cine-abas [role="tab"]')];
  const PAINEL = { seq: "painel-seq", comparar: "comparar", combinar: "combinar", decadas: "painel-decadas" };

  function visorAba(nome, { foco = false } = {}) {
    const aba = abas.find((a) => a.getAttribute("aria-controls") === PAINEL[nome]);
    if (!aba || aba.disabled) return;
    if (nome !== "seq") { sairCinema(); stop(); } // a sequência não roda escondida
    for (const a of abas) {
      const on = a === aba;
      a.setAttribute("aria-selected", String(on));
      a.tabIndex = on ? 0 : -1;
      $c(a.getAttribute("aria-controls")).hidden = !on;
    }
    if (foco) aba.focus();
    renderCompare(); // carrega as imagens A/B ao abrir "Comparar"; para o piscar ao sair
  }
  window.visorAba = visorAba;
  const abaAtual = () => Object.keys(PAINEL).find((k) => !$c(PAINEL[k]).hidden) ?? "seq";

  abas.forEach((a) => a.addEventListener("click", () =>
    visorAba(Object.keys(PAINEL).find((k) => PAINEL[k] === a.getAttribute("aria-controls")))));
  v.visor.querySelector(".cine-abas").addEventListener("keydown", (e) => {
    const ativas = abas.filter((a) => !a.disabled);
    const i = ativas.indexOf(document.activeElement);
    if (i < 0) return;
    const j = { ArrowRight: i + 1, ArrowLeft: i - 1, Home: 0, End: ativas.length - 1 }[e.key];
    if (j === undefined) return;
    e.preventDefault(); // impede que as setas também troquem o quadro (atalho global de app.js)
    const alvo = ativas[(j + ativas.length) % ativas.length];
    visorAba(Object.keys(PAINEL).find((k) => PAINEL[k] === alvo.getAttribute("aria-controls")), { foco: true });
  });

  /* ---------- Linha do tempo: marcas dos meses, preenchimento e bolha com a data ---------- */
  const fmtMes = (d) => d.toLocaleDateString("pt-BR", { month: "short", year: "2-digit", timeZone: "UTC" }).replace(" de ", "/").replace(".", "");
  const fmtCurta = (iso) => new Date(iso).toLocaleDateString("pt-BR", { day: "2-digit", month: "short", year: "numeric", timeZone: "UTC" }).replace(/ de /g, " ").replace(".", "");
  const frac = (i, n) => (n > 1 ? i / (n - 1) : 0);

  function desenharMarcas(frames) {
    const n = frames.length;
    v.marcas.replaceChildren();
    if (n < 2) return;
    const frag = document.createDocumentFragment();
    // Poucos quadros: um ponto por quadro (mostra onde caem as observações).
    if (n <= 80) frames.forEach((_, i) => {
      const d = document.createElement("i");
      d.className = "q";
      d.style.setProperty("--x", frac(i, n));
      frag.append(d);
    });
    // Início de cada mês (UTC). A linha do tempo anda por quadro, não por data: marcas próximas
    // indicam meses com muitas observações; marcas distantes, meses com poucas.
    let ultimo = null, ultimoRotulo = -1;
    frames.forEach((f, i) => {
      const d = new Date(f.date);
      const k = d.getUTCFullYear() * 12 + d.getUTCMonth();
      if (k === ultimo) return;
      ultimo = k;
      const x = frac(i, n);
      const m = document.createElement("span");
      m.className = "m";
      m.style.setProperty("--x", x);
      if (x - ultimoRotulo >= 0.13 && x <= 0.92) { // rótulos espaçados para não se sobreporem
        const b = document.createElement("b");
        b.textContent = fmtMes(d);
        m.append(b);
        ultimoRotulo = x;
      }
      frag.append(m);
    });
    v.marcas.append(frag);
  }

  /* ---------- Tira de miniaturas (só imagens já baixadas: não gera recortes novos no IRSA) ---------- */
  const baixadas = new Set();
  document.addEventListener("load", (e) => {
    const t = e.target;
    if (t.tagName !== "IMG") return;
    const src = t.getAttribute("src");
    if (!src || baixadas.has(src)) return;
    baixadas.add(src);
    if (v.tira.querySelector(`[data-src="${CSS.escape(src)}"]`)) agendarTira();
  }, true);

  // Quadros de cada lado do atual: menos em telas estreitas.
  const telaMedia = window.matchMedia("(max-width: 900px)"), telaPequena = window.matchMedia("(max-width: 760px)");
  const vizinhos = () => (telaPequena.matches ? 2 : telaMedia.matches ? 3 : 5);
  [telaMedia, telaPequena].forEach((m) => m.addEventListener?.("change", () => desenharTira()));
  let tiraPendente = false;
  const agendarTira = () => {
    if (tiraPendente) return;
    tiraPendente = true;
    requestAnimationFrame(() => { tiraPendente = false; desenharTira(); });
  };

  function desenharTira() {
    const frames = state.frames, n = frames.length;
    if (n < 2) { v.tira.replaceChildren(); v.tira.hidden = true; return; }
    v.tira.hidden = false;
    const k0 = vizinhos(), largura = 2 * k0 + 1;
    const ini = Math.max(0, Math.min(state.index - k0, n - largura));
    const fim = Math.min(n, ini + largura);
    v.tira.style.setProperty("--n", largura);
    const itens = [];
    for (let k = ini; k < fim; k++) {
      const f = frames[k];
      const li = document.createElement("li");
      const b = document.createElement("button");
      b.type = "button";
      b.dataset.i = k;
      if (k === state.index) b.setAttribute("aria-current", "true");
      if (isPartial(f)) b.classList.add("parcial");
      b.setAttribute("aria-label", `Ver observação de ${fmtDateTime(f.date)}, detector ${f.detectorLabel}` +
        (isPartial(f) ? `, quadro parcial (${fmtPct(f.coverage)} dentro do detector)` : ""));
      b.style.setProperty("--det", DET_COLORS[(f.detector ?? 0) - 1] ?? "#6de3e8");
      const pronta = f.imageUrl && (f.imageUrl.startsWith("data:") || baixadas.has(f.imageUrl));
      const fig = document.createElement(pronta ? "img" : "span");
      fig.className = "t-img";
      if (pronta) { fig.src = f.imageUrl; fig.alt = ""; } else if (f.imageUrl) fig.dataset.src = f.imageUrl;
      const rot = document.createElement("small");
      rot.textContent = new Date(f.date).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", year: "2-digit", timeZone: "UTC" });
      b.title = `${fmtDateTime(f.date)} · ${f.detectorLabel}`;
      b.append(fig, rot);
      li.append(b);
      itens.push(li);
    }
    const tinhaFoco = v.tira.contains(document.activeElement) ? Number(document.activeElement.dataset.i) : null;
    v.tira.replaceChildren(...itens);
    if (tinhaFoco !== null) v.tira.querySelector(`[data-i="${tinhaFoco}"]`)?.focus({ preventScroll: true });
  }
  v.tira.addEventListener("click", (e) => {
    const b = e.target.closest("button[data-i]");
    if (!b) return;
    stop();
    showFrame(Number(b.dataset.i));
  });

  /* ---------- Quadro exibido: informações sobre a imagem, bolha, tira ---------- */
  function aoQuadro(i, f) {
    const n = state.frames.length;
    v.data.textContent = fmtDateTime(f.date);
    v.det.textContent = f.detector ? `Detector ${f.detectorLabel}` : f.detectorLabel || "—";
    v.det.style.setProperty("--det", DET_COLORS[(f.detector ?? 0) - 1] ?? "#6de3e8");
    v.cont.textContent = `${i + 1} de ${n}`;
    v.parcial.hidden = !isPartial(f);
    if (isPartial(f)) v.parcial.textContent = `parcial · ${fmtPct(f.coverage)}`;
    const x = frac(i, n);
    v.trilho.style.setProperty("--x", x);
    v.bolha.textContent = fmtCurta(f.date);
    desenharTira();
  }
  document.addEventListener("visor:quadro", (e) => aoQuadro(e.detail.index, e.detail.frame));

  function aoQuadros(frames) {
    desenharMarcas(frames);
    const cmpAba = abas.find((a) => a.id === "aba-comparar");
    cmpAba.disabled = frames.length < 2;
    cmpAba.title = cmpAba.disabled ? "É preciso ter pelo menos duas observações visíveis para comparar." : "";
    if (cmpAba.disabled && abaAtual() === "comparar") visorAba("seq");
    if (frames.length < 2) desenharTira();
    if (!frames.length) sairCinema();
  }
  document.addEventListener("visor:quadros", (e) => aoQuadros(e.detail.frames));

  /* ---------- Nitidez: pixels nítidos (sem borrar) quando a imagem é ampliada ---------- */
  const z = { s: 1, x: 0, y: 0 };
  function atualizarNitidez() {
    const w = v.wrap.offsetWidth * z.s * (window.devicePixelRatio || 1);
    const nat = v.img.naturalWidth || 0;
    v.img.classList.toggle("ampliada", nat > 0 && w > nat * 1.05);
  }
  v.img.addEventListener("load", atualizarNitidez);
  if ("ResizeObserver" in window) new ResizeObserver(atualizarNitidez).observe(v.wrap);

  /* ---------- Zoom e arrastar ----------
   * O transform fica no próprio #imgwrap: getBoundingClientRect() já devolve o retângulo
   * transformado, então o clique para marcar pontos do espectro (app.js) continua exato.
   * Sem zoom por duplo clique: cada clique na imagem marca um ponto e pede um espectro. */
  const Z_MAX = 12;
  function aplicarZoom() {
    const w = v.wrap.offsetWidth, h = v.wrap.offsetHeight;
    if (z.s <= 1.001) { z.s = 1; z.x = 0; z.y = 0; }
    z.x = Math.min(0, Math.max(w - z.s * w, z.x)); // a imagem sempre cobre o próprio quadro
    z.y = Math.min(0, Math.max(h - z.s * h, z.y));
    v.wrap.style.transform = z.s === 1 ? "" : `translate(${z.x}px, ${z.y}px) scale(${z.s})`;
    v.vista.classList.toggle("com-zoom", z.s > 1);
    v.ajustar.hidden = z.s === 1;
    v.ajustar.textContent = `Ajustar (${z.s.toFixed(1).replace(".", ",")}×)`;
    v.zoomMenos.disabled = z.s === 1;
    v.zoomMais.disabled = z.s >= Z_MAX;
    atualizarNitidez();
  }
  // Zoom mantendo fixo o ponto (cx, cy) da tela.
  function zoomEm(fator, cx, cy) {
    const r = v.wrap.getBoundingClientRect();
    if (cx === undefined) { cx = r.left + r.width / 2; cy = r.top + r.height / 2; }
    const baseX = r.left - z.x, baseY = r.top - z.y; // origem do #imgwrap sem transform
    const px = (cx - baseX - z.x) / z.s, py = (cy - baseY - z.y) / z.s;
    const s = Math.min(Z_MAX, Math.max(1, z.s * fator));
    z.x = cx - baseX - s * px;
    z.y = cy - baseY - s * py;
    z.s = s;
    aplicarZoom();
  }
  const ajustar = () => { z.s = 1; aplicarZoom(); };
  v.zoomMais.addEventListener("click", () => zoomEm(1.5));
  v.zoomMenos.addEventListener("click", () => zoomEm(1 / 1.5));
  v.ajustar.addEventListener("click", ajustar);
  window.addEventListener("resize", () => aplicarZoom());

  // Roda do mouse: no cinema, sempre; na página, só com Ctrl (a roda sozinha rola a página).
  v.vista.addEventListener("wheel", (e) => {
    if (!cine.on && !e.ctrlKey) return;
    e.preventDefault();
    zoomEm(Math.exp(-e.deltaY * 0.0018), e.clientX, e.clientY);
  }, { passive: false });

  const toques = new Map();
  let arrasto = null, arrastou = false;
  v.vista.addEventListener("pointerdown", (e) => {
    if (e.target.closest("button, .img-falha")) return;
    toques.set(e.pointerId, { x: e.clientX, y: e.clientY });
    arrastou = false;
    if (toques.size === 2) {
      const [a, b] = [...toques.values()];
      arrasto = { pinca: Math.hypot(a.x - b.x, a.y - b.y) };
    } else arrasto = { x0: e.clientX, y0: e.clientY, zx: z.x, zy: z.y };
  });
  v.vista.addEventListener("pointermove", (e) => {
    if (!toques.has(e.pointerId) || !arrasto) return;
    toques.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (toques.size === 2 && arrasto.pinca) {
      const [a, b] = [...toques.values()];
      const d = Math.hypot(a.x - b.x, a.y - b.y);
      zoomEm(d / arrasto.pinca, (a.x + b.x) / 2, (a.y + b.y) / 2);
      arrasto.pinca = d;
      arrastou = true;
      return;
    }
    if (z.s === 1 || arrasto.x0 === undefined) return;
    const dx = e.clientX - arrasto.x0, dy = e.clientY - arrasto.y0;
    if (!arrastou && Math.hypot(dx, dy) < 5) return; // abaixo disso é um clique (marca ponto)
    if (!arrastou) { arrastou = true; v.vista.setPointerCapture?.(e.pointerId); v.vista.classList.add("arrastando"); }
    z.x = arrasto.zx + dx;
    z.y = arrasto.zy + dy;
    aplicarZoom();
  });
  const soltar = (e) => {
    toques.delete(e.pointerId);
    if (!toques.size) { arrasto = null; v.vista.classList.remove("arrastando"); }
  };
  v.vista.addEventListener("pointerup", soltar);
  v.vista.addEventListener("pointercancel", soltar);
  // Depois de arrastar, o "click" não deve marcar um ponto do espectro.
  v.vista.addEventListener("click", (e) => {
    if (arrastou) { e.stopPropagation(); e.preventDefault(); arrastou = false; }
  }, true);

  /* ---------- Modo cinema ---------- */
  const cine = { on: false, fixo: false, fs: false, timer: null };
  const OCIOSO_MS = 2600;
  const fsEl = () => document.fullscreenElement ?? document.webkitFullscreenElement ?? null;

  function rotuloBotao() {
    v.btn.setAttribute("aria-pressed", String(cine.on));
    v.btn.querySelector("span").textContent = cine.on ? "Sair do cinema" : "Modo cinema";
    v.btn.title = cine.on ? "Sair do modo cinema (Esc)" : "Modo cinema (F)";
  }

  function entrarCinema() {
    if (cine.on || v.visor.hidden) return;
    visorAba("seq");
    cine.on = true;
    v.palco.classList.add("cinema");
    v.sair.hidden = false;
    rotuloBotao();
    const req = v.palco.requestFullscreen ?? v.palco.webkitRequestFullscreen;
    const usarFixo = () => {
      if (!cine.on) return;
      cine.fixo = true;
      v.palco.classList.add("cine-fixo");
      document.documentElement.classList.add("cine-travado");
    };
    if (req && (document.fullscreenEnabled ?? document.webkitFullscreenEnabled)) {
      try {
        const p = req.call(v.palco, { navigationUI: "hide" });
        if (p?.catch) p.catch(usarFixo);
      } catch { usarFixo(); }
      // Alguns navegadores embutidos aceitam o pedido mas nunca entram em tela cheia.
      setTimeout(() => { if (fsEl() !== v.palco) usarFixo(); }, 600);
    } else usarFixo();
    v.palco.focus({ preventScroll: true }); // Espaço/setas agem no visor, não no botão
    acordar();
    requestAnimationFrame(() => aplicarZoom());
  }

  function sairCinema() {
    if (!cine.on) return;
    cine.on = false;
    clearTimeout(cine.timer);
    if (fsEl() === v.palco) (document.exitFullscreen ?? document.webkitExitFullscreen)?.call(document)?.catch?.(() => {});
    v.palco.classList.remove("cinema", "cine-fixo", "ocioso");
    document.documentElement.classList.remove("cine-travado");
    cine.fixo = false;
    v.sair.hidden = true;
    rotuloBotao();
    requestAnimationFrame(() => aplicarZoom());
    if (v.palco.contains(document.activeElement) || document.activeElement === document.body) v.btn.focus({ preventScroll: true });
  }

  const alternarCinema = () => (cine.on ? sairCinema() : entrarCinema());
  v.btn.addEventListener("click", alternarCinema);
  v.sair.addEventListener("click", sairCinema);
  // Saiu da tela cheia nativa (Esc do navegador, F11…): sai também do cinema.
  const aoMudarTelaCheia = () => {
    if (fsEl() === v.palco) { cine.fs = true; return; }
    if (cine.on && cine.fs) sairCinema();
    cine.fs = false;
  };
  document.addEventListener("fullscreenchange", aoMudarTelaCheia);
  document.addEventListener("webkitfullscreenchange", aoMudarTelaCheia);

  // Controles somem após alguns segundos sem movimento; voltam ao mexer o mouse, tocar ou teclar.
  function acordar() {
    if (!cine.on) return;
    v.palco.classList.remove("ocioso");
    clearTimeout(cine.timer);
    cine.timer = setTimeout(dormir, OCIOSO_MS);
  }
  function dormir() {
    if (!cine.on) return;
    const emUso = [v.barra, v.tira, v.sair, v.visor.querySelector(".cine-zoom")].some((x) => x?.matches(":hover")) ||
      v.palco.querySelector(".cine-barra :focus-visible, .cine-tira :focus-visible, .cine-zoom :focus-visible, .cine-sair:focus-visible") ||
      v.barra.querySelector("select:focus");
    if (emUso) { acordar(); return; }
    v.palco.classList.add("ocioso");
  }
  ["pointermove", "pointerdown", "keydown", "wheel"].forEach((t) =>
    v.palco.addEventListener(t, acordar, { passive: true }));

  // Atalhos: F ou C liga/desliga o cinema; Esc sai (a tela cheia nativa também sai sozinha com Esc).
  const visorNaTela = () => {
    const r = v.visor.getBoundingClientRect();
    return r.bottom > 0 && r.top < innerHeight;
  };
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && cine.on) { sairCinema(); return; }
    if (e.defaultPrevented || e.ctrlKey || e.metaKey || e.altKey || e.repeat) return;
    if (!["f", "F", "c", "C"].includes(e.key)) return;
    const t = e.target;
    if (t.isContentEditable || t.matches?.("input, select, textarea")) return;
    if (el.player.hidden || v.visor.hidden || (!cine.on && !visorNaTela())) return;
    e.preventDefault();
    alternarCinema();
  });

  rotuloBotao();
  aplicarZoom();
  // app.js pode ter carregado os quadros (ex.: exemplo salvo em cache) antes deste script rodar.
  if (state.frames.length) {
    aoQuadros(state.frames);
    const f = state.frames[state.index];
    if (f) aoQuadro(state.index, f);
  }
})();
