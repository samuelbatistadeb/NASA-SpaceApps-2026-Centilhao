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