"use strict";

/* ============================================================
 * Outras bases de dados (WISE/AllWISE, 2MASS, DSS2) e busca por nome do objeto.
 * Funciona só no navegador, sem o servidor do SPHEREx Explorer. Depende de app.js
 * (carregado antes): CONFIG, el, sky, loadAladin, fovPolygon, openSky, applyBackground,
 * centerSky, setCeuStatus, setMotion.
 *
 * Serviços (verificados com requisições reais em 2026-11-15):
 * - Imagens por banda: IRSA Finder Chart (NASA/IPAC), mode=getImage&type=jpgurl → PNG,
 *   norte para cima e leste à esquerda (conferido com M51/NGC 5195). Cobre WISE W1–W4,
 *   2MASS J/H/K e DSS2 azul/vermelho/IR. O 2MASS sai todo preto acima de ~12′ (15′, 20′ e 30′
 *   testados), por isso o limite FC_MAX_ARCMIN.
 * - Visualizador interativo: Aladin Lite (o mesmo do mapa do céu) com os HiPS do CDS espelhados
 *   no IRSA (CONFIG.HIPS_FALLBACK e as bandas abaixo; "properties" respondendo 200).
 * - Nomes: Sesame do CDS (-oxp = XML), espelho da CfA primeiro (resposta direta, CORS liberado);
 *   cds.unistra.fr redireciona para vizier.idia.ac.za (também com CORS).
 * - O hips2fits do CDS (alasky) respondia 404 "page unavailable" em 2026-11-15: não é usado.
 * ============================================================ */
(() => {
  const IRSA_HIPS = "https://irsa.ipac.caltech.edu/data/hips/CDS";
  const FINDER = "https://irsa.ipac.caltech.edu/applications/finderchart/servlet/api";
  const SESAME = [
    "https://vizier.cfa.harvard.edu/viz-bin/nph-sesame/-oxp/SNV?",
    "https://cds.unistra.fr/cgi-bin/nph-sesame/-oxp/SNV?",
  ];
  const SESAME_TIMEOUT_MS = 10000;
  const IMG_TIMEOUT_MS = 90000; // o Finder Chart leva de 1 a ~25 s por imagem sem cache

  // Fundo colorido: o mesmo HiPS (e o mesmo nome) usado no seletor "Imagem de fundo" do mapa.
  const mapLayer = (name) => CONFIG.HIPS_FALLBACK.find((h) => h.name === name);

  const SURVEYS = {
    wise: {
      nome: "WISE / AllWISE",
      camada: "AllWISE (WISE)",
      cor: "Composição colorida AllWISE: vermelho = W4 (22 µm), verde = W2 (4,6 µm), azul = W1 (3,4 µm).",
      aviso: "O WISE (Wide-field Infrared Survey Explorer) é outra missão da NASA, não o SPHEREx. As imagens AllWISE " +
        "combinam observações de 2010 e 2011 numa imagem só por banda: não há linha do tempo. Servem para comparar a " +
        "mesma região em outra luz infravermelha.",
      credito: "Imagens WISE: NASA/JPL-Caltech/UCLA (AllWISE).",
      fcMax: 30,
      bandas: [
        { rotulo: "W1", luz: "3,4 µm", fc: "survey=wise&wise_bands=1", hips: `${IRSA_HIPS}/AllWISE/W1` },
        { rotulo: "W2", luz: "4,6 µm", fc: "survey=wise&wise_bands=2", hips: `${IRSA_HIPS}/AllWISE/W2` },
        { rotulo: "W3", luz: "12 µm", fc: "survey=wise&wise_bands=3", hips: `${IRSA_HIPS}/AllWISE/W3` },
        { rotulo: "W4", luz: "22 µm", fc: "survey=wise&wise_bands=4", hips: `${IRSA_HIPS}/AllWISE/W4` },
      ],
    },
    "2mass": {
      nome: "2MASS",
      camada: "2MASS",
      cor: "Composição colorida 2MASS, feita com as bandas J, H e K.",
      aviso: "O 2MASS (Two Micron All Sky Survey) mapeou o céu inteiro com dois telescópios em solo, não com o SPHEREx. " +
        "É uma imagem por banda, sem linha do tempo: serve para comparar a região no infravermelho próximo.",
      credito: "2MASS: Universidade de Massachusetts e IPAC/Caltech, com financiamento da NASA e da NSF.",
      fcMax: 12,
      bandas: [
        { rotulo: "J", luz: "1,23 µm", fc: "survey=2mass&twomass_bands=j", hips: `${IRSA_HIPS}/2MASS/J` },
        { rotulo: "H", luz: "1,66 µm", fc: "survey=2mass&twomass_bands=h", hips: `${IRSA_HIPS}/2MASS/H` },
        { rotulo: "K", luz: "2,16 µm", fc: "survey=2mass&twomass_bands=k", hips: `${IRSA_HIPS}/2MASS/K` },
      ],
    },
    dss: {
      nome: "DSS2",
      camada: "DSS2",
      cor: "Composição colorida das placas DSS2 (luz visível).",
      aviso: "O DSS (Digitized Sky Survey) são placas fotográficas de telescópios em solo, digitalizadas; a data das placas " +
        "varia de região para região. Uma imagem por banda, sem linha do tempo: serve para comparar a região em luz visível.",
      credito: "DSS: produzido no Space Telescope Science Institute (STScI) a partir de placas dos telescópios Schmidt de Palomar e UK Schmidt.",
      fcMax: 30,
      bandas: [
        { rotulo: "DSS2 azul", luz: "luz visível", fc: "survey=dss&dss_bands=poss2ukstu_blue", hips: null },
        { rotulo: "DSS2 vermelho", luz: "luz visível", fc: "survey=dss&dss_bands=poss2ukstu_red", hips: `${IRSA_HIPS}/DSS2/red` },
        { rotulo: "DSS2 IR", luz: "infravermelho fotográfico", fc: "survey=dss&dss_bands=poss2ukstu_ir", hips: null },
      ],
    },
  };
  const CREDITO_SERVICOS = "Recortes por banda: IRSA Finder Chart (NASA/IPAC). Visualizador: Aladin Lite (CDS), com ladrilhos HiPS do CDS espelhados no IRSA.";

  const $id = (id) => document.getElementById(id);
  const ui = {
    nome: $id("nome"), localizar: $id("nome-localizar"), nomeStatus: $id("nome-status"), base: $id("base"),
    box: $id("outras-bases"), titulo: $id("ob-titulo"), aviso: $id("ob-aviso"), status: $id("ob-status"),
    viewer: $id("ob-viewer"), viewerLegenda: $id("ob-viewer-legenda"), bandas: $id("ob-bandas"),
    credito: $id("ob-credito"), mapa: $id("ob-mapa"), voltar: $id("ob-spherex"),
  };
  if (!ui.base || !ui.box) return; // página sem a seção de busca

  const ob = { resolved: null, cur: null, aladin: null, overlay: null, mark: null, skyOverlay: null, seq: 0 };
  const fmtGraus = (n, d = 4) => n.toFixed(d).replace(".", ",").replace("-", "−");
  const fmtArcmin = (n) => String(n).replace(".", ",");

  function setNomeStatus(msg, kind = "") {
    ui.nomeStatus.textContent = msg;
    ui.nomeStatus.className = "nome-status " + kind;
  }

  /* Páginas (js/router.js): depois de um submit, o router leva a "Observações". Quando o resultado
   * fica na busca (outra base ou nome não encontrado), volta para "Explorar o céu" e mostra o elemento.
   * O setTimeout roda depois do do router (registrado antes, no mesmo submit). */
  function stayOnSearch(target) {
    setTimeout(() => {
      if (window.spxRouter && window.spxRouter.current !== "busca") window.spxRouter.go("busca", { replace: true, focus: false });
      requestAnimationFrame(() => target?.scrollIntoView({ behavior: "smooth", block: "start" }));
    }, 0);
  }

  function setObStatus(msg, kind = "") {
    ui.status.textContent = msg;
    ui.status.className = "status " + kind;
  }

  /* ---------- Nome do objeto → RA/Dec (Sesame do CDS) ---------- */
  async function sesame(name) {
    for (const base of SESAME) {
      try {
        const r = await fetch(base + encodeURIComponent(name), { signal: AbortSignal.timeout(SESAME_TIMEOUT_MS) });
        if (!r.ok) continue;
        const xml = new DOMParser().parseFromString(await r.text(), "application/xml");
        if (!xml.querySelector("Sesame")) continue; // resposta inesperada: tenta o próximo espelho
        const res = [...xml.querySelectorAll("Resolver")].find((x) => x.querySelector("jradeg") && x.querySelector("jdedeg"));
        if (!res) return { found: false };
        const num = (sel) => { const t = res.querySelector(sel)?.textContent; return t ? Number(t) : NaN; };
        return {
          found: true, ra: num("jradeg"), dec: num("jdedeg"),
          pmRa: num("pmRA"), pmDe: num("pmDE"),
          fonte: (res.getAttribute("name") ?? "").match(/=\s*([A-Za-z]+)/)?.[1] ?? "Sesame",
          oname: res.querySelector("oname")?.textContent?.replace(/^NAME\s+/, "") ?? "",
        };
      } catch { /* sem resposta: tenta o próximo espelho */ }
    }
    throw new Error("sesame-indisponivel");
  }

  /** Resolve o nome digitado e preenche RA/Dec. Retorna true se deu certo. */
  async function locate() {
    const name = ui.nome.value.trim();
    if (!name) { setNomeStatus("Digite o nome de um objeto, por exemplo M42."); ui.nome.focus(); return false; }
    ui.localizar.disabled = true;
    el.buscar.disabled = true;
    setNomeStatus(`Procurando “${name}”…`, "carregando");
    try {
      const r = await sesame(name);
      if (!r.found || !Number.isFinite(r.ra) || !Number.isFinite(r.dec)) {
        setNomeStatus(`Não encontrei “${name}” nos catálogos SIMBAD, NED e VizieR. Confira a grafia (ex.: M42, NGC 1976, Barnard's Star) ou informe RA e Dec.`, "aviso");
        stayOnSearch(ui.nome.closest(".field"));
        ui.nome.focus({ preventScroll: true });
        return false;
      }
      el.ra.value = r.ra.toFixed(6);
      el.dec.value = r.dec.toFixed(6);
      ["ra", "dec"].forEach((k) => { el[k].setAttribute("aria-invalid", "false"); $id(k + "-erro").textContent = ""; });
      setMotion(null); // a posição do catálogo não traz a época de referência de forma explícita
      ob.resolved = { name, ra: el.ra.value, dec: el.dec.value };
      const pm = Math.hypot(r.pmRa || 0, r.pmDe || 0);
      setNomeStatus(`${r.oname || name}: RA ${fmtGraus(r.ra)}°, Dec ${fmtGraus(r.dec)}° (${r.fonte}, via Sesame/CDS).` +
        (pm > 100 ? ` Este objeto se move rápido no céu (${fmtGraus(pm / 1000, 2)}″ por ano): a posição é a do catálogo e pode não coincidir com imagens de outras datas.` : ""), "ok");
      return true;
    } catch {
      setNomeStatus("O serviço de nomes do CDS não respondeu agora. Tente de novo em instantes ou informe RA e Dec diretamente.", "aviso");
      stayOnSearch(ui.nome.closest(".field"));
      return false;
    } finally {
      ui.localizar.disabled = false;
      el.buscar.disabled = false;
    }
  }

  async function resolveNameIfNeeded() {
    const name = ui.nome.value.trim();
    if (!name || (ob.resolved && ob.resolved.name === name)) return true;
    return locate();
  }

  function clearName() {
    ui.nome.value = "";
    ob.resolved = null;
    setNomeStatus("");
  }

  ui.localizar.addEventListener("click", locate);
  // Coordenadas digitadas à mão ou alvo de exemplo: o nome resolvido antes deixa de valer.
  ["ra", "dec"].forEach((k) => el[k].addEventListener("input", () => { if (ob.resolved) clearName(); }));
  $id("presets")?.addEventListener("click", (e) => { if (e.target.closest("button")) clearName(); }, true);

  /* ---------- Seletor de base ---------- */
  const selected = () => (SURVEYS[ui.base.value] ? ui.base.value : "spherex");

  function syncButton() {
    const s = SURVEYS[selected()];
    el.buscar.textContent = s ? `Mostrar imagens ${s.nome}` : "Buscar observações";
  }
  ui.base.addEventListener("change", syncButton);
  syncButton();

  /* ---------- Imagens por banda (IRSA Finder Chart) ---------- */
  const fcUrl = (b, v) =>
    `${FINDER}?mode=getImage&RA=${v.ra}&DEC=${v.dec}&subsetsize=${v.fov}&thumbnail_size=large&${b.fc}&type=jpgurl`;

  function bandFigure(s, b, v, seq, done) {
    const fig = document.createElement("figure");
    fig.className = "ob-fig";
    const wrap = document.createElement("div");
    wrap.className = "ob-img";
    const cap = document.createElement("figcaption");
    const titulo = document.createElement("strong");
    titulo.textContent = `${b.rotulo} · ${b.luz}`;
    const msg = document.createElement("span");
    msg.className = "ob-msg";
    const acoes = document.createElement("span");
    acoes.className = "ob-acoes";
    cap.append(titulo, msg, acoes);
    fig.append(wrap, cap);

    const verNoVisor = () => {
      if (!b.hips) return null;
      const bt = document.createElement("button");
      bt.type = "button";
      bt.className = "chip";
      bt.textContent = "Ver no visualizador";
      bt.addEventListener("click", () => showViewer(b.hips, `${s.nome} ${b.rotulo} (${b.luz})`, v));
      return bt;
    };

    if (v.fov > s.fcMax) {
      wrap.classList.add("vazio");
      msg.textContent = `O serviço de recortes do IRSA não gera imagens ${s.nome} maiores que ${s.fcMax}′.` +
        (b.hips ? " Veja esta banda no visualizador interativo." : "");
      const bt = verNoVisor();
      if (bt) acoes.append(bt);
      done(false);
      return fig;
    }

    const url = fcUrl(b, v);
    const img = document.createElement("img");
    img.alt = `Região em RA ${v.ra}°, Dec ${v.dec}° vista por ${s.nome}, banda ${b.rotulo} (${b.luz}). Norte para cima, leste à esquerda.`;
    img.decoding = "async";
    wrap.classList.add("carregando");
    msg.textContent = "Carregando do IRSA…";
    let terminou = false;
    const fim = (ok) => {
      if (terminou || seq !== ob.seq) return;
      terminou = true;
      clearTimeout(timer);
      wrap.classList.remove("carregando");
      acoes.replaceChildren();
      if (ok) {
        msg.textContent = "";
        const a = document.createElement("a");
        a.href = url;
        a.target = "_blank";
        a.rel = "noopener";
        a.textContent = "Abrir PNG";
        acoes.append(a);
      } else {
        img.removeAttribute("src");
        img.remove(); // sem a imagem quebrada (e o texto alternativo) por cima do hachurado
        wrap.classList.add("vazio");
        msg.textContent = "Esta banda não chegou agora (o serviço do IRSA pode estar ocupado).";
        const retry = document.createElement("button");
        retry.type = "button";
        retry.className = "chip";
        retry.textContent = "Tentar de novo";
        retry.addEventListener("click", () => fig.replaceWith(bandFigure(s, b, v, ob.seq, () => {})));
        acoes.append(retry);
      }
      const bt = verNoVisor();
      if (bt) acoes.append(bt);
      done(ok);
    };
    const timer = setTimeout(() => fim(false), IMG_TIMEOUT_MS);
    img.addEventListener("load", () => fim(img.naturalWidth > 0));
    img.addEventListener("error", () => fim(false));
    img.src = url;
    wrap.append(img);
    return fig;
  }

  /* ---------- Visualizador interativo (Aladin Lite, uma instância reaproveitada) ---------- */
  async function showViewer(url, legenda, v) {
    const seq = ob.seq;
    ui.viewerLegenda.textContent = `${legenda} · carregando o visualizador…`;
    try {
      const A = await loadAladin();
      if (seq !== ob.seq) return;
      const fovGraus = Math.max((v.fov / 60) * 1.6, 0.02);
      if (!ob.aladin) {
        ob.aladin = A.aladin("#ob-viewer", {
          survey: url, target: `${v.ra} ${v.dec}`, fov: fovGraus, projection: "TAN",
          showCooGrid: false, showCooGridControl: false, showLayersControl: false, showGotoControl: false,
          showShareControl: false, showSimbadPointerControl: false, showSettingsControl: false,
          showProjectionControl: false, showFrame: false, showContextMenu: false, showFullscreenControl: true,
        });
        ob.overlay = A.graphicOverlay({ color: "#ff5c8a", lineWidth: 2 });
        ob.aladin.addOverlay(ob.overlay);
      } else {
        (ob.aladin.setBaseImageLayer ?? ob.aladin.setImageSurvey).call(ob.aladin, url);
        ob.aladin.gotoRaDec(v.ra, v.dec);
        ob.aladin.setFoV(fovGraus);
      }
      ob.overlay.removeAll();
      ob.overlay.addFootprints([fovPolygon(A, v, v.fov)]);
      ui.viewerLegenda.textContent = `${legenda.replace(/\.$/, "")}. Arraste e use a roda do mouse para navegar; o quadrado rosa é a área (FOV) escolhida.`;
    } catch (err) {
      console.error("Outras bases (visualizador):", err);
      if (seq !== ob.seq) return;
      ui.viewerLegenda.textContent = /webgl/i.test(String(err))
        ? "O visualizador interativo precisa de WebGL2, que está desligado neste navegador. As imagens por banda continuam valendo."
        : "O visualizador interativo não carregou agora (a biblioteca Aladin Lite não respondeu). As imagens por banda continuam valendo.";
    }
  }

  /* ---------- Mostrar a região na base escolhida ---------- */
  function show(values) {
    const key = selected();
    const s = SURVEYS[key];
    if (!s) return;
    const seq = ++ob.seq;
    const v = { ra: values.ra, dec: values.dec, fov: values.fov };
    ob.cur = { key, v };
    ui.box.hidden = false;
    ui.titulo.textContent = `Esta região no ${s.nome}`;
    ui.aviso.textContent = s.aviso;
    ui.credito.textContent = `${s.credito} ${CREDITO_SERVICOS} Imagens com norte para cima e leste à esquerda.`;
    setObStatus(`RA ${fmtGraus(v.ra)}°, Dec ${fmtGraus(v.dec)}°, FOV ${fmtArcmin(v.fov)}′. As imagens por banda vêm do IRSA e podem levar de alguns segundos a meio minuto.`, "carregando");

    let pend = s.bandas.length, ok = 0;
    const done = (deuCerto) => {
      if (seq !== ob.seq) return;
      if (deuCerto) ok++;
      if (--pend > 0) return;
      setObStatus(ok === s.bandas.length
        ? `Pronto: ${ok} bandas do ${s.nome} · RA ${fmtGraus(v.ra)}°, Dec ${fmtGraus(v.dec)}°, FOV ${fmtArcmin(v.fov)}′.`
        : `${ok} de ${s.bandas.length} bandas carregadas. As que faltam podem ser vistas no visualizador interativo ou tentadas de novo.`,
      ok === s.bandas.length ? "" : "info");
    };
    ui.bandas.replaceChildren(...s.bandas.map((b) => bandFigure(s, b, v, seq, done)));
    const camada = mapLayer(s.camada);
    if (camada) showViewer(camada.url, s.cor, v);
    else ui.viewerLegenda.textContent = s.cor;

    if (sky.aladin) setCeuStatus(`Região RA ${fmtGraus(v.ra)}°, Dec ${fmtGraus(v.dec)}° mostrada no ${s.nome}, na página “Explorar o céu”. Use “Abrir esta posição no mapa interativo” para vê-la aqui.`);
    stayOnSearch(ui.box);
  }

  function hide() {
    ob.seq++;
    ui.box.hidden = true;
  }

  /* ---------- Abrir no mapa do céu, com o fundo da mesma base ---------- */
  function drawSkyMark() {
    if (!sky.aladin || !sky.A || !ob.mark) return;
    try {
      ob.skyOverlay?.removeAll();
      ob.skyOverlay = sky.A.graphicOverlay({ color: "#ffd36b", lineWidth: 2, lineDash: [6, 4] });
      sky.aladin.addOverlay(ob.skyOverlay);
      ob.skyOverlay.addFootprints([fovPolygon(sky.A, ob.mark.v, ob.mark.v.fov)]);
    } catch (err) { console.error("Mapa do céu (região de outra base):", err); }
  }

  async function openInMap() {
    if (!ob.cur) return;
    const s = SURVEYS[ob.cur.key], v = ob.cur.v;
    const camada = mapLayer(s.camada);
    if (camada && [...el.ceuFundo.options].some((o) => o.value === camada.url)) el.ceuFundo.value = camada.url;
    ob.mark = { v, nome: s.nome };
    if (window.spxRouter) window.spxRouter.go("ceu");
    else $id("ceu").scrollIntoView({ behavior: "smooth", block: "start" });
    await openSky(); // se falhar, o próprio mapa mostra a mensagem
    if (!sky.aladin) return;
    await applyBackground(el.ceuFundo.value);
    centerSky(v, v.fov);
    drawSkyMark();
    setCeuStatus(`Mapa centrado em RA ${fmtGraus(v.ra)}°, Dec ${fmtGraus(v.dec)}°, com o fundo ${camada?.name ?? s.nome}. ` +
      `O quadrado amarelo tracejado marca a região vista no ${s.nome}.`);
  }

  ui.mapa.addEventListener("click", openInMap);
  ui.voltar.addEventListener("click", () => {
    ui.base.value = "spherex";
    syncButton();
    hide();
    el.form.requestSubmit();
  });

  window.Surveys = { selected, show, hide, resolveNameIfNeeded, clearName, drawSkyMark };
})();
