# Plano de implementação — SPHEREx Explorer (backend)

## 1. Objetivo

Documentar o plano executável de implementação do backend FastAPI do SPHEREx Explorer,
compatível com:

- `docs/architecture/system.md` (arquitetura aprovada).
- `docs/architecture/api-contract.md` (contrato de API aprovado).
- `docs/architecture/requirements.md` (RF-001..RF-013, RNF-001..RNF-010, RC-001..RC-005).
- `docs/science/data-sources.md` (fontes IRSA/SPHEREx).
- `docs/science/validation.md` (critérios de validação científica).

Este documento é um artefato de implementação. Ele **não substitui** `docs/decisions.md`,
que é mantido pelo Integrante 1 (Liderança técnica).

**Estado do plano:** Fase 1 (backend esqueleto funcional, sem rede real).
**Data:** 14/11/2026.

---

## 2. Ambiguidades resolvidas

| # | Ambiguidade | Decisão adotada | Justificativa |
|---|---|---|---|
| A-01 | `system.md` §7 propõe `backend/app/...` e `backend/tests/`, mas o repositório já contém `src/backend/app/` e `tests/backend/` (diretórios vazios, criados na preparação). | Manter `src/backend/app/` como pacote da aplicação e `tests/backend/` como raiz dos testes. | Evita duplicar a estrutura e respeita o repositório existente. `src/` é a raiz do código-fonte; `tests/` a raiz dos testes. |
| A-02 | `system.md` §7 propõe `cutout_service.py` separado de `fits_processor.py`; a tarefa da Fase 1 pede recorte dentro de `irsa_client.py`/`fits_processor.py`. | Criar `app/services/cutout_service.py` como módulo de **decisão de estratégia** (serviço remoto de cutout vs. download local + `Cutout2D`), mantendo `irsa_client.py` (transporte/consulta) e `fits_processor.py` (abrir FITS, metadados, recorte local, PNG). | Preserva a arquitetura aprovada e mantém responsabilidades únicas: *rede*, *estratégia*, *processamento*. |
| A-03 | Contrato §3: parâmetros opcionais `start_date`, `end_date`, `band` "somente deverão ser implementados após confirmação de compatibilidade". | **Não** implementados no MVP. Se enviados, a API responde `INVALID_PARAMETERS` (HTTP 400) informando que o filtro ainda não foi validado cientificamente. | Ignorar silenciosamente parâmetros daria ao usuário a impressão de que o filtro foi aplicado — falsa impressão científica. |
| A-04 | Contrato não define limites de `fov_arcmin`; RF-003 remete às "limitações do arquivo científico e da aplicação". | Limites **de aplicação** (não científicos), configuráveis por env: `SPHEREX_MIN_FOV_ARCMIN` (padrão `0.1`) e `SPHEREX_MAX_FOV_ARCMIN` (padrão `120.0`). O valor padrão é defensivo e **não** afirma nada sobre o SPHEREx. | O endpoint real ainda não foi verificado; limites arbitrários fixos no código seriam difíceis de revisar. Configuração por env permite ajuste imediato após a validação do Researcher. |
| A-05 | Contrato não define o formato do `id` interno da observação. | `id` determinístico e estável: `"obs_" + sha1(canonical_product_key)[:16]`, onde `canonical_product_key` combina o identificador real do produto + banda + detector. O identificador original do produto é preservado em `metadata.product_id` (RNF-007, rastreabilidade). | Um id aleatório quebraria a URL `/api/images/{id}` entre requisições. O sha1 curto é opaco, seguro em URL e reproduzível. |
| A-06 | Contrato §5 mostra `metadata` com apenas `product_id` e `quality`. | `ObservationMetadata` contém `product_id` e `quality` **com os mesmos nomes e tipos** e acrescenta campos **todos opcionais/nulos** exigidos pelo contrato §6 (data original, instrumento, WCS, flags de contaminação, origem, URL do FITS original, release, normalização visual). | O contrato §6 exige preservação de metadados adicionais; todos os campos novos são `null` quando ausentes — nunca inventados (RC-005). O frontend pode ignorar campos extras. |
| A-07 | Contrato §9 exige ordem cronológica crescente, mas não define o que fazer com observações sem data. | Observações **sem data interpretável** vão para o fim da lista, com `observed_at = null` e `metadata.timing_status = "unresolved"`. O valor bruto original é preservado em `metadata.observed_at_source`. | Nunca inventar datas. Descartar observações silenciosamente também seria perda de informação (RNF-010). |
| A-08 | Contrato §8 define os códigos de erro mas não os status HTTP. | Mapeamento fixo: `INVALID_PARAMETERS`→400, `NO_OBSERVATIONS_FOUND`→404, `SOURCE_UNAVAILABLE`→503, `PROCESSING_ERROR`→500, `IMAGE_NOT_FOUND`→404, `INTERNAL_ERROR`→500. | O contrato exige que "os códigos HTTP deverão refletir corretamente a natureza do erro". 503 é o status correto para fonte externa indisponível. |
| A-09 | Contrato §7: a imagem renderizada "deverá ser identificada como representação visual processada". | A resposta de `/api/images/{id}` inclui os cabeçalhos `X-SpherEx-Image-Type: visual-representation` e `X-SpherEx-Normalization: <descrição do estiramento>`; o metadado `metadata.visual_normalization` descreve o método. | Identificação explícita, conforme contrato §7 e `validation.md` §8 ("a normalização visual não deverá ser confundida com uma medição fotométrica"). |
| A-10 | `system.md` §9 prevê `data/cache/`; `data/**` está fora da alçada de edição desta fase. | Cache em disco padrão `<repo_root>/data/cache/spherex`, sobrescrevível por `SPHEREX_CACHE_DIR`. Criado em tempo de execução; nenhum arquivo versionado de `data/` é alterado. | Mantém a arquitetura aprovada sem editar arquivos fora da alçada. **Pendência reportada:** `.gitignore` não cobre `data/cache/` (não pode ser alterado nesta fase). |
| A-11 | `requirements.txt` na raiz vs. `src/backend/requirements.txt` previsto em `system.md` §7. | Manter **um único** `requirements.txt` na raiz do repositório (alçada desta fase) e um `src/backend/pyproject.toml` apenas com metadados e configuração de pytest para o pacote do backend. | Evita duas listas de dependências divergentes. O `pyproject.toml` do backend é declarado como "se necessário" na alçada da tarefa. |
| A-12 | Como garantir que o `import app` funcione nos testes sem instalar o pacote. | `tests/backend/conftest.py` insere `src/backend` no `sys.path` de forma determinística, resolvendo o caminho a partir de `__file__`. | Solução sem `pip install -e .`, sem dependência de plugins de pytest e funcionando com `pytest` executado de qualquer diretório. |

---

## 3. Estrutura final de arquivos do backend

```text
src/backend/
├── README.md                     # Como rodar em Windows PowerShell
├── pyproject.toml                # Metadados do pacote + config do pytest (backend)
└── app/
    ├── __init__.py
    ├── main.py                   # FastAPI: CORS dev, handlers de erro, /api/health
    ├── api/
    │   ├── __init__.py
    │   ├── errors.py             # Exceções de domínio + mapeamento para o contrato
    │   └── observations.py       # Router: GET /api/observations, GET /api/images/{id}
    ├── core/
    │   ├── __init__.py
    │   └── config.py             # Settings via env com prefixo SPHEREX_
    ├── schemas/
    │   ├── __init__.py
    │   └── observation.py        # Modelos Pydantic do contrato
    └── services/
        ├── __init__.py
        ├── cache.py              # Cache em disco (JSON + PNG), TTL, chave por consulta
        ├── cutout_service.py     # Decisão: cutout remoto vs. download local + Cutout2D
        ├── fits_processor.py     # Astropy: metadados, Cutout2D, PNG (matplotlib Agg)
        ├── irsa_client.py        # Cliente IRSA/SIA2 com transporte injetável
        └── observation_service.py # Orquestração: consulta, ordenação, mapeamento

tests/backend/
├── conftest.py                   # sys.path + fakes de transporte + fixtures sintéticas
├── test_config.py                # Leitura de env, validação de faixas
├── test_irsa_client.py           # Consulta, params, retry, timeout, erros, parser SIA2
├── test_observation_service.py   # Ordenação cronológica, mapeamento, sem resultados
├── test_fits_processor.py        # Metadados FITS, Cutout2D, PNG (tamanho/formato/não-vazio)
├── test_cutout_service.py        # Escolha de estratégia e download local
├── test_cache.py                 # Chave, TTL, hit/miss
├── test_api_observations.py      # TestClient: com resultados, sem resultados, inválido, fonte indisponível
└── test_api_images.py            # IMAGE_NOT_FOUND e PNG de um FITS sintético
```

**Fora do escopo desta fase (não criar agora):** `src/backend/app/services/archive_browser.py`,
integração Gaia/WISE, comparação/subtração de imagens, banco de dados.

---

## 4. Dependências Python

Versões fixadas a partir de `pip freeze` do ambiente `.venv` (Python 3.12.5, Windows 11).

| Pacote | Versão | Razão |
|---|---|---|
| `fastapi` | ver `requirements.txt` | Framework da API (RF-004..RF-013, `system.md` §3). |
| `uvicorn[standard]` | idem | Servidor ASGI para rodar localmente (`python -m uvicorn`). |
| `pydantic` | idem | Modelos do contrato de API (`api-contract.md` §5, §8); `Field(description=...)`. |
| `starlette` | idem | Dependência direta do FastAPI; usada pelos `TestClient`. |
| `httpx` | idem | **Transporte HTTP do cliente IRSA** + `TestClient` do FastAPI. Não há dependência de `requests` no código do projeto. |
| `astropy` | idem | Leitura FITS, WCS, `Cutout2D`, VOTable (`astropy.io.votable`) para a resposta SIA2. |
| `numpy` | idem | Manipulação dos arrays de imagem e normalização visual. |
| `matplotlib` | idem | Renderização PNG (backend `Agg`, sem display). |
| `astroquery` | idem | Previsto em `system.md` §3; mantido como dependência declarada para a Fase 2 (consultas via TAP/footprints), ainda **não importado** pelo código do MVP. |
| `pyvo` | idem | Previsto em `system.md` §3; mantido para a Fase 2 (SIA2 via PyVO). Não usado no MVP para evitar duplicar o parser já implementado sobre `astropy.io.votable`. |
| `pytest` | idem | Testes unitários e de API. |
| `scipy` | idem | Dependência transitiva obrigatória do Astropy (versão compatível pinada). |

**Removidos:** `jupyterlab` e `ipykernel` — não são necessários ao backend nem aos testes e
aumentam significativamente o tempo e o tamanho da instalação.
**Decisão para registro pelo Integrante 1 em `docs/decisions.md`:**
*"Remover `jupyterlab` e `ipykernel` do `requirements.txt` do MVP; os notebooks de exploração
continuam possíveis fora do ambiente de produção."*

---

## 5. Estratégia do cliente IRSA

### 5.1 Configuração (base URL vindo de configuração/env)

`app/core/config.py` lê variáveis de ambiente com prefixo **`SPHEREX_`**:

| Variável | Padrão | Uso |
|---|---|---|
| `SPHEREX_IRSA_SIA2_URL` | *(vazio)* | Endpoint SIA2 oficial — **PENDENTE de verificação pelo Researcher**. |
| `SPHEREX_IRSA_CUTOUT_URL` | *(vazio)* | Endpoint de cutout do IRSA (se existir). |
| `SPHEREX_IRSA_DATA_BASE_URL` | *(vazio)* | Base para download do FITS original (derivada do `access_url` retornado pelo SIA2 quando presente). |
| `SPHEREX_HTTP_TIMEOUT_SECONDS` | `30` | Timeout por requisição. |
| `SPHEREX_HTTP_MAX_ATTEMPTS` | `3` | Tentativas totais (retry só para falhas transitórias). |
| `SPHEREX_USER_AGENT` | `SPHERExExplorer/0.1 (NASA Space Apps Challenge 2026)` | User-Agent. |
| `SPHEREX_MAX_CUTOUT_PIXELS` | `2048` | Guarda de segurança para o tamanho do recorte local. |
| `SPHEREX_MAX_FITS_BYTES` | `536870912` (512 MiB) | Guarda de segurança para download de FITS. |
| `SPHEREX_MIN_FOV_ARCMIN` / `SPHEREX_MAX_FOV_ARCMIN` | `0.1` / `120.0` | Limites de aplicação do campo de visão. |
| `SPHEREX_CACHE_DIR` | `<repo>/data/cache/spherex` | Diretório do cache em disco. |
| `SPHEREX_CACHE_TTL_SECONDS` | `3600` | Validade das entradas de cache. |
| `SPHEREX_CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:8000` | Origens permitidas (somente localhost em desenvolvimento). |
| `SPHEREX_PORT` | `8000` | Porta do servidor. |

**Nenhuma credencial é gravada no código.** Se um serviço exigir autenticação, a chave será lida
exclusivamente de variável de ambiente (`.env` já está no `.gitignore`).

### 5.2 Constantes nomeadas e estado "pendente"

Em `app/services/irsa_client.py`:

```python
IRSA_SIA2_BASE_URL: str = ""    # PENDENTE: URL oficial SIA2 do SPHEREx não verificada
IRSA_CUTOUT_BASE_URL: str = ""  # PENDENTE: URL oficial de cutout do IRSA não verificada
```

O padrão é **vazio de propósito**: enquanto o Researcher não confirmar a URL oficial,
`SPHEREX_IRSA_SIA2_URL` fica vazio e o cliente levanta `SourceUnavailableError`,
resultando em **HTTP 503 / `SOURCE_UNAVAILABLE`** — nunca em observações fictícias.
O comentário `TODO(RESEARCHER-PENDING)` marca cada ponto a ser completado.

### 5.3 Transporte injetável

```python
class HttpTransport(Protocol):
    def request(self, method: str, url: str, *, params=None, headers=None, timeout=None) -> HttpResponse: ...
```

- `HttpResponse`: `status_code: int`, `content: bytes`, `headers: dict`, `text: str`.
- `HttpxTransport`: implementação real sobre `httpx.Client` (injeção de `httpx.Client` permite
  `MockTransport` do próprio httpx nos testes).
- `FakeTransport` (em `tests/backend/conftest.py`): devolve respostas **sintéticas** pré-definidas
  e registra as requisições. Nenhum teste toca a rede.

O `IrsaClient` recebe `transport` no construtor; se não for informado, usa `HttpxTransport`.

### 5.4 Timeout, retry e user-agent

- **Timeout:** aplicado por requisição via `SPHEREX_HTTP_TIMEOUT_SECONDS` (mesmo em streaming).
- **Retry:** laço manual (sem dependência extra). Só re-tenta em falhas **transitórias**:
  timeout, erro de conexão, HTTP `429`, HTTP `5xx`. Espera exponencial
  (`1s, 2s, 4s` — com jitter determinístico de 0 para os testes; o `sleep` é injetável).
  HTTP `4xx` (exceto `429`) **não** é repetido.
- **User-Agent:** sempre enviado, identificando o projeto e o desafio.

### 5.5 Tratamento de erro por modo de falha

| Modo de falha | Detecção | Exceção | Código da API | HTTP |
|---|---|---|---|---|
| Serviço não configurado (URL vazia) | verificação pré-requisito | `SourceUnavailableError` | `SOURCE_UNAVAILABLE` | 503 |
| Timeout de rede | `httpx.TimeoutException` | `SourceUnavailableError` | `SOURCE_UNAVAILABLE` | 503 |
| Erro de conexão / DNS | `httpx.TransportError` | `SourceUnavailableError` | `SOURCE_UNAVAILABLE` | 503 |
| HTTP 5xx / 429 (após retry) | status code | `SourceUnavailableError` | `SOURCE_UNAVAILABLE` | 503 |
| HTTP 4xx | status code | `SourceUnavailableError` | `SOURCE_UNAVAILABLE` | 503 |
| Corpo ilegível (não é VOTable nem JSON) | parser | `MalformedResponseError` (subclasse de `SourceUnavailableError`) | `SOURCE_UNAVAILABLE` | 503 |
| Resposta válida e vazia | lista vazia | `NoObservationsFoundError` | `NO_OBSERVATIONS_FOUND` | 404 |
| Parâmetros fora das faixas | validação Pydantic/FastAPI | `InvalidParametersError` | `INVALID_PARAMETERS` | 400 |
| FITS corrompido / erro do Astropy | exceção do `astropy` | `ProcessingError` | `PROCESSING_ERROR` | 500 |
| Imagem ausente no cache e não gerável | verificação | `ImageNotFoundError` | `IMAGE_NOT_FOUND` | 404 |
| Exceção não esperada | handler global | `InternalError` | `INTERNAL_ERROR` | 500 |

Nenhum detalhe interno (traceback, host, caminho local) é devolvido ao cliente: a mensagem é
genérica e o detalhe técnico fica no log do servidor.

### 5.6 Parâmetros da consulta SIA2 (padrão VO, ainda não confirmado)

O `IrsaClient.query_by_position(ra_deg, dec_deg, radius_deg, fov_arcmin)` monta a consulta com
parâmetros do padrão SIA2/IVOA — `POS`, `SIZE`, `BAND`, `TIME` — e um `format` de resposta.
**Os nomes exatos dos parâmetros dependem do endpoint oficial e serão ajustados na Fase 2.**
Enquanto isso, a construção fica isolada em um único método
(`IrsaClient._build_sia2_params`), para que a correção seja pontual.

### 5.7 Interpretação da resposta

- Leitura de **VOTable** via `astropy.io.votable` (resposta padrão de um serviço SIA2).
- Leitura de **JSON** (fallback, para o caso de o serviço oficial responder JSON).
- Mapeamento tolerante: cada campo é procurado por uma lista de nomes padrão VO
  (`obs_publisher_did`, `obs_id`, `access_url`, `s_ra`, `s_dec`, `s_fov`, `t_min`, `t_max`,
  `mjd-obs`, `band_name`, `band_pass`, `instrument_name`, `detector_name`, `provenance`,
  `obs_release_date`, `quality`, ...). Ausente → `None`. **Nada é inventado.**
- `access_url` é validado: só `http`/`https` e apenas hosts permitidos (configurável) são
  aceitos para download (RNF-006).

---

## 6. Estratégia de recorte de imagem

### 6.1 Decisão entre serviço de cutout e download local

`app/services/cutout_service.py` decide **por configuração**, não por tentativa:

1. Se `SPHEREX_IRSA_CUTOUT_URL` estiver definido **e** o registro do produto indicar acesso ao
   serviço de recorte → **REMOTE_CUTOUT**: o backend pede o recorte ao serviço, que devolve FITS
   (ou PNG) já com a região correta. Menos bytes trafegados (RNF-002).
2. Caso contrário → **LOCAL_DOWNLOAD**: baixa o FITS original pelo `access_url` e aplica
   `astropy.nddata.Cutout2D` localmente.

A decisão é explícita e registrada em `metadata.cutout_strategy`, para que a origem do pixel
exibido seja auditável. O registro do produto traz o flag `cutout_service_ref` quando o SIA2 o
publica; se o serviço de cutout existir mas não for detectado no registro, o modo local é usado
(fallback seguro).

### 6.2 Recorte local (`Cutout2D`)

1. Abrir o FITS com `astropy.io.fits` (memória ou arquivo temporário).
2. Selecionar a HDU com dados 2D (preferir a extensão que contém `NAXIS=2`).
3. Se houver WCS (`header` com `CTYPE`/`CRVAL`), converter (RA, Dec) → pixel com `wcs_world2pix`;
   caso contrário, usar o pixel central (`NAXIS1/2 // 2`).
4. `Cutout2D(data, position=(y, x), size=n)` com `n` calculado a partir do
   `fov_arcmin` e da escala de pixels (`s_pixel_scale` do SIA2 ou `CDELT` do WCS).
   Se a escala não for conhecida, usar `SPHEREX_DEFAULT_CUTOUT_PIXELS` (padrão `256`) e
   registrar o critério em `metadata.cutout_pixel_size_source`.
5. `Cutout2D` com `wcs=` quando disponível → o recorte preserva coordenadas.
6. A escala de pixels usada **nunca** é inventada: se não vier do SIA2 nem do WCS, o valor é
   marcado como "assumido pela aplicação" em `metadata`.

### 6.3 Pré-visualização em PNG

- Backend matplotlib **`Agg`** (sem display).
- Estiramento **visual** por percentis: `vmin = percentil(1)`, `vmax = percentil(99)` dos valores
  finitos; colormap `gray`; NaN/inf → 0 (branco) na renderização.
- A escolha de percentis **não** é declarada como medida fotométrica: o método é gravado em
  `metadata.visual_normalization` e enviado no cabeçalho `X-SpherEx-Normalization`.
- Sem eixos, sem escala artificial, sem legenda — apenas a área da imagem.

### 6.4 Escala para JSON

- O PNG **não** é embutido no JSON. O JSON traz `image_url = "/api/images/{observation_id}"`.
- `GET /api/images/{observation_id}` devolve `image/png` (bytes), gerado sob demanda e cacheado
  em disco.
- `metadata` carrega a rastreabilidade: `product_id`, `original_file_url` (acesso ao FITS
  original), `cutout_strategy`, `cutout_size_pixels`, `visual_normalization`.

---

## 7. Normalização e ordenação temporal

### 7.1 Extração do instante de observação

Prioridade (primeiro valor válido encontrado):

1. `DATE-OBS` do cabeçalho FITS (quando o arquivo é aberto).
2. Coluna SIA2/VO `mjd-obs` (MJD) → data UTC.
3. Colunas SIA2/VO `t_min` / `t_max` (ISO 8601) → início e/ou fim.
4. `obs_release_date` — **data de publicação, NÃO de observação**: usada apenas em
   `metadata.observed_at_source` com `timing_status = "release_date_fallback"`, e nunca como
   instante de observação sem marcação.

### 7.2 Normalização

- Entrada → `datetime` com timezone UTC → serialização em ISO 8601 com `Z`.
- O valor bruto original é sempre preservado em `metadata.observed_at_source`.
- `metadata.timing_status` ∈ {`observation_date`, `mjd_observation_date`, `interval_start`,
  `release_date_fallback`, `unresolved`}.
- Sem data interpretável → `observed_at = null` e `timing_status = "unresolved"`.

### 7.3 Ordenação

- Chave: `observed_at` em UTC, **crescente** (contrato §9).
- Empate: desempate estável por `product_id` (para determinismo entre requisições).
- Itens sem data: ao final, preservando a ordem original entre eles.
- Deduplicação: mesmo `product_id` (+ banda + detector) aparece uma única vez; as duplicatas são
  contadas em `metadata.duplicate_count` e registradas no log (validação temporal §4).

### 7.4 Compatibilidade espectral

`docs/architecture/api-contract.md` §10 proíbe misturar bandas sem justificativa. No MVP:
- `band` e `detector` vêm do registro real do produto (ou `null`).
- A API **não** filtra por banda (parâmetro `band` não implementado — ver A-03).
- `metadata` expõe `band`/`detector`/`quality` para que o frontend identifique
  incompatibilidades (contrato §10, RC-001, RC-004).

---

## 8. Modelos Pydantic (mapeamento do contrato)

`app/schemas/observation.py`:

| Modelo | Campos | Regra |
|---|---|---|
| `Target` | `ra_deg: float`, `dec_deg: float` | Idêntico ao exemplo do contrato §4. |
| `QueryParams` | `fov_arcmin: float` | Idêntico ao exemplo do contrato §4. |
| `ObservationMetadata` | `product_id: str\|None`, `quality: float\|None` + extras opcionais | `product_id`/`quality` mantêm nome e tipo do exemplo do contrato. Extras: `observed_at_source`, `timing_status`, `instrument`, `detector`→(não, é de topo), `exposure_time_s`, `wavelength_min_nm`, `wavelength_max_nm`, `wcs`, `contamination_flags`, `source`, `original_file_url`, `data_release`, `cutout_strategy`, `cutout_size_pixels`, `visual_normalization`, `duplicate_count`. Todos `None` por padrão. |
| `Observation` | `id: str`, `observed_at: datetime\|None`, `band: str\|None`, `detector: str\|None`, `image_url: str\|None`, `metadata: ObservationMetadata` | Nomes exatos do contrato §5. |
| `ObservationResponse` | `target: Target`, `query: QueryParams`, `total_observations: int`, `observations: list[Observation]` | Nomes exatos do contrato §4. |
| `ErrorDetail` | `code: str`, `message: str` | Contrato §8. |
| `ErrorResponse` | `error: ErrorDetail` | Contrato §8. |

Regras gerais:
- Todo campo tem `Field(description=...)` e docstring.
- Todo campo ausente na fonte é `null`. **Nenhum valor é inventado** (RC-005).
- `extra="forbid"` nos modelos de **entrada** (parâmetros de query) para rejeitar campos
  desconhecidos; `extra="ignore"` nos de **saída** para tolerar evolução do contrato.
- `observed_at` serializado em ISO 8601 com `Z` (UTC).

---

## 9. Estratégia de testes

### 9.1 Testes unitários (sem rede)

| Arquivo | Cobertura |
|---|---|
| `test_config.py` | Leitura de env com prefixo `SPHEREX_`; valores padrão; validação de faixas de FOV; ausência de URL de SIA2 → serviço não configurado. |
| `test_irsa_client.py` | Parâmetros montados na consulta; URL base vindo da config; user-agent e timeout aplicados; **retry** em 5xx/timeout; ausência de retry em 4xx; tradução de cada falha de rede para `SourceUnavailableError`; parser VOTable sintético; parser JSON sintético; corpo inválido → `MalformedResponseError`. |
| `test_observation_service.py` | Ordenação cronológica crescente; item sem data vai ao final; desempate determinístico; deduplicação; mapeamento do registro SIA2 sintético para os schemas (campos ausentes → `null`); sem resultados → `NoObservationsFoundError`. |
| `test_fits_processor.py` | Extração de `DATE-OBS` e palavras-chave do cabeçalho; `Cutout2D` com posição e tamanho corretos; geração de PNG (dimensões > 0, formato PNG, arquivo não vazio); marcação de normalização visual. |
| `test_cutout_service.py` | Escolha `REMOTE_CUTOUT` vs `LOCAL_DOWNLOAD` conforme configuração; guarda de tamanho máximo. |
| `test_cache.py` | Chave estável por consulta; hit/miss; expiração por TTL. |

### 9.2 Testes de API (`TestClient`)

`test_api_observations.py`:

1. **Com resultados** — fake de transporte devolve SIA2 sintético → HTTP 200, `total_observations`
   correto, `observations` em ordem cronológica, `image_url` no formato do contrato.
2. **Sem resultados** — SIA2 sintético vazio → HTTP 404 + `{"error":{"code":"NO_OBSERVATIONS_FOUND",...}}`.
3. **Parâmetro inválido** — `ra_deg=400`, `dec_deg=100`, `fov_arcmin=0` → HTTP 400 +
   `INVALID_PARAMETERS`.
4. **Fonte indisponível** — fake de transporte levantando timeout / URL não configurada →
   HTTP 503 + `SOURCE_UNAVAILABLE`.

`test_api_images.py`: `GET /api/images/{id}` inexistente → HTTP 404 + `IMAGE_NOT_FOUND`;
imagem gerada a partir de um FITS **sintético** → HTTP 200, `content-type: image/png`,
corpos não vazio.

`GET /api/health` → HTTP 200 e `{"status":"ok"}` (sem nenhum dado científico).

### 9.3 Fixtures sintéticas

Todas as fixtures são **sintéticas**, com nomes prefixados por `synthetic_` e comentários
explícitos. São construídas em memória (`astropy.io.fits` / `astropy.io.votable`) e **não**
representam observações SPHEREx reais.

### 9.4 Testes de integração (marcados, opcionais, exigem rede)

- Marcador `integration` registrado em `src/backend/pyproject.toml` / `pytest.ini`.
- Execução padrão: `pytest tests/backend -q` → testes de integração **skipados**.
- Execução com rede: `pytest tests/backend -q -m integration` (desativado por padrão; exige
  `SPHEREX_IRSA_SIA2_URL` configurada e coordenar com o Researcher).

---

## 10. Plano de cache (disco, sem banco de dados)

- **Sem banco de dados no MVP** (`system.md` §12).
- Duas camadas, no diretório `SPHEREX_CACHE_DIR` (padrão `<repo>/data/cache/spherex`):
  1. `queries/` — resposta bruta da consulta SIA2, em JSON, indexada por
     `sha256(canonical_query)`.
  2. `images/` — PNG gerado, indexado por `sha256(product_key + cutout + normalização)`.
- **Chave de consulta** = SHA-256 da string canônica
  `ra_deg|dec_deg|fov_arcmin|band|fov_policy|sia2_base_url` (parâmetros normalizados: floats com
  6 casas, ordem fixa).
- **Invalidação simples:** TTL (`SPHEREX_CACHE_TTL_SECONDS`, padrão 3600 s). Entradas expiradas
  são re-consultadas e sobrescritas. Invalidação manual = apagar o diretório de cache.
- O cache nunca altera a resposta entregue: é uma otimização de rede. O resultado entregue é
  scientificamente idêntico ao que a fonte retornaria no momento da requisição original (limitação documentada:
  até `TTL` a resposta reflete o estado da fonte na hora da primeira consulta).

---

## 11. Riscos e contingências

| # | Risco | Impacto | Mitigação / contingência |
|---|---|---|---|
| R-01 | O IRSA **pode não expor** um serviço SIA2 para o SPHEREx. | Alto — impede a consulta espacial. | O parser e o cliente ficam isolados; a contingência é migrar para **TAP** (`astroquery.ipac.irsa`) ou para o serviço de *footprints*, mantendo o mesmo contrato interno (`IrsaClient.query_by_position`). Nenhuma mudança na API ou no frontend. |
| R-02 | A URL oficial muda ou exige parâmetros não documentados. | Médio. | A URL é **somente** configuração; a construção de parâmetros está em um método único (`_build_sia2_params`). |
| R-03 | Formato real da resposta difere de VOTable/JSON. | Médio. | Parser tolerante + `MalformedResponseError` explícito, sem inventar campos. Teste de integração com rede é o mecanismo de detecção. |
| R-04 | Estrutura real do FITS diferente do esperado (número de HDUs, extensões). | Médio. | Seleção automática da HDU 2D; metadados extraídos de forma tolerante; `metadata` reflete apenas o que existe. |
| R-05 | Downloads grandes / lentos (RNF-002). | Médio. | Preferência pelo serviço de cutout; limite `SPHEREX_MAX_FITS_BYTES`; cache em disco; timeout. |
| R-06 | Limite de requisições do IRSA (rate limit). | Médio. | User-Agent identificando o projeto; retry com backoff exponencial; cache que reduz repetição. |
| R-07 | Escala de pixels desconhecida → recorte local dimensionado errado. | Médio. | Prioridade: `s_pixel_scale` do SIA2 → `CDELT` do WCS → valor de aplicação marcado como "assumido" em `metadata`. |
| R-08 | Leitura de datetime ambígua (MJD vs. data de publicação). | Alto (interpretação científica). | `timing_status` explícito; `observed_at` só é preenchido com data de **observação**; data de publicação nunca substitui a de observação sem marcação. |
| R-09 | Mistura de bandas na sequência temporal. | Alto. | `band`/`detector` sempre visíveis; parâmetro `band` rejeitado até validação; alinhamento de escalas documentado. |
| R-10 | `.gitignore` não cobre `data/cache/` (fora da alçada desta fase). | Baixo. | **Reportado ao Integrante 1** para inclusão de `data/cache/` no `.gitignore`. |
| R-11 | `jupyterlab`/`ipykernel` removidos podem quebrar notebooks existentes. | Baixo. | Os notebooks do repositório (`notebooks/`) são de exploração; a remoção foi solicitada e é registrada para decisão. |
| R-12 | CORS restrito a localhost → frontend em outra porta/origem falha. | Baixo. | `SPHEREX_CORS_ORIGINS` configurável; nenhum segredo exposto. |

---

## 12. Sequência de implementação (etapas pequenas)

| Etapa | Conteúdo | Critério de conclusão **verificável** |
|---|---|---|
| 1 | `docs/architecture/implementation-plan.md` (este documento) | Arquivo existe e cobre os 12 itens exigidos. |
| 2 | `app/core/config.py` + `app/schemas/observation.py` | `python -c "from app.core.config import get_settings"` importa sem erro; `ObservationResponse` instancia com o exemplo do contrato. |
| 3 | `app/api/errors.py` (exceções → contrato) | `pytest tests/backend/test_config.py` verde; mapeamento de exceções coberto. |
| 4 | `app/services/irsa_client.py` com `FakeTransport` | `pytest tests/backend/test_irsa_client.py` verde (sem rede). |
| 5 | `app/services/fits_processor.py` | `pytest tests/backend/test_fits_processor.py` verde; PNG gerado de um FITS sintético com tamanho > 0. |
| 6 | `app/services/cache.py` + `app/services/cutout_service.py` | `pytest tests/backend/test_cache.py` e `test_cutout_service.py` verdes. |
| 7 | `app/services/observation_service.py` | `pytest tests/backend/test_observation_service.py` verde; ordenação cronológica verificada. |
| 8 | `app/api/observations.py` + `app/main.py` | `pytest tests/backend/test_api_observations.py` verde; `GET /api/health` → `{"status":"ok"}`. |
| 9 | `src/backend/README.md` | Comando de execução documentado e conferível. |
| 10 | `requirements.txt` fixado a partir do `pip freeze` real | `pip install -r requirements.txt` reproduz o ambiente; `jupyterlab`/`ipykernel` ausentes. |
| 11 | Suíte completa | `.\.venv\Scripts\python.exe -m pytest tests/backend -q` → **todo verde**, saída anexada ao relatório. |

Cada etapa é executada e verificada antes da próxima. Nenhuma etapa depende de rede.

---

## 13. O que NÃO será feito no MVP (limites explícitos)

1. **Não** serão implementados os parâmetros `start_date`, `end_date` e `band` (A-03): retornam
   `INVALID_PARAMETERS` até validação científica.
2. **Não** haverá banco de dados, histórico de consultas, autenticação ou usuários.
3. **Não** haverá comparação, subtração de imagens, seleção de bandas ou análise espectral.
4. **Não** haverá integração com Gaia/WISE.
5. **Não** será feita correção astrométrica por movimento próprio (RC-003): o backend usa as
   coordenadas informadas e **preserva** a época de referência quando disponível nos metadados.
6. **Não** haverá download assíncrono/streaming de FITS para o navegador: o backend processa e
   entrega PNG.
7. **Não** haverá medição fotométrica de magnitude a partir da imagem renderizada; a
   normalização é **visual** e identificada como tal.
8. **Não** haverá tentativa automática de adivinhação de campos ausentes: todo campo sem fonte
   permanece `null`.
9. **Não** haverá frontend nesta fase (responsabilidade do Integrante 3).
10. **Não** haverá consulta real ao IRSA nesta fase: sem endpoint verificado, a API responde
    `SOURCE_UNAVAILABLE`.

---

## 14. Pontos de código pendentes de verificação pelo Researcher

| Ponto de código | O que precisa ser confirmado |
|---|---|
| `src/backend/app/services/irsa_client.py::IRSA_SIA2_BASE_URL` | URL oficial do serviço SIA2 do SPHEREx no IRSA. |
| `src/backend/app/services/irsa_client.py::IrsaClient._build_sia2_params` | Nomes e formatos exatos dos parâmetros aceitos (POS, SIZE, BAND, TIME, formato de resposta). |
| `src/backend/app/services/irsa_client.py::IrsaClient._parse_sia2_payload` | Formato real da resposta (VOTable e/ou JSON) e nomes das colunas. |
| `src/backend/app/services/irsa_client.py::IRSA_CUTOUT_BASE_URL` | Existência e URL do serviço de cutout do IRSA. |
| `src/backend/app/services/irsa_client.py::IrsaClient._build_cutout_params` | Parâmetros do serviço de cutout (centro, tamanho, formato). |
| `src/backend/app/core/config.py::Settings.irsa_data_base_url` | Base URL para download do FITS original, caso o `access_url` não seja absoluto. |
| `src/backend/app/services/fits_processor.py::extract_header_metadata` | Palavras-chave reais dos produtos SPHEREx (data, banda, detector, exposição, WCS). |
| `src/backend/app/services/cutout_service.py::CutoutService.decide_strategy` | Campo que indica a disponibilidade do serviço de recorte no registro do produto. |
| `src/backend/app/services/observation_service.py::_extract_observed_at` | Coluna canônica de data de observação no SIA2 do SPHEREx. |
| `src/backend/app/core/config.py::Settings.max_fov_arcmin` | Campo de visão real do produto e limites cientificamente válidos. |

---

## 15. Decisões a registrar pelo Integrante 1 em `docs/decisions.md`

1. Remoção de `jupyterlab` e `ipykernel` do `requirements.txt` do MVP.
2. Configuração por variável de ambiente com prefixo `SPHEREX_` (sem segredos no código).
3. `id` interno determinístico (`obs_<sha1[:16]>`) preservando o identificador real em
   `metadata.product_id`.
4. Limites de campo de visão como limites **de aplicação** (não científicos), configuráveis.
5. Parâmetros opcionais (`start_date`, `end_date`, `band`) rejeitados com `INVALID_PARAMETERS`
   até validação científica.
6. Cache em disco (sem banco de dados) com invalidação por TTL.
7. `data/cache/` precisa ser adicionado ao `.gitignore` (fora da alçada da Fase 1).
