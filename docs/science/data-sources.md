# Fontes de dados científicos

## 1. Objetivo

Documentar as fontes científicas utilizadas pelo projeto, os produtos de dados disponíveis e os mecanismos de consulta necessários para recuperar observações da missão SPHEREx.

Nenhuma fonte deverá ser considerada validada apenas por ter sido mencionada em documentação ou pesquisa preliminar.

A disponibilidade, os formatos e os mecanismos de acesso deverão ser testados.

> **Estado da pesquisa (data de consulta: 2026-11-14).** Todos os endpoints, parâmetros e
> formatos de resposta listados nas seções 3 a 5 foram **testados ativamente** contra os
> serviços do IRSA. As consultas de exemplo foram executadas com sucesso e os resultados
> estão registrados. Onde a verificação não foi possível, o item está marcado
> explicitamente como **NÃO VERIFICADO**.
>
> As seções 1–10 preservam a estrutura original deste documento; o material novo foi
> acrescentado nas seções 11–17.

---

## 2. Fonte principal — SPHEREx Archive

**Instituição:** NASA / IPAC / Caltech.

**Arquivo:** Infrared Science Archive (IRSA).

**Endereço:**

https://irsa.ipac.caltech.edu/Missions/spherex.html

**Documentação primária complementar (mesma instituição):**

| Documento | URL | Data do documento |
|---|---|---|
| SPHEREx Archive at IRSA — User Guide | https://caltech-ipac.github.io/spherex-archive-documentation/ | 12/11/2026 |
| SPHEREx Data Releases | https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-releases | 12/11/2026 |
| SPHEREx Data Products | https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products | 12/11/2026 |
| SPHEREx Data Access | https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access | 12/11/2026 |
| SPHEREx Explanatory Supplement (PDF) | https://irsa.ipac.caltech.edu/data/SPHEREx/docs/SPHEREx_Expsupp.pdf | — |
| IRSA Data Explorer (GUI) | https://irsa.ipac.caltech.edu/applications/spherex | — |

**Finalidade no projeto:**

Obter imagens e metadados de observações SPHEREx para as coordenadas celestes informadas pelo usuário.

Informações a investigar — **todas confirmadas empiricamente em 2026-11-14** (ver §3, §4, §5, §12):

- Produtos científicos disponíveis. ✔ (§4)
- Identificação dos levantamentos (releases). ✔ (§4)
- Datas e épocas de observação. ✔ (§12)
- Bandas espectrais. ✔ (§4.2)
- Detectores. ✔ (§4.2, §12.3)
- Coordenadas e cobertura espacial. ✔ (§4.2, §12)
- Metadados dos arquivos. ✔ (§12)
- Qualidade e sinalizadores das observações. ✔ (§12.3, §14)
- Condições de acesso e utilização. ✔ (§16)

---

## 3. Serviços de consulta

### 3.1 Simple Image Access — SIA2 (SERVIÇO PRINCIPAL)

**Endpoint exato (VERIFICADO em 2026-11-14):**

```
https://irsa.ipac.caltech.edu/SIA?
```

> ### ⚠ CORREÇÃO IMPORTANTE — o caminho `/SIA` **É** o serviço SIA **v2**
>
> Uma sondagem anterior de disponibilidade registrou que `/SIA?` responde 200 e que
> `/SIA2?` responde 404, e conclui que `/SIA` seria "protocolo SIA1". **Isso está
> incorreto.** O IRSA **não** usa o caminho `/SIA2`: a implementação SIA v2 do IRSA é
> servida em `/SIA`, conforme a própria documentação oficial
> (https://irsa.ipac.caltech.edu/ibe/sia.html — "IRSA implementation of the IVOA SIA v2
> specification") e o guia do arquivo SPHEREx
> (https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access —
> "IRSA's generic SIA2 endpoint is: https://irsa.ipac.caltech.edu/SIA?").
>
> **Como confirmar na prática (3 evidências independentes, todas verificadas em 2026-11-14):**
> 1. `GET /SIA?MAXREC=0` devolve um VOTable cujo auto-descritivo lista os parâmetros
>    **exclusivos da SIA v2** (`BAND`, `CLOSEST`, `DPTYPE`, `POS`, `RESPONSEFORMAT`,
>    `SPECRP`, `TIME`, `UPLOAD`…), que **não existem na SIA v1**.
> 2. `GET /SIA?...&POS=circle+...` funciona com a sintaxe **SIA v2**
>    (`circle <ra> <dec> <raio>`), e a mesma consulta em `/SIA2?` devolve 404.
> 3. As colunas devolvidas (`access_url`, `obs_id`, `t_min`, `t_max`, `em_min`, `em_max`,
>    `energy_bandpassname`, `cloud_access`, `obs_publisher_did`…) são exatamente as
>    **unified columns da SIA v2** descritas na doc do IRSA.
>
> **Consequência:** a estratégia de consulta deve usar **`/SIA` = SIA v2**, e **não**
> procurar um caminho `/SIA2`. O SIA v1 do IRSA (`/ibe/sia_v1.html`) é limitado a
> WISE/2MASS/PTF e **não** cobre SPHEREx.
>
> ### ⚠ CORREÇÃO IMPORTANTE — o serviço de cutout **não** é um CGI
>
> Uma sondagem anterior procurou `/cgi-bin/nph-cutout?` e `/cutout?` (ambos 404) e
> concluiu que o caminho de recorte precisava ser descoberto. **O caminho existe e foi
> verificado:** o IRSA Image Back End (IBE) gera o recorte **acrescentando uma query
> string ao `access_url` do próprio arquivo FITS**, que é servido sob `/ibe/data/`
> (ver §3.3). Não existe endpoint de cutout autônomo para o SPHEREx.

Documentação oficial:
- https://irsa.ipac.caltech.edu/ibe/sia.html
- https://irsa.ipac.caltech.edu/docs/program_interface/api_images.html
- https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access

**Coleções SPHEREx (VERIFICADAS por consulta direta):**

| `COLLECTION` | Conteúdo | Status |
|---|---|---|
| `spherex_dr1` | DR1 Spectral Image MEFs — **Wide Survey** | ativo |
| `spherex_dr1_deep` | DR1 Spectral Image MEFs — **Deep Survey** | ativo |
| `spherex_dr1_cube` | DR1 All-Sky Cube FITS | ativo |
| `spherex_qr3` | QR3 Spectral Image MEFs — **Wide Survey** | ativo |
| `spherex_qr3_deep` | QR3 Spectral Image MEFs — **Deep Survey** | ativo |
| (QR2 / QR1) | — | **não buscáveis**; QR2 só por download direto até fev/2027 |

> Para obter **toda** a cobertura SPHEREx atual, é obrigatório consultar
> `spherex_dr1` **e** `spherex_qr3` (mais as variantes `_deep`).
> **Isto foi confirmado empiricamente**: WISE 0855 só aparece em `spherex_dr1` (0 linhas em
> QR3 no cone testado), enquanto Barnard, RW Aur e R Dra aparecem nos dois.

**Parâmetros aceitos** (lista completa do auto-descritivo do serviço, `GET /SIA?MAXREC=0`):

`BAND`, `CALIB`, `CLOSEST`, `COLLECTION`, `DPTYPE`, `EXPTIME`, `FACILITY`, `FORMAT`, `FOV`,
`ID`, `INSTRUMENT`, `MAXREC`, `POL`, `POS`, `RESPONSEFORMAT`, `SPATRES`, `SPECRP`, `TARGET`,
`TIME`, `TIMERES`, `UPLOAD`.

**Formato de resposta (VERIFICADO):** `RESPONSEFORMAT` aceita `VOTABLE` (padrão), `CSV`,
`TSV`, `JSON`, `FITS`, `IPAC_TABLE`, `HDF5`, `HTML`, `TEXT`, `POSTGRES`, `SQLITE`,
`ORACLE`, `DB`. **VOTABLE, CSV, TSV e JSON testados com sucesso em 2026-11-14.**

**Colunas de retorno (51, verificadas):**

`s_ra`, `s_dec`, `facility_name`, `instrument_name`, `dataproduct_subtype`, `calib_level`,
`dataproduct_type`, `energy_bandpassname`, `energy_emband`, `obs_id`, `s_resolution`,
`em_min`, `em_max`, `em_res_power`, `proposal_title`, `access_url`, `access_format`,
`access_estsize`, `t_exptime`, `s_region`, `obs_collection`, `obs_intent`, `algorithm_name`,
`facility_keywords`, `instrument_keywords`, `environment_photometric`, `proposal_id`,
`proposal_pi`, `proposal_project`, `target_name`, `target_type`, `target_standard`,
`target_moving`, `target_keywords`, `obs_release_date`, `s_xel1`, `s_xel2`, `s_pixel_scale`,
`position_timedependent`, `t_min`, `t_max`, `t_resolution`, `t_xel`, `obs_publisher_did`,
`s_fov`, `em_xel`, `pol_states`, `pol_xel`, `cloud_access`, `o_ucd`, `upload_row_id`.
Com `CLOSEST` é acrescentada `min_dist_to_point`.

**Semântica crítica de `energy_bandpassname`:** apesar do nome, **o valor é o DETECTOR**
(`SPHEREx-D1` … `SPHEREx-D6`) — não existe `W1`/`J` para SPHEREx. `instrument_name` vale
`SPHEREx` em todas as linhas.

**Semântica crítica de `s_resolution`:** vale **3.075 arcsec**, que é exatamente
`s_pixel_scale / 2` (6.15"/2). **Não é o FWHM da PSF** (~7.45", ver §14.1).

**Semântica crítica de `obs_release_date`:** é a data de **publicação/ingestão** do
produto no arquivo (ex.: `2026-09-27 23:59:28`), **não** a data de observação.

**Exemplos verificados (executados com sucesso em 2026-11-14):**

```bash
# Consulta multi-coleção (4 coleções SPHEREx ativas), VOTable (formato padrão)
wget -O results.vot "https://irsa.ipac.caltech.edu/SIA?COLLECTION=spherex_dr1&COLLECTION=spherex_qr3&COLLECTION=spherex_dr1_deep&COLLECTION=spherex_qr3_deep&POS=circle+269.448503+4.739420+0.05&RESPONSEFORMAT=VOTABLE&MAXREC=5000"
# → HTTP 200, 12.7 s, 378 linhas para Barnard

# Restringir a uma banda (detector) e a um intervalo de datas (MJD)
wget -O w.csv "https://irsa.ipac.caltech.edu/SIA?COLLECTION=spherex_dr1&COLLECTION=spherex_qr3&POS=circle+133.795129+-7.245147+0.05&TIME=60800+60900&BAND=1.0e-6+2.5e-6&RESPONSEFORMAT=CSV"
# → HTTP 200, 0.6 s, 19 linhas

# Apenas a imagem mais próxima de cada coleção
wget -O c.csv "https://irsa.ipac.caltech.edu/SIA?COLLECTION=spherex_dr1&COLLECTION=spherex_qr3&POS=circle+133.795129+-7.245147+0.05&CLOSEST=COLLECTION&RESPONSEFORMAT=CSV"
# → HTTP 200, 0.7 s, 2 linhas

# Esquema completo do serviço
wget -O schema.xml "https://irsa.ipac.caltech.edu/SIA?MAXREC=0"
```

**Filtros verificados experimentalmente:**
- `TIME=60800+60900` (MJD) → funciona.
- `BAND=1.0e-6+2.5e-6` (metros) → funciona.
- `CLOSEST=COLLECTION` → funciona; 1 linha por coleção + `min_dist_to_point`.
- `POS=circle <ra> <dec> <raio_em_graus>` → sintaxe obrigatória (ver §11).

### 3.2 Table Access Protocol (TAP) — serviço de segunda opção, **mais fresco**

**Endpoint exato (VERIFICADO em 2026-11-14):**

```
https://irsa.ipac.caltech.edu/TAP/sync?REQUEST=doQuery&LANG=ADQL&FORMAT=csv&QUERY=<ADQL>
```

Variantes: `FORMAT=csv|tsv|votable|json` (todas testadas com sucesso). Endpoint assíncrono
existente (documentado no guia SIA2): `https://irsa.ipac.caltech.edu/TAP/async`.

Documentação: https://irsa.ipac.caltech.edu/docs/program_interface/TAP.html

**Tabelas SPHEREx no TAP do IRSA (VERIFICADAS via `TAP_SCHEMA.tables`):**

`spherex.artifact`, `spherex.plane`, `spherex.observation`, `spherex.obscore`,
`spherex.provenance_input`.

**Tabelas Gaia DR3 no mesmo TAP (VERIFICADAS):** `gaia_dr3_source` (com `ra`, `dec`,
`ra_error`, `dec_error`, `parallax`, `parallax_error`, `pmra`, `pmra_error`, `pmdec`,
`pmdec_error`, `ref_epoch`, `phot_g_mean_mag`, `designation`, `source_id` — unidades
`mas`, `mas/yr`), `gaia_dr3_astrophys_param`, `gaia_dr3_astrophys_supp`,
`gaia_allwise_best_neighbour`, `gaia_variablesummary`.

> **Vantagem decisiva do TAP:** os dados SPHEREx são ingeridos semanalmente; o guia de
> arquivo afirma que a **disponibilidade via SIA2 tem defasagem de ~1 dia**, enquanto
> consultas TAP veem o dado imediatamente após a ingestão. O próprio tutorial oficial de
> cutouts usa TAP por esse motivo.

**Consulta verificada (modelo do tutorial oficial "Spectral Image Cutouts"), executada com
sucesso em 2026-11-14 para Barnard/D3 (18.5 s, 61 linhas):**

```sql
SELECT
  'https://irsa.ipac.caltech.edu/' || a.uri || '?center=269.448503,4.73942d&size=0.05' AS uri,
  p.time_bounds_lower,
  p.time_bounds_upper,
  p.energy_bandpassname
FROM spherex.artifact a
JOIN spherex.plane p ON a.planeid = p.planeid
WHERE 1 = CONTAINS(POINT('ICRS', 269.448503, 4.739420), p.poly)
  AND p.energy_bandpassname = 'SPHEREx-D3'
ORDER BY p.time_bounds_lower
```

### 3.3 IBE Cutout Service — recortes de imagem

**Sintaxe (VERIFICADA em 2026-11-14):** acrescentar a query string ao `access_url` do
arquivo FITS servido em `/ibe/data/`:

```
<access_url>?center=<x>,<y><units>&size=<x>[,<y>]<units>[&gzip=false]
```

- `center`: `x,y` separados por vírgula. Sem unidades → **graus**. Unidades aceitas:
  `deg`, `rad`, `arcmin`, `arcsec`, `px`/`pix`/`pixels`. Em coordenadas angulares,
  `x` = **RA J2000**, `y` = **Dec**.
  **⚠ O sufixo de unidade aplica-se ao PAR INTEIRO, não a cada valor.** Verificado em
  2026-11-14: `center=248.167378,66.755007d` → HTTP 200; `center=248.167378,66.755007`
  → HTTP 200; `center=248.167378deg,66.755007d` → **HTTP 422** (unidade repetida).
  A forma do tutorial oficial (`?center=<ra>,<dec>d`) foi verificada em execução real.
- `size`: um ou dois valores (largura em NAXIS1, altura em NAXIS2). Sem unidades → **graus**.
  Unidades: `px`/`pix`/`pixels`, `arcsec`, `arcmin`, `deg`, `rad`. Tamanhos negativos → erro.
- `gzip`: por padrão `true`; **os cutouts do SPHEREx NÃO são gzipped** (exceção documentada
  pela IRSA).
- O recorte herda os mesmos HDUs do arquivo original; `IMAGE`, `FLAGS`, `VARIANCE` e `ZODI`
  são recortados, `WCS-WAVE` é remapeado, e `EPSF`/`PSF` vem **sem modificação**.

Documentação oficial: https://irsa.ipac.caltech.edu/ibe/cutouts.html

**Exemplo real executado com sucesso em 2026-11-14:**

```
https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/level2/2025W19_1B/l2b-v27-2026-197/3/level2_2025W19_1B_0116_1D3_spx_l2b-v27-2026-197.fits?center=133.795129,-7.245147&size=0.02
```

Resposta: HTTP 200, `content-type: application/fits`, **4 037 760 bytes**, 7.2 s.

**URL montada pelo TAP (forma exata do tutorial oficial) — verificada em 2026-11-14:**

```
https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/level2/2025W23_2B/l2b-v27-2026-201/1/level2_2025W23_2B_0206_1D1_spx_l2b-v27-2026-201.fits?center=248.167378,66.755007d&size=0.05
```
→ HTTP 200, `application/fits`, **3 965 760 bytes**, 4.7 s (R Draconis, detector D1,
primeira linha da TAP query do tutorial oficial).

**Comportamento do serviço verificado empiricamente (limitação importante):**

| Situação | Resposta observada |
|---|---|
| Cutout válido (size=0.02) | 200, ~4 MB, FITS válido |
| Cutout válido (size=0.05) | 200, ~4 MB (1ª vez) **ou** `503` + corpo `Server busy, retry later.` (25 bytes) |
| Query malformada | HTTP 400 |
| Recorte sem sobreposição com a imagem | HTTP 500 |

→ **O backend precisa implementar retry/backoff** para `503` e para erros de rede
transientes (`IncompleteRead`, `RemoteDisconnected`), exatamente como o tutorial oficial faz
(`process_cutout_with_error_handling`).

**Alternativa de recorte no cliente:** `astropy.io.fits.Cutout2D` sobre `fits.open(url)`
(remotamente) ou `astropy.utils.data.download_file`. O guia do IBE confirma que o
`Cutout2D` do Astropy pode extrair recortes sem baixar o arquivo completo.

**Custo de banda:** mesmo um recorte de 0.02° (12×12 pixels!) retorna ~4 MB, porque a
extensão `EPSF` (451×11, sobreamostrada) domina o tamanho. Um MEF completo tem ~70 MB.
→ **Recomendação:** o backend deve baixar o cutout e extrair apenas `IMAGE`+`WCS-WAVE`,
descartando `EPSF`/`FLAGS`/`VARIANCE`/`ZODI` quando não forem necessários.

### 3.4 Outros mecanismos de acesso

| Mecanismo | Endpoint | Observação |
|---|---|---|
| Diretórios navegáveis | `https://irsa.ipac.caltech.edu/ibe/data/spherex/{dr1,qr3,qr2}/...` | Sem API; útil para download em lote |
| Nuvem (AWS S3) | `s3://nasa-irsa-spherex/` (região `us-east-1`; prefixos `dr1/`, `qr3/`, `qr2/`) | **Anônimo**, sem credenciais e sem custo de egress |
| Moving Object Search Tool (MOST) | `https://irsa.ipac.caltech.edu/cgi-bin/MOST/nph-most?catalog=spherex&...` | Verificado: devolve `mjd_start`, `mjd_end`, `uri` por imagem. **Projetado para objetos do Sistema Solar** |
| SPHEREx Data Explorer (GUI) | `https://irsa.ipac.caltech.edu/applications/spherex` | GUI oficial, com opções de download e cutout |
| IRSA Viewer / Firefly | `https://irsa.ipac.caltech.edu/irsaviewer` | Interpreta o WCS alternativo do SPHEREx (λ e bandwidth por pixel) |
| IRSA TAP assíncrono | `https://irsa.ipac.caltech.edu/TAP/async` | Apenas para consultas SQL; **não** é um serviço de cutout assíncrono |
| IRSA IBE cutout **assíncrono** | — | **NÃO VERIFICADO / provavelmente inexistente** (ver §16) |

**Serviços do IRSA que NÃO se aplicam ao SPHEREx** (verificado na matriz oficial de
`/docs/program_interface/api_images.html`):

| Serviço | Observação |
|---|---|
| SIA v1 (`/ibe/sia_v1.html`) | Limitado a WISE/2MASS/PTF — **não** cobre SPHEREx |
| Image Server API (`/ibe/ibe_search_api.html`) | Limitado a WISE/2MASS/PTF — **não** cobre SPHEREx |
| Image Cutouts API genérica | WISE/2MASS/PTF — para SPHEREx usar o **IBE cutout** (§3.3) |
| Cutouts "Atlas" (`/applications/Cutouts/...`) | Só Atlas — **não** aplicável |
| Finder Chart API | Sem SPHEREx no conjunto suportado |
| Simple Cone Search (formato antigo, `/ConeSearch`) | **NÃO VERIFICADO** — não consta na doc de imagens do IRSA; **usar SIA2** |

---

## 4. Releases e produtos SPHEREx

### 4.1 Tabela de releases (verificado em 2026-11-14)

| Release | Data de disponibilização | Conteúdo | Buscável por SIA2? | DOI |
|---|---|---|---|---|
| **QR1** | Julho/2025 | Spectral Image MEFs (nível 2) | **NÃO** — aposentado em fev/2026 | 10.26131/IRSA629 |
| **QR2** | Outubro/2025 (reprocessamento do QR1 com calibrações melhoradas) | Spectral Image MEFs (nível 2) | **NÃO** (desde nov/2026, com a saída do DR1). Download direto até fev/2027 | 10.26131/IRSA652 |
| **QR3** | Setembro/2026 | Spectral Image MEFs (nível 2), ePSF e calibrações melhoradas | **SIM** — `spherex_qr3`, `spherex_qr3_deep` | 10.26131/IRSA662 |
| **DR1** | **Novembro/2026** (mês corrente) | Spectral Image MEFs (nível 2, reprocessamento do QR2) **+ All-Sky Cube** | **SIM** — `spherex_dr1`, `spherex_dr1_deep`, `spherex_dr1_cube` | 10.26131/IRSA678 (imagens) / 10.26131/IRSA679 (cube) |

**Fontes:**
- https://irsa.ipac.caltech.edu/Missions/spherex.html (seção "SPHEREx Releases")
- https://irsa.ipac.caltech.edu/data/SPHEREx/docs/overview_qr.html
- https://irsa.ipac.caltech.edu/data/SPHEREx/docs/overview_dr1.html

**FATO CONFIRMADO.** DR1 e QR3 são processados de forma **uniforme** — o guia do arquivo
recomenda explicitamente usar DR1 + QR3 em conjunto. QR2 e QR1 **não devem** ser comparados
com DR1/QR3 sem a correção de fluxo (`l3_flux_corrections`).

**Observação crítica de compatibilidade:** as versões de processamento (`l2b-v<Version>-<Data>`)
variam **entre observações dentro do mesmo release** (ex.: `l2b-v27-2026-197`,
`l2b-v27-2026-228`, `l2b-v27-2026-273`, e variantes `l2b_retry-...`). A chave `VERSION` do
HDU primário registra a versão exata de cada arquivo. Fotometria absoluta entre arquivos com
versões diferentes **não é garantida** — ver §14.

### 4.2 Produto principal — Spectral Image Multi-Extension FITS (MEF), nível 2

Cada observação é um **apontamento único** (exposição individual), **não um mosaico**. Por
apontamento existem até 6 arquivos (um por detector).

Bandas / detectores (valores **reais retornados pelo SIA2** em 2026-11-14):

| Detector | Banda nominal | Cobertura λ real (SIA2 `em_min`–`em_max`) | R real (`em_res_power`) |
|---|---|---|---|
| D1 | 0.75–1.09 µm, R=39 | 0.75–1.12 µm | 39.1 |
| D2 | 1.10–1.62 µm, R=41 | 1.10–1.65 µm | 41.4 |
| D3 | 1.63–2.41 µm, R=41 | 1.63–2.43 µm | 40.6 |
| D4 | 2.42–3.82 µm, R=35 | 2.40–3.85 µm | 34.9 |
| D5 | 3.83–4.41 µm, R=112 | 3.81–4.43 µm | 111.6 |
| D6 | 4.42–5.00 µm, R=128 | 4.41–5.01 µm | 127.8 |

As 6 bandas × 17 canais = **102 canais espectrais**. **Isto NÃO é uma sequência temporal**
(ver §14).

### 4.3 All-Sky Cube (somente DR1)

- Coleção SIA2: `spherex_dr1_cube` (verificado: `DPTYPE=cube`, `calib_level=3`).
- HEALPix order 5 (NESTED), 12 288 tiles de ~1.8°×1.8°, cada tile 512×512 pixels
  (**12.88"/pixel**) em **102 canais**.
- Exemplo real retornado pelo SIA2 para WISE 0855:
  `https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/hips5_cube/hips_20261026/Norder5/Dir10000/Npix10226_cube.fits`
  com `t_min=60789.848`, `t_max=61174.4729` (MJD).
- HDUs: `IMAGE` (512×512×102), `NHITS`, `FLAGS`, `SPECTRAL_CHANNELS`, `WCS-WAVE`.
- **FATO CONFIRMADO:** o cube é um **mosaico único** que agrega todo o intervalo do DR1.
  Ele **não** pode ser usado como sequência temporal (embora o `t_min`/`t_max` span sugira o
  contrário).
- Canais 51 e 52 são vazios (listados em `BLANKCH`); linhas de emissão atmosférica
  (He 1.083 µm) criam listras; projeção HEALPix não é exibida corretamente por muitos
  visualizadores FITS.

### 4.4 Produtos de calibração e ancillary (não buscáveis por SIA2)

Acessíveis apenas por **diretórios navegáveis**
(https://irsa.ipac.caltech.edu/ibe/data/spherex/): `abs_gain_matrix/`, `aurora_template/`,
`dark/`, `dichroic/`, `epsf/`, `gain_factors/`, `l3_flux_corrections/`, `nonfunc_v2/`,
`nonlinear_pars/`, `readnoise_pars/`, `shuttle_glow_template/`, `sip/`,
`solid_angle_pixel_map/`, `spectral_channels/`, `spectral_wcs/`, `xtalk_classN/`,
`zodi_scaling_vN/`, `he_template/`.

**Fonte:** https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access
e https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products
(consultados em 2026-11-14).

---

## 5. Produtos FITS

### 5.1 Estrutura do arquivo (verificada empiricamente)

Leitura direta de um cutout real (`size=0.02`, detector 3), baixado em 2026-11-14:

```
HDU 0  PRIMARY    5 cards  (VERSION='7.0.5' — SSDC Pipelines)
HDU 1  IMAGE      NAXIS1=12 NAXIS2=12 BITPIX=-32   BUNIT='MJy / sr'
HDU 2  FLAGS      NAXIS1=12 NAXIS2=12 BITPIX=32
HDU 3  VARIANCE   NAXIS1=12 NAXIS2=12 BITPIX=-32   BUNIT='MJy2 / sr2'
HDU 4  ZODI       NAXIS1=12 NAXIS2=12 BITPIX=-32   BUNIT='MJy / sr'
HDU 5  EPSF       BinTableHDU NAXIS1=8752 NAXIS2=451
HDU 6  WCS-WAVE   BinTableHDU NAXIS1=1100 NAXIS2=1
```

No arquivo completo (2040×2040), conforme o tutorial oficial:

| HDU | EXTNAME | Tipo | Dimensões | Conteúdo |
|---|---|---|---|---|
| 0 | (primário) | PrimaryHDU | — | `VERSION` (versão do pipeline SSDC, ex.: `'7.0.5'`) |
| 1 | `IMAGE` | ImageHDU | 2040×2040 float32 | brilho de superfície calibrado em **MJy/sr**; **luz zodiacal NÃO subtraída** |
| 2 | `FLAGS` | CompImageHDU | 2040×2040 int32 | bitmap de status/flags por pixel (chaves `MSKNnnnn` / `MSKDnnnn`) |
| 3 | `VARIANCE` | ImageHDU | 2040×2040 float32 | variância em **(MJy/sr)²** |
| 4 | `ZODI` | ImageHDU | 2040×2040 float32 | modelo de luz zodiacal (MJy/sr), **não subtraído** |
| 5 | `EPSF` | BinTableHDU | 441×11 (D1,D2,D4,D5,D6) ou 451×11 (D3) | ePSF 33×33 por zona, sobreamostrada ×5 |
| 6 | `WCS-WAVE` | BinTableHDU | 1×3 | tabela de lookup do WCS espectral (X 9×9, Y 9×9, VALUES (9,9,2)) |

**Convenção de nomes de arquivo:**

```
level2_[Observation ID]D[Detector]_spx_l2b-v[Version]-[Processing Date].fits
ex.: level2_2025W18_2B_0001_1D1_spx_l2b-v12-2025-164.fits
```

- `Observation ID` = período de planejamento + contador de slew grande + contador de slew
  pequeno (ex.: `2025W18_2B_0001_1`). Cada slew grande tem no máximo 4 pequenos.
- `Detector` = inteiro de 1 a 6.
- `Processing Date` = ano + dia-do-ano (ex.: `2025-164`).

### 5.2 WCS

WCS espacial (do tutorial oficial):
`CTYPE = 'RA---TAN-SIP' / 'DEC--TAN-SIP'`, `CRPIX = 1020.5 1020.5`,
matriz `PC1_1/PC1_2/PC2_1/PC2_2`, `CDELT = 1.0 1.0`, `CUNIT='deg'`.
WCS alternativos: `WCSNAMEA` = "0-based active pixel coordinates";
`WCSNAMEW` = "Approximated per-pixel wavelength and bandwidth" (aponta para `WCS-WAVE`).

Para obter λ por pixel (do tutorial oficial):
```python
spectral_wcs = WCS(header=hdulist["IMAGE"].header, fobj=hdulist, key="W")
spectral_wcs.sip = None          # desligar SIP no WCS espectral
wavelength, bandwidth = spectral_wcs.pixel_to_world(x, y)
```
**⚠** muitos readers FITS ainda não implementam o WAVE-TAB lookup table; usar interpolação
bilinear manual sobre X/Y/VALUES (~1 nm de acurácia) ou o produto `spectral_wcs`
(`CWAVE`/`CBAND`) para análise científica.

### 5.3 Biblioteca prevista para investigação

**Astropy** — validada: `fits.open(url)` com `memmap=False`, `hdulist.info()`, leitura das
7 extensões, `WCS(header, fobj=hdulist, key="W")`, `Cutout2D` remoto.
Requisito crítico: `from astropy.utils.data import conf; conf.remote_timeout = 120`.

---

## 6. Ferramentas e bibliotecas

| Ferramenta | Finalidade prevista | Situação |
|---|---|---|
| Astropy | Leitura FITS, WCS e operações astronômicas | **Validada** (estrutura real lida em 2026-11-14) |
| Astroquery (`astroquery.ipac.irsa`) | Consultas a arquivos astronômicos (`query_sia`, `query_tap`, `list_collections`) | **Validada** (procedimento do tutorial oficial) |
| PyVO | Comunicação com serviços VO, incluindo SIA2 | A validar (alternativa de baixo nível ao astroquery) |
| NumPy | Operações numéricas e processamento | A validar |
| FastAPI | Disponibilização dos resultados pela API | Planejada (fora do escopo desta pesquisa) |
| `boto3` / `s3fs` | Acesso anônimo ao bucket `nasa-irsa-spherex` | A validar (bucket, região e prefixos confirmados) |
| `firefly-client` | Visualização interativa do WCS espectral | **Validada** (tutorial oficial) |
| `astropy.times` | Conversão MJD → UTC (`Time(mjd, format='mjd', scale='utc')`) | A validar (mapeamento MJD↔`DATE-OBS` confirmado) |

A escolha definitiva das bibliotecas de consulta dependerá da compatibilidade com os serviços
oficiais — **já confirmada** para astroquery + astropy.

---

## 7. Fontes complementares

### 7.1 Gaia

https://archive.stsci.edu/missions-and-data/gaia

Página institucional (NASA/STScI + ESA). A própria página lista o **GAIA Archive @ ESA**
como ferramenta de busca oficial.

**Endpoint TAP usado nesta pesquisa (VERIFICADO em 2026-11-14):**

```
https://gea.esac.esa.int/tap-server/tap/sync?REQUEST=doQuery&LANG=ADQL&FORMAT=csv&QUERY=<ADQL>
```

Consulta usada (modelo ADQL padrão):
```sql
SELECT source_id,ra,dec,ra_error,dec_error,parallax,parallax_error,
       pmra,pmra_error,pmdec,pmdec_error,ref_epoch,phot_g_mean_mag,ruwe
FROM gaiadr3.gaia_source
WHERE CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',269.448503,4.739420,0.001))=1
```

**Observações:**
- `ref_epoch` = **2016.0** para todas as fontes Gaia DR3 — as coordenadas catalogadas
  **não** são a posição atual do objeto.
- `pmra` é **μ(α\*)** (já multiplicado por cos δ), em mas/ano; `pmdec` é μ(δ), em mas/ano.
- O IRSA também hospeda a mesma tabela (`gaia_dr3_source`) no seu TAP — útil para manter o
  backend em um único host.
- Em várias buscas a fonte não aparece no raio pequeno esperado (Barnard a 0.0006°,
  ε Indi a 0.0006°): **é preciso um raio compatível com o deslocamento por movimento
  próprio acumulado desde 2016.0**.

**Não faz parte do MVP inicial** para a interface, mas **é essencial** para o teste de
movimento próprio (Barnard, WISE 0855).

### 7.2 WiseView

http://byw.tools/wiseview

Possível utilização (apenas como **referência de experiência de usuário**):
- Navegação temporal entre imagens.
- Controles de visualização (zoom, contraste, canal/banda).
- Comparação entre épocas.
- Reprodução de uma sequência de imagens.

**Não substitui os dados oficiais do SPHEREx** e **nunca deve ser usado como fonte de
observações SPHEREx.** Observação de método: o WISE é um survey **não repetido** no tempo,
de modo que sua "navegação temporal" é uma metáfora visual; no SPHEREx o tempo é um eixo
**físico real** dos dados.

---

## 8. Registro de fontes

Toda descoberta científica deverá registrar: nome, instituição responsável, endereço
eletrônico, data de consulta, data de publicação/release, informação obtida, evidência,
limitações e tarefas do projeto que usam a informação.

### 8.1 Fontes oficiais consultadas (data de consulta: **2026-11-14**)

| # | Fonte | Instituição | URL | Evidência extraída |
|---|---|---|---|---|
| F1 | SPHEREx Archive at IRSA | NASA/IPAC Caltech | https://irsa.ipac.caltech.edu/Missions/spherex.html | Releases, ferramentas, serviços, papers canônicos |
| F2 | SPHEREx DR1 Overview | NASA/IPAC Caltech | https://irsa.ipac.caltech.edu/data/SPHEREx/docs/overview_dr1.html | DOI, produtos, vias de acesso |
| F3 | SPHEREx Quick Release Overview | NASA/IPAC Caltech | https://irsa.ipac.caltech.edu/data/SPHEREx/docs/overview_qr.html | Ciclo de vida QR1/QR2/QR3, aposentar QR2 |
| F4 | SPHEREx Archive User Guide (12/11/2026) | NASA/IPAC Caltech | https://caltech-ipac.github.io/spherex-archive-documentation/ | Estrutura, releases |
| F5 | SPHEREx Data Products | NASA/IPAC Caltech | https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products | HDUs, nomes de arquivo, ePSF, cube |
| F6 | SPHEREx Data Access | NASA/IPAC Caltech | https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access | Endpoints SIA2/TAP/cutout, coleções |
| F7 | IRSA SIA v2 queries | NASA/IPAC Caltech | https://irsa.ipac.caltech.edu/ibe/sia.html | Parâmetros, sintaxe, colunas |
| F8 | IRSA Querying/Downloading Images | NASA/IPAC Caltech | https://irsa.ipac.caltech.edu/docs/program_interface/api_images.html | Matriz de APIs, o que não se aplica |
| F9 | IRSA Program Interfaces | NASA/IPAC Caltech | https://irsa.ipac.caltech.edu/voapi.html | Índice de APIs |
| F10 | IRSA IBE Cutouts | NASA/IPAC Caltech | https://irsa.ipac.caltech.edu/ibe/cutouts.html | Sintaxe `center`/`size`/`gzip` |
| F11 | IRSA Cloud Data Access | NASA/IPAC Caltech | https://irsa.ipac.caltech.edu/cloud_access/#spherex | Bucket S3, prefixos |
| F12 | IRSA MOST API | NASA/IPAC Caltech | https://irsa.ipac.caltech.edu/applications/MOST/MOSTProgramInterface.html | `catalog=spherex` |
| F13 | IRSA Tutorials — SPHEREx (índice) | NASA/IPAC Caltech | https://caltech-ipac.github.io/irsa-tutorials/spherex/ | Lista de tutoriais |
| F14 | Tutorial: Introduction to SPHEREx Spectral Images | NASA/IPAC Caltech | https://caltech-ipac.github.io/irsa-tutorials/spherex-intro/ | Procedimento SIA2, WCS, flags |
| F15 | Tutorial: Spectral Image Cutouts | NASA/IPAC Caltech | https://caltech-ipac.github.io/irsa-tutorials/spherex-cutouts/ | Procedimento TAP, paralelismo |
| F16 | Gaia DR3 — MAST/ESA | ESA / STScI | https://archive.stsci.edu/missions-and-data/gaia | Página institucional |
| F17 | ESA Gaia Archive TAP | ESA | https://gea.esac.esa.int/tap-server/tap/sync | Astrometria DR3 (consultas ADQL) |
| F18 | IRSA TAP `gaia_dr3_source` | NASA/IPAC Caltech | https://irsa.ipac.caltech.edu/TAP/sync | Tabela Gaia DR3 espelhada no IRSA |
| F19 | SPHEREx PSF header error | NASA/IPAC Caltech | https://irsa.ipac.caltech.edu/data/SPHEREx/docs/psfhdrerr.html | Erro de header PSF (QR anterior a 31/03/2026) |
| F20 | SPHEREx Explanatory Supplement (PDF) | NASA/IPAC Caltech | https://irsa.ipac.caltech.edu/data/SPHEREx/docs/SPHEREx_Expsupp.pdf | Referência normativa (Tabela 16 = flags) |

### 8.2 Fontes complementares (justificadas)

| Fonte | Finalidade | Justificativa | Data |
|---|---|---|---|
| Wikipedia (EN) — "Barnard's Star", "Epsilon Indi", "RW Aurigae", "WISE 0855−0714", "List of stars in Draco", "Mira variable" | Obter coordenadas **J2000** e identificadores de catálogo (HD/HIP) como *seed* para a consulta ao Gaia DR3 | O ambiente de pesquisa só alcança `irsa.ipac.caltech.edu`, `gea.esac.esa.int`, `caltech-ipac.github.io` e `en.wikipedia.org`; SIMBAD/VizieR/ADS/MAST-CasJobs **não** são acessíveis (verificado). Wikipedia foi usada **apenas** como fonte secundária de coordenadas, e **todas** as posições foram reconferidas no Gaia DR3 | 2026-11-14 |
| Wikidata (Q12775006 = R Draconis) | Identificadores HD 149880 / HIP 81014 de R Dra | Mesmo motivo | 2026-11-14 |

> **Transparência:** os valores de paralaxe e movimento próprio de WISE 0855 vêm da infobox
> da Wikipedia, que cita Kirkpatrick et al. (2021). **Não foi possível** confirmar esses
> dois números contra o artigo primário (ADS inacessível neste ambiente). O achado crítico
> sobre o Gaia DR3 (§13 e `docs/science/target-catalog.md` §3.3) **foi** verificado
> diretamente no serviço do ESA.

---

## 9. Critérios de utilização

Antes de utilizar qualquer conjunto de dados:

1. Confirmar sua origem. ✔ (§8)
2. Identificar o produto. ✔ (§4)
3. Verificar a documentação. ✔ (§3, §4, §5)
4. Identificar sua cobertura temporal e espacial. ✔ (§13)
5. Examinar os metadados. ✔ (§12)
6. Verificar as condições de utilização. ✔ (§16)
7. Registrar limitações. ✔ (§14)
8. Confirmar sua adequação ao objetivo científico. ✔ (§13, §14)

---

## 10. Pendências de pesquisa

**Todas as 7 pendências originais foram respondidas em 2026-11-14.** Detalhamento e
resultados em §16. Resumo:

- [x] **Confirmar os serviços oficiais de consulta.** → SIA2, TAP, IBE Cutout, diretórios,
      S3, MOST, GUI. Seção 3.
- [x] **Identificar os endpoints SIA2 aplicáveis.** →
      `https://irsa.ipac.caltech.edu/SIA?` com `COLLECTION=spherex_dr1|spherex_dr1_deep|spherex_dr1_cube|spherex_qr3|spherex_qr3_deep`. Seção 3.1.
- [x] **Consultar produtos SPHEREx disponíveis.** → 5 coleções ativas (DR1 + QR3). Seção 4.
- [x] **Investigar os releases relevantes.** → QR1/QR2/QR3/DR1, com datas, DOIs e status de
      busca. Seção 4.1.
- [x] **Examinar um arquivo FITS real.** → cutout real baixado e analisado HDU a HDU;
      keywords de época confirmadas. Seções 5.1 e 13.
- [x] **Identificar os metadados necessários.** → 51 colunas do SIA2 + 7 HDUs FITS +
      tabelas TAP. Seções 13 e 5.
- [x] **Testar a recuperação de um recorte.** → HTTP 200, FITS válido, 4 037 760 bytes;
      comportamento `503` documentado. Seção 3.3.
- [x] **Documentar as condições de utilização dos dados.** → Seção 16.

---

## 11. Consultas espaciais (cone search) — sintaxe

**Parâmetro:** `POS`. **Unidade:** graus decimais, sistema **ICRS**.

**Formas aceitas (da especificação SIA2 do IRSA):**

```
POS=circle   <ra> <dec> <raio_em_graus>
POS=polygon <ra1> <dec1> <ra2> <dec2> ... <raN> <decN>
POS=range   <ra1> <ra2> <dec1> <dec2>
```

Exemplos (todos documentados na especificação e verificados no serviço):
```
POS=circle+133.795129+-7.245147+0.05
POS=polygon+164+-5+165+-5+165+-6+164+-6
POS=range+104+105+-22+-12
```

**Semântica:** a consulta seleciona **todas as imagens que intersectam** a forma — não
exige que o centro da imagem esteja dentro da forma. O predicado espacial é avaliado sobre
polígonos convexos esféricos; implementações em ponto flutuante implicam que os resultados
não são matematicamente exatos.

**Raio mínimo prático para o SPHEREx:** as imagens têm FOV de **3.485°** de lado
(`s_fov`), com pixel de 6.15". Um raio de 0.05°–0.2° já garante a cobertura de qualquer
alvo; o raio define o **conjunto de imagens candidatas**, não o recorte.

**UPLOAD:** permite múltiplas posições numa única requisição, via `UPLOAD=nome,URI` e
`POS=CIRCLE tabela.ra tabela.dec raio`. Requer `POS=CIRCLE` ou `POS=RANGE` (não funciona com
POLYGON). Formatos aceitos: VOTable, CSV, TSV, IPAC_TABLE. **Não testado empiricamente
neste ambiente** (documentado na especificação).

**CLOSEST:** agrupa os resultados e devolve, por grupo, apenas a imagem de menor distância ao
centro. Só funciona com `POS=CIRCLE`. Cada grupo pode ser `COLLECTION`, `FACILITY`,
`INSTRUMENT`, `DPTYPE`, `TARGET` ou `FORMAT`. **Verificado com `CLOSEST=COLLECTION`.**

---

## 12. Épocas e metadados

### 12.1 Como identificar a ÉPOCA DE OBSERVAÇÃO

**Palavras-chave FITS (verificadas empiricamente em um arquivo real baixado):**

Presentes nas extensões `IMAGE`, `FLAGS`, `VARIANCE` e `ZODI`:

| Keyword | Conteúdo | Exemplo real |
|---|---|---|
| `DATE-OBS` | início da exposição, UTC (ISO) | `2025-05-05T16:48:02.459` |
| `MJD-OBS` | MJD do início | `60800.700028461` |
| `DATE-BEG` / `MJD-BEG` | idem `DATE-OBS` | `2025-05-05T16:48:02.459` / `60800.700028461` |
| `DATE-AVG` / `MJD-AVG` | ponto médio | `2025-05-05T16:49:00.018` / `60800.70069465` |
| `DATE-END` / `MJD-END` | fim | `2025-05-05T16:49:57.577` / `60800.701360839` |
| `TIMESYS` | escala de tempo | `UTC` |
| `MJDREF` | referência MJD | `0.0` |
| `OBSID` | ID da observação | `2025W19_1B_0116_1` |
| `EXPIDN` | ID inteiro da exposição | `202519102011613` |
| `DETECTOR` | 1..6 | `3` |
| `RADESYS` | sistema de coordenadas | `ICRS` |
| `PSF_FWHM` | FWHM da PSF em arcsec | `7.448130062949859` |
| `SPS_TARGET` | ID do alvo do Survey Planning | `SPS_119395_S12` |
| `SPS_FLAGS` | flags do planejamento | `all_sky ` |
| `L2 N_*` (HIERARCH) | contadores de pixels por flag | `L2 N_SOURCE = 4135535`, `L2 N_PERSIST = 23502`, … |

**⚠ ARMADILHA CONFIRMADA:** a keyword `DATE` do cabeçalho FITS é o **momento de criação do
HDU** (`2026-07-17T10:16:06.188` para uma exposição de 2025-05-05). **Não é a data de
observação.** O mesmo cabeçalho traz `DATE-OBS` correto.

**Onde a época aparece nos serviços:**

| Serviço | Campo | Valor |
|---|---|---|
| SIA2 | `t_min` | = `MJD-BEG` = `MJD-OBS` (dias MJD) |
| SIA2 | `t_max` | = `MJD-END` (dias MJD) |
| SIA2 | `t_exptime` | ~113.58 s |
| SIA2 | `obs_release_date` | data de **publicação** no arquivo — **não** é época |
| SIA2 | `obs_id` | ID da observação (período de planejamento + contadores de slew) |
| TAP | `spherex.plane.time_bounds_lower` | = `t_min` |
| TAP | `spherex.plane.time_bounds_upper` | = `t_max` |
| TAP | `spherex.plane.energy_bandpassname` | `SPHEREx-D1`…`D6` (detector) |

**Verificação cruzada executada:** para o arquivo
`level2_2025W19_1B_0116_1D3_spx_l2b-v27-2026-197.fits`, o SIA2 retornou
`t_min=60800.700028`, `t_max=60800.701361`; o cabeçalho FITS retornou
`MJD-OBS=60800.700028461`, `MJD-END=60800.701360839`. **Coincidem.** O mesmo `t_min` foi
confirmado via TAP (`time_bounds_lower=60902.864715` para Barnard D3, idêntico ao SIA2).

### 12.2 Metadados de um produto

Três caminhos, todos verificados:

1. **SIA2** — a linha de resultado já contém 51 campos de metadados (§3.1), incluindo
   `access_url`, `obs_id`, `energy_bandpassname`, `em_min`/`em_max`/`em_res_power`,
   `s_pixel_scale`, `s_fov`, `t_min`/`t_max`, `t_exptime`, `obs_publisher_did`,
   `target_name`, `cloud_access`.
2. **TAP** — `spherex.plane` + `spherex.artifact` + `spherex.observation` +
   `spherex.obscore` (metadados mais ricos, e ~1 dia mais fresco).
3. **Cabeçalho FITS** — via HTTP range request ou `astropy.io.fits.open(url)`:
   `astropy.utils.data.conf.remote_timeout = 120` é obrigatório.

### 12.3 Qualidade — indicadores disponíveis

- Por produto (SIA2): `calib_level=2`, `dataproduct_subtype=science`,
  `dataproduct_type=image`, `algorithm_name=exposure`, `obs_intent=science`,
  `target_type=field`, `target_standard=0`, `target_moving=0`.
- No FITS: `L1DQAFLG='Pass'`, contadores `L2 N_*` por flag, bitmask `MSKN*`/`MSKD*`
  (TRANSIENT, OVERFLOW, SUR_ERROR, NONFUNC, DICHROIC, MISSING_DATA, HOT, COLD,
  FULLSAMPLE, PHANMISS, NONLINEAR, PERSIST, OUTLIER, CROSSTALK, SOURCE, GHOST, GHOST_FPA,
  GHOST_EXT, STREAK, BLOOM, SNOWBALL, HALO).
- **Vazio e inutilizável para SPHEREx:** `s_resolution` (ver §14), `t_resolution`,
  `em_xel`, `pol_states`, `pol_xel`, `target_keywords`.

---

## 13. Existe sequência temporal? — TESTE DA HIPÓTESE CENTRAL

**FATO CONFIRMADO: SIM.** A hipótese central do projeto foi testada empiricamente contra o
serviço SIA2 real.

**Método:** `POS=circle <RA> <Dec> 0.05` sobre as 4 coleções ativas
(`spherex_dr1`, `spherex_qr3`, `spherex_dr1_deep`, `spherex_qr3_deep`), contando
**épocas distintas** (`t_min` distintos) e separando por detector.

**Resultados (2026-11-14):**

| Objeto | produtos (linhas SIA2) | **épocas distintas (todas as bandas)** | épocas por banda | Cobertura temporal |
|---|---|---|---|---|
| Estrela de Barnard | 378 | **192** | 60–67 | 2025-08-15 → 2026-09-22 (13.2 meses) |
| Epsilon Indi A | 524 | **273** | 50–122 | 2025-04-24 → 2026-10-02 (17.3 meses) |
| WISE 0855 | 282 | **143** | 45–50 | 2025-05-05 → 2026-05-14 (12.3 meses) |
| RW Aurigae A | 342 | **172** | 57 | 2025-09-01 → 2026-09-16 (12.3 meses) |
| R Draconis | 2587 | **1309** | 94–603 | 2025-04-24 → 2026-09-27 (15.7 meses) |

**Estrutura temporal (verificada):**
- Cada **época** (`t_min` distinto) é **uma exposição de UM detector**. Exposições
  consecutivas dentro de uma mesma "visita" estão separadas por ~2 minutos (pequenos slews).
- **Discretização por banda** (ex.: Barnard D3): 61 épocas, das quais **14 separadas por
  ≥ 1 dia**, separação mediana **2.8 dias**, máximo **203.8 dias**.
  R Dra (campo profundo) D1: 599 épocas, 67 separadas por ≥ 1 dia, mediana 1.8 d, máx 227.8 d.
- **DR1 e QR3 são temporalmente disjuntos**: DR1 cobre MJD 60789.88–61173.25
  (2025-04-24 → 2026-05-13); QR3 cobre MJD 61176.36–61237.87 (2026-06-01 → 2026-09-27);
  `spherex_dr1_deep` 60789.88–61166.53; `spherex_qr3_deep` 61231.97–61310.29
  (→ 2026-09-27). **Não há sobreposição** → comparar DR1 com QR3 é temporalmente limpo.
- **WISE 0855 só aparece em `spherex_dr1`** na janela testada (0 linhas em QR3).
  → É obrigatório consultar as duas coleções para não perder a sequência.
- **R Draconis está num DEEP FIELD** (`spherex_dr1_deep` + `spherex_qr3_deep`): 4× mais
  produtos que a média.

**Distinções que a aplicação DEVE respeitar:**

1. **102 canais espectrais ≠ sequência temporal.** As 6 bandas/102 canais coexistem
   **dentro de cada imagem**. Uma única imagem já contém os 102 canais do detector. A
   sequência temporal vem de **exposições distintas em instantes distintos** (`t_min`
   diferentes), não de canais diferentes.
2. **Mudança de brilho ≠ movimento.** A variação de brilho é medida **entre épocas** para a
   **mesma banda** (mesmo detector), com correção de calibração.
3. **Ausência de observação ≠ ausência do objeto.** Se um detetor/canal não está coberto
   numa certa data, isso é uma limitação de agendamento, não do objeto.
4. **Diferença de processamento ≠ mudança física.** DR1 e QR3 são reprocessamentos
   diferentes (ganho, PSF). Comparação fotométrica absoluta entre DR1 e QR3 exige o
   produto `l3_flux_corrections` e atenção ao `VERSION`.

---

## 14. Limitações

### 14.1 Limitações do instrumento e dos produtos

| Aspecto | Valor / situação | Fonte |
|---|---|---|
| Escala de pixel | **6.15"/pixel** (`s_pixel_scale`), imagens 2040×2040 | SIA2 verificado |
| FOV | **3.485°** de lado (`s_fov`) | SIA2 verificado |
| FWHM da PSF | **~7.45"** (D3, medido em arquivo real: `PSF_FWHM=7.448`); ~7.53" no D1 (tutorial) | cabeçalho FITS |
| Amostragem | PSF (~7.5") maior que o pixel (6.15") → **subamostrada** (~1.2 px) | derivado |
| `s_resolution` do SIA2 | 3.075" = metade do pixel — **não** é o FWHM | derivado do SIA2 |
| Luz zodiacal | **NÃO subtraída** no HDU `IMAGE`; modelo no HDU `ZODI` | User Guide |
| Canais do cube | 51 e 52 **vazios** (`BLANKCH`) | User Guide |
| Listras no cube | linhas de emissão atmosférica (He 1.083 µm) e de fontes com linhas fortes | User Guide |
| Projeção do cube | HEALPix (HPX) — muitos visualizadores FITS não exibem corretamente | User Guide |
| Orientação das imagens | **Não é north-up**; eixos seguem a orientação da nave | doc do IBE |
| Distorção | SIP presente no WCS; muitos visualizadores ignoram | tutorial oficial |
| ePSF | 33×33 sobreamostrada ×5; D3 tem zona 11×41 (demais 21×21) | User Guide |
| Artefatos catalogados | TRANSIENT, OVERFLOW, SUR_ERROR, NONFUNC, DICHROIC, MISSING_DATA, HOT, COLD, FULLSAMPLE, PHANMISS, NONLINEAR, PERSIST, OUTLIER, CROSSTALK, SOURCE, GHOST, GHOST_FPA, GHOST_EXT, STREAK, BLOOM, SNOWBALL, HALO | tutorial oficial (bitmask `MSKN*`) |
| Versões de processamento | variam dentro do release (`l2b-v27-2026-197`, `-228`, `-273`, `l2b_retry-...`) | observação direta |
| Tempo de exposição | ~113.58 s por exposição | SIA2 `t_exptime` |

### 14.2 Limitações dos serviços

| Limitação | Evidência |
|---|---|
| **SIA2 tem defasagem de ~1 dia** em relação à ingestão semanal | Guide + tutorial |
| **Cutout pode devolver `503 "Server busy, retry later."`** | observado em 2026-11-14 |
| Cutouts SPHEREx **não são gzipped** | doc do IBE |
| Cutout de 0.02° ainda tem ~4 MB (dominado pelo `EPSF`) | medido |
| SIA2 tem ~1 bilhão de registros → **consultas sem restrição expiram** | doc do IRSA |
| Jobs SIA2 > 5 min são cancelados | doc do IRSA |
| `MAXREC` default é ilimitado | doc do IRSA |
| TAP sem filtro espacial pode ser lento (medido: 18.5 s para a consulta filtrada do tutorial) | medido |
| Recortes fora da imagem → HTTP 500 | doc do IBE |
| Leitura FITS remota precisa `remote_timeout=120` | tutorial oficial |

### 14.3 Limitações astronômicas para os alvos de teste

- **Resolução ~7.45" FWHM**: sistemas binários separados por menos de ~10" **não são
  resolvidos** pelo SPHEREx (ex.: ε Indi A/B ≈ 6.5"; RW Aur A/B = **1.49"**, medido do Gaia).
- **Alvos de baixo brilho**: no infravermelho próximo (1–2.5 µm) estrelas anãs vermelhas
  fracas e anãs marrons podem estar abaixo do limite de detecção em banda larga.
- **Campo profundo**: R Dra está num Deep Field → photometria diferente da Wide Survey.
- **Propagação astrométrica é responsabilidade da aplicação**: o SPHEREx não marca alvos
  com movimento próprio (`target_moving = 0`) e nenhum serviço do IRSA propaga posições de
  alvos estelares.

---

## 15. Tutoriais oficiais (procedimentos exatos)

Fonte: https://caltech-ipac.github.io/irsa-tutorials/spherex/ — **consultados em 2026-11-14**.

| # | Tutorial | O que demonstra |
|---|---|---|
| 1 | **Introduction to SPHEREx Spectral Images** (`/spherex-intro/`) | 1) Buscar Spectral Image MEFs que sobrepõem uma coordenada com `Irsa.query_sia(pos=..., collection=['spherex_dr1','spherex_qr3'])`; 2) abrir com Astropy e mapear as 7 extensões; 3) visualizar no Firefly; 4) WCS espacial (`CTYPE TAN-SIP`), WCS espectral (`key="W"`, `sip=None`), mapa de λ por pixel; 5) ler `L2 N_*` e o bitmask `MSKN*`/`MSKD*` do FLAGS; 6) `PSF_FWHM`. **Atualizado em 5/03/2026.** |
| 2 | **Download a collection of SPHEREx Spectral Image cutouts as a multi-extension FITS file** (`/spherex-cutouts/`) | 1) Consulta **TAP** em `spherex.artifact` ⋈ `spherex.plane` filtrando por `CONTAINS(POINT(...), p.poly)` e `p.energy_bandpassname`, **ordenada por `p.time_bounds_lower`**; 2) montar a URL de cutout (`'https://irsa.ipac.caltech.edu/' || a.uri || '?center=..d&size=..'`); 3) `process_cutout()` com retry; 4) série vs. paralelo (`ThreadPoolExecutor`, **7–12 workers** para 8 cores); 5) empacotar tudo num MEF único com HDU `CUTOUT_INFO` (`observation_date`, `central_wavelength`, `version`, `access_url`). **Atualizado em 5/03/2026.** |
| 3 | **Understanding and Extracting the ePSF Extension in a SPHEREx Cutout** (`/spherex-psf/`) | Como localizar a zona do ePSF (21×21 para D1/D2/D4/D5/D6; 11×41 para D3) e extrair a ePSF 33×33 sobreamostrada ×5. Atenção ao offset 1-based (FITS) vs 0-based (Astropy) via `CRPIX1A`/`CRPIX2A`. |
| 4 | **SPHEREx Source Discovery Tool IRSA Demo** (`/spherex-source-discovery-tool-demo/`) | Detectar e caracterizar fontes numa região **sem a priori posicional**, usando apenas dados SPHEREx. Relevante para o teste de detecção do alvo. |
| 5 | **Understanding and Analyzing SPHEREx Mosaic Cubes** (`/spherex-mosaic/`) | Cubos mosaicados multi-λ gerados pela **IRSA Mosaic Tool** (`/applications/spherex/tool-mosaic`) a partir das Spectral Images. |
| 6 | **Using SPHEREx HiPS All-Sky Mosaic Cubes** (`/spherex-hipscube/`) | Explorar o All-Sky Cube (DR1) no Firefly, baixar os tiles FITS e extrair um espectro rápido. **Atenção:** PNGs HiPS têm faixa fixa 0–40 MJy/sr — usar os FITS para ciência. |

**Regras que os tutoriais impõem e que o backend deve seguir:**
- `conf.remote_timeout = 120` (Astropy).
- Retry com backoff para erros de rede transitórios; **pular** o cutout que falhou.
- `cache=False` se o volume cacheado for grande.
- Paralelismo limitado a **7–12 workers** para não sobrecarregar o IRSA.
- Preservar o `VERSION` de cada arquivo ao combinar vários cutouts num MEF.

---

## 16. Condições de utilização, citação e pendências residuais

### 16.1 Acesso e reutilização (FATO CONFIRMADO)

- Os produtos SPHEREx são **gratuitamente acessíveis** sem restrições de acesso:
  - via HTTPS (IRSA IBE), **e**
  - via AWS S3 **anônimo** (bucket `nasa-irsa-spherex`, região `us-east-1`, prefixes
    `dr1/`, `qr3/`, `qr2/`), sem credenciais e **sem custo de egress**
    (AWS Open Data Sponsorship Program). Fonte: https://irsa.ipac.caltech.edu/cloud_access/#spherex
- O guia do arquivo e a página de missões do IRSA **não enunciam** uma licença restritiva
  específica; o uso segue as condições gerais do IRSA e da NASA. **A verificar pela
  liderança científica.**

### 16.2 Citação obrigatória (texto exato fornecido pelo IRSA)

> *"This publication makes use of data products from the Spectro-Photometer for the History
> of the Universe, Epoch of Reionization and Ices Explorer (SPHEREx), which is a joint
> project of the Jet Propulsion Laboratory and the California Institute of Technology, and
> is funded by the National Aeronautics and Space Administration."*

**DOIs a citar conforme o produto usado:**
`10.26131/IRSA678` (DR1 Spectral Images) · `10.26131/IRSA679` (DR1 All-Sky Cube) ·
`10.26131/IRSA662` (QR3) · `10.26131/IRSA652` (QR2) · `10.26131/IRSA629` (QR1).

### 16.3 Pendências residuais (bloqueadas ou fora do escopo desta etapa)

- [ ] **Cutout assíncrono via IRSA.** O serviço de cutout do IRSA é **síncrono**
      (devolve o FITS diretamente). Não foi encontrado na documentação um endpoint de
      cutout **assíncrono** no IRSA; o TAP assíncrono (`/TAP/async`) serve apenas para
      consultas SQL. **Não verificado** se há fila assíncrona de cutouts.
      *Impacto no MVP: baixo — o cutout síncrono é aceitável, com retry.*
- [ ] **Endpoint "Simple Cone Search"** no formato antigo (`/ConeSearch?...`):
      **NÃO VERIFICADO** — não consta da documentação de imagens do IRSA (§3.4).
      **Recomendação: usar SIA2.**
- [ ] **Limites de taxa (rate limits) numéricos** do SIA2/TAP/cutout: **NÃO VERIFICADOS**
      (não há números publicados). Documentado apenas o retorno `503 "Server busy"`.
- [ ] **Tamanho máximo de recorte:** **NÃO VERIFICADO** (não publicado). Observado: 0.05°
      chegou a ser aceito. Recomenda-se manter recortes pequenos (≤ 0.2°).
- [ ] **Fotometria real** (extração de fluxo em um recorte real) — **não executada** nesta
      etapa; a detectabilidade dos alvos por banda permanece **não verificada**.

---

## 17. Recomendações técnicas (para o Developer)

1. **SIA2 como consulta principal** (`https://irsa.ipac.caltech.edu/SIA?`), sempre com as
   **4 coleções** (`spherex_dr1`, `spherex_qr3`, `spherex_dr1_deep`, `spherex_qr3_deep`).
   `RESPONSEFORMAT=CSV` para backend (leve) e `VOTABLE` para reproduzir a doc.
2. **TAP como alternativa/complemento** (`/TAP/sync?...&FORMAT=csv`) — mais fresca (~1 dia de
   vantagem sobre o SIA2) e já devolve a URL de cutout pronta e ordenada por tempo.
   A ordenação cronológica estável vem de `p.time_bounds_lower`.
3. **Época = `t_min`/`time_bounds_lower`** (MJD). Converter para UTC com
   `astropy.time.Time(mjd, format='mjd', scale='utc')`.
   **Nunca** usar `obs_release_date` nem a keyword FITS `DATE`.
4. **Recorte**: `access_url + "?center={ra},{dec}d&size={size}"`.
   Implementar retry com backoff para `503` e erros de rede; limitar a 7–12 downloads
   simultâneos; `astropy.utils.data.conf.remote_timeout = 120`.
   Extrair apenas `IMAGE` (+ `WCS-WAVE`) para não arrastar os ~4 MB do `EPSF`.
5. **Propagar a posição do alvo para a época de cada observação** antes de recortar ou
   detectar (ver `docs/science/target-catalog.md` — WISE 0855 desloca ~207" entre J2000 e
   as épocas SPHEREx; Barnard desloca ~100–112").
6. **Separar "banda" (detector) de "época"** na modelagem de dados: a chave de um item da
   sequência deve ser `(detector, t_min)`, e a série temporal por banda é o subconjunto com
   `detector` fixo e `t_min` distinto.
7. **Metadados a exibir por frame**: `t_min`/`t_max` (MJD + ISO UTC), `obs_id`,
   `energy_bandpassname`, `em_min`/`em_max`/`em_res_power`, `s_pixel_scale`, `s_fov`,
   `calib_level`, `obs_collection`, `target_name`, `access_url`, `cloud_access`,
   `obs_publisher_did`, `t_exptime`, `VERSION` (do cabeçalho).
8. **Nunca** usar `s_resolution` como resolução; usar `PSF_FWHM` (~7.45") ou
   `s_pixel_scale` (6.15").
9. **Normalização visual por frame** (ou por banda): R Dra varia ~6.5 mag em V — um
   *stretch* fixo tornará a sequência ilegível.
