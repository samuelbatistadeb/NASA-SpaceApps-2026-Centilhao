# Registro de decisões

Este documento registra decisões que afetam o escopo, a arquitetura, a organização e o desenvolvimento do projeto.

Novas decisões devem ser acrescentadas sem apagar o histórico anterior.

## DECISÃO 001 — Escolha do desafio

**Data:** 14/11/2026

**Assunto:** Definição do desafio do NASA Space Apps Challenge 2026.

**Contexto:** A equipe avaliou os desafios disponíveis e selecionou um desafio avançado relacionado à exploração temporal de imagens da missão SPHEREx.

**Decisão tomada:** Desenvolver uma aplicação web pública para consultar imagens SPHEREx a partir de coordenadas celestes e permitir a exploração de observações em sequência temporal.

**Justificativa:** A proposta permite combinar desenvolvimento de software, processamento de dados científicos, astronomia e visualização interativa.

**Consequências:** O desenvolvimento deverá priorizar a consulta a dados reais e a comprovação da existência de sequências temporais úteis.

**Responsável:** Equipe.

---

## DECISÃO 002 — Organização das frentes humanas

**Data:** 14/11/2026

**Assunto:** Divisão inicial das responsabilidades.

**Contexto:** A equipe é composta por três integrantes e precisa trabalhar simultaneamente em frentes diferentes.

**Decisão tomada:**

- Integrante 1: liderança técnica, backend, dados e integração.
- Integrante 2: liderança científica, pesquisa astronômica e validação.
- Integrante 3: liderança de interface, frontend e visualização.

**Justificativa:** A divisão permite desenvolver as partes técnicas e científicas em paralelo, mantendo responsabilidades humanas definidas.

**Consequências:** Cada integrante deverá ter entregas, tarefas e critérios de aceitação próprios. A divisão poderá ser revisada conforme as necessidades do projeto.

**Responsável:** Equipe.

---

## DECISÃO 003 — Tecnologias iniciais

**Data:** 14/11/2026

**Assunto:** Definição preliminar da stack tecnológica.

**Contexto:** A aplicação precisa consultar dados científicos, processar imagens e disponibilizar uma interface web.

**Decisão tomada:**

- Backend: Python e FastAPI.
- Processamento científico: Astropy e bibliotecas compatíveis com os serviços do IRSA.
- Frontend: HTML, CSS e JavaScript.
- Comunicação: API HTTP com respostas JSON.
- Controle de versão: Git e GitHub.

**Justificativa:** A combinação permite utilizar ferramentas científicas do ecossistema Python sem introduzir complexidade desnecessária no frontend.

**Consequências:** A arquitetura deverá ser validada antes da implementação. Bibliotecas e serviços específicos ainda precisam ser testados.

**Responsável:** Liderança técnica.

---

## DECISÃO 004 — Escopo inicial do MVP

**Data:** 14/11/2026

**Assunto:** Priorização das funcionalidades.

**Contexto:** O desafio possui escopo avançado e pode envolver diferentes produtos científicos e funcionalidades complementares.

**Decisão tomada:** Priorizar:

1. Busca por RA e Dec.
2. Seleção do campo de visão.
3. Consulta de imagens reais do SPHEREx.
4. Organização cronológica das observações.
5. Reprodução, pausa e navegação temporal.
6. Exibição dos metadados.
7. Testes com os objetos indicados no desafio.

Comparação, subtração de imagens, exploração espectral e integração com outras bases serão avaliadas posteriormente.

**Justificativa:** É necessário comprovar primeiro o funcionamento da experiência central solicitada.

**Consequências:** Funcionalidades complementares não deverão atrasar a entrega do fluxo principal.

**Responsável:** Equipe.

---

## DECISÃO 005 — Ambiente Python isolado em ambiente virtual

**Data:** 14/11/2026

**Assunto:** Preparação do ambiente de execução do backend.

**Contexto:** A auditoria inicial verificou que o Python 3.12.5 estava instalado no sistema, porém nenhum dos pacotes necessários ao projeto (astropy, astroquery, pyvo, fastapi, numpy, matplotlib, pytest, httpx) estava presente, nem em ambiente global nem virtual. A instalação global do sistema foi descartada para evitar poluição do ambiente da máquina e por não ser reproduzível.

**Decisão tomada:** Adotar um ambiente virtual `.venv` na raiz do repositório, já coberto pelo `.gitignore`, com as dependências instaladas e pinadas. O interpretador do projeto é sempre `.\.venv\Scripts\python.exe` (Windows PowerShell 5.1).

**Justificativa:** Reprodutibilidade, isolamento do sistema e previsibilidade de versões durante o desenvolvimento do MVP.

**Consequências:**

- Nenhum comando de execução do projeto deve usar o Python global.
- As versões instaladas e pinadas são: astropy 8.0.2, astroquery 0.4.11, pyvo 1.10.0, fastapi 0.162.7, uvicorn 0.54.0, numpy 2.5.4, matplotlib 3.11.2, pytest 9.2.0, httpx 0.28.1, pydantic 2.14.3, pillow 13.0.0, requests 2.34.2.
- `jupyterlab` e `ipykernel`, presentes na lista inicial, são desnecessários ao MVP e pesam na instalação: sua remoção é tratada na DECISÃO 007.

**Responsável:** Liderança técnica.

---

## DECISÃO 007 — Estratégia de consulta ao arquivo SPHEREx

**Data:** 14/11/2026

**Assunto:** Definir como o backend consulta o arquivo IRSA e obtém recortes de imagem.

**Contexto:** A pesquisa (T-A) e a análise de dados (T-B), com verificação independente do Coordinator, estabeleceram o comportamento real dos serviços. A premissa inicial registrada em `docs/science/data-sources.md` §3.1 — de que o IRSA exporia SIA2 em `/SIA2` — estava **errada**: o caminho `/SIA2` devolve 404 por desenho, e `/SIA` serve a implementação **SIA v2**. O serviço de recorte também não é um CGI autônomo: o IBE gera o recorte acrescentando uma query string ao `access_url` do próprio arquivo FITS.

**Decisão tomada:**

1. **Consulta principal: SIA v2** em `https://irsa.ipac.caltech.edu/SIA?`, com `RESPONSEFORMAT=CSV`, `MAXREC` limitado e as **4 coleções ativas** (`spherex_dr1`, `spherex_qr3`, `spherex_dr1_deep`, `spherex_qr3_deep`) — consultar apenas `spherex_dr1` perderia metade da série temporal de alvos como WISE 0855.
2. **Complemento: TAP** em `https://irsa.ipac.caltech.edu/TAP/sync`, com `FORMAT=csv`, sobre `spherex.artifact ⋈ spherex.plane`. É ~1 dia mais fresco que o SIA2 e já devolve a URL de recorte pronta e ordenada por `p.time_bounds_lower`.
3. **Recorte: IBE cutout** via `<access_url>?center=<ra>,<dec>d&size=<graus>`, extraindo apenas as extensões `IMAGE` e `WCS-WAVE`.
4. **Época de observação = `t_min`** (SIA2) ≡ `time_bounds_lower` (TAP) ≡ `MJD-OBS`/`MJD-BEG` (FITS). **Nunca** usar `obs_release_date` nem a keyword FITS `DATE` (timestamp de criação do HDU).
5. **Chave do quadro = (detector, `t_min`)**, porque banda e época são eixos independentes: os 102 canais espectrais coexistem dentro de cada imagem e **não** formam uma sequência temporal.
6. **Pré-filtro de sobreposição**: manter apenas produtos com `angsep(alvo, s_ra/s_dec) ≤ s_fov/2`, pois o SIA2 devolve imagens que apenas **intersectam** o cone. Mesmo assim, tratar `422 "Arrays do not overlap."` e `500` como "produto sem sobreposição" e **pular** o produto.
7. **Retry com backoff exponencial é obrigatório** para `503 "Server busy, retry later."` (frequência observada de ~33%) e para erros de rede transitórios (`IncompleteRead`, `RemoteDisconnected`). Concorrência inicial conservadora.
8. **Propagação astrométrica é responsabilidade da aplicação**: o SPHEREx publica `target_moving = 0` em todos os produtos; alvos com movimento próprio (Barnard, WISE 0855) exigem posição propagada à época de cada observação.
9. **Normalização visual por quadro**, com esquema de cor estável na sequência; a normalização para exibição não é medição fotométrica.
10. **Sem banco de dados** no MVP: consulta direta ao arquivo + cache em disco.

**Justificativa:** Cada item é sustentado por execução real registrada em `docs/board.md` §6.3 e §6.4, e não por suposição.

**Consequências:**

- `docs/architecture/api-contract.md` e `docs/architecture/system.md` devem ser atualizados para refletir a estratégia de recorte real e a necessidade de propagação astrométrica.
- A compatibilidade fotométrica absoluta entre DR1 e QR3 **não está garantida** (ganho e PSF diferem entre reprocessamentos; `VERSION` varia dentro do release). O produto `l3_flux_corrections` fica como evolução, e a interface deve declarar as limitações de comparabilidade.
- Comparações entre detecores ou entre DR1 e QR3 não devem ser apresentadas como medidas fotométricas sem validação da liderança científica.

**Responsável:** Liderança técnica, com validação da liderança científica quanto aos itens fotométricos.

---

## DECISÃO 008 — Premissa da sequência temporal confirmada

**Data:** 14/11/2026

**Assunto:** Resultado da verificação da hipótese central do projeto (R-01).

**Contexto:** O risco R-01 era o maior do projeto: a solução depende de existirem **observações repetidas da mesma região do céu em instantes distintos** no arquivo SPHEREx. Se não existissem, a "reprodução temporal" seria uma metáfora sem lastro científico e o produto precisaria ser reformulado.

**Decisão tomada:** A premissa está **CONFIRMADA** e documentada. A verificação independente do Coordinator reproduziu os números do Researcher: WISE 0855 → 282 produtos, **143 épocas distintas**; Barnard → 378 produtos, **192 épocas distintas**; cobertura de 12 a 17 meses. Cada época é uma exposição individual de um detector. A sequência temporal vem de `t_min` distintos, e não dos 102 canais espectrais.

**Justificativa:** Constatado por execução real do serviço SIA v2 em 2026-11-14, registrado em `docs/board.md` §6.3.

**Consequências:**

- O escopo do MVP permanece como definido; não é necessário pivotar para uma abordagem puramente espectral.
- As séries por banda são **esparsas** (mediana de 2 a 5 dias entre épocas independentes) — a interface deve comunicar a escala temporal real, e não sugerir cadência regular.
- Os alvos de movimento próprio exigem propagação astrométrica (DECISÃO 007, item 8) para que o alvo permaneça no recorte.

**Responsável:** Liderança técnica, pendente de validação da liderança científica.

---

## DECISÃO 009 — Interpretação de época e detector na resposta real do SIA

**Data:** 14/11/2026

**Assunto:** Alinhar o parser do backend ao formato real da resposta SIA v2 do IRSA para SPHEREx.

**Contexto:** Uma consulta real (`/SIA?COLLECTION=spherex_dr1&POS=circle 133.795129 -7.245147 0.01&RESPONSEFORMAT=votable`) devolveu HTTP 200, `application/x-votable+xml`, 51 colunas. A primeira linha corresponde exatamente ao FITS local `level2_2025W19_1B_0116_1D3_spx_l2b-v27-2026-197.fits` (`t_min = 60800.700028` ≡ `MJD-OBS`). Foram identificados dois defeitos no backend:

1. `t_min` é publicado como **MJD numérico** (padrão ObsCore), mas o código o tratava como data ISO. A conversão falhava e a época passava a ser `obs_release_date` (data de publicação, 2026-09-27), contrariando a DECISÃO 007, item 4.
2. Não existe coluna de detector. O alias `instrument_name` fazia o detector aparecer como "SPHEREx".

**Decisão tomada:**

- `t_min`/`t_max` numéricos são interpretados como MJD. Strings ISO continuam aceitas para outras fontes.
- O fallback para `obs_release_date` foi **removido**: sem época resolvível, `observed_at = null` e `timing_status = "unresolved"`.
- O detector é extraído do sufixo `/D<n>` de `obs_publisher_did` ou de `energy_bandpassname = SPHEREx-D<n>`, no formato `"D3"`. `instrument_name` deixou de ser alias de detector.
- Uma resposta real e não editada foi salva em `tests/backend/fixtures/sia_spherex_dr1_wise0855.xml` para testes sem rede.

**Justificativa:** Execução real do serviço e comparação com o cabeçalho do FITS correspondente.

**Consequências:**

- A escala de tempo (UTC × TT, ~69 s) não é convertida; isso é irrelevante para ordenar exposições, mas deve ser revisto se houver cálculo de efemérides.
- Pendente: `em_min`/`em_max` vêm em **metros** no SIA, mas o schema os chama de `wavelength_*_nm` sem conversão. O teste sintético atual (`0.9` com `band_units = "um"`) também não converte. Resolvido na DECISÃO 011.

**Responsável:** Liderança técnica.

---

## DECISÃO 010 — SIA como padrão e recorte IBE no backend

**Data:** 14/11/2026

**Assunto:** Pôr em código as estratégias de consulta e recorte da DECISÃO 007.

**Decisão tomada:**

- `Settings.irsa_sia2_base_url` passa a ter como padrão `https://irsa.ipac.caltech.edu/SIA`, já verificado. Downloads e recortes ficam restritos a `irsa.ipac.caltech.edu` (`SPHEREX_ALLOWED_DOWNLOAD_HOSTS`).
- O recorte remoto usa o IBE do próprio produto: `<access_url>?center=<ra>,<dec>d&size=<graus>`, com `size = fov_arcmin / 60`. Não existe serviço de recorte separado; `irsa_cutout_base_url` fica vazio.
- HTTP 422/500 do IBE significa que o produto não cobre a posição. Nesse caso a API responde `IMAGE_NOT_FOUND`, sem retry. HTTP 503 continua com retry e backoff exponencial.
- `cutout_mode=local` continua forçando o download completo (~65 MB por produto).

**Evidência:** teste ao vivo pela API (WISE 0855, FoV 1′), com 258 observações em 5,2 s e 4 recortes IBE convertidos em PNG, de 11 a 15 s cada (sem cache). Um 503 real foi recuperado pelo retry.

**Consequências:**

- O recorte IBE é lento (~11–15 s por produto). O cache de imagens é essencial, e a interface não deve pedir todas as imagens de uma vez.
- A escala é de 6,15″/pixel: FoV de 1′ ≈ 10×10 pixels. Para a demonstração, convém um FoV padrão de vários minutos de arco.
- Pendente: o pré-filtro de sobreposição por `s_fov`/`s_region` (DECISÃO 007, item 6) ainda não foi implementado. Por enquanto, a falta de sobreposição só aparece como `IMAGE_NOT_FOUND` ao pedir a imagem. Resolvido na DECISÃO 013.

**Responsável:** Liderança técnica.

---

## DECISÃO 012 — Leitura parcial do FITS e limite de concorrência no IRSA

**Data:** 14/11/2026

**Assunto:** Lentidão das imagens: a galeria disparava ~25 recortes simultâneos e cada um levava 11–18 s.

**Contexto (medido ao vivo):** O IBE começa a responder em ~1 s, mas cada recorte de 29×29 px tem **4,05 MB**. A extensão `IMAGE`, a única que o app usa, ocupa 3,4 KB; a tabela `EPSF` (modelo de PSF) ocupa **3,95 MB (97,5%)** e vem por último. Com `gzip=true` o tempo piorou (32 s). Sob muitos pedidos simultâneos, o IRSA responde `503 Server busy`.

**Decisão tomada:**

1. **Leitura parcial:** o corpo é lido em streaming e a conexão é fechada assim que a extensão `IMAGE` termina (`fits_bytes_through_extension`, que analisa os cabeçalhos FITS sequenciais). Vale para o recorte IBE e para o download completo (65 MB → ~16,6 MB). Se a extensão não for encontrada, o arquivo é lido inteiro.
2. **Limite de concorrência:** no máximo `SPHEREX_MAX_CONCURRENT_PRODUCT_REQUESTS` (padrão 3) pedidos de produto simultâneos ao IRSA, em todas as threads.
3. **Deduplicação:** pedidos simultâneos da mesma imagem (por exemplo, visualizador e 1ª miniatura) esperam um único recorte e reutilizam o cache.

**Evidência:** um recorte real caiu de 17,7 s e 4.049.280 bytes para **1,2 s e 31.680 bytes**, com pixels **idênticos** aos do arquivo completo.

**Consequências:** `FLAGS`, `VARIANCE`, `ZODI`, `EPSF` e `WCS-WAVE` deixam de ser baixados. Se o app passar a usá-los (máscaras de qualidade, espectro), a extensão-alvo deverá ser a última necessária.

**Responsável:** Liderança técnica.

---

## DECISÃO 014 — Recorte na posição propagada pelo movimento próprio

**Data:** 14/11/2026

**Assunto:** Pendência 2: alvos de alto movimento próprio saem do centro do recorte ao longo da janela SPHEREx (DECISÃO 007, item 8).

**Decisão tomada:**

- `GET /api/observations` aceita `pm_ra_cosdec_masyr`, `pm_dec_masyr` e `ref_epoch_jyear`, sempre os três juntos. `ra_deg`/`dec_deg` passam a ser a posição na época de referência.
- Cada observação é filtrada pelo `s_region` (DECISÃO 013) e recortada na posição propagada para o seu próprio `t_min`. Os campos `metadata.cutout_center_ra_deg/dec_deg` e `position_source` (`requested` ou `proper_motion`) registram o que foi feito.
- Modelo: movimento linear no plano tangente (projeção gnomônica inversa), em `services/astrometry.py`. Paralaxe e velocidade radial são ignoradas: a oscilação paralática dos alvos é ≤ 0,55″ (< 0,1 px).
- A consulta SIA de um alvo móvel é centrada em 2026.0, com o raio ampliado pelo deslocamento de 1,5 ano.
- `GET /api/targets` publica o movimento próprio de cada alvo (valores de `docs/science/target-catalog.md`), e o frontend o envia ao clicar num alvo. Editar RA/Dec ou clicar no mapa descarta o movimento.
- O id da observação passa a incluir a assinatura da consulta (centro, FOV, movimento), para que o mesmo produto em consultas diferentes não colida.

**Evidência:**

- A propagação confere com as posições do catálogo científico (≤ 0,015″) e com o astropy (< 0,001″).
- Ao vivo, Estrela de Barnard no detector D1: sem correção a estrela se afasta até **2,18 px** (~13″) do centro em ago–set/2026; com correção ela fica a **≤ 0,73 px** em todas as datas amostradas (0,18–0,73 px). Nessa medição, o núcleo saturado (pixels `NaN`) foi tratado como o mais brilhante.

**Limitações:** a correção vale apenas para alvos com movimento próprio conhecido (os 5 de exemplo); uma coordenada digitada manualmente não é corrigida. Os recortes ainda não estão reprojetados para uma orientação comum (pendência 3).

**Responsável:** Liderança técnica.

---

## DECISÃO 015 — Quadro comum, cobertura por FOV e combinação de épocas

**Data:** 15/11/2026

**Assunto:** Base para comparar, somar e subtrair épocas (desafio: "somar dados de cada detector para melhorar o sinal-ruído", "somar ou subtrair imagens de momentos diferentes", "usuário escolhe o FOV").

**Contexto:** Cada exposição SPHEREx tem orientação própria (o detector gira no céu), e o recorte IBE é cortado nos eixos do detector e na borda dele. Sem uma grade comum, não é possível combinar épocas pixel a pixel, e a animação "gira".

**Decisão tomada:**

1. **Quadro comum:** projeção TAN centrada no alvo (na posição propagada, quando há movimento próprio), norte para cima e leste à esquerda, escala nativa de 6,15″/px, sem superamostragem, com lado igual ao FOV.
   - Reamostragem bilinear quando os 4 vizinhos são válidos; caso contrário, o pixel mais próximo.
   - O recorte IBE é pedido com 1,5× o FOV (mais que √2), para cobrir o quadro em qualquer rotação do detector.
2. **Sem dados ≠ céu escuro:** a área fora do detector fica transparente no PNG; pixels inválidos dentro do detector (núcleo saturado, pixel defeituoso) recebem a cor #B03060.
3. **Cobertura prevista:** `metadata.coverage_fraction` é a fração do quadro dentro do polígono `s_region`, calculada sem baixar a imagem.
4. **`GET /api/coverage`:** quadros completos e parciais para 1, 2, 3, 5, 10, 15 e 30′, com pixels por lado, custo estimado (KB da extensão IMAGE), FOV recomendado e deslocamento do alvo na janela observada.
   - Regra do FOV recomendado: o menor da lista que seja ≥ max(3′, 4× o deslocamento do alvo).
5. **`GET /api/composite`:**
   - `op=mean` faz a média de até 40 quadros do **mesmo detector**, para melhorar o sinal-ruído.
   - `op=diff` calcula média(A) − média(B).
   - A mediana de cada quadro é subtraída antes, porque o fundo zodiacal muda entre épocas.
   - Misturar detectores é recusado: cada detector vê outra faixa do infravermelho.

**Limitações:**

- Dentro de um detector o comprimento de onda varia com a posição (filtro linear variável). Como a posição do alvo no detector muda de uma exposição para outra, a média "por detector" mistura bandas vizinhas desse detector: é uma imagem de banda larga, não de uma única banda.
- A diferença mostra mudança aparente. Variações de PSF entre exposições e resíduos de fundo também aparecem nela, então não é uma detecção automática de movimento.
- A reamostragem suaviza levemente o ruído.

**Responsável:** Liderança técnica.

---

## DECISÃO 016 — Contaminação (FLAGS) e espectro de um ponto

**Data:** 15/11/2026

**Assunto:** Itens do desafio: "exibir metadados como indicadores de contaminação" e "gerar espectros instantaneamente".

**Base verificada** (pesquisa com dados reais e Explanatory Supplement v2.0, https://irsa.ipac.caltech.edu/data/SPHEREx/docs/SPHEREx_Expsupp_QR.pdf):

- **FLAGS:**
  - Bitmask com 23 bits nomeados no próprio cabeçalho (`MSKN/MSKM/MSKD`), conforme a Tabela 16.
  - `SOURCE` marca ~51% dos pixels e é informativo, não defeito.
- **WCS-WAVE:**
  - Tabela de 1 linha (pontos de controle de λ e largura de banda).
  - É idêntica em todas as exposições de um detector com a mesma calibração; vem inteira no recorte, e só o `CRPIX*W` muda.
  - Fica no **fim** do arquivo, depois da `EPSF` de 3,9 MB.
- **Ordem dos HDUs:** PRIMARY, IMAGE, FLAGS, VARIANCE, ZODI, EPSF, WCS-WAVE.

**Decisão tomada:**

1. Os recortes IBE são lidos até `VARIANCE` (≈ 3× o tamanho da `IMAGE`). O download completo é lido até `FLAGS`.
2. `FLAGS` e `VARIANCE` são projetadas no quadro comum pelo pixel mais próximo.
   - `GET /api/observations/{id}/quality` informa as flags no alvo (caixa 3×3) e a fração de pixels de cada flag.
   - `/api/composite` exclui os pixels contaminados.
3. **λ de cada exposição:**
   - É a `WCS-WAVE` avaliada no pixel do detector onde o alvo cai, pelo método do tutorial oficial: `WCS(hdr, fobj, key='W')` com `sip=None`.
   - A tabela é obtida por HTTP Range com os últimos 11.520 bytes do produto.
   - Ela é baixada uma vez por (detector, diretório de processamento `l2b-…`).
4. **`GET /api/spectrum`:**
   - Gera um ponto por exposição (até 60, distribuídas pelos 6 detectores).
   - Fluxo = média na abertura (raio padrão de 9″) menos a mediana de um anel de 2 a 3 raios. Erro calculado pela `VARIANCE`. Cada ponto traz as flags da abertura.

**Evidência:**

- O λ calculado só com a cauda do arquivo é idêntico ao do método oficial em 3 recortes reais: D3 centro 2,36218 µm, D6 4,96672 µm e D3 deslocado 2,08114 µm.
- Ao vivo, WISE 0855: as exposições cobrem 0,88–5,00 µm. Os únicos valores anômalos estavam sinalizados: 1,514 µm com TRANSIENT e 4,294 µm com OUTLIER+HALO. O alvo não é detectado em exposições únicas com abertura de 9″.
- No navegador: 42 pontos, 7 com contaminação.

**Limitações:**

- A `WCS-WAVE` é **aproximada**: o suplemento (§4.3.1) recomenda CWAVE/CBAND dos arquivos `spectral_wcs_N` para uso científico, e esses arquivos não foram localizados.
- O fluxo é brilho superficial médio na abertura, sem correção de PSF nem de abertura. Serve para comparar a forma do espectro, não como fotometria absoluta.
- O bit 29 (SATELLITE_HALO) consta do suplemento, mas não do cabeçalho testado.

**Responsável:** Liderança técnica, com validação científica pendente (Integrante 2).

---

## DECISÃO 017 — Site público resiliente: modo demonstração, mapa com fallback e ajuda contextual

**Data:** 15/11/2026

**Contexto:** O SIA do IRSA ficou instável o dia inteiro (502 e timeouts), e os servidores do CDS (alasky, HiPS SPHEREx, aladin.cds) também caíram. A ferramenta precisa servir ao público mesmo assim.

**Decisão tomada:**

1. **Modo demonstração com dados reais** (`src/frontend/demo/`, gerado por `data/scripts/17_export_demo.py`):
   - Contém WISE 0855 (50 observações, lista de uma resposta SIA salva) e Estrela de Barnard (354 observações, SIA ao vivo).
   - Ele é oferecido quando a busca falha ou o servidor está inacessível, e fica acessível por `?demo=<id>`.
   - A tela mostra sempre a data em que o exemplo foi salvo.
2. **Erro vira alternativa:** quando a busca falha, a página mostra um painel com:
   - os exemplos salvos;
   - nova tentativa automática com contagem regressiva e opção de cancelar;
   - o mapa do céu;
   - os dados fictícios, só para testar a interface.

   Falhas de imagem e de espectro oferecem "tentar de novo" ou "próxima observação".
3. **Mapa:**
   - O script do Aladin vem primeiro do jsdelivr, com limite de 8 s por fonte.
   - A disponibilidade do fundo HiPS é verificada antes do uso, na ordem SPHEREx (CDS) → AllWISE → 2MASS → DSS2 (IRSA).
   - O aviso informa qual fundo está em uso. Medido: o mapa abriu em 1,5 s com AllWISE, enquanto o HiPS SPHEREx dava 404.
4. **Detectores:**
   - Clique simples isola um detector; Ctrl, ⌘ ou Shift soma outro.
   - Cada botão mostra a contagem e a faixa real tirada dos metadados (ex.: D3 1,63–2,43 µm).
5. **Comparador de duas datas:** modos cortina e piscar.
6. **Atalhos de teclado:** ←/→ trocam o quadro e espaço reproduz/pausa.
7. **Glossário:** 53 termos com ícone "?" acessível por mouse, teclado e toque.
8. **Identidade visual:**
   - Céu estrelado gerado no navegador.
   - 3 imagens NASA/JPL-Caltech (PIA26600, PIA26280, PIA26531), com crédito e origem em `src/frontend/assets/CREDITS.md`.
   - Ícone original estilizado do SPHEREx, sem insígnia da NASA nem logotipo da missão, e menu com "feixe infravermelho".

**Evidência (diferença entre épocas):** na Estrela de Barnard com céu fixo, a diferença D1 entre 2025-08 e 2026-09 mostra o par claro (norte) e escuro (sul) do movimento próprio de ~10″/ano.

**Limitações:**
- **Lista parcial do WISE 0855:** o pacote veio de uma resposta SIA salva com no máximo 50 registros.
- **Espectro da Barnard inválido:** a estrela satura o SPHEREx, e todas as medidas vieram sinalizadas.
- **Pendente de revisão científica:** fatos do glossário vindos do conhecimento do agente — gelos por detector, contagem de fontes do Gaia, bandas do AllWISE, definição de MJD e significado de "QR".

**Responsável:** Liderança técnica e de interface.

---

## DECISÃO 019 — "Décadas": o mesmo campo do céu de 1950 ao SPHEREx, e correção da posição do WISE 0855

**Data:** 15/11/2026

**Contexto:** A equipe pediu para ver, com as imagens salvas, o movimento das estrelas ao longo do tempo, sem perder o foco no SPHEREx. Pediu também que os filtros D1–D6 funcionem nas imagens baixadas.

As imagens de referência da DECISÃO 018 (item 7) eram centradas no alvo em cada data. Isso deixava a estrela parada e escondia o movimento.

**Decisão tomada:**

1. **Campo fixo** (`data/scripts/19_motion_timeline.py`): todas as imagens de um alvo mostram o mesmo pedaço do céu, com o mesmo centro e o mesmo FOV, norte para cima.
   - O centro é o ponto médio do trajeto; o FOV é o trajeto + 3′ (máx. 20′).
   - Imagens DSS1/DSS2 (vermelho e IR), 2MASS K, WISE W1/W2, com a data real (`obsdate`) informada pelo IRSA Finder Chart.
   - O 2MASS é omitido acima de 12′, porque o serviço devolve uma imagem preta; a omissão fica registrada em `skipped`.
2. **SPHEREx no mesmo campo:** 3 exposições por detector, D1–D6 (a mais antiga, a do meio e a mais recente), escolhidas dos pacotes salvos.
   - Cada uma é recortada de novo no IBE pelo `original_file_url` e reamostrada com o `project_to_frame` do backend.
   - **Não depende do SIA**, a parte do IRSA que vive caindo.
3. **Posição prevista:** a marca e o trajeto vêm do movimento próprio do catálogo, propagado pelo `propagate_position` do backend para a data de cada imagem. Nada é ajustado às imagens.
4. **Interface** (`js/motion.js`):
   - **Aba "Décadas"** no visor de Observações, ao lado de Sequência, Comparar e Combinar. Só aparece quando a região é um alvo com dados salvos, e tem atalho de volta para a sequência SPHEREx mês a mês.
   - **Controles:** filtros "Outros telescópios" e D1–D6, eixo do tempo proporcional aos anos, reproduzir, "piscar 1ª ↔ última", trajeto previsto e as setas do teclado.
   - **Busca falha:** o mesmo player aparece no painel de alternativas (`js/refimages.js`), com acesso ao pacote SPHEREx salvo, que mantém os filtros D1–D6 do visor principal.
5. **Pacotes SPHEREx reais novos:** ε Indi (448 observações) e RW Aurigae, com `17_export_demo.py`.
   - R Draconis (957 observações) exportado depois que o SIA voltou; parte dos produtos é da coleção QR3.
   - O `17_export_demo.py` passou a preservar `motion/` e `motion.json` ao refazer um pacote.
6. **Substitui o item 7 da DECISÃO 018:** o script 18 e as imagens centradas foram removidos.

**Evidência:**
- **Estrela de Barnard** (13,2′ de trajeto em 76 anos, campo de 17′): nas 22 imagens (4 de outros telescópios + 18 SPHEREx), o centro da estrela, medido no núcleo saturado, fica a ≤ 6,6″ da posição prevista, com mediana de 2,3″.
- **ε Indi:** trajeto de 2,6′ desde 1993, campo de 6′.
- **RW Aurigae:** 0,03′ em 74 anos. O player avisa que o movimento não aparece e que a mudança a observar é de brilho.

**Correção do WISE 0855** (achado durante este trabalho):
- **O erro:** a coordenada do desafio é a da época da descoberta (~2010), não J2000.
- **A fonte primária:** o SIMBAD (Kirkpatrick et al. 2021) dá a posição J2000 133,81890825 / −7,247048 e o mesmo μ que já usávamos.
- **A confirmação nas imagens:** a fonte com maior excesso W2−W1 no campo AllWISE fica a 1,4″ da posição corrigida. Com a antiga, a distância era de 84″.
- **O que foi atualizado:** `TARGETS` (2025,35: 133,761244 / −7,242304), os testes (**199 passed, 2 skipped**) e o §3.3 de `docs/science/target-catalog.md`.
- **Pacote salvo:** o do WISE 0855 foi regenerado a partir da resposta SIA salva. O anterior tinha sido recortado 85″ fora do centro.

**Limitações:**
- O WISE 0855 não aparece no DSS (luz visível) nem em exposições únicas do SPHEREx. Isso é esperado para uma anã marrom Y, e o player avisa que um alvo fraco numa banda pode não aparecer.
- O brilho e a resolução variam entre levantamentos, então a comparação é de posição, não de fotometria.
- A data do AllWISE é a informada pelo serviço, mas a imagem soma exposições de 2010–2011.

**Responsável:** Liderança técnica. **Validação pendente:** Integrante 2 (época da posição do SIMBAD e o texto do §3.3).

---

## DECISÃO 018 — Interface em páginas, modo cinema, outras bases e imagens salvas dos 5 alvos

**Data:** 15/11/2026

**Contexto:** Pedidos da equipe:
- a landing em seções parecia engessada;
- a mensagem "Não foi possível conectar ao servidor…" assustava o usuário;
- a sonda do menu devia ser uma imagem real do SPHEREx;
- o visor de observações precisava de mais espaço;
- o site devia oferecer outra base (WISE) e mostrar imagens mesmo quando o IRSA falha.

O trabalho foi feito por 3 agentes em worktrees, com escopos de arquivo separados, e consolidado por merge em `feat/sia-integration`.

**Decisão tomada:**

1. **Páginas** (`js/router.js`):
   - Uma seção por vez, endereçada por hash (`#busca`, `#observacoes`, `#ceu`, `#mapa`, `#espectro`, `#galeria`).
   - O botão voltar funciona, `?demo=` continua valendo, e depois de uma busca o site vai para Observações.
   - Sem JS, ou com `?embed=1`, tudo continua visível.
   - API: `spxRouter.go(id)` e o evento `spx:page`.
   - Acoplamento conhecido: o router intercepta `scrollIntoView` e `history.replaceState` para não editar app.js.
2. **Sonda real com feixe** (`js/theme.js`, `css/theme.css`):
   - Usa o render oficial "Sectional View of the SPHEREx Spacecraft (Transparent)" (Caltech/IPAC, NASA/JPL-Caltech). O PNG já é transparente; só foi reduzido.
   - O uso segue a política de imagens do site, com crédito em `assets/CREDITS.md`.
   - O feixe infravermelho sai da sonda e forma a navbar; no celular, a sonda é o botão do menu.
3. **Tema:** fundo `#03050b` e painéis como cartões flutuantes. Contraste AA calculado, pior caso 4,73:1.
4. **Modo cinema** (`js/cinema.js`, `css/cinema.css`):
   - A imagem é a protagonista e os controles ficam numa barra no estilo player.
   - Abas Sequência | Comparar | Combinar, marcas de mês na linha do tempo e faixa de miniaturas, só com imagens já baixadas.
   - Tela cheia (`F`/`C`, com fallback para um overlay fixo), zoom e arrasto sem quebrar a marcação do espectro.
5. **Mensagem amigável:** a falha de conexão vira um status neutro (classe `info`) que oferece:
   - exemplo salvo;
   - outras bases;
   - nova tentativa.
6. **Outras bases** (`js/surveys.js`):
   - WISE W1–W4, 2MASS J/H/K e DSS2, via IRSA Finder Chart. O hips2fits do CDS estava em 404.
   - Busca por nome via Sesame, com espelho da CfA.
   - Visualizador Aladin com o mesmo HiPS do mapa.
   - Sempre com o aviso de que é outra missão, sem linha do tempo.
7. **Imagens salvas dos 5 alvos** (`data/scripts/18_reference_images.py`, `js/refimages.js`):
   - Imagens DSS1/DSS2 vermelho, 2MASS J/H/K e WISE W1–W4, baixadas do IRSA Finder Chart e servidas como arquivos estáticos (`demo/<id>/ref/`, manifesto `demo/reference.json`).
   - Quando a busca falha, o painel de alternativas mostra as imagens do alvo mais próximo (≤ 10′) ou uma galeria dos alvos.
   - Cada imagem é **centrada no alvo propagado para a data da própria imagem**: o `obsdate` informado pelo Finder Chart é reconferido na posição propagada. Isso usa o mesmo `propagate_position` do backend.
   - Os pacotes SPHEREx reais dos alvos que faltavam foram exportados com `17_export_demo.py`.

**Evidência:**
- Estrela de Barnard: a placa DSS1 é de 09/07/1950 e a DSS2 vermelho de 16/06/1991. A estrela aparece no centro das duas imagens. Sem a propagação, ela estaria ~13′ fora do quadro de 3′ em 1950.
- Finder Chart: 200 `image/png`, 131×131 px para 3′.

**Limitações:**
- O AllWISE soma exposições de 2010–2011. A data usada é a que o serviço informa para o ladrilho.
- As datas DSS são de placas individuais.
- As imagens de referência são de outros telescópios e servem só para orientação; não entram em nenhuma medida.
- A tela cheia nativa não foi testada no navegador embutido, só o overlay.
- A animação do feixe foi conferida em quadros congelados.

**Responsável:** Liderança técnica e de interface.

---

## DECISÃO 006 — Quadro de tarefas local provisório

**Data:** 14/11/2026

**Assunto:** Onde registrar e acompanhar as tarefas do projeto.

**Contexto:** `docs/team/workflow.md` §2 determina o uso de GitHub Issues e GitHub Projects. A auditoria verificou que o repositório local **não possui remote configurado** e que commits e envios ao GitHub estão proibidos nesta fase pela regra 11 das regras de execução e pela §6 do `AGENTS.md`. Não existe, portanto, onde hospedar o quadro no formato previsto no workflow.

**Decisão tomada:** Criar `docs/board.md` como quadro de tarefas provisório, contendo identificador, objetivo, agente responsável, responsável humano, arquivos envolvidos, dependências, critérios de conclusão, estado e as evidências do marco. Ao ser configurado o repositório compartilhado, o quadro será transferido para GitHub Issues/Projects e este documento será mantido apenas como histórico da fase de preparação.

**Justificativa:** As regras de execução exigem um quadro de tarefas com estados explícitos e as evidências precisam ser rastreadas desde já. Nenhuma informação se perde na migração futura.

**Consequências:**

- O quadro de tarefas deixa de depender de infraestrutura externa não disponível.
- As decisões do quadro que afetarem escopo, arquitetura ou critérios científicos continuam registradas neste documento e em `docs/progress.md`.

**Responsável:** Liderança técnica.

---

## DECISÃO 011 — Conversão de `em_min`/`em_max` para nanômetros

**Data:** 14/11/2026

**Assunto:** Unidade de `wavelength_min_nm`/`wavelength_max_nm` publicada pela API.

**Contexto:** Na resposta real do IRSA SIA v2 (`tests/backend/fixtures/sia_spherex_dr1_wise0855.xml`), `em_min`/`em_max` são declarados com `unit="m"` (ex.: `1.63010e-06`), como define o padrão IVOA ObsCore. O serviço copiava o valor sem conversão, rotulando metros como nanômetros.

**Decisão tomada:** `wavelength_to_nm` (`src/backend/app/services/observation_service.py`) aplica a regra:

1. Com `band_units` (ou alias) reconhecido — `m`, `um`/`µm`/`micron`, `nm`, `angstrom`/`Å` — converte a partir dessa unidade.
2. Unidade presente mas desconhecida → `null` (o valor não é adivinhado).
3. Sem unidade, valor lido de alias cujo nome já indica nm (`em_min_nm`, `wavelength_min_nm`, ...) é mantido.
4. Sem unidade nos demais casos → assume metros (IVOA ObsCore).

**Justificativa:** Verificação na resposta real; o contrato da API (nomes `*_nm`) é mantido.

**Consequências:** A primeira observação real passa a mostrar 1630,1–2434,6 nm. O teste sintético com `band_units = "um"` passou a esperar 900 nm.

**Responsável:** Liderança técnica.

---

## DECISÃO 013 — Pré-filtro de sobreposição pelo polígono `s_region`

**Data:** 14/11/2026

**Assunto:** Implementar o item 6 da DECISÃO 007 (produtos que só tocam a borda do cone de busca).

**Contexto:** O SIA devolve toda imagem que **intersecta** o cone. Parte delas não contém a posição pedida e o recorte falhava depois com `422 Arrays do not overlap`. A DECISÃO 007 previa o critério `angsep ≤ s_fov/2`, mas `s_fov` é o diâmetro de um círculo e o detector é um quadrilátero de ~3,5°: o círculo não descreve as bordas. A resposta real traz `s_region` (`POLYGON ICRS` com os 4 cantos do detector) em **todos** os produtos consultados.

**Decisão tomada:**

1. Manter apenas os produtos cujo polígono `s_region` **contém a posição pedida** (teste ponto-em-polígono na projeção gnomônica centrada na posição; `sky_coverage.py`). Isso substitui o critério `s_fov/2`.
2. Produto sem `s_region` legível é **mantido** (nada é descartado sem evidência); o tratamento de 422/500 no recorte continua valendo.
3. O filtro roda depois do cache de consultas, então vale também para consultas já em cache.
4. Se nenhum produto cobrir a posição, a API responde `NO_OBSERVATIONS_FOUND`.

**Evidência (IRSA ao vivo, FoV 3′, 14/11/2026):**

| Alvo | Produtos SIA | Mantidos | Descartados |
|---|---|---|---|
| ε Indi | 517 | 460 | 57 |
| Estrela de Barnard | 380 | 358 | 22 |
| WISE 0855 | 259 | 258 | 1 |

- Amostra de 30 recortes de produtos mantidos: 29 × HTTP 200 e 1 × 503 (servidor ocupado), **nenhum 422**.
- Produtos descartados (52 testados): **todos** os 422 observados estavam entre eles. Os que ainda devolvem HTTP 200 têm a posição fora do detector por menos de ~1,5′–1,8′ (metade do FoV): o IBE entrega um recorte **parcial**, em que o centro pedido cai fora da imagem.

**Consequências:**

- Os recortes parciais em que o alvo está fora do detector deixam de aparecer na sequência. É intencional: um quadro sem o alvo não é uma observação dele.
- Recortes parciais com o alvo **dentro** do detector, perto da borda, continuam aparecendo (parte do quadro pode vir vazia).
- Limitação: a exatidão do `s_region` em escala de pixel não foi medida; o caso mais próximo da borda estava a 0,14′ (~1,4 px) do lado de fora. Um produto pode ser descartado ou mantido indevidamente nessa margem.

**Responsável:** Liderança técnica.