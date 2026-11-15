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
- **Frontend novo (mapa interativo, `src/frontend/`) ligado à API real (14/11/2026):** substituiu o frontend antigo (`src/frontend/src/frontend/`, removido no merge). Usa o contrato real, lê o envelope de erro e mostra data/hora UTC, detector e faixa espectral. A galeria é limitada a 24 itens. Novo `GET /api/targets` com os 5 alvos de `docs/science/target-catalog.md`; para objetos de alto movimento próprio, a posição vem propagada às épocas SPHEREx (WISE 0855: 133.737467, −7.240406, época 2025.35; a coordenada J2000 do desafio fica ~3,5′ distante). Validado no navegador: o alvo WISE 0855 trouxe 259 observações em 130 instantes; filtrando só D3, ficaram 45 observações em 45 instantes; a imagem real foi exibida. **Pendente:** as miniaturas disparam ~25 recortes IBE simultâneos e carregam muito devagar, e o backend precisa limitar a concorrência. `/api/spectrum` não existe; a seção avisa isso com dados reais.
- **Desempenho das imagens (DECISÃO 012):** o backend lê só a extensão `IMAGE` do FITS (recorte IBE de 17,7 s/4,05 MB para 1,2 s/31,7 KB, pixels idênticos), limita a 3 os pedidos simultâneos ao IRSA e deduplica pedidos da mesma imagem. Medição pela API, alvo Estrela de Barnard sem cache: 25 imagens em paralelo concluídas em 17 s, todas com HTTP 200 (antes, só 1 de 24 miniaturas havia carregado depois de ~60 s). O frontend carrega as miniaturas em fila (no máximo 2 por vez), só depois da imagem principal, e descarta a fila ao trocar de busca ou filtro. Validado no navegador com o IRSA real, alvo ε Indi sem cache (517 observações): busca em 11,7 s, imagem principal 0,8 s depois, 24 miniaturas resolvidas em ~26 s com no máximo 2 simultâneas; 23 carregaram e 1 retornou 422 (o produto não cobre a posição, caso do pré-filtro de sobreposição ainda pendente). Os 503 do IRSA foram absorvidos pelo retry.
- **Unidades espectrais (DECISÃO 011):** `wavelength_*_nm` agora em nanômetros (SIA publica em metros). Suíte: **113 passed, 2 skipped**.
- **Pré-filtro de sobreposição (14/11/2026, DECISÃO 013):** `/api/observations` só lista produtos cujo polígono `s_region` contém a posição pedida. Ao vivo, FoV 3′: ε Indi 517 → 460, Barnard 380 → 358, WISE 0855 259 → 258. Em 30 recortes de produtos mantidos não houve nenhum 422; todos os 422 observados estavam entre os descartados. Também saem os recortes parciais em que o alvo cai fora do detector. Suíte: **144 passed, 2 skipped**. Não revalidado no navegador (a mudança é só no backend e não altera o contrato).
- **Frontend público e resiliente (15/11/2026, DECISÃO 017):**
  - Modo demonstração com dados reais (WISE 0855 e Estrela de Barnard).
  - Painel de alternativas em vez de erro.
  - Mapa em 1,5 s com fallback honesto (AllWISE enquanto o HiPS SPHEREx do CDS está fora).
  - Detectores com faixa real e clique simples.
  - Comparador de duas datas e atalhos de teclado.
  - Glossário com 53 termos.
  - Tema astronômico com 3 imagens NASA/JPL-Caltech creditadas e ícone original do SPHEREx.
  - Validado no navegador real: busca ao vivo (M31, 362 observações, com o SIA intermitente), painel de falha com 503 simulado → exemplo salvo da Barnard (354 observações), detector D3 isolado com 1,63–2,43 µm, mapa com AllWISE.
  - Diferença D1 da Barnard (céu fixo) mostra o par claro/escuro do movimento próprio.
  - Corrigida a escala do quadro comum (um quadro D6 de 29 px entre quadros de 31 px).
  - Suíte: **198 passed, 2 skipped**.
  - **Não verificado:** a aparência visual por captura de tela (janela do navegador minimizada) e a abertura automática do mapa ao rolar a página.
- **Contaminação e espectro de um ponto (15/11/2026, DECISÃO 016):**
  - `FLAGS` (23 bits) por quadro e no alvo; combinações excluem pixels contaminados.
  - `GET /api/spectrum`: um ponto por exposição, λ pela `WCS-WAVE` (idêntico ao método oficial em 3 recortes reais), erro pela `VARIANCE`.
  - Validado no navegador com IBE real e lista de produtos de uma resposta real do SIA salva (o SIA estava em 502):
    - WISE 0855, 50 observações;
    - espectro com 42 pontos de 0,88–5,00 µm, 7 com contaminação;
    - qualidade "nenhuma" no alvo;
    - diferença entre épocas D1 em ~1 s;
    - seletor de FOV com 50/50 quadros completos.
  - Corrigido um bug de gravação concorrente no cache (Windows/OneDrive) encontrado nessa validação.
  - Suíte: **197 passed, 2 skipped**.
  - **Pendente:**
    - validar com um alvo brilhante (Estrela de Barnard), para mostrar um espectro com sinal real;
    - revalidar a busca ao vivo quando o SIA voltar;
    - validação científica pela Integrante 2.
- **"Décadas" e correção do WISE 0855 (15/11/2026, DECISÃO 019):**
  - O mesmo campo do céu de 1950 ao SPHEREx (`data/scripts/19_motion_timeline.py`): DSS, 2MASS e WISE + 3 exposições SPHEREx por detector, recortadas de novo no IBE (sem depender do SIA).
  - Aba "Décadas" no visor e no painel de falha (`js/motion.js`): filtros "Outros telescópios" e D1–D6, eixo do tempo, reproduzir, piscar e trajeto previsto.
  - Estrela de Barnard: 13,2′ em 76 anos; a estrela fica a ≤ 6,6″ da posição prevista nas 22 imagens.
  - Novos pacotes SPHEREx reais: ε Indi (448 observações) e RW Aurigae.
  - WISE 0855: a coordenada do desafio é da época ~2010, não J2000. Corrigido com o SIMBAD (Kirkpatrick et al. 2021); a fonte W2 confirma (1,4″).
  - Testes: **199 passed, 2 skipped**. Testado no navegador: aba Décadas (Barnard), painel de falha (ε Indi) e o atalho para o pacote SPHEREx com D1–D6.
  - **Pendente:** pacote e linha do tempo do R Draconis (o SIA estava fora do ar); o servidor backend na porta 8000 precisa ser reiniciado para servir o alvo corrigido.
- **Interface em páginas, modo cinema, outras bases e imagens salvas (15/11/2026, DECISÃO 018):**
  - Páginas por hash (`js/router.js`); sonda SPHEREx real (render oficial transparente) com feixe que forma a navbar; fundo mais escuro e cartões flutuantes.
  - Visor redesenhado com modo cinema (`js/cinema.js`): abas Sequência/Comparar/Combinar, zoom e marcas de data.
  - Mensagem amigável quando o servidor cai; busca por nome (Sesame) e outras bases (WISE, 2MASS, DSS2 via IRSA Finder Chart).
  - Imagens de referência dos 5 alvos salvas no site (`data/scripts/18_reference_images.py`), centradas no alvo na data de cada imagem; aparecem no painel de alternativas quando a busca falha (`js/refimages.js`).
  - Testado no navegador embutido: falha simulada do servidor mostra as imagens da Barnard (alvo próximo) e a galeria de alvos (região sem imagens); ampliar e fechar com Esc funcionam.
  - **Pendente:** testar a tela cheia nativa num Chrome comum; ver a animação do feixe em tempo real; revisar a navbar entre 761 e 1000 px.
- **Quadro comum, cobertura, combinação de épocas e releases (15/11/2026, DECISÃO 015):**
  - Imagens reamostradas numa grade norte-acima centrada no alvo; área fora do detector transparente.
  - `GET /api/coverage` (quadros completos/parciais por FOV, sem baixar imagens) e `GET /api/composite` (média por detector e diferença entre épocas).
  - Coleções configuráveis (`SPHEREX_COLLECTIONS`, `auto` com fallback) e `GET /api/releases`.
  - Frontend: seletor de FOV com cobertura, custo e Lua; selo de quadro parcial e filtro "só completos"; "Seguir o alvo"; "Combinar épocas". O Gaia/AllWISE no Aladin foi corrigido (o domínio `vizier.unistra.fr` não resolvia) e há espelho CfA quando o CDS cai.
  - Contingência: cache vencido sinalizado quando o IRSA cai; imagens não expiram.
  - Suíte: **185 passed, 2 skipped**.
  - **Pendente:** validação ao vivo desses recursos. O SIA do IRSA respondeu 502 em todas as tentativas de 15/11 (o IBE seguiu respondendo 200). Também pendente confirmar a descoberta de coleções contra o IRSA real.
- **Correção do movimento próprio por época (14/11/2026, DECISÃO 014):** com o movimento próprio do alvo, cada observação é filtrada e recortada na posição da sua data. Ao vivo, Estrela de Barnard no D1: sem correção a estrela se afastava até 2,18 px do centro; com correção ficou a ≤ 0,73 px em todas as datas. No navegador, o botão do alvo envia o movimento, o status confirma a correção e os detalhes mostram o centro propagado. Suíte: **155 passed, 2 skipped**.

## Em andamento

- T-B — Data Analyst: obtenção e caracterização de arquivos FITS reais, incluindo a verificação da existência de sequência temporal utilizável.
- T-C1 — Developer: plano de implementação, esqueleto do backend FastAPI, cliente IRSA configurável, schemas da API e testes automatizados.
- T-E — Coordinator: manutenção da documentação e do quadro de tarefas.

## Pendências prioritárias

1. ~~Verificar os endpoints de consulta e de recorte do IRSA~~ — **CONCLUÍDO** (DECISÃO 007).
2. ~~Identificar e extrair as épocas de observação e os metadados dos produtos reais~~ — **CONCLUÍDO** (T-A + §6.3 do quadro).
3. ~~Verificar se existe sequência temporal utilizável~~ — **CONCLUÍDO** (DECISÃO 008).
4. ~~Implementar o cliente IRSA real e o endpoint `/api/observations` (T-C2), com retry, pré-filtro de sobreposição e recorte IBE~~ — **CONCLUÍDO** (DECISÕES 010, 012 e 013).
5. Recuperar e processar pelo menos um recorte de imagem real **pelo backend** (mapeando M2, M4 e M5).
6. Submeter as entregas do marco à revisão independente (T-D).
7. Preparar o frontend contra a API com dados reais (Integrante 3).
8. Atualizar `docs/architecture/system.md` e `api-contract.md` para refletir a estratégia de recorte real e a propagação astrométrica.
9. Configurar o repositório compartilhado e migrar o quadro para GitHub Issues/Projects.
10. Normalizar o esquema de permissões dos agentes (T-F), após aprovação.

## Questões que exigem validação da liderança científica (Integrante 2)

1. **WISE 0855 — astrometria.** ~~Fonte secundária~~ — posição J2000 e μ confirmados no SIMBAD (Kirkpatrick et al. 2021); a coordenada do desafio era da época ~2010 (DECISÃO 019). Falta conferir no artigo a época de referência da posição.
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