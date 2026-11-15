# Contrato da API

## 1. Objetivo

Definir o formato de comunicação entre o frontend e o backend do SPHEREx Explorer.

O contrato permite que frontend e backend sejam desenvolvidos em paralelo, desde que ambos respeitem a estrutura acordada.

## 2. Padrões gerais

- Protocolo: HTTP.
- Formato de dados: JSON.
- Codificação: UTF-8.
- API: REST inicial.
- Parâmetros numéricos: unidades explicitamente documentadas.
- Datas: ISO 8601, preferencialmente com indicação de fuso ou escala temporal quando aplicável.

## 3. Endpoint principal

### Consultar observações

**Método:** GET

**Rota proposta:**

`/api/observations`

**Parâmetros:**

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `ra_deg` | float | Sim | Ascensão Reta em graus |
| `dec_deg` | float | Sim | Declinação em graus |
| `fov_arcmin` | float | Sim | Campo de visão em minutos de arco |
| `start_date` | string | Não | Data inicial, se suportada |
| `end_date` | string | Não | Data final, se suportada |
| `band` | string | Não | Identificador de banda, se aplicável |

Exemplo:

```http
GET /api/observations?ra_deg=133.795129&dec_deg=-7.245147&fov_arcmin=5
```

Os parâmetros opcionais somente deverão ser implementados após confirmação de compatibilidade com a consulta científica.

## 4. Exemplo de resposta com resultados

O exemplo abaixo é ilustrativo. Não representa uma consulta real nem observações confirmadas.

```json
{
  "target": {
    "ra_deg": 133.795129,
    "dec_deg": -7.245147
  },
  "query": {
    "fov_arcmin": 5
  },
  "total_observations": 2,
  "observations": [
    {
      "id": "observation-example-001",
      "observed_at": "2026-05-20T00:00:00Z",
      "band": "example-band",
      "detector": "example-detector",
      "image_url": "/api/images/observation-example-001",
      "metadata": {
        "product_id": "example-product-001",
        "quality": null
      }
    },
    {
      "id": "observation-example-002",
      "observed_at": "2026-06-20T00:00:00Z",
      "band": "example-band",
      "detector": "example-detector",
      "image_url": "/api/images/observation-example-002",
      "metadata": {
        "product_id": "example-product-002",
        "quality": null
      }
    }
  ]
}
```

## 5. Campos da resposta

### target

Representa a coordenada consultada.

- `ra_deg`: Ascensão Reta em graus.
- `dec_deg`: Declinação em graus.

### query

Representa os parâmetros utilizados na consulta.

- `fov_arcmin`: campo de visão em minutos de arco.

### total_observations

Quantidade de observações retornadas.

### observations

Lista de observações disponíveis.

Cada item poderá conter:

| Campo | Descrição |
|---|---|
| `id` | Identificador interno da observação |
| `observed_at` | Data/hora da observação |
| `band` | Identificação da banda |
| `detector` | Identificação do detector |
| `image_url` | Endereço da imagem processada |
| `metadata` | Metadados complementares |

Os nomes e tipos definitivos deverão ser compatibilizados com os produtos reais.

## 6. Metadados

Sempre que disponíveis, deverão ser preservados:

- Identificador original do produto.
- Data da observação.
- Identificador da banda.
- Detector.
- Coordenadas.
- WCS, quando necessário.
- Qualidade.
- Indicadores de contaminação.
- Origem do produto.
- Referência ao arquivo original.

Informações indisponíveis deverão ser representadas como `null` ou omitidas conforme o contrato definitivo.

Não inventar valores para preencher campos ausentes.

## 7. Endpoint de imagem

**Método:** GET

**Rota proposta:**

`/api/images/{observation_id}`

Finalidade:

Disponibilizar a imagem processada correspondente à observação.

O backend deverá localizar o produto e retornar uma imagem adequada ao navegador, preferencialmente em formato de imagem convencional.

A imagem renderizada deverá ser identificada como representação visual processada do produto científico.

O arquivo FITS original deverá permanecer acessível por referência ou mecanismo controlado, quando necessário.

## 8. Respostas de erro

Formato proposto:

```json
{
  "error": {
    "code": "NO_OBSERVATIONS_FOUND",
    "message": "Nenhuma observação foi encontrada para os parâmetros informados."
  }
}
```

Códigos iniciais:

| Código | Significado |
|---|---|
| `INVALID_PARAMETERS` | Parâmetros inválidos |
| `NO_OBSERVATIONS_FOUND` | Nenhuma observação encontrada |
| `SOURCE_UNAVAILABLE` | Fonte científica indisponível |
| `PROCESSING_ERROR` | Erro no processamento |
| `IMAGE_NOT_FOUND` | Imagem não encontrada |
| `INTERNAL_ERROR` | Erro interno |

Os códigos HTTP deverão refletir corretamente a natureza do erro.

## 9. Ordenação temporal

O backend deverá devolver as observações em ordem cronológica crescente.

O frontend poderá utilizar essa ordenação para implementar a reprodução temporal.

O backend deverá preservar a informação temporal original e sua interpretação.

Se houver diferenças de escala temporal ou metadados incompletos, elas deverão ser documentadas.

## 10. Compatibilidade científica

A sequência não deverá misturar automaticamente observações de bandas incompatíveis.

O backend deverá preservar as informações necessárias para que o frontend identifique:

- Bandas diferentes.
- Detectores diferentes.
- Qualidade diferente.
- Datas distintas.
- Limitações de comparação.

A compatibilidade científica entre observações deverá ser avaliada conforme os critérios de `docs/science/validation.md`.

## 11. Contrato de desenvolvimento

O frontend poderá utilizar respostas simuladas para desenvolver a interface antes da conclusão do backend.

Essas respostas deverão ser identificadas como dados fictícios de desenvolvimento.

Não deverão ser apresentadas como observações científicas reais.

## 12. Controle de alterações

Alterações neste contrato deverão ser comunicadas às lideranças técnica e de interface.

Mudanças relevantes deverão ser registradas em `docs/decisions.md`.

O contrato deverá ser atualizado após a primeira integração com dados reais do IRSA.
## 13. Contrato implementado (atualizado em 15/11/2026)

> Esta seção descreve a API **como implementada e validada com dados reais**. Onde ela divergir das seções anteriores, vale esta. Decisões: DECISÕES 009–015 em `docs/decisions.md`.

Base local: `http://localhost:8000`. Erros sempre em `{ "error": { "code", "message" } }` (códigos da seção 8).

### 13.1 `GET /api/observations`

Parâmetros: `ra_deg` (0 ≤ ra < 360), `dec_deg` (−90 a 90), `fov_arcmin` (0,1 a 120).

Opcionais, **os três juntos**: `pm_ra_cosdec_masyr`, `pm_dec_masyr`, `ref_epoch_jyear`. Com eles, `ra_deg`/`dec_deg` são a posição na época de referência, e cada observação é filtrada e recortada na posição propagada para a sua data (DECISÃO 014).

Retorna as observações em ordem cronológica. Cada observação é **uma exposição de um detector**:

| Campo | Significado |
|---|---|
| `id` | Identificador interno (inclui a assinatura da consulta) |
| `observed_at` | UTC, de `t_min` (MJD) |
| `detector` | `"D1"` … `"D6"` |
| `band` | Ex.: `"SPHEREx-D3"` |
| `image_url` | `/api/images/{id}` |
| `metadata.product_id` | `obs_publisher_did` do IRSA |
| `metadata.wavelength_min_nm` / `wavelength_max_nm` | Faixa do detector, em nm |
| `metadata.exposure_time_s` | Tempo de exposição |
| `metadata.data_release` | Coleção (ex. `spherex_dr1`) |
| `metadata.original_file_url` | FITS original no IRSA |
| `metadata.cutout_center_ra_deg` / `cutout_center_dec_deg` | Centro do quadro |
| `metadata.position_source` | `requested` ou `proper_motion` |
| `metadata.coverage_fraction` | Fração do quadro dentro do detector (0–1) |
| `metadata.frame` | `common_north_up` |

Produtos cujo detector não contém a posição pedida não são listados (DECISÃO 013).

### 13.2 `GET /api/images/{id}`

PNG 600×600 (pixels SPHEREx ampliados sem interpolação):
- norte para cima, leste à esquerda, centrado no alvo, lado igual ao FOV;
- área fora do detector **transparente**;
- pixel inválido dentro do detector (saturação, defeito) na cor `#B03060`.

Cabeçalhos: `X-SpherEx-Image-Type`, `X-SpherEx-Frame`, `X-SpherEx-Normalization`, `X-SpherEx-Cutout-Strategy`.

### 13.3 `GET /api/targets`

`{ targets: [{ name, ra, dec, fov, position_epoch, note, source, pm_ra_cosdec_masyr, pm_dec_masyr, ref_epoch_jyear }] }`. São os 5 alvos de `docs/science/target-catalog.md`, com posição na época `ref_epoch_jyear`.

### 13.4 `GET /api/coverage`

Parâmetros: `ra_deg`, `dec_deg` e, opcionalmente, o movimento próprio (os três parâmetros juntos).

Retorna, para 1, 2, 3, 5, 10, 15 e 30′:
- `fovs[]` com `fov_arcmin`, `pixels` (lado), `observations`, `complete`, `partial` e `estimated_kb_per_image`;
- `recommended_fov_arcmin`;
- `motion_arcsec_over_survey`;
- `pixel_scale_arcsec`.

Tudo é calculado pelos polígonos dos detectores, sem baixar imagens.

### 13.5 `GET /api/composite`

- `op=mean&a=id1,id2,…`: média de até 40 quadros do **mesmo detector**, para melhorar o sinal-ruído.
- `op=diff&a=…&b=…`: média(A) − média(B), em cinza simétrico (cinza médio = sem mudança).

A mediana de cada quadro é subtraída antes de combinar. Misturar detectores retorna `INVALID_PARAMETERS`.

Retorna PNG, com metadados nos cabeçalhos `X-SpherEx-Composite-Op`, `-Frames-A`, `-Frames-B` e `-Detector`.
