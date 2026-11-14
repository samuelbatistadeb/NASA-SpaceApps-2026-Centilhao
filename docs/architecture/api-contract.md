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