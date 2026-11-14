# Progresso do projeto

## Desafio escolhido

Desafio avançado do NASA Space Apps Challenge 2026 relacionado à exploração temporal de imagens da missão SPHEREx.

## Objetivo

Desenvolver uma aplicação web pública que permita ao usuário informar coordenadas celestes (RA e Dec), selecionar um campo de visão e visualizar, em sequência temporal, imagens reais disponíveis no arquivo científico SPHEREx.

A aplicação deverá organizar as observações cronologicamente e oferecer controles para reproduzir, pausar e navegar entre imagens, apresentando os metadados correspondentes.

## Situação atual

**Primeiro marco técnico em andamento: prova de viabilidade com dados reais do SPHEREx.**

A fase de planejamento e documentação foi concluída. Os três grupos documentais previstos em `docs/continuity.md` §13 estão finalizados:

- `docs/team/` — `roles.md` e `workflow.md`.
- `docs/science/` — `data-sources.md`, `target-catalog.md` e `validation.md`.
- `docs/architecture/` — `system.md`, `api-contract.md` e `requirements.md`.

Uma auditoria completa do repositório foi executada em 14/11/2026, com o registro de inconsistências em `docs/board.md` §4 e de riscos científicos em `docs/board.md` §5.

O ambiente Python foi preparado: ambiente virtual `.venv` com astropy 8.0.2, astroquery 0.4.11, pyvo 1.10.0, fastapi 0.162.7, numpy 2.5.4, matplotlib 3.11.2, pytest 9.2.0 e httpx 0.28.1 (DECISÃO 005). O acesso de rede ao IRSA foi verificado com sucesso (HTTP 200).

O quadro de tarefas provisório foi criado em `docs/board.md` (DECISÃO 006), já que o repositório compartilhado ainda não existe.

Ainda **não** existe implementação funcional do backend ou frontend, e **nenhuma** consulta real ao arquivo IRSA/SPHEREx foi concluída até o momento.

## Organização da equipe

| Integrante | Responsabilidade |
|---|---|
| Integrante 1 | Liderança técnica: backend, dados e integração |
| Integrante 2 | Liderança científica: pesquisa astronômica e validação |
| Integrante 3 | Liderança de interface: frontend e visualização |

A divisão é inicial e poderá ser ajustada conforme a evolução do projeto.

## Concluído

- Desafio selecionado.
- Conceito inicial da solução definido.
- Escopo preliminar do MVP estabelecido.
- Repositório Git local inicializado.
- Estrutura inicial do OpenCode criada.
- Agentes especializados criados.
- Skills e comandos iniciais criados.
- Instruções gerais do projeto estabelecidas.
- Frentes humanas iniciais definidas.
- Desafio formalizado em `docs/challenge.md`.
- Responsabilidades e fluxo de trabalho registrados em `docs/team/`.
- Arquitetura, contrato de API e requisitos documentados em `docs/architecture/`.
- Auditoria completa do repositório executada, com inconsistências e riscos catalogados.
- Ambiente Python isolado preparado e verificado (DECISÃO 005).
- Quadro de tarefas provisório criado (DECISÃO 006).
- **T-A — Pesquisa científica concluída:** produtos SPHEREx, releases (DR1 + QR3), endpoints SIA v2/TAP/IBE cutout, estrutura FITS, metadados de época, astrometria dos 5 objetos e limitações — documentados em `docs/research.md` e `docs/science/data-sources.md` (901 linhas) e `docs/science/target-catalog.md`.
- **R-01 resolvido — a premissa da sequência temporal está CONFIRMADA** por execução real do serviço SIA v2 (DECISÃO 008): 143 épocas distintas em WISE 0855, 192 em Barnard, cobertura de 12–17 meses.
- **Estratégia de consulta ao arquivo definida e verificada empiricamente** (DECISÃO 007), incluindo a correção da premissa errada sobre o caminho `/SIA2`.
- **Verificação independente do Coordinator** dos achados de T-A: todos os números reproduzidos, com acréscimo de dois achados operacionais novos (§6.4 de `docs/board.md`).

- **Descoberta real via SIA integrada ao backend (14/11/2026, DECISÃO 009):** corrigidos três defeitos que só apareciam com a resposta real: (1) colunas da VOTable lidas pelo `ID` (`col_N`) em vez do `name`, o que deixava todos os metadados nulos; (2) `t_min` em MJD não era interpretado e a época caía na data de publicação; (3) o detector aparecia como "SPHEREx". Resposta real salva em `tests/backend/fixtures/sia_spherex_dr1_wise0855.xml`. Suíte: **86 passed, 2 skipped** (os 2 pulados dependem do FITS real, ausente neste clone). Busca ao vivo em WISE 0855 (FoV 1′): **258 observações, 129 épocas, 2025-05-05 → 2026-05-14**, detectores D1–D6.
- **Fluxo backend ponta a ponta com dados reais (14/11/2026, DECISÃO 010):** SIA como padrão + recorte IBE por produto. Validado ao vivo pela API: `GET /api/observations` (WISE 0855) → `GET /api/images/{id}` → PNG para 4 épocas de 2025-05 a 2026-05.
- **Frontend alinhado ao contrato real e validado com o backend real (14/11/2026):** a aplicação usa `ra_deg`/`dec_deg`/`fov_arcmin`, lê `observed_at`, `detector` e `band`, trata o envelope de erro e oferece filtro por detector. A galeria é limitada a 60 miniaturas lazy. Foi servida em `localhost:5173` (CORS ok) contra o uvicorn em `:8000`. O exemplo WISE 0855 com FoV 3′ trouxe 271 observações em 137 instantes e a primeira imagem real foi exibida, sem erros no console. Como rodar: `.claude/launch.json` (local) ou `src/frontend/src/frontend/README.md`.
- **Unidades espectrais (DECISÃO 011):** `wavelength_*_nm` agora em nanômetros (SIA publica em metros). Suíte: **113 passed, 2 skipped**.

## Em andamento

- T-B — Data Analyst: obtenção e caracterização de arquivos FITS reais, incluindo a verificação da existência de sequência temporal utilizável.
- T-C1 — Developer: plano de implementação, esqueleto do backend FastAPI, cliente IRSA configurável, schemas da API e testes automatizados.
- T-E — Coordinator: manutenção da documentação e do quadro de tarefas.

## Pendências prioritárias

1. ~~Verificar os endpoints de consulta e de recorte do IRSA~~ — **CONCLUÍDO** (DECISÃO 007).
2. ~~Identificar e extrair as épocas de observação e os metadados dos produtos reais~~ — **CONCLUÍDO** (T-A + §6.3 do quadro).
3. ~~Verificar se existe sequência temporal utilizável~~ — **CONCLUÍDO** (DECISÃO 008).
4. Implementar o cliente IRSA real e o endpoint `/api/observations` (T-C2), com retry, pré-filtro de sobreposição e recorte IBE.
5. Recuperar e processar pelo menos um recorte de imagem real **pelo backend** (mapeando M2, M4 e M5).
6. Submeter as entregas do marco à revisão independente (T-D).
7. Preparar o frontend contra a API com dados reais (Integrante 3).
8. Atualizar `docs/architecture/system.md` e `api-contract.md` para refletir a estratégia de recorte real e a propagação astrométrica.
9. Configurar o repositório compartilhado e migrar o quadro para GitHub Issues/Projects.
10. Normalizar o esquema de permissões dos agentes (T-F), após aprovação.

## Questões que exigem validação da liderança científica (Integrante 2)

1. **WISE 0855 — astrometria.** Paralaxe e movimento próprio vieram de fonte secundária (infobox da Wikipédia citando Kirkpatrick et al. 2021); o artigo primário não pôde ser lido (ADS inacessível). O Gaia DR3 **não** oferece homólogo confiável para o objeto.
2. **ε Indi B** — não consta do Gaia DR3 e a separação (~6,5") é menor que a PSF (~7,45" FWHM). O teste precisa ser reformulado como "sistema ε Indi (A+B combinado)".
3. **Detectabilidade por banda** — nenhuma fotometria real foi extraída até aqui; a detectabilidade dos alvos por banda permanece não verificada.
4. **Comparabilidade DR1 × QR3** — definir se `l3_flux_corrections` entra no MVP para comparar fotometricamente entre reprocessamentos.
5. **RW Aurigae e R Draconis** — naturezas das variáveis e período de R Dra (245,5 d) dependem de confirmação bibliográfica.

## Próximo marco

**Comprovação da viabilidade científica e técnica:**

Conseguir consultar o arquivo SPHEREx para uma coordenada celeste, identificar observações disponíveis, obter seus metadados e verificar se existe uma sequência temporal utilizável.

## Critério de conclusão do MVP

O usuário deverá conseguir:

- Informar RA e Dec.
- Selecionar o campo de visão.
- Consultar observações reais do SPHEREx.
- Visualizar imagens em ordem cronológica.
- Reproduzir, pausar e navegar pela sequência.
- Consultar os metadados de cada observação.

A aplicação deverá demonstrar esse fluxo com dados reais e apresentar claramente eventuais limitações científicas.