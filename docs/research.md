# Pesquisa e referências

> Registro de pesquisa do SPHEREx Explorer — NASA Space Apps Challenge 2026.
> **Data da pesquisa: 2026-11-14.** Todas as afirmações abaixo foram verificadas por
> consulta direta aos serviços oficiais, salvo quando explicitamente marcado como
> **NÃO VERIFICADO**.

Documentos detalhados:
- `docs/science/data-sources.md` — produtos, serviços, endpoints, metadados, limitações.
- `docs/science/target-catalog.md` — os 5 objetos de teste com astrometria e sequências.

---

## Fontes oficiais

| Fonte | Instituição | URL | Data de consulta | O que foi extraído |
|---|---|---|---|---|
| SPHEREx Archive at IRSA | NASA / IPAC / Caltech | https://irsa.ipac.caltech.edu/Missions/spherex.html | 2026-11-14 | Releases (QR1/QR2/QR3/DR1), ferramentas, serviços, papers canônicos |
| SPHEREx DR1 Overview | NASA / IPAC / Caltech | https://irsa.ipac.caltech.edu/data/SPHEREx/docs/overview_dr1.html | 2026-11-14 | DOI 10.26131/IRSA678 / IRSA679, produtos, vias de acesso |
| SPHEREx Quick Release Overview | NASA / IPAC / Caltech | https://irsa.ipac.caltech.edu/data/SPHEREx/docs/overview_qr.html | 2026-11-14 | Ciclo de vida dos QRs; QR2 não buscável; QR1 aposentado |
| SPHEREx Archive at IRSA — User Guide (12/11/2026) | NASA / IPAC / Caltech | https://caltech-ipac.github.io/spherex-archive-documentation/ | 2026-11-14 | Visão geral do arquivo |
| SPHEREx Data Products | NASA / IPAC / Caltech | https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products | 2026-11-14 | HDUs, convenções de nome, ePSF, All-Sky Cube, calibrativos |
| SPHEREx Data Access | NASA / IPAC / Caltech | https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access | 2026-11-14 | **Endpoint SIA2, coleções, endpoint TAP, sintaxe do cutout** |
| IRSA SIA v2 — consultas | NASA / IPAC / Caltech | https://irsa.ipac.caltech.edu/ibe/sia.html | 2026-11-14 | Lista completa de parâmetros, sintaxe de `POS`, colunas, formatos |
| IRSA — Querying and Downloading Images | NASA / IPAC / Caltech | https://irsa.ipac.caltech.edu/docs/program_interface/api_images.html | 2026-11-14 | Matriz de APIs e quais **não** se aplicam ao SPHEREx |
| IRSA — Program Interfaces | NASA / IPAC / Caltech | https://irsa.ipac.caltech.edu/voapi.html | 2026-11-14 | Índice de APIs do IRSA |
| IRSA IBE — Image Server Cutouts | NASA / IPAC / Caltech | https://irsa.ipac.caltech.edu/ibe/cutouts.html | 2026-11-14 | Sintaxe `center`/`size`/`gzip`, exemplo SPHEREx, erros |
| IRSA — Cloud Data Access | NASA / IPAC / Caltech | https://irsa.ipac.caltech.edu/cloud_access/#spherex | 2026-11-14 | Bucket S3 `nasa-irsa-spherex`, região, prefixos, acesso anônimo |
| IRSA — MOST API | NASA / IPAC / Caltech | https://irsa.ipac.caltech.edu/applications/MOST/MOSTProgramInterface.html | 2026-11-14 | `catalog=spherex`; tabela com `mjd_start`/`mjd_end`/`uri` por imagem |
| IRSA Tutorials — SPHEREx (índice) | NASA / IPAC / Caltech | https://caltech-ipac.github.io/irsa-tutorials/spherex/ | 2026-11-14 | Lista dos 6 tutoriais SPHEREx |
| Tutorial — Introduction to SPHEREx Spectral Images | NASA / IPAC / Caltech | https://caltech-ipac.github.io/irsa-tutorials/spherex-intro/ | 2026-11-14 | Procedimento SIA2, WCS (espacial/espectral), flags, `PSF_FWHM` |
| Tutorial — Spectral Image Cutouts | NASA / IPAC / Caltech | https://caltech-ipac.github.io/irsa-tutorials/spherex-cutouts/ | 2026-11-14 | Procedimento **TAP**, montagem da URL de cutout, paralelismo (7–12 workers) |
| Gaia DR3 — MAST | ESA / STScI | https://archive.stsci.edu/missions-and-data/gaia | 2026-11-14 | Página institucional; aponta o GAIA Archive @ ESA como ferramenta oficial |
| GAIA Archive @ ESA — TAP | ESA | https://gea.esac.esa.int/tap-server/tap/sync | 2026-11-14 | **Astrometria real dos 5 objetos** (ADQL sobre `gaiadr3.gaia_source`) |
| IRSA TAP — `gaia_dr3_source` | NASA / IPAC / Caltech | https://irsa.ipac.caltech.edu/TAP/sync | 2026-11-14 | Tabela Gaia DR3 espelhada no IRSA (mesma do ESA) |
| SPHEREx Expository Supplement (PDF) | NASA / IPAC / Caltech | https://irsa.ipac.caltech.edu/data/SPHEREx/docs/SPHEREx_Expsupp.pdf | — | Referência normativa (Tabela 16 = flags) — **não lido nesta etapa** |

### Fontes complementares (com justificativa)

| Fonte | Justificativa | Data |
|---|---|---|
| Wikipedia (EN): "Barnard's Star", "Epsilon Indi", "RW Aurigae", "WISE 0855−0714", "List of stars in Draco" | Obter coordenadas **J2000** e identificadores HD/HIP como *seed* para a consulta ao Gaia DR3. SIMBAD, VizieR, ADS e MAST/CasJobs **não são alcançáveis** a partir do ambiente de pesquisa (verificado: `ENOTFOUND` / `ECONNREFUSED` / HTTP 404/405). Todas as posições foram reconferidas no Gaia DR3 | 2026-11-14 |
| Wikidata Q12775006 (R Draconis) | Identificadores HD 149880 / HIP 81014 (o artigo "R Draconis" não existe na Wikipédia) | 2026-11-14 |

---

## Artigos científicos

Artigos **canônicos** listados pela própria página da missão SPHEREx no IRSA
(https://irsa.ipac.caltech.edu/Missions/spherex.html), com link no ADS:

| Papel | Referência | ADS |
|---|---|---|
| Missão | Bock et al. (2026), ApJ 999, 139 | https://ui.adsabs.harvard.edu/abs/2026ApJ...999..139B/abstract |
| Pipeline | Akeson et al. (2026), ApJS 285, 67 | https://ui.adsabs.harvard.edu/abs/2026ApJS..285...67A/abstract |
| Simulador de céu | Crill et al. (2025), ApJS 281, 10 | https://ui.adsabs.harvard.edu/abs/2025ApJS..281...10C/abstract |
| Instrumento & calibração | Korngut et al. (2026), arXiv:2603.29835 | https://ui.adsabs.harvard.edu/abs/2026arXiv260329835K/abstract |

**Fontes secundárias citadas nos objetos de teste** (via infobox da Wikipédia, com a
referência original indicada na própria infobox):

| Objeto | Fonte indicada na infobox | Uso aqui |
|---|---|---|
| WISE 0855−0714 | **Kirkpatrick et al. (2021)** | paralaxe 439.0 ± 2.4 mas; μ(α\*) = −8123.7 ± 1.3 mas/ano; μ(δ) = +673.2 ± 1.3 mas/ano |
| WISE 0855−0714 | Luhman (2014) / Luhman (2024) | posição J2000 de descoberta; massa 3–10 M_J |

**Artigos primários NÃO verificados nesta etapa** (ADS inacessível — HTTP 405 no ambiente):
Kirkpatrick et al. (2021), Luhman (2014). → **Requer validação da liderança científica.**

---

## Datasets

### Dataset primário — SPHEREx no IRSA

| Produto | Coleção SIA2 | Buscável | DOI |
|---|---|---|---|
| DR1 Spectral Image MEF (Wide) | `spherex_dr1` | sim | 10.26131/IRSA678 |
| DR1 Spectral Image MEF (Deep) | `spherex_dr1_deep` | sim | 10.26131/IRSA678 |
| DR1 All-Sky Cube (HEALPix N5, 512×512×102) | `spherex_dr1_cube` | sim | 10.26131/IRSA679 |
| QR3 Spectral Image MEF (Wide) | `spherex_qr3` | sim | 10.26131/IRSA662 |
| QR3 Spectral Image MEF (Deep) | `spherex_qr3_deep` | sim | 10.26131/IRSA662 |
| QR2 / QR1 | — | **não** (QR2 só por download direto até fev/2027) | 10.26131/IRSA652 / IRSA629 |

### Dataset complementar — Gaia DR3

- ESA: `gaiadr3.gaia_source` (TAP `https://gea.esac.esa.int/tap-server/tap/sync`).
- IRSA: `gaia_dr3_source` (TAP `https://irsa.ipac.caltech.edu/TAP/sync`) — mesma tabela,
  mesma astrometria, útil para manter o backend em um único host.
- Também no IRSA: `gaia_dr3_astrophys_param`, `gaia_dr3_astrophys_supp`,
  `gaia_allwise_best_neighbour`, `gaia_variablesummary`.

### Dataset de referência de UX — WiseView

http://byw.tools/wiseview — **usado apenas como referência de experiência de usuário**
(navegação temporal, controles, comparação entre épocas). **Nunca** como fonte de dados
SPHEREx. Observação: o WISE é um survey *não repetido* no tempo, o que significa que a
analogia com SPHEREx tem limites — em SPHEREx o tempo é um eixo **real**, não uma metáfora.

---

## Tecnologias

| Tecnologia | Papel no projeto | Status |
|---|---|---|
| `astroquery.ipac.irsa.Irsa.query_sia` | Consulta SIA2 às coleções SPHEREx | **validado** (procedimento do tutorial oficial) |
| `astroquery.ipac.irsa.Irsa.query_tap` | Consulta TAP a `spherex.artifact`/`spherex.plane` | **validado** (procedimento do tutorial oficial) |
| `pyvo` | Acesso de baixo nível a SIA2/TAP | a validar (alternativa ao astroquery) |
| `astropy.io.fits` | Leitura de MEF, WCS, `Cutout2D` | **validado** (extensões lidas de arquivo real) |
| `astropy.wcs.WCS(header, fobj=hdulist, key="W")` | λ e bandwidth por pixel | **validado** (tutorial oficial) |
| `astropy.utils.data.conf.remote_timeout = 120` | Necessário para ler SPHEREx remoto | **validado** (tutorial oficial) |
| `numpy` | Processamento numérico | a validar |
| `fastapi` + `uvicorn` | API do backend | planejada (fora do escopo desta pesquisa) |
| `boto3` / `s3fs` | Acesso anônimo ao bucket `nasa-irsa-spherex` | a validar (prefixos e região confirmados) |
| `firefly-client` | Visualização interativa do WCS espectral | **validado** (tutorial oficial) |

---

## Descobertas

1. **O arquivo SPHEREx no IRSA está em DR1 (novembro/2026) + QR3 (setembro/2026).**
   QR1 está aposentado (desde fev/2026) e QR2 não é mais retornado em buscas (mas pode ser
   baixado diretamente até fev/2027). DR1 e QR3 juntos formam o conjunto uniforme
   recomendado.
   *Fonte:* IRSA SPHEREx page + QR/DR1 Overview. **FATO CONFIRMADO.**

2. **O endpoint SIA2 é `https://irsa.ipac.caltech.edu/SIA?`** e exige o parâmetro
   `COLLECTION`. As 5 coleções SPHEREx são `spherex_dr1`, `spherex_dr1_deep`,
   `spherex_dr1_cube`, `spherex_qr3`, `spherex_qr3_deep`.
   *Fonte:* SPHEREx Data Access + teste direto. **FATO CONFIRMADO.**

3. **O serviço de cutout é síncrono e baseado em query string**:
   `<access_url>?center=<ra>,<dec><units>&size=<x>[,<y>]<units>`. Documentado em
   `/ibe/cutouts.html`; verificado em execução real (HTTP 200, FITS válido).
   *Fonte:* IBE Cutouts + teste. **FATO CONFIRMADO.**

4. **A hipótese central do projeto — de que existem observações repetidas da mesma região
   do céu em momentos diferentes — está CONFIRMADA.** Os 5 objetos de teste têm
   **143 a 1309 épocas distintas**, com cobertura de 12 a 17 meses entre abril/2025 e
   outubro/2026. Cada época é uma **exposição individual de um detector** (não um mosaico).
   *Fonte:* SIA2, consultas reais em 2026-11-14. **FATO CONFIRMADO.**
   Detalhe em `docs/science/data-sources.md` §13.

5. **Os 102 canais espectrais do SPHEREx NÃO são uma sequência temporal.** As 6 bandas
   coexistem dentro de cada imagem; a sequência temporal vem de **`t_min` distintos**.
   Um recorte contém os 102 canais do seu detector.
   *Fonte:* User Guide + estrutura FITS verificada. **FATO CONFIRMADO.**

6. **A epoch de cada produto está em `t_min`/`t_max` (SIA2) e
   `time_bounds_lower`/`time_bounds_upper` (TAP), em MJD**, e corresponde exatamente a
   `MJD-OBS`/`MJD-END` do cabeçalho FITS. Verificado numericamente.
   **Armadilhas confirmadas:** `obs_release_date` é a data de *publicação*, e a keyword FITS
   `DATE` é o *timestamp de criação do HDU* — nenhuma das duas é a data de observação.
   *Fonte:* cabeçalho FITS real + SIA2 + TAP. **FATO CONFIRMADO.**

7. **A coordenada do desafio para WISE 0855 é a posição J2000.0 de WISE 0855−0714**
   (coincide até < 0.01″ com a infobox: RA 08h55m10.83168s, Dec −07°14′42.5256″).
   Com μ ≈ 8.15"/ano, o objeto estará **~207″ (3.5′) deslocado** nas épocas SPHEREx
   2025–2026 — cerca de 34 pixels de 6.15".
   *Fonte:* Wikipédia (infobox, J2000) + propagação própria. **FATO CONFIRMADO**
   (com a ressalva de que paralaxe e μ vêm de fonte secundária).

8. **O Gaia DR3 não oferece um homólogo astrométrico utilizável para WISE 0855.** Em uma
   busca num raio de 0.15° em torno da posição J2000 (e de 0.04° em torno da posição
   prevista para 2016.0), **nenhuma** fonte apresenta μ(α\*) < −3000 mas/ano. A fonte mais
   próxima tem μ(α\*) = −6.19 mas/ano, ou seja, é uma estrela de campo coincidente.
   *Fonte:* ADQL direto no GAIA Archive @ ESA. **FATO CONFIRMADO (resultado negativo).**

9. **Em 2026-11-14 o IRSA_lookup só tinha `spherex_dr1` para a região de WISE 0855**
   (nenhum QR3 no cone testado) — logo, uma implementação que consulte só uma coleção
   **perde metade da série temporal** em vários alvos.
   *Fonte:* SIA2. **FATO CONFIRMADO.**

10. **R Draconis está num campo profundo** do SPHEREx (`spherex_dr1_deep` + `spherex_qr3_deep`),
    o que lhe dá 4× mais produtos que a média e o torna o melhor caso de teste para
    variação de brilho. *Fonte:* SIA2. **FATO CONFIRMADO.**

11. **A resolução real é ~7.45″ FWHM, não os 3.075″ do campo `s_resolution` do SIA2**
    (que é apenas `s_pixel_scale / 2`). Consequência: binários como ε Indi A/B (~6.5″) e
    RW Aur A/B (**1.49″**, medido do Gaia) são **indissociáveis** pelo SPHEREx.
    *Fonte:* `PSF_FWHM` no cabeçalho FITS + tutorial oficial. **FATO CONFIRMADO.**

12. **O serviço de cutout pode responder `503 "Server busy, retry later."`** (25 bytes),
    observ empiricamente em 2026-11-14 → o backend precisa de retry com backoff.
    *Fonte:* teste real. **FATO CONFIRMADO.**

13. **Even um recorte de 0.02° (12×12 pixels) tem ~4 MB**, porque a extensão `EPSF` domina
    o volume. Recortes devem ser pequenos e processados para extrair apenas `IMAGE`.
    *Fonte:* medição direta. **FATO CONFIRMADO.**

14. **As séries temporais por banda são esparsas**: em Barnard/D3, apenas **14 das 61**
    épocas estão separadas por ≥ 1 dia (mediana 2.8 d, máx 203.8 d). O "total" de 192 épocas
    inclui exposures separadas por ~2 minutos dentro de uma mesma visita.
    *Fonte:* SIA2. **FATO CONFIRMADO.**

15. **DR1 e QR3 são temporalmente disjuntos** (DR1: MJD 60789.88–61173.25; QR3:
    61176.36–61310.29) — não há sobreposição de épocas, o que facilita a comparação, mas
    exige atenção à compatibilidade de calibração (ganho, PSF) e ao uso de
    `l3_flux_corrections`.
    *Fonte:* SIA2 + User Guide. **FATO CONFIRMADO.**

---

## Hipóteses

| # | Hipótese | Estado | Base |
|---|---|---|---|
| H1 | O IRSA oferece um serviço consultável (SIA2) que devolve as observações SPHEREx de uma posição, com a época de observação | **CONFIRMADA** | consultas reais |
| H2 | Existem observações repetidas da mesma região em instantes diferentes (pré-requisito da sequência temporal) | **CONFIRMADA** | 143–1309 épocas por alvo |
| H3 | A "temporalidade" do SPHEREx é o eixo central da experiência de usuário (a serExplorer) | **CONFIRMADA** | achados 4, 14 |
| H4 | Os 102 canais do SPHEREx seriam uma "sequência temporal" | **REFUTADA** | achado 5 |
| H5 | A coordenada do desafio para WISE 0855 seria a posição atual do objeto | **REFUTADA** | achados 7 e 8 |
| H6 | A aplicação pode usar apenas `spherex_dr1` | **REFUTADA** | achado 9 |
| H7 | O SIA2 sozinho basta para o backend | **PARCIALMENTE CONFIRMADA** — basta para o MVP; o TAP é ~1 dia mais fresco e já entrega a URL de cutout pronta e ordenada | achados 1, 4 e docs do User Guide |
| H8 | Binários próximos (ε Indi AB, RW Aur AB) podem ser separados nas imagens SPHEREx | **REFUTADA** | achado 11 |
| H9 | `s_resolution` do SIA2 descreve a resolução efetiva | **REFUTADA** | achado 11 |
| H10 | Os dados podem ser acessados sem autenticação e sem custo | **CONFIRMADA** | bucket S3 anônimo + IRSA sem login |
| H11 | Há um serviço de cutout **assíncrono** no IRSA | **NÃO VERIFICADO / provavelmente inexistente** — o serviço de cutout é síncrono; só o TAP tem `/async` | docs do IRSA |
| H12 | Um "Simple Cone Search" no formato antigo está disponível para SPHEREx | **NÃO VERIFICADO** — não consta na doc de imagens do IRSA; usar SIA2 | `/docs/program_interface/api_images.html` |
| H13 | A paralaxe/μ de WISE 0855 confirmados pelo artigo primário | **NÃO VERIFICADO** — ADS inacessível (HTTP 405) | ver abaixo |

---

## Limitações

### Quadro de riscos científicos — disposição após a pesquisa de 2026-11-14

*(IDs conforme `docs/board.md` §5. Este quadro é informativo; a atualização oficial do
quadro é do Coordinator.)*

| ID | Risco | Disposição após esta pesquisa | Evidência |
|---|---|---|---|
| **R-01** | Crítico — a premissa de "sequência temporal" exige re-observações da mesma região em épocas distintas | **CONFIRMADO** — 143 a 1309 épocas distintas por alvo, cobertura de 12–17 meses | `data-sources.md` §13; consultas SIA2 reais |
| **R-02** | Objetos com movimento próprio podem sair do campo sem correção de época | **CONFIRMADO E QUANTIFICADO** — WISE 0855 desloca **207″** (≈34 px) e Barnard **100–112″** (≈17 px) entre J2000/2016 e as épocas SPHEREx. **Mitigação obrigatória: propagar a posição à época de cada observação** | `target-catalog.md` §3.1, §3.3; §14.3 |
| **R-03** | ε Indi B: separação de poucos arcsegundos pode ser indistinguível na PSF | **CONFIRMADO** — ε Indi B não tem entrada no Gaia DR3 e a separação (~6.5″) é menor que a PSF (~7.45″ FWHM). **O teste deve ser declarado como "sistema ε Indi (A+B combinado)"** | `target-catalog.md` §3.2 |
| **R-04** | Variação real pode se confundir com mudança de detector/calibração/unidade/pipeline | **PARCIALMENTE** — cada época é de **um detector**, logo comparar exige fixar a banda; DR1 e QR3 são reprocessamentos distintos e **não** são temporalmente sobrepostos (logo a comparação entre eles é temporalmente limpa, mas fotometricamente exige `l3_flux_corrections` e atenção ao `VERSION`) | `data-sources.md` §13, §14.1 |
| **R-05** | Escala de fluxo pode ser relativa, não absoluta | **CONFIRMADO** — o HDU `IMAGE` é brilho de superfície **calibrado** em MJy/sr, e existe o produto `l3_flux_corrections` para combinar DR1 (ganho antigo) com QR3 (ganho novo). A compatibilidade **absoluta entre DR1 e QR3 não foi verificada** | `data-sources.md` §4.4, §5.1 |
| **R-06** | Máscaras, saturação, PSF variável e ruído podem produzir sequência convincente e inválida | **MITIGAÇÕES IDENTIFICADAS** — HDU `FLAGS` (bitmask `MSKN*`/`MSKD*`), contadores `L2 N_*`, `PSF_FWHM` por imagem, ePSF por zona (441/451 zonas) | `data-sources.md` §5.1, §12.3, §14.1 |
| **R-07** | Época de referência das coordenadas inadequada para objetos com movimento próprio | **CONFIRMADO** — o Gaia DR3 usa `ref_epoch = 2016.0`; para WISE 0855 a coordenada do desafio é **J2000.0**; propagação obrigatória | `target-catalog.md` §3.1–§3.5 |
| **R-08** | Distinguir data de observação de data de publicação/processamento | **CONFIRMADO E RESOLVIDO** — a época é `t_min`/`MJD-OBS`; `obs_release_date` é publicação e a keyword FITS `DATE` é o timestamp de criação do HDU (armadilha confirmada) | `data-sources.md` §12.1 |
| **R-10** | Compatibilidade de `astroquery`/`pyvo` com os SIA2 do IRSA ainda não testada | **PARCIALMENTE** — a camada HTTP crua do SIA2 e do TAP foi testada e **funciona**; o wrapper `astroquery` segue o procedimento do tutorial oficial, mas **não foi executado** neste ambiente (sem Python disponível). `pyvo` idem | `data-sources.md` §3.1, §3.2 |

### Limitações do ambiente de pesquisa (importante para o registro)

- **ADS (`ui.adsabs.harvard.edu`, `adsabs.harvard.edu`)**: HTTP 405 → artigos primários
  **não** puderam ser lidos. As referências canônicas da missão são conhecidas, mas seu
  conteúdo não foi verificado.
- **SIMBAD (`simbad.u-strasbg.fr`)**: DNS não resolve (`ENOTFOUND`).
- **VizieR (`tapvizier.cds.unistra.fr`)**: conexão recusada (`ECONNREFUSED`).
- **MAST CasJobs / catalogs.mast.stsci.edu**: HTTP 404 nos endpoints testados
  (`/api/v0.1/gaia/search`, `/tap/sync`, `/api/v0.1/Mashup/request`).
- **Consequência:** a resolução de nomes/objetos foi feita via Wikipedia/Wikidata como
  *seed*, seguida de **verificação no Gaia DR3** (ESA). Todas as coordenadas astrométricas
  finais vêm do **Gaia DR3**, não da Wikipédia.
- **Nenhum acesso a FTP/SSH**; downloads feitos por HTTP GET.

### Limitações dos dados e dos serviços (detalhadas em `docs/science/data-sources.md` §14)

- Resolução ~7.45″ FWHM com pixel de 6.15″ → PSF subamostrada; binários < ~10″ inseparáveis.
- Luz zodiacal **não** subtraída no HDU `IMAGE` (modelo no HDU `ZODI`).
- Canais 51–52 do All-Sky Cube vazios; listras de emissão atmosférica no cube.
- Imagens não são north-up; distorção SIP presente no WCS.
- Versões de processamento variam dentro do release → comparabilidade fotométrica não
  garantida sem `l3_flux_corrections`.
- SIA2 com ~1 dia de defasagem; TAP é a via mais fresca.
- Cutout pode falhar com `503 "Server busy, retry later."`; sem limite de taxa publicado.
- Sem cutout assíncrono documentado.
- Séries por banda esparsas (mediana 2–5 dias entre épocas independentes).
- SPHEREx **não** marca alvos com movimento próprio (`target_moving = 0`): a propagação
  astrométrica é responsabilidade da aplicação.

### Limitações desta pesquisa

- Não foi feita fotometria real (extração de fluxo) em nenhum recorte → a
  **detectabilidade** dos alvos por banda (especialmente WISE 0855 em Y4 e os canais
  4–6) **permanece NÃO VERIFICADA**.
- O número de objetos do catálogo é pequeno (5) e todos em açoitava da mesma ordem de
  grandeza; não se pode generalizar a densidade de épocas para toda a esfera celeste a
  partir de 5 pontos.
- `s_resolution`, `t_resolution`, `em_xel`, `pol_states`, `target_keywords` vêm **vazios**
  no SIA2 para SPHEREx — não são utilizáveis como metadados.
- Os valores de paralaxe e μ de WISE 0855 (fonte secundária) e o período de R Dra
  (fonte secundária) ainda não foram confirmados contra a literatura primária.
