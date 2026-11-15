// Identidade visual: céu estrelado procedural e menu "tiro de infravermelho".
// Independente de app.js. Sem JS, o menu continua visível e o fundo usa só CSS.
(() => {
  "use strict";
  const reduz = window.matchMedia("(prefers-reduced-motion: reduce)");
  document.documentElement.classList.add("js-tema");

  /* ---------- Céu estrelado (canvas) ---------- */
  function ceu() {
    if (document.body.classList.contains("embed")) return;
    const cv = document.createElement("canvas");
    cv.className = "ceu-estrelado";
    cv.setAttribute("aria-hidden", "true");
    document.body.prepend(cv);
    const ctx = cv.getContext("2d");
    if (!ctx) return;
    let estrelas = [], w = 0, h = 0, raf = 0, ultimo = 0;
    // Gerador pseudoaleatório com semente fixa: o céu é o mesmo a cada visita.
    let s = 20260415;
    const rnd = () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);

    function gerar() {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      w = window.innerWidth; h = window.innerHeight;
      cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      s = 20260415;
      const n = Math.round(Math.min(260, (w * h) / 5200));
      const cores = ["#ffffff", "#cfe3ff", "#ffe6c7", "#ffd0b0", "#bfe9ff"];
      estrelas = Array.from({ length: n }, () => ({
        x: rnd() * w, y: rnd() * h,
        r: rnd() < .92 ? .4 + rnd() * .6 : 1 + rnd() * .5,
        a: .25 + rnd() * .5,
        f: .4 + rnd() * 1.4,          // frequência da cintilação
        p: rnd() * Math.PI * 2,
        c: cores[Math.floor(rnd() * cores.length)],
      }));
    }

    function desenhar(t) {
      ctx.clearRect(0, 0, w, h);
      for (const e of estrelas) {
        const k = reduz.matches ? 1 : .75 + .25 * Math.sin(t / 1000 * e.f + e.p);
        ctx.globalAlpha = e.a * k;
        ctx.fillStyle = e.c;
        ctx.beginPath(); ctx.arc(e.x, e.y, e.r, 0, Math.PI * 2); ctx.fill();
      }
      ctx.globalAlpha = 1;
    }

    function laco(t) {
      raf = requestAnimationFrame(laco);
      if (t - ultimo < 66) return;   // ~15 quadros/s bastam para cintilar
      ultimo = t; desenhar(t);
    }

    function iniciar() {
      cancelAnimationFrame(raf);
      desenhar(performance.now());
      if (!reduz.matches && !document.hidden) raf = requestAnimationFrame(laco);
    }

    let tr;
    window.addEventListener("resize", () => { clearTimeout(tr); tr = setTimeout(() => { gerar(); iniciar(); }, 150); });
    document.addEventListener("visibilitychange", iniciar);
    reduz.addEventListener?.("change", iniciar);
    gerar(); iniciar();
  }

  /* ---------- Menu: a sonda dispara um feixe infravermelho ---------- */
  function menu() {
    const botao = document.querySelector(".probe-toggle");
    const sidebar = document.querySelector(".sidebar");
    const nav = botao && document.getElementById(botao.getAttribute("aria-controls"));
    if (!botao || !sidebar || !nav) return;
    const celular = window.matchMedia("(max-width: 760px)");
    botao.hidden = false;
    let timer = 0;

    function definir(aberto, focarBotao) {
      clearTimeout(timer);
      botao.setAttribute("aria-expanded", String(aberto));
      sidebar.classList.toggle("menu-aberto", aberto);
      sidebar.classList.remove("disparando");
      if (aberto && !reduz.matches) {
        void sidebar.offsetWidth;           // reinicia a animação
        sidebar.classList.add("disparando");
        timer = setTimeout(() => sidebar.classList.remove("disparando"), 900);
      }
      if (!aberto && focarBotao) botao.focus();
    }

    botao.addEventListener("click", () => definir(botao.getAttribute("aria-expanded") !== "true"));
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && botao.getAttribute("aria-expanded") === "true") definir(false, true);
    });
    document.addEventListener("click", (e) => {
      if (botao.getAttribute("aria-expanded") === "true" && !sidebar.contains(e.target)) definir(false);
    });
    nav.addEventListener("click", (e) => { if (e.target.closest("a")) definir(false); });
    celular.addEventListener?.("change", () => definir(false));
  }

  function iniciar() { ceu(); menu(); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", iniciar);
  else iniciar();
})();
