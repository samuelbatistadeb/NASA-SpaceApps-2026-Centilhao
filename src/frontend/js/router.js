// Páginas do SPHEREx Explorer: router por hash (#busca, #observacoes, #ceu, #mapa, #espectro, #galeria).
// Mostra uma seção por vez, mantendo a query string (?demo=, ?ra=&dec=&fov=...) intacta.
// Independente de app.js: observa o DOM em vez de depender de funções internas.
//
// API pública:
//   window.spxRouter.go("ceu", { replace?: boolean, focus?: boolean })
//   window.spxRouter.current            -> id da página ativa
//   window.addEventListener("spx:page", (e) => e.detail.page / e.detail.prev)
//
// Sem JS tudo continua visível (a classe html.js-paginas só é posta aqui).
// No modo incorporado (?embed=1) o router não é ativado.
(() => {
  "use strict";
  const q = new URLSearchParams(location.search);
  if (q.get("embed") === "1" || document.body.classList.contains("embed")) return;

  const main = document.querySelector("main");
  if (!main) return;
  const pages = [...main.querySelectorAll(":scope > section.page[id]")].map((s) => s.id);
  if (!pages.length) return;
  const HOME = pages.includes("busca") ? "busca" : pages[0];
  const reduz = window.matchMedia("(prefers-reduced-motion: reduce)");
  const tituloBase = document.title.split(" — ")[0] || "SPHEREx Explorer";
  const tituloInicial = document.title;
  const navLinks = [...document.querySelectorAll('.navbar nav a[href^="#"]')];

  let current = null;

  document.documentElement.classList.add("js-paginas");

  // Página que contém um id qualquer (ex.: #combinar fica dentro de #observacoes).
  function pageOf(id) {
    if (!id) return null;
    if (pages.includes(id)) return id;
    const el = document.getElementById(id);
    const sec = el?.closest("main > [data-page]");
    return sec ? sec.dataset.page : null;
  }

  function rotulo(page) {
    const a = navLinks.find((l) => l.hash === "#" + page);
    return a ? a.textContent.replace(/^\S\s*/u, "").trim() : page;
  }

  function render(page, { focus = true, scrollTo = null } = {}) {
    const prev = current;
    current = page;
    document.body.dataset.page = page;
    main.querySelectorAll(":scope > [data-page]").forEach((s) => {
      const ativa = s.dataset.page === page;
      s.classList.toggle("ativa", ativa);
      s.classList.remove("entrando");
      if (ativa && prev !== null && prev !== page && !reduz.matches) {
        void s.offsetWidth; // reinicia a animação de entrada
        s.classList.add("entrando");
        const fim = (e) => {
          if (e.target !== s) return; // ignora animações dos elementos internos
          s.classList.remove("entrando");
          s.removeEventListener("animationend", fim);
        };
        s.addEventListener("animationend", fim);
      }
    });
    navLinks.forEach((a) => {
      if (a.hash === "#" + page) { a.setAttribute("aria-current", "page"); a.classList.remove("novidade"); }
      else a.removeAttribute("aria-current");
    });
    document.title = page === HOME ? tituloInicial : `${rotulo(page)} · ${tituloBase}`;

    if (prev !== page) {
      // Volta ao topo sem animação (html tem scroll-behavior: smooth).
      if (!scrollTo) window.scrollTo({ top: 0, left: 0, behavior: "instant" });
      if (prev !== null && focus) {
        const sec = document.getElementById(page);
        const h = sec?.querySelector("h2");
        if (h) {
          if (!h.hasAttribute("tabindex")) h.setAttribute("tabindex", "-1");
          h.focus({ preventScroll: true });
        }
      }
      // Mapas e gráficos medem o tamanho ao abrir: avisa que o espaço mudou (Aladin Lite).
      requestAnimationFrame(() => window.dispatchEvent(new Event("resize")));
      setTimeout(() => window.dispatchEvent(new Event("resize")), 450);
      window.dispatchEvent(new CustomEvent("spx:page", { detail: { page, prev } }));
    }
    if (scrollTo) {
      const alvo = document.getElementById(scrollTo);
      requestAnimationFrame(() => nativeScroll.call(alvo, { block: "start", behavior: "instant" }));
    }
  }

  // Lê o hash atual e mostra a página correspondente.
  function fromHash({ focus = true } = {}) {
    const id = decodeURIComponent(location.hash.slice(1));
    const page = pageOf(id) || HOME;
    render(page, { focus, scrollTo: id && !pages.includes(id) && document.getElementById(id) ? id : null });
  }

  function go(page, { replace = false, focus = true } = {}) {
    const p = pageOf(page);
    if (!p) return;
    if (p === current && location.hash === "#" + p) { render(p, { focus }); return; }
    // pushState não dispara hashchange: renderiza já (síncrono). Voltar/avançar dispara hashchange.
    if (replace) history.replaceState(history.state, "", "#" + p);
    else history.pushState(history.state, "", "#" + p);
    render(p, { focus });
  }

  window.addEventListener("hashchange", () => fromHash());

  // Clique no item da página já aberta: só volta ao topo.
  navLinks.forEach((a) => a.addEventListener("click", (e) => {
    if (a.hash === "#" + current && location.hash === a.hash) {
      e.preventDefault();
      window.scrollTo({ top: 0, behavior: reduz.matches ? "auto" : "smooth" });
    }
  }));

  /* ---------- Integração com app.js sem editá-lo ---------- */

  // 1) app.js chama scrollIntoView() em #ceu ("Explorar o mapa do céu enquanto isso") e em
  //    #combinar. Se o elemento estiver numa página escondida, abre essa página antes.
  const nativeScroll = Element.prototype.scrollIntoView;
  Element.prototype.scrollIntoView = function (...args) {
    const sec = this.closest?.("main > [data-page]");
    if (sec && sec.dataset.page !== current) {
      go(sec.dataset.page);
      requestAnimationFrame(() => nativeScroll.apply(this, args));
      return;
    }
    return nativeScroll.apply(this, args);
  };

  // 2) app.js grava a busca com history.replaceState(null, "", "?ra=..."), o que apagaria o
  //    hash da página. Mantém o hash atual quando a nova URL só traz a query string.
  const nativeReplace = history.replaceState.bind(history);
  history.replaceState = function (state, title, url) {
    if (typeof url === "string" && url.startsWith("?") && !url.includes("#") && location.hash) url += location.hash;
    return nativeReplace(state, title, url);
  };

  // 3) Busca a partir da página inicial: vai para "Observações" (o status "Buscando…" fica lá).
  //    O submit de app.js roda antes (registrado antes); se a validação falhou, fica na busca.
  const form = document.getElementById("form");
  let buscouEm = 0;
  form?.addEventListener("submit", () => {
    buscouEm = Date.now();
    if (current !== HOME) return;
    setTimeout(() => {
      if (current === HOME && !form.querySelector('[aria-invalid="true"]')) go("observacoes");
    }, 0);
  });

  // 4) Resultado aparecendo enquanto o usuário está na busca (ex.: exemplo salvo, ?demo=).
  const ficouVisivel = (el, cb) => {
    if (!el) return;
    new MutationObserver(() => { if (!el.hidden) cb(); })
      .observe(el, { attributes: true, attributeFilter: ["hidden"] });
  };
  ficouVisivel(document.getElementById("player"), () => { if (current === HOME) go("observacoes"); });
  // Painel "não foi possível buscar": só leva a "Observações" se veio de uma busca. Se apareceu
  // sozinho ao abrir o site (servidor fora do ar), o usuário fica na página inicial, onde
  // app.js já oferece os exemplos salvos junto dos alvos de exemplo.
  ficouVisivel(document.getElementById("alternativas"), () => {
    if (current === HOME && Date.now() - buscouEm < 120000) go("observacoes");
  });

  // 5) Clicar numa miniatura da galeria ou num ponto do mapa de observações mostra o quadro.
  document.addEventListener("click", (e) => {
    const t = e.target;
    if (!(t instanceof Element)) return;
    if (t.closest("#galeria-lista button")) { go("observacoes"); return; }
    const ponto = t.closest("#mapa-grafico circle");
    if (ponto && ponto.style.cursor === "pointer") go("observacoes");
  });

  // 6) Espectro: é calculado ao clicar na imagem, mas aparece em outra página.
  //    Marca o item "Espectro" no menu e mostra um aviso com atalho.
  let aviso = null, avisoTimer = 0;
  function avisar(texto, page, botao) {
    if (!aviso) {
      aviso = document.createElement("div");
      aviso.className = "spx-aviso";
      aviso.setAttribute("role", "status");
      document.body.append(aviso);
    }
    clearTimeout(avisoTimer);
    const b = document.createElement("button");
    b.type = "button"; b.className = "chip"; b.textContent = botao;
    b.addEventListener("click", () => { fecharAviso(); go(page); });
    const fechar = document.createElement("button");
    fechar.type = "button"; fechar.className = "chip"; fechar.textContent = "Fechar";
    fechar.addEventListener("click", fecharAviso);
    const span = document.createElement("span");
    span.textContent = texto;
    aviso.replaceChildren(span, b, fechar);
    aviso.hidden = false;
    avisoTimer = setTimeout(fecharAviso, 9000);
  }
  function fecharAviso() { clearTimeout(avisoTimer); if (aviso) aviso.hidden = true; }
  window.addEventListener("spx:page", fecharAviso);

  const marcarNovidade = (page) => {
    if (page === current) return;
    navLinks.find((a) => a.hash === "#" + page)?.classList.add("novidade");
  };
  const imgwrap = document.getElementById("imgwrap");
  const pontoMarcado = () => {
    if (current === "espectro") return;
    marcarNovidade("espectro");
    avisar("Ponto marcado: o espectro é calculado na página Espectro.", "espectro", "Ver espectro");
  };
  imgwrap?.addEventListener("click", pontoMarcado);
  imgwrap?.addEventListener("keydown", (e) => { if (e.key === "Enter") pontoMarcado(); });
  ficouVisivel(document.getElementById("esp-grafico"), () => marcarNovidade("espectro"));

  /* ---------- Página inicial ---------- */
  let inicial = pageOf(decodeURIComponent(location.hash.slice(1)));
  // Link compartilhado com uma busca (?demo=, ?ra=&dec=): abre direto em "Observações".
  if (!location.hash && (q.has("demo") || (q.has("ra") && q.has("dec")))) {
    inicial = "observacoes";
    nativeReplace(history.state, "", "#observacoes");
  }
  if (inicial && location.hash) fromHash({ focus: false });
  else render(inicial || HOME, { focus: false });

  window.spxRouter = { go, pages: pages.slice(), get current() { return current; } };
})();
