"use strict";

/* ============================================================
 * Quando a consulta ao IRSA/servidor falha: mostra as imagens SALVAS no site.
 * - Região de um alvo de teste: o player "Décadas" (js/motion.js) — mesmo campo do céu de
 *   1950 até o SPHEREx (D1–D6), com o trajeto previsto — e o atalho para a sequência SPHEREx salva.
 * - Outra região: galeria dos alvos salvos; ao escolher um, o player abre logo abaixo.
 * Integração com app.js: showAlternatives() dispara "spx:alternativas" { kind, values }.
 * ============================================================ */
(() => {
  const h = (tag, props = {}, ...kids) => {
    const n = Object.assign(document.createElement(tag), props);
    n.append(...kids.filter((k) => k != null));
    return n;
  };

  let demoIds = null;
  const loadDemoIds = () => {
    demoIds ??= fetch("demo/manifest.json", { signal: AbortSignal.timeout(10000) })
      .then((r) => (r.ok ? r.json() : null))
      .then((m) => new Set((m?.targets ?? []).filter((t) => t?.observations).map((t) => t.id)))
      .catch(() => new Set());
    return demoIds;
  };

  let player = null;
  async function abrir(id, alvo) {
    player?.pausar();
    alvo.replaceChildren(h("p", { className: "status carregando", textContent: "Carregando as imagens salvas…" }));
    const [data, ids] = await Promise.all([window.SpxMotion.load(id), loadDemoIds()]);
    if (!data) { alvo.replaceChildren(h("p", { className: "status aviso", textContent: "Não foi possível abrir as imagens salvas." })); return; }
    player = window.SpxMotion.mount(alvo, data, ids.has(id) ? {
      onSpherex: async () => {
        await window.spxEnterDemo?.(id);
        document.getElementById("observacoes")?.scrollIntoView({ block: "start" });
      },
      spherexLabel: `Ver todas as observações SPHEREx salvas de ${data.name} (mês a mês)`,
    } : {});
  }

  async function render(values) {
    const alt = document.getElementById("alternativas");
    if (!alt || !window.SpxMotion) return;
    let host = document.getElementById("alt-imagens");
    if (!host) {
      host = h("section", { id: "alt-imagens", className: "alt-imagens", ariaLabel: "Imagens salvas" });
      const opcoes = alt.querySelector("#alt-opcoes, .alt-opcoes");
      if (opcoes) opcoes.before(host); else alt.append(host);
    }
    player?.pausar(); player = null;
    const alvos = await window.SpxMotion.index();
    if (!alvos.length) { host.hidden = true; return; }
    host.hidden = false;
    const perto = values ? await window.SpxMotion.near(Number(values.ra), Number(values.dec)) : null;
    const detalhe = h("div", { className: "ref-detalhe" });
    if (perto) {
      host.replaceChildren(detalhe);
      abrir(perto.id, detalhe);
      return;
    }
    const lista = h("div", { className: "ref-alvos" });
    for (const t of alvos) {
      const bt = h("button", { type: "button", className: "ref-alvo", ariaPressed: "false" },
        t.thumb ? h("img", { src: t.thumb, alt: "", loading: "lazy", width: 96, height: 96 }) : null,
        h("span", { textContent: t.name }),
        h("small", { textContent: `${t.frames} imagens${t.years ? ` · ${t.years[0]}–${t.years[1]}` : ""}` }));
      bt.addEventListener("click", () => {
        for (const b of lista.children) b.setAttribute("aria-pressed", String(b === bt));
        abrir(t.id, detalhe);
        detalhe.scrollIntoView({ behavior: "smooth", block: "nearest" });
      });
      lista.append(bt);
    }
    host.replaceChildren(h("div", { className: "ref-bloco" },
      h("h4", { textContent: "Veja estrelas se moverem ao longo de décadas" }),
      h("p", { className: "dica", textContent:
        "Imagens reais salvas no próprio site, que funcionam mesmo com o arquivo da NASA fora do ar: o mesmo pedaço do céu " +
        "fotografado desde os anos 1950 até o SPHEREx. Escolha um alvo." }),
      lista), detalhe);
  }

  document.addEventListener("spx:alternativas", (e) => {
    render(e.detail?.values ?? null).catch((err) => console.debug("Imagens salvas:", err));
  });
})();
