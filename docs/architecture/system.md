# Arquitetura do sistema

## 1. Objetivo

Definir a arquitetura inicial da aplicação SPHEREx Explorer, seus componentes, responsabilidades e fluxo de comunicação.

A arquitetura deverá priorizar simplicidade, separação de responsabilidades e facilidade de integração.

## 2. Visão geral

A aplicação será dividida em dois componentes principais:

- Frontend: interface de pesquisa e visualização.
- Backend: consulta aos dados científicos, processamento e disponibilização dos resultados.

O backend será responsável por interagir com os serviços do IRSA e processar os arquivos científicos.

O frontend não deverá acessar diretamente os produtos FITS originais.

## 3. Tecnologias previstas

| Camada | Tecnologia |
|---|---|
| Frontend | HTML |
| Estilos | CSS |
| Interatividade | JavaScript |
| Backend | Python |
| Framework da API | FastAPI |
| Processamento astronômico | Astropy |
| Consulta a arquivos científicos | Astroquery e/ou PyVO |
| Formato de comunicação | JSON |
| Controle de versão | Git |
| Repositório compartilhado | GitHub |

As bibliotecas de consulta deverão ser validadas antes da escolha definitiva.

## 4. Diagrama lógico

```text
                    USUÁRIO
                       |
                       v
              FRONTEND WEB
              HTML / CSS / JS
                       |
                       | HTTP / JSON
                       v
               BACKEND FASTAPI
                       |
             +---------+---------+
             |                   |
             v                   v
       SERVIÇO IRSA         PROCESSAMENTO
       CONSULTAS            ASTROPY / FITS
             |                   |
             v                   v
       PRODUTOS SPHEREx    RECORTES / IMAGENS
             |                   |
             +---------+---------+
                       |
                       v
             RESPOSTA DA API
             JSON + URLs DE IMAGEM
                       |
                       v
                FRONTEND WEB
                       |
                       v
              VISUALIZADOR TEMPORAL
```

## 5. Responsabilidades do frontend

O frontend deverá:

1. Receber RA e Dec.
2. Receber o campo de visão.
3. Validar os campos básicos.
4. Enviar a consulta à API.
5. Exibir carregamento e erros.
6. Apresentar as observações disponíveis.
7. Organizar a navegação temporal.
8. Exibir as imagens processadas.
9. Apresentar os metadados.
10. Oferecer controles de reprodução.

O frontend não deverá:

- Interpretar diretamente arquivos FITS.
- Realizar consultas complexas ao arquivo científico.
- Armazenar arquivos científicos grandes.
- Inventar metadados ausentes.

## 6. Responsabilidades do backend

O backend deverá:

1. Receber e validar parâmetros.
2. Consultar o arquivo científico.
3. Interpretar as respostas dos serviços.
4. Identificar os produtos relevantes.
5. Recuperar os arquivos ou recortes necessários.
6. Processar os dados científicos.
7. Gerar imagens adequadas à visualização.
8. Organizar as observações cronologicamente.
9. Preservar os metadados.
10. Retornar respostas JSON.
11. Tratar erros e ausência de resultados.

## 7. Organização interna do backend

Estrutura prevista:

```text
backend/
├── app/
│   ├── main.py
│   ├── api/
│   │   └── observations.py
│   ├── services/
│   │   ├── irsa_client.py
│   │   ├── observation_service.py
│   │   ├── cutout_service.py
│   │   └── fits_processor.py
│   ├── schemas/
│   │   └── observation.py
│   └── core/
│       └── config.py
├── tests/
└── requirements.txt
```

Essa estrutura é uma proposta inicial. Os arquivos deverão ser criados conforme as necessidades reais da implementação.

## 8. Organização interna do frontend

Estrutura prevista:

```text
frontend/
├── index.html
├── src/
│   ├── css/
│   │   └── styles.css
│   ├── js/
│   │   ├── api.js
│   │   ├── search.js
│   │   ├── player.js
│   │   └── metadata.js
│   └── assets/
└── tests/
```

A estrutura poderá evoluir conforme a complexidade da interface.

## 9. Organização dos dados

Estrutura prevista:

```text
data/
├── samples/
├── cache/
├── raw/
└── temporary/
```

Finalidade:

- `samples`: pequenas amostras autorizadas para desenvolvimento e testes.
- `cache`: dados temporários recuperados para reutilização.
- `raw`: arquivos científicos originais.
- `temporary`: arquivos intermediários.

Arquivos grandes e dados recuperáveis não deverão ser adicionados indiscriminadamente ao Git.

Os diretórios de cache e dados originais deverão ser protegidos pelo `.gitignore`.

## 10. Fluxo de consulta

1. O usuário informa as coordenadas.
2. O frontend valida os valores.
3. O frontend envia a solicitação à API.
4. O backend valida os parâmetros.
5. O serviço de consulta pesquisa o arquivo IRSA.
6. Os produtos disponíveis são identificados.
7. Os metadados são interpretados.
8. Os recortes necessários são recuperados.
9. As imagens são processadas.
10. As observações são organizadas cronologicamente.
11. A API devolve os resultados.
12. O frontend apresenta a sequência.

## 11. Processamento e desempenho

Os arquivos científicos originais podem ser grandes.

Por isso:

- Evitar downloads desnecessários.
- Priorizar recortes espaciais.
- Processar os dados no backend.
- Utilizar cache quando apropriado.
- Evitar processamento repetido.
- Não enviar arquivos FITS enormes ao navegador.
- Monitorar tempo de consulta e processamento.

O método de geração das imagens deverá preservar informações suficientes para a visualização sem apresentar a imagem renderizada como substituta dos dados científicos originais.

## 12. Armazenamento

Não será introduzido banco de dados no MVP sem uma necessidade concreta.

Inicialmente, a aplicação poderá trabalhar com respostas da API e arquivos processados temporariamente.

A necessidade de persistência deverá ser reavaliada quando houver requisitos claros de histórico, usuários ou armazenamento de consultas.

## 13. Segurança

- Validar todos os parâmetros recebidos.
- Limitar valores de campo de visão.
- Não expor segredos.
- Evitar acesso arbitrário a arquivos.
- Validar URLs e identificadores dos produtos.
- Controlar downloads e arquivos temporários.
- Tratar erros sem expor informações internas.

## 14. Evolução da arquitetura

A arquitetura poderá receber novos componentes quando houver justificativa:

- Banco de dados.
- Serviço de cache.
- Processamento assíncrono.
- Integração Gaia/WISE.
- Comparação de imagens.
- Subtração de imagens.
- Análise espectral.

Esses componentes não fazem parte da arquitetura mínima obrigatória.

## 15. Responsáveis

**Liderança técnica:** Integrante 1.

**Frontend:** Integrante 3.

**Validação científica:** Integrante 2.