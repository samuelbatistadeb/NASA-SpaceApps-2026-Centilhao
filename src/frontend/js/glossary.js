/* SPHEREx Explorer — ajuda contextual (glossário).
 *
 * Insere um ícone "?" ao lado de termos científicos. Ao passar o mouse, focar pelo teclado
 * ou tocar, abre um balão com o título, uma explicação curta e o link "Saiba mais" para termos.html.
 *
 * Duas formas de marcar um termo:
 *   1. HTML estático: <h3 data-term="chave">…</h3> (várias chaves separadas por espaço geram
 *      um ícone para cada uma).
 *   2. Automática, para o conteúdo que o app.js gera: RULES abaixo associam textos de
 *      contêineres conhecidos a chaves do glossário. Um MutationObserver reaplica as regras
 *      quando o app reescreve esses contêineres. A inserção é idempotente.
 *
 * Sem dependências. Dados em js/glossary-data.js (window.SPHEREX_GLOSSARY).
 */
(function () {
  "use strict";

  const DATA = window.SPHEREX_GLOSSARY || {};
  const TERMS_PAGE = "termos.html";
  const ICON_CLASS = "gl-icon";
  const POP_ID = "gl-pop";

  /* ---------- Regras para o conteúdo dinâmico ---------- */
  const norm = (s) => String(s || "").replace(/\s+/g, " ").trim();

  const exact = (map) => (text) => map[text] || null;
  const DET_PREFIX = (text) => {
    const m = /^D([1-6]) \(/.exec(text) || /^Detector ([1-6])$/.exec(text);
    return m ? "detector-d" + m[1] : null;
  };

  const RULES = [
    {
      sel: "#meta > dt",
      key: exact({
        "Data da observação": "epoca",
        "Identificador do produto": "produto",
        "Detector": "detector",
        "Faixa espectral do detector": "lvf",
        "Tempo de exposição": "exposicao",
        "Centro do recorte": "recorte",
        "Cobertura do quadro": "cobertura",
        "Contaminação no alvo": "flags",
        "Coleção": "colecao",
        "Fonte dos dados": "irsa",
      }),
    },
    // Botões de detector: o ícone vai DEPOIS do botão (não pode haver botão dentro de botão).
    // O texto do botão junta "Detector N" com a faixa em µm; usa só o nó de texto do nome.
    {
      sel: "#detectores > button.det",
      key: (t, el) => {
        const tn = [...el.childNodes].find((n) => n.nodeType === 3 && /Detector\s*[1-6]/.test(n.textContent));
        return tn ? DET_PREFIX(norm(tn.textContent)) : null;
      },
    },
    {
      sel: "#mapa-grafico .legenda > li, #esp-grafico .legenda > li",
      key: (t) => DET_PREFIX(t) || (t.startsWith("contaminado") ? "flags" : null),
    },
    {
      sel: "#esp-tabela th",
      key: exact({
        "λ (µm)": "comprimento-onda", "Largura (µm)": "banda", "Detector": "detector",
        "Fluxo": "mjy-sr", "Erro": "erro", "Data (UTC)": "utc", "Contaminação": "flags",
      }),
    },
    { sel: "#esp-tabela > caption", key: (t) => (t.startsWith("Fluxo por comprimento de onda") ? "mjy-sr" : null) },
    { sel: "#legenda", key: (t) => (t.includes("Cobertura do quadro") ? "cobertura" : null) },
    { sel: "#comb-legenda", key: (t) => (t.startsWith("Média de") ? "media-epocas" : t.startsWith("Diferença") ? "diferenca" : null) },
    { sel: "#esp-nota", key: (t) => (t.includes("filtro linear variável") ? "lvf" : null) },
  ];

  /* ---------- Inserção dos ícones ---------- */
  let uid = 0;

  // Texto do elemento sem os ícones já inseridos.
  function ownText(el) {
    let s = "";
    for (const n of el.childNodes) {
      if (n.nodeType === 1 && n.classList.contains(ICON_CLASS)) continue;
      s += n.textContent;
    }
    return norm(s);
  }

  function makeIcon(key) {
    const t = DATA[key];
    const b = document.createElement("button");
    b.type = "button";
    b.className = ICON_CLASS;
    b.dataset.glKey = key;
    b.id = "gl-i" + ++uid;
    b.setAttribute("aria-label", "O que é " + t.titulo + "?");
    b.setAttribute("aria-expanded", "false");
    b.setAttribute("aria-controls", POP_ID);
    b.textContent = "?";
    return b;
  }

  // Um botão não pode ficar dentro de outro elemento interativo: nesse caso o ícone vai depois dele.
  const INTERACTIVE = "button, a[href], summary, select, option, textarea";

  function placeIcons(el, keys) {
    keys = keys.filter((k) => DATA[k]);
    const host = el.matches(INTERACTIVE) ? el : el.closest(INTERACTIVE);
    if (host) {
      // Ícones ficam como irmãos seguintes do host, marcados com data-gl-for.
      const forId = host.id || (host.dataset.glHost ||= "h" + ++uid);
      const have = [];
      let n = host.nextElementSibling;
      while (n && n.classList.contains(ICON_CLASS) && n.dataset.glFor === forId) { have.push(n); n = n.nextElementSibling; }
      if (sameKeys(have, keys)) return;
      have.forEach((x) => x.remove());
      let ref = host;
      for (const k of keys) {
        const ic = makeIcon(k);
        ic.dataset.glFor = forId;
        ref.after(ic);
        ref = ic;
      }
      return;
    }
    const have = [...el.children].filter((c) => c.classList.contains(ICON_CLASS));
    if (sameKeys(have, keys)) return;
    have.forEach((x) => x.remove());
    for (const k of keys) el.append(makeIcon(k));
  }

  const sameKeys = (icons, keys) =>
    icons.length === keys.length && icons.every((ic, i) => ic.dataset.glKey === keys[i]);

  function scan() {
    for (const el of document.querySelectorAll("[data-term]")) {
      placeIcons(el, el.dataset.term.split(/\s+/).filter(Boolean));
    }
    for (const r of RULES) {
      for (const el of document.querySelectorAll(r.sel)) {
        const k = r.key(ownText(el), el);
        placeIcons(el, k ? [k] : []);
      }
    }
    if (current && !current.isConnected) close(false);
  }

  /* ---------- Balão (um só, compartilhado) ---------- */
  let pop, popTitle, popText, popMore, popLink;
  let current = null;   // ícone ativo
  let pinned = false;   // aberto por clique/toque/Enter: não fecha ao tirar o mouse
  let hideTimer = 0;

  function buildPop() {
    pop = document.createElement("div");
    pop.id = POP_ID;
    pop.className = "gl-pop";
    pop.setAttribute("role", "dialog");
    pop.setAttribute("aria-modal", "false");
    pop.setAttribute("aria-labelledby", "gl-pop-titulo");
    pop.hidden = true;
    popTitle = document.createElement("strong");
    popTitle.id = "gl-pop-titulo";
    popTitle.className = "gl-pop-titulo";
    popText = document.createElement("p");
    popText.id = "gl-pop-curto";
    popText.className = "gl-pop-curto";
    popMore = document.createElement("p");
    popMore.className = "gl-pop-detalhe";
    popLink = document.createElement("a");
    popLink.className = "gl-pop-link";
    popLink.target = "_blank";
    popLink.rel = "noopener";
    pop.append(popTitle, popText, popMore, popLink);
    document.body.append(pop);

    pop.addEventListener("pointerenter", () => clearTimeout(hideTimer));
    pop.addEventListener("pointerleave", (e) => { if (e.pointerType === "mouse" && !pinned) scheduleHide(); });
    popLink.addEventListener("keydown", (e) => {
      if (e.key !== "Tab" || !current) return;
      e.preventDefault();
      const ic = current;
      if (e.shiftKey) { ic.focus(); return; }
      close(false);
      focusAfter(ic);
    });
  }

  function open(icon, pin) {
    const t = DATA[icon.dataset.glKey];
    if (!t) return;
    clearTimeout(hideTimer);
    if (current && current !== icon) close(false);
    current = icon;
    pinned = pinned || !!pin;
    popTitle.textContent = t.titulo;
    popText.textContent = t.curto;
    popMore.textContent = t.detalhe || "";
    popMore.hidden = !t.detalhe;
    popLink.href = TERMS_PAGE + (t.ancora ? "#" + t.ancora : "");
    popLink.textContent = "Saiba mais no guia de termos";
    popLink.setAttribute("aria-label", "Saiba mais sobre " + t.titulo + " no guia de termos (abre em nova aba)");
    icon.setAttribute("aria-expanded", "true");
    icon.setAttribute("aria-describedby", "gl-pop-curto");
    pop.hidden = false;
    position();
  }

  function close(returnFocus) {
    clearTimeout(hideTimer);
    if (!current) return;
    const ic = current;
    current = null;
    pinned = false;
    ic.setAttribute("aria-expanded", "false");
    ic.removeAttribute("aria-describedby");
    pop.hidden = true;
    if (returnFocus && ic.isConnected) { suppressFocusOpen = true; ic.focus(); suppressFocusOpen = false; }
  }

  function scheduleHide() {
    clearTimeout(hideTimer);
    hideTimer = setTimeout(() => close(false), 180);
  }

  // Mantém o balão dentro da tela: abaixo do ícone, ou acima se não couber.
  function position() {
    if (!current || pop.hidden) return;
    if (!current.isConnected) { close(false); return; }
    const r = current.getBoundingClientRect();
    const vw = document.documentElement.clientWidth, vh = document.documentElement.clientHeight;
    const M = 8, GAP = 6;
    pop.style.maxWidth = Math.min(320, vw - 2 * M) + "px";
    pop.style.left = "0px";
    pop.style.top = "0px";
    const w = pop.offsetWidth, h = pop.offsetHeight;
    let left = r.left + r.width / 2 - w / 2;
    left = Math.max(M, Math.min(left, vw - w - M));
    let top = r.bottom + GAP;
    let below = true;
    if (top + h > vh - M && r.top - GAP - h >= M) { top = r.top - GAP - h; below = false; }
    top = Math.max(M, Math.min(top, vh - h - M));
    pop.style.left = Math.round(left) + "px";
    pop.style.top = Math.round(top) + "px";
    pop.dataset.lado = below ? "abaixo" : "acima";
    pop.style.setProperty("--gl-seta", Math.round(Math.max(12, Math.min(w - 12, r.left + r.width / 2 - left))) + "px");
  }

  const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]):not([type="hidden"]), select:not([disabled]), textarea:not([disabled]), summary, [tabindex]:not([tabindex="-1"])';

  function focusAfter(icon) {
    const all = [...document.querySelectorAll(FOCUSABLE)].filter(
      (n) => !pop.contains(n) && n.getClientRects().length && !n.closest("[hidden], [inert]"));
    const i = all.indexOf(icon);
    const next = i >= 0 ? all[i + 1] : null;
    if (next) next.focus(); else icon.focus();
  }

  /* ---------- Eventos (delegados no documento: funcionam para ícones criados depois) ---------- */
  let suppressFocusOpen = false;
  const iconOf = (t) => (t instanceof Element ? t.closest("." + ICON_CLASS) : null);

  function bindEvents() {
    document.addEventListener("click", (e) => {
      const ic = iconOf(e.target);
      if (!ic) return;
      e.preventDefault();
      e.stopPropagation(); // não aciona o rótulo/checkbox ou o contêiner em volta
      if (current === ic && pinned) close(false);
      else open(ic, true);
    }, true);

    document.addEventListener("pointerover", (e) => {
      if (e.pointerType !== "mouse") return;
      const ic = iconOf(e.target);
      if (ic && ic !== current) open(ic, false);
      else if (ic) clearTimeout(hideTimer);
    });
    document.addEventListener("pointerout", (e) => {
      if (e.pointerType !== "mouse") return;
      const ic = iconOf(e.target);
      if (!ic || ic !== current || pinned) return;
      if (e.relatedTarget && (ic.contains(e.relatedTarget) || pop.contains(e.relatedTarget))) return;
      scheduleHide();
    });

    document.addEventListener("focusin", (e) => {
      const ic = iconOf(e.target);
      if (!ic || suppressFocusOpen) return;
      let visible = true;
      try { visible = ic.matches(":focus-visible"); } catch { /* navegador antigo */ }
      if (visible) open(ic, false);
    });
    document.addEventListener("focusout", (e) => {
      if (!current) return;
      const to = e.relatedTarget;
      if (!to || to === current || pop.contains(to)) return;
      close(false);
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && current) {
        const inside = document.activeElement === current || pop.contains(document.activeElement);
        close(inside);
        if (inside) e.stopPropagation();
        return;
      }
      if (e.key === "Tab" && !e.shiftKey && current && document.activeElement === current && !pop.hidden) {
        e.preventDefault();
        popLink.focus();
      }
    });

    document.addEventListener("pointerdown", (e) => {
      if (!current) return;
      if (iconOf(e.target) || pop.contains(e.target)) return;
      close(false);
    });

    let raf = 0;
    const repos = () => { if (!raf) raf = requestAnimationFrame(() => { raf = 0; position(); }); };
    window.addEventListener("scroll", repos, { passive: true, capture: true });
    window.addEventListener("resize", repos);
  }

  /* ---------- Observador do conteúdo dinâmico ---------- */
  // Ignora as mudanças feitas pelo próprio glossário (ícones e balão): evita laço com o observador.
  const ownNode = (n) => n.nodeType === 1 && (n.classList.contains(ICON_CLASS) || n.id === POP_ID);

  function relevant(records) {
    for (const r of records) {
      if (pop && pop.contains(r.target)) continue;
      if (r.type === "attributes") return true;
      const nodes = [...r.addedNodes, ...r.removedNodes];
      if (!nodes.length || nodes.some((n) => !ownNode(n))) return true;
    }
    return false;
  }

  function init() {
    buildPop();
    bindEvents();
    scan();
    const mo = new MutationObserver((records) => { if (relevant(records)) scan(); });
    mo.observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ["data-term"] });
    window.SPHEREX_GLOSSARY_UI = { scan, close: () => close(false) };
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
