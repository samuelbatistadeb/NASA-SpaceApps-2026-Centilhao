# Catálogo de objetos de teste

## 1. Objetivo

Registrar os objetos astronômicos utilizados para testar a aplicação e documentar as informações necessárias para localizar e validar suas observações no arquivo SPHEREx.

Os objetos foram indicados no contexto do desafio.

A presença de um objeto neste catálogo não significa que já existam observações SPHEREx adequadas para ele.

> **Estado da pesquisa (consulta em 2026-11-14).** Todas as coordenadas, épocas e
> movimentos próprios abaixo foram obtidos do **Gaia DR3** (fonte primária, consultada
> diretamente no serviço TAP do ESA) e depois **verificados contra o arquivo SPHEREx** por
> consultas reais ao SIA2 do IRSA. Itens não verificáveis estão marcados como
> **NÃO VERIFICADO**.

### 1.1 Fontes astrométricas

| Sigla | Fonte | Instituição | Endpoint | Data de consulta |
|---|---|---|---|---|
| **G3** | Gaia DR3, tabela `gaiadr3.gaia_source` | ESA (via GAIA Archive @ ESA, listado como ferramenta de busca oficial em archive.stsci.edu/missions-and-data/gaia) | `https://gea.esac.esa.int/tap-server/tap/sync?REQUEST=doQuery&LANG=ADQL&FORMAT=csv&QUERY=...` | 2026-11-14 |
| **G3-IRSA** | Gaia DR3 espelhado no IRSA (mesma tabela `gaia_dr3_source`) | NASA/IPAC Caltech | `https://irsa.ipac.caltech.edu/TAP/sync?...` | 2026-11-14 |
| **SX** | Arquivo SPHEREx no IRSA (SIA2) | NASA/IPAC Caltech | `https://irsa.ipac.caltech.edu/SIA?` | 2026-11-14 |
| **WP** | Wikipédia (EN) — *seed* de coordenadas J2000 e identificadores HD/HIP | Wikimedia Foundation | `https://en.wikipedia.org/w/api.php` | 2026-11-14 |
| **WD** | Wikidata Q12775006 (R Draconis) | Wikimedia Foundation | `https://www.wikidata.org/wiki/Special:EntityData/Q12775006.json` | 2026-11-14 |

**Sistema de referência:** ICRS, graus decimais. **Época de referência do Gaia DR3: 2016.0**
(confirmado no campo `ref_epoch` de todas as linhas consultadas).

---

## 2. Objetos selecionados

| Objeto | Tipo ou característica investigada | Situação |
|---|---|---|
| Estrela de Barnard | Estrela com movimento próprio elevado (10.39"/ano) | **Pesquisado — sequências temporais confirmadas** |
| Epsilon Indi B | Sistema de anãs marrons | **Pesquisado — sequências temporais confirmadas** (do sistema ε Indi A) |
| WISE 0855 | Objeto de movimento próprio elevado (8.15"/ano) | **Pesquisado — sequências confirmadas; divergência de época registrada** |
| RW Aurigae | Estrela variável / sistema jovem | **Pesquisado — sequências temporais confirmadas** |
| R Draconis | Estrela variável (Mira) | **Pesquisado — sequências temporais confirmadas; campo profundo** |

---

## 3. Registro individual dos objetos

### 3.1 Estrela de Barnard

**Nome:** Barnard's Star · **Identificadores:** Gaia DR3 `source_id` **4472832130942575872**;
HD 87937 · HIP 87937 · ID Wikimedia (não confirmado em catálogo astronômico aqui).

| Campo | Valor | Fonte / Classificação |
|---|---|---|
| RA (ICRS, graus) | **269.44850252543836** | G3 — FATO CONFIRMADO |
| Dec (ICRS, graus) | **4.739420051112412** | G3 — FATO CONFIRMADO |
| Época de referência | **2016.0** (`ref_epoch`) | G3 — FATO CONFIRMADO |
| σ(RA), σ(Dec) | 0.026239 mas, 0.029044 mas | G3 |
| Paralaxe | **546.975940 ± 0.040116 mas** | G3 — FATO CONFIRMADO |
| Distância | **1.828 pc (5.96 ly)** | derivado de G3 |
| μ(α\*) (mov. próp. em RA, já com cos δ) | **−801.550978 ± 0.031821 mas/ano** | G3 — FATO CONFIRMADO |
| μ(δ) (mov. próp. em Dec) | **+10362.394207 ± 0.036070 mas/ano** | G3 — FATO CONFIRMADO |
| Movimento próprio total | **10.39"/ano** | derivado de G3 |
| Magnitude G | 8.194 · RUWE 1.085 | G3 |
| Coordenada J2000 (secundária) | RA 17h57m48.49847s, Dec +04°41′36.1139″ | WP — FATO CONFIRMADO (coincide com G3 propagado a J2000) |

**Convenção de sinal e unidade:** μ(α\*) é a componente de movimento próprio em RA
**já multiplicada por cos δ**, em mas/ano, com sinal **negativo = RA decrescente** e
**positivo = Dec crescente**. É a convenção padrão do Gaia (`pmra`, `pmdec`).

**Posições propagadas para as épocas SPHEREx** (a partir de G3, epoch 2016.0):

| Época | RA | Dec | Deslocamento desde 2016.0 |
|---|---|---|---|
| 2025.60 | 269.446358 | 4.767053 | 99.8″ |
| 2026.75 | 269.446101 | 4.770363 | 111.7″ |

**Observações SPHEREx (SX, cone raio 0.05°, 4 coleções):**

| Métrica | Valor |
|---|---|
| Produtos (linhas SIA2) | **378** |
| Épocas distintas (`t_min`) | **192** |
| Épocas por banda/detector | 60–67 (D1: 61, D2: 67, D3: 61, D4: 60, D5: 67, D6: 62) |
| Cobertura temporal | **2025-08-15 → 2026-09-22** (13.2 meses) |
| Coleções | `spherex_dr1` (250), `spherex_qr3` (128) |
| Amostragem em banda D3 | 61 épocas, **14 separadas por ≥ 1 dia**, mediana 2.8 d, máx 203.8 d |

**Limitações específicas:**
- O deslocamento de ~100–112″ entre J2000/2016 e as épocas SPHEREx equivale a **~17 pixels**
  de 6.15". Uma implementação que use a coordenada de referência sem propagar **errará por
  ~17 pixels** ao recortar.
- Resolução efetiva ~7.45″ FWHM — a estrela é isolada, sem problema de blend.
- Barnard é uma anã vermelha fraca (G = 8.19); o sinal no infravermelho próximo é maior que
  no visível, favorecendo a detecção.

**Status:** **Adequado** — observações suficientes, compatíveis e bem distribuídas no tempo.

---

### 3.2 Epsilon Indi B

**Nome:** Epsilon Indi B (componente B do sistema ε Indi) · **Sistema:** ε Indi A
Gaia DR3 `source_id` **6412595290592307840** · HD 104949 · HIP 104214.

| Campo | Valor | Fonte / Classificação |
|---|---|---|
| RA (ICRS, graus) | **330.8724078795965** | G3 — FATO CONFIRMADO |
| Dec (ICRS, graus) | **−56.79725466122902** | G3 — FATO CONFIRMADO |
| Época de referência | **2016.0** | G3 — FATO CONFIRMADO |
| σ(RA), σ(Dec) | 0.068695 mas, 0.065466 mas | G3 |
| Paralaxe | **274.843142 ± 0.095615 mas** | G3 — FATO CONFIRMADO |
| Distância | **3.638 pc (11.87 ly)** | derivado de G3 |
| μ(α\*) | **+3966.660539 ± 0.085571 mas/ano** | G3 — FATO CONFIRMADO |
| μ(δ) | **−2536.191987 ± 0.092213 mas/ano** | G3 — FATO CONFIRMADO |
| Movimento próprio total | **4.71"/ano** | derivado de G3 |
| Magnitude G | 4.3229 · RUWE 1.148 | G3 |
| Componente **B** (anã marrom T6) | **NÃO VERIFICADO** — sem entrada própria no Gaia DR3 | ver limitação |
| Separação A–B | ≈ 6.5″ (literatura) | **NÃO VERIFICADO** neste ambiente |

**Por que "Epsilon Indi B" e não "A":**
- **FATO CONFIRMADO:** a busca no Gaia DR3 com raio 0.01° em torno de ε Indi A retorna
  **apenas** 3 fontes, e **nenhuma** com a paralaxe esperada de ε Indi B (≈ 274.8 mas).
  A fonte mais brilhante é ε Indi A. **Não existe entrada do Gaia DR3 para ε Indi B**
  (magnitude de B: **NÃO VERIFICADA**), e portanto **B também não será resolvido pelo
  SPHEREx** (pixel 6.15″, PSF ~7.45″ FWHM).
- **Consequência prática:** a passagem do SPHEREx sobre ε Indi registra **uma única fonte
  resolvida (A+B, não separável)**. O teste do sistema ε Indi deve ser formulado como
  "observar o sistema ε Indi (A+B combinado)", e a demonstração deve usar **ε Indi A**
  como identificador de referência.
- **Atenção à tarefa original:** o `docs/science/target-catalog.md` na versão anterior
  alertava "verificar a identificação exata do componente ou sistema mencionado no desafio
  antes de selecionar coordenadas". Esta verificação **está feita**: o alvo é um **sistema**
  binário com componente A (estrela K) e componente B (par de anãs marrons Bb/Ba), e o
  SPHEREx só pode observar o conjunto.

**Posições propagadas (G3, epoch 2016.0):**

| Época | RA | Dec | Deslocamento desde 2016.0 |
|---|---|---|---|
| 2025.30 | 330.891121 | −56.803806 | 43.8″ |
| 2026.78 | 330.894099 | −56.804849 | 50.8″ |

**Observações SPHEREx (SX, cone raio 0.05°, 4 coleções):**

| Métrica | Valor |
|---|---|
| Produtos (linhas SIA2) | **524** |
| Épocas distintas | **273** |
| Épocas por banda/detector | 50–122 (D1: 50, D2: 96, D3: 122, D4: 52, D5: 87, D6: 117) |
| Cobertura temporal | **2025-04-24 → 2026-10-02** (17.3 meses — a mais longa do conjunto) |
| Coleções | `spherex_dr1` (402), `spherex_qr3` (122) |

**Limitações específicas:**
- Resolução ~7.5″ FWHM < separação A–B (~6.5″) → **A e B são indissociáveis**.
- Deslocamento de 44–51″ desde 2016.0 → ~8 pixels. Propagação de posição necessária.
- Brilho: ε Indi A é G = 4.32, **muito brilhante** → excelente sinal, mas risco de
  *bleeding/saturation* e de flags `GHOST`/`BLOOM` nas vizinhanças.

**Status:** **Parcialmente adequado** — há observações abundante e de longa cobertura para
o **sistema**, mas o **componente B isolado não é observável** com a resolução do SPHEREx.

---

### 3.3 WISE 0855

> **CORREÇÃO DE 15/11/2026 (DECISÃO 019) — prevalece sobre o texto abaixo.**
>
> 1. **A coordenada do desafio NÃO é a posição na época J2000.0.** É a posição embutida no nome do objeto
>    (`WISE J085510.83−071442.5`), da época da descoberta nos dados WISE (~2010).
> 2. **Fonte primária** (SIMBAD, via Sesame do CDS, consultado em 15/11/2026; referência
>    `2021ApJS..253....7K`, Kirkpatrick et al. 2021):
>    - posição J2000: RA **133.81890825°**, Dec **−7.247048°**;
>    - μα* **−8123,7 ± 1,3** mas/ano, μδ **+673,2 ± 1,3** mas/ano, paralaxe 439,0 ± 2,4 mas.
>
>    O μ coincide com o valor usado até aqui, que agora tem confirmação na fonte primária.
> 3. **Evidência nas imagens:**
>    - Propagando a posição J2000 do SIMBAD para 2010,3, ela cai a ~1″ da coordenada do desafio.
>    - No campo de 14′ do AllWISE, a fonte com maior excesso W2 (4,6 µm) sobre W1 (3,4 µm) está a 1,4″ da posição prevista. É a assinatura esperada de uma anã marrom Y.
>    - A propagação antiga (da coordenada do desafio tratada como J2000) errava por **~84–85″**.
> 4. **Posição usada pelo projeto em 2025,35:** RA **133.761244°**, Dec **−7.242304°**. A posição antiga era 133.737467 / −7.240406.
> 5. **Pendente (Integrante 2):** conferir no artigo de Kirkpatrick et al. 2021 a época de referência da posição citada pelo SIMBAD. Admitimos J2000.0, o padrão do SIMBAD, e as imagens confirmam esse valor dentro de ~1–2″.

**Nome:** WISE 0855−0714 · **Identificadores:** WISE J085510.83−071442.5 ·
HD 2MASS J08551083−0714425 · anã marrom Y4.

**Coordenadas fornecidas no contexto do desafio:**

- RA: 08h55m10.831s.
- Dec: -7°14'42.53".

Conversão aproximada:

- RA: 133.795129°.
- Dec: -7.245147°.

**VERIFICAÇÃO DA ORIGEM E DA ÉPOCA (resultado principal desta seção):**

| Verificação | Resultado | Classificação |
|---|---|---|
| A coordenada do desafio é a posição **J2000.0** de WISE 0855−0714? | **SIM.** A infobox da Wikipédia gives RA **08h55m10.83168s**, Dec **−07°14′42.5256″**, `epoch=[[J2000]]`, nome `WISE J085510.83−071442.5` — coincide com o valor do desafio até < 0.01″ | FATO CONFIRMADO (fonte secundária WP) |
| É a posição **corrente** (2026)? | **NÃO.** Ver abaixo | FATO CONFIRMADO |
| Existe um homólogo com **movimento próprio de ~8"/ano** no Gaia DR3? | **NÃO.** Nenhuma fonte num raio de 0.04° em torno da posição prevista para 2016.0 (e nem em 0.15° em torno da posição J2000) tem `pmra < −3000 mas/ano` | FATO CONFIRMADO (consulta direta ao Gaia DR3) |

**DIVERGÊNCIA REGISTRADA (crítica para o projeto):**
A coordenada do desafio é **J2000.0**. Com o movimento próprio de ≈ 8.15"/ano, o objeto
estará deslocado em **~207″ (3.5′)** em relação a ela nas épocas SPHEREx (2025–2026) —
ou seja, **~34 pixels** de 6.15".

Propagação a partir da posição J2000 e do μ da infobox (que cita Kirkpatrick et al. 2021):

| Época | RA | Dec | Deslocamento desde J2000 |
|---|---|---|---|
| 2016.00 (época Gaia) | 133.758736 | −7.242154 | 130.4″ |
| **2025.35** (1ª obs. SPHEREx do campo) | **133.737467** | **−7.240406** | **206.6″** |
| 2026.45 | 133.734965 | −7.240200 | 215.6″ |

**Candidato Gaia mais próximo (e por que NÃO é o objeto):**
`source_id` 5756956644387831296 — RA 133.758183, Dec −7.241156, G = 16.31,
paralaxe 0.2859 ± 0.0502 mas, μ(α\*) = **−6.19** mas/ano, μ(δ) = **+1.93** mas/ano,
RUWE 0.9996. Está a ~4″ da posição prevista para 2016.0, mas tem **movimento próprio
praticamente nulo** → é uma **estrela de campo coincidente**, não WISE 0855.

| Campo | Valor | Fonte / Classificação |
|---|---|---|
| RA / Dec J2000 (ICRS, graus) | **133.7951320 / −7.2451460** | WP (infobox, `epoch=J2000`) — FATO CONFIRMADO |
| Época de referência | **J2000.0** (não 2016.0) | WP — FATO CONFIRMADO |
| σ(RA), σ(Dec) | **NÃO VERIFICADO** | não há entrada Gaia utilizável |
| Paralaxe | **439.0 ± 2.4 mas** | WP, citando Kirkpatrick et al. (2021) — FATO CONFIRMADO (fonte secundária) |
| Distância | **2.278 pc (7.43 ly)** | derivado |
| μ(α\*) / μ(δ) | **−8123.7 ± 1.3** / **+673.2 ± 1.3 mas/ano** | WP, citando Kirkpatrick et al. (2021) — FATO CONFIRMADO (fonte secundária; **artigo primário não acessível** neste ambiente — ADS retornou HTTP 405) |
| Movimento próprio total | **8.15"/ano** | derivado |
| Magnitude G | **NÃO VERIFICADO** | sem homólogo Gaia DR3 |
| Identificador Gaia DR3 | **NÃO VERIFICADO / não aplicável** | sem homólogo |

**Observações SPHEREx (SX, cone raio 0.05°, 4 coleções):**

| Métrica | Valor |
|---|---|
| Produtos (linhas SIA2) | **282** (na coordenada J2000) / 263 (na posição propagada 2025.35 — diferença = imagens cujo canto intersecta a borda do cone) |
| Épocas distintas | **143** |
| Épocas por banda/detector | 45–50 (D1: 47, D2: 50, D3: 46, D4: 45, D5: 49, D6: 45) |
| Cobertura temporal | **2025-05-05 → 2026-05-14** (12.3 meses) |
| Coleções | **apenas `spherex_dr1`** — nenhum produto QR3 (profundidade) localizado neste cone em 2026-11-14 |

**Limitações específicas:**
- **Deslocamento de 207″** → a aplicação **precisa** propagar a posição à época de cada
  observação, ou o alvo ficará ~34 pixels fora do centro do recorte.
- Objeto muito fraco (Y4, T_eff ≈ 276 K). A banda 1 (0.75–1.12 µm) é a mais favorável
  (emissão termal); as bandas 4–6 (2.4–5.0 µm) provavelmente **não** detectarão o objeto.
  **NÃO VERIFICADO** por fotometria real (requer análise de cutouts).
- Sem cobertura QR3 → a série termina em 2026-05-14; novas ingestões semanais podem
  mudar isso.

**Status:** **Parcialmente adequado** — há 143 épocas confirmadas, mas (a) exige propagação
de posição, (b) a detectabilidade por banda **não foi verificada**, e (c) não há sobreposição
DR1/QR3 para este alvo.

---

### 3.4 RW Aurigae

**Nome:** RW Aurigae · **Sistema:** componente **A** — Gaia DR3 `source_id`
**156430822114424576** · HD 37986 · HIP 29605.
Componente **B** — Gaia DR3 `source_id` **156430817820015232**.

| Campo | Valor | Fonte / Classificação |
|---|---|---|
| RA (ICRS, graus) | **76.95608119552952** | G3 — FATO CONFIRMADO |
| Dec (ICRS, graus) | **30.401204589097233** | G3 — FATO CONFIRMADO |
| Época de referência | **2016.0** | G3 — FATO CONFIRMADO |
| σ(RA), σ(Dec) | 0.036507 mas, 0.025246 mas | G3 |
| Paralaxe | **6.406249 ± 0.044123 mas** | G3 — FATO CONFIRMADO |
| Distância | **156.10 pc (509.1 ly)** | derivado de G3 |
| μ(α\*) | **+2.640643 ± 0.048949 mas/ano** | G3 — FATO CONFIRMADO |
| μ(δ) | **−27.397583 ± 0.035927 mas/ano** | G3 — FATO CONFIRMADO |
| Movimento próprio total | **27.53 mas/ano** | derivado de G3 |
| Magnitude G | 12.184 · RUWE 1.500 | G3 |
| Componente B: RA / Dec | 76.9565443110343 / 30.401316149887936 | G3 |
| Componente B: paralaxe | 5.454096 ± 0.332450 mas | G3 |
| Componente B: μ(α\*), μ(δ) | +4.906034 ± 0.329159, −24.577535 ± 0.254650 mas/ano | G3 |
| Componente B: G, RUWE | 13.035, **RUWE 16.42** (astrometria degradada / blend) | G3 |
| Separação A–B | **1.49″** (calculada das posições Gaia) | derivado de G3 — FATO CONFIRMADO |
| Coordenada J2000 (secundária) | RA 05h07m49.4562s, Dec +30°24′04.774″ | WP — FATO CONFIRMADO |
| Tipo de variável | disco circumestelar / variável irregular (T Tauriana) | **NÃO VERIFICADO** em catálogo de variability aqui |

**Observações SPHEREx (SX, cone raio 0.05°, 4 coleções):**

| Métrica | Valor |
|---|---|
| Produtos (linhas SIA2) | **342** |
| Épocas distintas | **172** |
| Épocas por banda/detector | **57 em todas as 6 bandas** (D1–D6) |
| Cobertura temporal | **2025-09-01 → 2026-09-16** (12.3 meses) |
| Coleções | `spherex_dr1` (228), `spherex_qr3` (114) — **DR1 e QR3 bem equilibrados** |
| Amostragem | 7–10 épocas por banda separadas por ≥ 1 dia; mediana 1.9–5.4 d; máx 181–195 d |

**Limitações específicas:**
- **A e B separados por 1.49″** → **totalmente indissociáveis** pelo SPHEREx
  (pixel 6.15″, PSF ~7.45″). A fotometria de "RW Aur" no SPHEREx é a do **sistema A+B**.
- Blends com o disco circumestelar podem contaminar a fotometria da banda 1 (0.75–1.12 µm)
  e gerar flags `GHOST`/`BLOOM`/`HALO`.
- Deslocamento desde 2016.0 é **irrelevante** (0.3″) → propagate mesmo assim, por uniformidade.
- RUWE de B = 16.42 → a astrometria de B é duvidosa; **não usar B para medir o movimento**.

**Status:** **Adequado** para a demonstração de variação temporal de brilho do **sistema**,
com cobertura balanceada entre DR1 e QR3 (o que permite mostrar o efeito do reprocessamento
como um caso de estudo de compatibilidade fotométrica).

---

### 3.5 R Draconis

**Nome:** R Draconis (R Dra) · **Identificadores:** Gaia DR3 `source_id`
**1648328016354496384** · **HD 149880** · **HIP 81014** (Wikidata Q12775006).

| Campo | Valor | Fonte / Classificação |
|---|---|---|
| RA (ICRS, graus) | **248.1673783672889** | G3 — FATO CONFIRMADO |
| Dec (ICRS, graus) | **66.75500674547219** | G3 — FATO CONFIRMADO |
| Época de referência | **2016.0** | G3 — FATO CONFIRMADO |
| σ(RA), σ(Dec) | 0.066872 mas, 0.066013 mas | G3 |
| Paralaxe | **1.250918 ± 0.064788 mas** | G3 — FATO CONFIRMADO |
| Distância | **799.41 pc (2607 ly)** | derivado de G3 |
| μ(α\*) | **−20.642812 ± 0.085128 mas/ano** | G3 — FATO CONFIRMADO |
| μ(δ) | **+6.148819 ± 0.091321 mas/ano** | G3 — FATO CONFIRMADO |
| Movimento próprio total | **21.54 mas/ano** | derivado de G3 |
| Magnitude G | 6.374 · RUWE 1.298 | G3 |
| Tipo | **Mira** — protótipo; V_max = 6.7, V_min = 13.2, **P = 245.5 d** | WP ("List of stars in Draco" / "Mira variable") — FATO CONFIRMADO (fonte secundária) |
| Coordenada J2000 (secundária) | RA 16h32m40.23s, Dec +66°45′17.9″ | WP — FATO CONFIRMADO |

**Observações SPHEREx (SX, cone raio 0.05°, 4 coleções):**

| Métrica | Valor |
|---|---|
| Produtos (linhas SIA2) | **2587** — o maior conjunto do grupo de teste |
| Épocas distintas | **1309** |
| Épocas por banda/detector | 94–603 (D1: 599, D2: 95, D3: 597, D4: 599, D5: 94, D6: 603) |
| Cobertura temporal | **2025-04-24 → 2026-09-27** (15.7 meses) |
| Coleções | `spherex_dr1_deep` (1260), `spherex_qr3_deep` (749), `spherex_dr1` (451), `spherex_qr3` (127) |
| Amostragem D1 | 67 épocas separadas por ≥ 1 dia; mediana 1.8 d; máx 227.8 d |

**⚠ R Dra está num DEEP FIELD do SPHEREx.** As coleções `*_deep` (campos profundos) têm
exposições mais profundas, e por isso são **as de maior valor para testar variação de
brilho**. O mesmo objeto também aparece nas coleções *wide* (451 + 127 produtos) —
a mesma região é observada nos dois modos.

**Limitações específicas:**
- **Variação de brilho enorme** (V de 6.7 a 13.2, amplitude ~6.5 mag). Uma demonstração de
  "sequência temporal" com o mesmo *stretch* de cor vai saturar a fase de máximo e ficar
  invisível na fase de mínimo. **O produto precisa de escalonamento automático por
  época** (ou de normalização por banda) para ser demonstrativo.
- Período de 245.5 d ≈ 8.1 meses. A cobertura de ~15.7 meses permite **~6 ciclos** — bom
  para verificar a periodicidade, mas cada ciclo tem poucas amostras por banda.
- **Deslocamento desde 2016.0 irrelevante** (0.2″).
- R Dra é a **única** das 5 que está num campo profundo — usar com cuidado a comparação
  de profundidade entre objetos.

**Status:** **Adequado e o melhor caso de teste para variação de brilho** — 1309 épocas
confirmadas, cobertura longa, amostragem densa e presença em campos profundo e largo.

---

## 4. Campos que deverão ser preenchidos para cada objeto

| Campo | Descrição |
|---|---|
| Nome | Nome do objeto |
| Identificador | Identificador em catálogo confiável |
| RA | Ascensão Reta |
| Dec | Declinação |
| Unidade | Graus ou unidade original documentada |
| Época de referência | Referência temporal das coordenadas |
| Movimento próprio RA | Com unidade e convenção documentadas |
| Movimento próprio Dec | Com unidade e convenção documentadas |
| Fonte astrométrica | Catálogo ou referência utilizada |
| Observações SPHEREx | Produtos encontrados |
| Épocas disponíveis | Datas das observações |
| Bandas | Bandas espectrais encontradas |
| Detectores | Identificação dos detectores |
| Qualidade | Indicadores disponíveis |
| Limitações | Restrições identificadas |
| Resultado | Adequado, parcialmente adequado ou indisponível |

**Resumo preenchido (todos os valores de SX são de 2026-11-14, cone raio 0.05°):**

| Objeto | Identificador principal | RA (ICRS°) | Dec (ICRS°) | Época | μ(α\*) mas/ano | μ(δ) mas/ano | Paralaxe mas | Distância | Épocas SPHEREx | Cobertura | Bandas | Detectores | Resultado |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Barnard | Gaia DR3 4472832130942575872 / HD 87937 | 269.448503 | +4.739420 | 2016.0 | −801.551 ± 0.032 | +10362.394 ± 0.036 | 546.976 ± 0.040 | 1.83 pc | **192** | 2025-08-15 → 2026-09-22 | 6 | D1–D6 | **Adequado** |
| ε Indi (A) | Gaia DR3 6412595290592307840 / HD 104949 | 330.872408 | −56.797255 | 2016.0 | +3966.661 ± 0.086 | −2536.192 ± 0.092 | 274.843 ± 0.096 | 3.64 pc | **273** | 2025-04-24 → 2026-10-02 | 6 | D1–D6 | **Parcialmente adequado** (B não resolvido) |
| WISE 0855 | WISE J085510.83−071442.5 | 133.795132 | −7.245146 | **J2000.0** | −8123.7 ± 1.3 | +673.2 ± 1.3 | 439.0 ± 2.4 | 2.28 pc | **143** | 2025-05-05 → 2026-05-14 | 6 | D1–D6 | **Parcialmente adequado** (propagar 207″; sem homólogo Gaia) |
| RW Aur A | Gaia DR3 156430822114424576 / HD 37986 | 76.956081 | +30.401205 | 2016.0 | +2.641 ± 0.049 | −27.398 ± 0.036 | 6.406 ± 0.044 | 156.1 pc | **172** | 2025-09-01 → 2026-09-16 | 6 | D1–D6 | **Adequado** (A+B inseparáveis) |
| R Dra | Gaia DR3 1648328016354496384 / HD 149880 / HIP 81014 | 248.167378 | +66.755007 | 2016.0 | −20.643 ± 0.085 | +6.149 ± 0.091 | 1.251 ± 0.065 | 799.4 pc | **1309** | 2025-04-24 → 2026-09-27 | 6 | D1–D6 | **Adequado** (campo profundo) |

**Qualidade e limites disponíveis:**
- Por produto: `calib_level=2`, `dataproduct_subtype=science`, `algorithm_name=exposure`,
  `obs_intent=science`, `target_type=field`, `target_standard=0`, `target_moving=0`.
- No FITS: `L1DQAFLG='Pass'`, `L2 N_*` (contadores por flag), bitmask `MSKN*`/`MSKD*`.
- **Detalhe crítico de qualidade:** `target_moving = 0` para todos os produtos — o SPHEREx
  **não marca** alvos com movimento próprio. Nenhum serviço do IRSA faz propagação
  astrométrica para alvos estelares. **A propagação é responsabilidade da aplicação.**

---

## 5. Regras de pesquisa

Para cada objeto:

1. Identificar a fonte astrométrica. ✔ (Gaia DR3 / ESA)
2. Registrar coordenadas e unidades. ✔
3. Registrar a época de referência. ✔
4. Verificar movimento próprio. ✔
5. Calcular ou obter a posição apropriada para a época de observação, quando necessário. ✔ (seção 3)
6. Consultar o arquivo SPHEREx. ✔ (SIA2, 4 coleções)
7. Registrar os produtos encontrados. ✔
8. Avaliar a qualidade e a compatibilidade das observações. ✔
9. Documentar resultados negativos também. ✔ (ε Indi B; WISE 0855 sem homólogo Gaia; QR3 ausente para WISE 0855)

---

## 6. Classificação dos resultados

**Adequado:** Existem observações suficientes e compatíveis com o objetivo do teste.

**Parcialmente adequado:** Existem observações, mas as limitações impedem uma demonstração completa.

**Indisponível:** Não foram encontradas observações adequadas após a consulta documentada.

Não classificar um objeto como indisponível sem registrar os critérios e as consultas realizadas.

**Nenhum dos 5 objetos foi classificado como indisponível.** Todos têm ≥ 143 épocas distintas
confirmadas no arquivo.

---

## 7. Evidências

Cada resultado deverá conter: fonte consultada, data da consulta, coordenadas utilizadas,
época considerada, identificadores dos produtos, datas das observações, metadados relevantes
e registros que permitam reproduzir a consulta.

**Consultas reproduzíveis (executadas com sucesso em 2026-11-14).**

Sequência temporal por objeto (SIA2):
```bash
curl -s "https://irsa.ipac.caltech.edu/SIA?COLLECTION=spherex_dr1&COLLECTION=spherex_qr3&COLLECTION=spherex_dr1_deep&COLLECTION=spherex_qr3_deep&POS=circle+269.448503+4.739420+0.05&RESPONSEFORMAT=CSV&MAXREC=5000" -o barnard.csv
```
(substituir `POS=circle <RA> <Dec> 0.05` pela posição do objeto e o nome do arquivo)

Ordenação cronológica + URL de cutout pronta (TAP, igual ao tutorial oficial):
```sql
SELECT 'https://irsa.ipac.caltech.edu/' || a.uri || '?center=269.448503,4.73942d&size=0.05' AS uri,
       p.time_bounds_lower, p.time_bounds_upper, p.energy_bandpassname
FROM spherex.artifact a JOIN spherex.plane p ON a.planeid = p.planeid
WHERE 1 = CONTAINS(POINT('ICRS', 269.448503, 4.739420), p.poly)
  AND p.energy_bandpassname = 'SPHEREx-D3'
ORDER BY p.time_bounds_lower
```

Recorte individual (IBE Cutout):
```
https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/level2/2025W19_1B/l2b-v27-2026-197/3/level2_2025W19_1B_0116_1D3_spx_l2b-v27-2026-197.fits?center=133.795129,-7.245147&size=0.02
```

Astrometria (Gaia DR3 via ESA):
```sql
SELECT source_id,ra,dec,ra_error,dec_error,parallax,parallax_error,
       pmra,pmra_error,pmdec,pmdec_error,ref_epoch,phot_g_mean_mag,ruwe
FROM gaiadr3.gaia_source
WHERE CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',269.448503,4.739420,0.001))=1
```

---

## 8. Responsável

**Liderança científica:** Integrante 2.

A liderança técnica deverá auxiliar na implementação das consultas e na interpretação dos metadados necessários ao backend.

### 8.1 Perguntas em aberto para a liderança científica

1. **WISE 0855:** os valores de paralaxe (439.0 ± 2.4 mas) e de movimento próprio
   (−8123.7 / +673.2 mas/ano) vêm de fonte secundária (infobox da Wikipédia citando
   Kirkpatrick et al. 2021). O artigo primário não pôde ser acessado (ADS retornou HTTP 405).
   **Precisa-se validação contra a literatura primária.**
2. **WISE 0855 no Gaia DR3:** confirmar com a liderança se há um homólogo publicado sob
   outro `source_id` (o Gaia DR3 é conhecido por dar paralaxe nula/insuficiente para
   anãs marrons Y). A conclusão desta pesquisa é *negativa* (nenhuma fonte com
   μ(α\*) < −3000 mas/ano num raio de 0.15°), e deve ser revista se a astrometria for
   reprocessada.
3. **ε Indi B:** confirmar a separação A–B (~6.5″) e a magnitude G de B na literatura
   primária, e decidir se o teste deve ser declarado como "sistema ε Indi (A+B)".
4. **RW Aur:** confirmar a natureza da variável (disco circumestelar / variável irregular)
   e se a fotometria de banda 1 estará contaminada pelo disco.
5. **R Draconis:** o valor P = 245.5 d vem da Wikipédia; confirmar na literatura.
6. **Definir** se a aplicação deve fazer propagação astrométrica (recomendado) ou apenas
   informar o deslocamento máximo.
