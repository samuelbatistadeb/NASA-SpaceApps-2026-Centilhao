"use strict";

/* ============================================================
 * Imagens salvas dos 5 alvos de teste (DSS, 2MASS, WISE), exibidas quando a consulta ao
 * IRSA/servidor falha. Arquivos estáticos gerados por data/scripts/18_reference_images.py
 * (manifesto em demo/reference.json); nada aqui depende do servidor nem do IRSA.
 *
 * Integração com app.js: showAlternatives() dispara o evento "spx:alternativas"
 * { kind, values } e este módulo preenche um bloco dentro de #alternativas.
 * ============================================================ */
(() => {
  const MANIFEST = "demo/reference.json";
  const MATCH_ARCMIN = 10; // distância máxima entre a busca e o alvo salvo
  let manifestPromise = null;

  const load = () => {
    manifestPromise ??= fetch(MANIFEST, { signal: AbortSignal.timeout(10000) })
      .then((r) => (r.ok ? r.json() : null))
      .then((m) => ((m?.targets ?? []).some((t) => t.images?.length) ? m : null))
      .catch(() => null);
    return manifestPromise;
  };

  const rad = (d) => (d * Math.PI) / 180;
  function sepArcmin(ra1, dec1, ra2, dec2) {
    const s = Math.sin(rad(dec1)) * Math.sin(rad(dec2)) +
      Math.cos(rad(dec1)) * Math.cos(rad(dec2)) * Math.cos(rad(ra1 - ra2));
    return (Math.acos(Math.min(1, Math.max(-1, s))) * 180 / Math.PI) * 60;
  }

  const fmtData = (iso) => {
    const [y, m, d] = String(iso).split("-");
    return d && m && y ? `${d}/${m}/${y}` : String(iso);
  };
  const nomeBanda = (img) =>
    img.survey === "WISE" ? `WISE ${img.band.toUpperCase()}` :
    img.survey === "2MASS" ? `2MASS ${img.band}` : img.band;

  const h = (tag, props = {}, ...kids) => {
    const n = Object.assign(document.createElement(tag), props);
    n.append(...kids.filter((k) => k != null));
    return n;
  };

  // Caixa para ampliar uma imagem (dialog nativo; Esc fecha).
  let dlg = null;
  function ampliar(img, alvo) {
    if (!dlg) {
      dlg = h("dialog", { className: "ref-dialog", ariaLabel: "Imagem ampliada" });
      dlg.addEventListener("click", (e) => { if (e.target === dlg) dlg.close(); });
      document.body.append(dlg);
    }
    const fechar = h("button", { type: "button", className: "chip ref-fechar", textContent: "✕ Fechar" });
    fechar.addEventListener("click", () => dlg.close());
    dlg.replaceChildren(
      h("img", { src: img.file, alt: `${alvo}: ${nomeBanda(img)} (${img.wavelength}), ${fmtData(img.obsdate)}` }),
      h("p", { textContent: `${alvo} · ${nomeBanda(img)} · ${img.wavelength} · imagem de ${fmtData(img.obsdate)} · ` +
        `${img.fov_arcmin}′ × ${img.fov_arcmin}′, norte para cima. ${img.credit}` }),
      fechar,
    );
    dlg.showModal();
  }

  function figura(img, alvo) {
    const bt = h("button", { type: "button", className: "ref-thumb", title: "Ampliar" },
      h("img", { src: img.file, loading: "lazy", width: 160, height: 160,
        alt: `${alvo}: ${nomeBanda(img)}, ${fmtData(img.obsdate)}` }));
    bt.addEventListener("click", () => ampliar(img, alvo));
    return h("figure", { className: "ref-fig" }, bt,
      h("figcaption", {},
        h("strong", { textContent: nomeBanda(img) }), ` · ${img.wavelength}`,
        h("br"), h("span", { textContent: fmtData(img.obsdate) })));
  }

  function blocoAlvo(t, demoIds) {
    const imgs = [...t.images].sort((a, b) => String(a.obsdate).localeCompare(String(b.obsdate)));
    const anos = imgs.map((i) => String(i.obsdate).slice(0, 4));
    const box = h("div", { className: "ref-bloco" },
      h("h4", { textContent: `Imagens salvas de ${t.name} (${anos[0]}–${anos[anos.length - 1]})` }),
      h("p", { className: "dica", textContent:
        "Outros telescópios (não SPHEREx), salvas no próprio site: aparecem mesmo com o arquivo da NASA fora do ar. " +
        "Em ordem de data. Cada imagem está centrada onde o alvo estava naquela data; em estrelas rápidas, " +
        "são as estrelas de fundo que parecem se deslocar. Clique para ampliar." }));
    if (demoIds.has(t.id)) {
      const ver = h("button", { type: "button", className: "primary", textContent: `Ver as observações SPHEREx salvas de ${t.name}` });
      ver.addEventListener("click", () => window.spxEnterDemo?.(t.id));
      box.append(h("div", { className: "alt-botoes" }, ver));
    }
    box.append(h("div", { className: "ref-grade" }, ...imgs.map((i) => figura(i, t.name))));
    return box;
  }

  function galeriaAlvos(m) {
    const box = h("div", { className: "ref-bloco" },
      h("h4", { textContent: "Imagens salvas dos alvos de exemplo" }),
      h("p", { className: "dica", textContent:
        "Esta região não tem imagens salvas. Escolha um dos alvos de exemplo para ver imagens de outros telescópios guardadas no site." }));
    const lista = h("div", { className: "ref-alvos" });
    const detalhe = h("div", { className: "ref-detalhe" });
    for (const t of m.targets) {
      if (!t.images?.length) continue;
      const capa = t.images.find((i) => i.id === "wise_w1") ?? t.images.find((i) => i.survey === "2MASS") ?? t.images[0];
      const bt = h("button", { type: "button", className: "ref-alvo" },
        h("img", { src: capa.file, alt: "", loading: "lazy", width: 96, height: 96 }),
        h("span", { textContent: t.name }), h("small", { textContent: `${t.images.length} imagens` }));
      bt.addEventListener("click", () => {
        for (const b of lista.children) b.setAttribute("aria-pressed", String(b === bt));
        detalhe.replaceChildren(blocoAlvo(t, demoIdsCache));
        detalhe.scrollIntoView({ behavior: "smooth", block: "nearest" });
      });
      lista.append(bt);
    }
    box.append(lista, detalhe);
    return box;
  }

  let demoIdsCache = new Set();
  async function demoIds() {
    try {
      const r = await fetch("demo/manifest.json", { signal: AbortSignal.timeout(10000) });
      const m = r.ok ? await r.json() : null;
      demoIdsCache = new Set((m?.targets ?? []).filter((t) => t?.observations).map((t) => t.id));
    } catch { /* sem exemplos SPHEREx: só as imagens de referência */ }
    return demoIdsCache;
  }

  async function render(values) {
    const alt = document.getElementById("alternativas");
    if (!alt) return;
    let host = document.getElementById("alt-imagens");
    if (!host) {
      host = h("section", { id: "alt-imagens", className: "alt-imagens", ariaLabel: "Imagens salvas" });
      const opcoes = alt.querySelector("#alt-opcoes, .alt-opcoes");
      if (opcoes) opcoes.before(host); else alt.append(host);
    }
    const [m, ids] = await Promise.all([load(), demoIds()]);
    if (!m) { host.hidden = true; return; }
    host.hidden = false;
    const perto = values && m.targets
      .filter((t) => t.images?.length)
      .map((t) => ({ t, d: sepArcmin(values.ra, values.dec, t.ra, t.dec) }))
      .sort((a, b) => a.d - b.d)[0];
    const alvo = h("div");
    if (perto && perto.d <= MATCH_ARCMIN) alvo.append(blocoAlvo(perto.t, ids));
    else alvo.append(galeriaAlvos(m));
    host.replaceChildren(alvo);
  }

  document.addEventListener("spx:alternativas", (e) => {
    render(e.detail?.values ?? null).catch((err) => console.debug("Imagens salvas:", err));
  });
})();
