# CONTEXTO DE CONTINUIDADE — NASA SPACE APPS 2026

Este documento contém o contexto necessário para continuar o projeto em uma nova conversa com o ChatGPT, mesmo que a conversa anterior tenha atingido seu limite de contexto.

O objetivo é permitir a continuidade do trabalho sem repetir etapas, perder decisões ou presumir que tarefas ainda não executadas já foram concluídas.

---

# 1. IDENTIFICAÇÃO DO PROJETO

**Projeto:** NASA Space Apps Challenge 2026

**Nome provisório da aplicação:** SPHEREx Explorer

**Nível do desafio:** Avançado

**Equipe:** 3 integrantes.

**Diretório local:**
`C:\NASA-SpaceApps-2026`

**Sistema operacional:** Windows 11.

**Terminal:** Windows PowerShell 5.1.

**Editor:** Visual Studio Code.

**Ferramenta de agentes:** OpenCode.

**Idioma de comunicação:** Português brasileiro.

---

# 2. DESAFIO ESCOLHIDO

A equipe escolheu um desafio avançado do NASA Space Apps Challenge 2026 relacionado à construção de uma ferramenta web pública para explorar imagens da missão SPHEREx em sequência temporal.

O usuário deverá conseguir:

1. Informar Ascensão Reta (RA).
2. Informar Declinação (Dec).
3. Selecionar o campo de visão.
4. Consultar observações disponíveis no arquivo científico SPHEREx.
5. Organizar as imagens cronologicamente.
6. Reproduzir uma sequência temporal.
7. Pausar, avançar e retroceder.
8. Consultar os metadados das observações.

A solução deverá utilizar dados científicos reais.

Não apresentar dados simulados como se fossem observações reais.

## Distinção científica fundamental

Não confundir:

- Bandas espectrais: diferentes intervalos de comprimento de onda.
- Épocas de observação: momentos distintos em que uma região do céu foi observada.

As 102 bandas espectrais do SPHEREx não representam automaticamente 102 quadros temporais.

---

# 3. OBJETIVO DO PROJETO

Desenvolver uma aplicação web acessível que permita explorar visualmente mudanças em regiões do céu utilizando observações reais do SPHEREx.

A proposta é simplificar a exploração de dados astronômicos sem exigir que o usuário conheça Python, FITS ou ferramentas especializadas.

O principal diferencial deverá ser a experiência de exploração temporal com dados científicos reais.

---

# 4. ESCOPO DO MVP

## Funcionalidades essenciais

- Busca por RA e Dec.
- Seleção do campo de visão.
- Consulta de imagens reais do SPHEREx.
- Organização cronológica das observações.
- Visualizador de imagens.
- Reprodução, pausa e navegação temporal.
- Exibição dos metadados.
- Testes com os objetos indicados no desafio.

## Funcionalidades futuras

- Comparação entre duas épocas.
- Subtração de imagens.
- Seleção de bandas espectrais.
- Exploração de espectros.
- Sobreposição de dados Gaia ou WISE.

Detecção automática de novos objetos não faz parte do MVP inicial.

---

# 5. OBJETOS DE TESTE

O desafio apresenta os seguintes objetos:

1. Estrela de Barnard.
2. Epsilon Indi B.
3. WISE 0855.
4. RW Aurigae.
5. R Draconis.

Para cada objeto, será necessário investigar:

- Coordenadas celestes.
- Época de referência das coordenadas.
- Movimento próprio, quando aplicável.
- Observações disponíveis no SPHEREx.
- Datas das observações.
- Bandas e detectores envolvidos.
- Qualidade e compatibilidade dos dados.

Coordenadas e resultados científicos ainda precisam ser verificados em fontes confiáveis.

WISE 0855 possui coordenadas fornecidas no contexto do desafio:

- RA: 08h55m10.831s.
- Dec: -7°14'42.53".

Conversão aproximada para graus:

- RA: 133.795129°.
- Dec: -7.245147°.

---

# 6. DIVISÃO HUMANA DA EQUIPE

A divisão inicial foi confirmada pela equipe.

## Integrante 1 — Liderança técnica

Responsável: usuário desta conversa.

Frente:

- Backend.
- Engenharia de dados.
- Arquitetura.
- Integração.
- Testes de ponta a ponta.

Responsabilidades:

1. Definir a arquitetura técnica.
2. Desenvolver o backend Python/FastAPI.
3. Investigar e implementar consultas ao IRSA.
4. Recuperar recortes de imagens FITS.
5. Processar dados com Astropy.
6. Criar endpoints.
7. Integrar frontend e backend.
8. Testar a aplicação completa.

## Integrante 2 — Liderança científica

Frente:

- Astronomia.
- Pesquisa.
- Dados científicos.
- Validação.

Responsabilidades:

1. Investigar os produtos científicos do SPHEREx.
2. Estudar formatos FITS e metadados.
3. Identificar coordenadas dos cinco objetos.
4. Pesquisar movimento próprio e épocas de referência.
5. Investigar a disponibilidade de observações.
6. Identificar imagens e bandas comparáveis.
7. Documentar limitações científicas.
8. Validar interpretações e resultados.

## Integrante 3 — Liderança de interface

Frente:

- Frontend.
- Visualização.
- Experiência do usuário.

Responsabilidades:

1. Projetar a interface.
2. Desenvolver HTML, CSS e JavaScript.
3. Criar formulário de RA, Dec e campo de visão.
4. Desenvolver o visualizador.
5. Criar controles de reprodução temporal.
6. Exibir metadados.
7. Integrar o frontend com a API.

A divisão é inicial e poderá ser ajustada conforme a evolução do projeto.

A apresentação, demonstração e pitch serão responsabilidades compartilhadas.

---

# 7. ARQUITETURA TECNOLÓGICA PREVISTA

## Backend

- Python.
- FastAPI.
- Astropy.
- Astroquery e/ou PyVO, conforme compatibilidade com os serviços disponíveis.

## Frontend

- HTML.
- CSS.
- JavaScript.

Não introduzir React ou outras tecnologias desnecessárias antes de comprovar sua necessidade.

## Fonte de dados

- SPHEREx Archive — IRSA/IPAC.
- Produtos científicos disponibilizados pelo arquivo.
- Serviços de consulta espacial e temporal, após validação.

## Fluxo previsto

Usuário → Frontend → API FastAPI → IRSA/SPHEREx → Processamento FITS/Astropy → JSON e imagens processadas → Frontend.

O frontend não deverá baixar diretamente arquivos FITS enormes.

O backend deverá processar ou extrair recortes adequados para exibição.

---

# 8. FONTES INICIAIS

SPHEREx Archive — IRSA/IPAC:

https://irsa.ipac.caltech.edu/Missions/spherex.html

Tutoriais IRSA:

https://caltech-ipac.github.io/irsa-tutorials/spherex/

Gaia:

https://archive.stsci.edu/missions-and-data/gaia

WiseView:

http://byw.tools/wiseview

As fontes deverão ser verificadas durante a pesquisa. Não presumir que endpoints, produtos ou funcionalidades estejam disponíveis sem teste.

---

# 9. ESTADO ATUAL DO REPOSITÓRIO

Diretório:

`C:\NASA-SpaceApps-2026`

Estrutura atual verificada na auditoria de 14/11/2026:

```text
NASA-SpaceApps-2026/
├── .git/
├── .opencode/
│   ├── agents/
│   │   ├── coordinator.md
│   │   ├── data-analyst.md
│   │   ├── developer.md
│   │   ├── researcher.md
│   │   └── reviewer.md
│   ├── commands/
│   │   ├── plan.md
│   │   ├── review-project.md
│   │   └── status.md
│   └── skills/
│       ├── data-analysis/
│       ├── nasa-research/
│       ├── rapid-prototyping/
│       └── scientific-validation/
├── data/
│   ├── processed/
│   ├── raw/
│   └── temporary/
├── docs/
│   ├── architecture/
│   │   ├── api-contract.md
│   │   ├── requirements.md
│   │   └── system.md
│   ├── interface/
│   ├── science/
│   │   ├── data-sources.md
│   │   ├── target-catalog.md
│   │   └── validation.md
│   ├── team/
│   │   ├── roles.md
│   │   └── workflow.md
│   ├── board.md
│   ├── challenge.md
│   ├── continuity.md
│   ├── decisions.md
│   ├── progress.md
│   └── research.md
├── src/
│   ├── backend/app/{api,core,services}/
│   └── frontend/assets/{css,js}/
├── tests/
│   ├── backend/
│   └── integration/
├── .gitignore
├── .venv/            (ambiente virtual, ignorado pelo Git)
├── AGENTS.md
├── requirements.txt
└── opencode.jsonc
```

Observação: a estrutura de diretórios acima é o esqueleto confirmado. O preenchimento dos diretórios de código, dados e testes ocorre conforme as tarefas do quadro em `docs/board.md` forem concluídas.

## Estado do Git

- Repositório local inicializado.
- Branch atual: `master`.
- **Verificado em 14/11/2026: o repositório NÃO possui remote configurado.** Não há repositório remoto compartilhado no GitHub.
- Existe 1 commit: `ce59297 chore: initialize NASA AI workspace`.
- Há modificações não commitadas em `AGENTS.md`, `docs/progress.md`, `docs/decisions.md` e `.opencode/agents/researcher.md`, e arquivos ainda não rastreados (`docs/architecture/`, `docs/challenge.md`, `docs/continuity.md`, `docs/science/`, `docs/team/`, `docs/board.md`, `docs/interface/`, `.opencode/agents/developer.md`, `requirements.txt`).
- Commits e push estão **proibidos** nesta fase, salvo autorização explícita.

## Estado do código

Na auditoria de 14/11/2026:

- `src/backend/app/{api,core,services}` e `src/frontend/assets/{css,js}`: diretórios criados, sem arquivos.
- `tests/backend` e `tests/integration`: diretórios criados, sem arquivos.
- `data/{raw,processed,temporary}`: diretórios criados, sem arquivos.

Não havia implementação funcional de backend ou frontend na auditoria. A implementação do backend foi iniciada pela tarefa T-C1 (Developer) em 14/11/2026.

## Ambiente Python

- Interpretador do projeto: `.\.venv\Scripts\python.exe` (Windows PowerShell 5.1).
- Python 3.12.5 no sistema; pacotes do projeto instalados **apenas** no ambiente virtual.
- Versões pinadas registradas na DECISÃO 005.
- O `.gitignore` protege `.venv/`, `data/raw/`, `data/temporary/`, `data/processed/` e `data/cache/`.

---

# 10. OPENCode — AGENTES EXISTENTES

Os seguintes agentes foram criados:

- coordinator: coordenação e integração.
- researcher: pesquisa científica e fontes.
- data-analyst: análise de dados.
- developer: implementação.
- reviewer: revisão independente.

Skills existentes:

- nasa-research.
- data-analysis.
- rapid-prototyping.
- scientific-validation.

Comandos existentes:

- plan.
- review-project.
- status.

Configuração principal:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "default_agent": "coordinator"
}
```

Antes de alterar agentes, verificar a documentação e a compatibilidade das permissões com a versão instalada do OpenCode.

As ferramentas web do agente researcher ainda precisam ser verificadas na prática.

Os agentes são auxiliares. Cada entrega deve ter um responsável humano.

---

# 11. DOCUMENTOS JÁ CRIADOS OU ATUALIZADOS

Na preparação inicial, foram estabelecidos:

- `AGENTS.md`: instruções gerais.
- `docs/progress.md`: acompanhamento do projeto.
- `docs/decisions.md`: registro de decisões.
- `docs/research.md`: pesquisa e referências.
- `docs/challenge.md`: descrição do desafio.

O conteúdo de progress, decisions e challenge foi preparado para refletir o desafio selecionado, a divisão da equipe e o escopo inicial.

A equipe confirmou que as alterações desses documentos estavam funcionando.

---

# 12. REGRAS OBRIGATÓRIAS PARA CONTINUIDADE

Ao assumir esta conversa:

1. Não reiniciar o projeto.
2. Não presumir que arquivos estão vazios sem verificá-los.
3. Não sobrescrever arquivos existentes sem ler seu conteúdo.
4. Não executar comandos destrutivos sem autorização.
5. Não realizar commits ou envios ao GitHub sem autorização.
6. Não implementar funcionalidades fora do MVP sem justificar.
7. Não inventar dados, coordenadas, observações ou resultados.
8. Priorizar fontes científicas oficiais.
9. Diferenciar fatos, hipóteses e estimativas.
10. Testar antes de declarar uma funcionalidade concluída.
11. Manter a documentação atualizada.
12. Preservar decisões anteriores, registrando alterações quando necessário.

## Continuidade entre sessões

No início de cada nova sessão:

1. Ler `AGENTS.md`.
2. Ler `docs/continuity.md`.
3. Ler `docs/progress.md`.
4. Ler `docs/decisions.md`.
5. Consultar `docs/challenge.md`.
6. Identificar as últimas tarefas concluídas e pendentes.

Ao finalizar etapas importantes:

1. Atualizar `docs/progress.md`.
2. Registrar decisões em `docs/decisions.md`.
3. Atualizar este documento de continuidade.
4. Atualizar a documentação técnica e científica correspondente.

---

# 13. ETAPA ATUAL DO PROJETO

O projeto está no **primeiro marco técnico: prova de viabilidade com dados reais do SPHEREx**.

A fase de definição e consolidação documental está **concluída**. Os três grupos documentais foram criados e confirmados:

### Grupo 1 — Equipe — CONCLUÍDO

- `docs/team/roles.md`
- `docs/team/workflow.md`

### Grupo 2 — Ciência — CONCLUÍDO

- `docs/science/data-sources.md`
- `docs/science/target-catalog.md`
- `docs/science/validation.md`

### Grupo 3 — Arquitetura — CONCLUÍDO

- `docs/architecture/system.md`
- `docs/architecture/api-contract.md`
- `docs/architecture/requirements.md`

Além disso, em 14/11/2026 foram executados:

- Auditoria completa do repositório, com registro de inconsistências (I-01 a I-09) e riscos (R-01 a R-10) em `docs/board.md`.
- Preparação do ambiente Python em `.venv` (DECISÃO 005).
- Criação do quadro de tarefas provisório `docs/board.md` (DECISÃO 006).
- Correção do `.gitignore` para proteger `data/processed/` e `data/cache/`.

## Atividades em andamento

Tarefas ativas e seus responsáveis estão registrados em `docs/board.md` §2. Na auditoria de 14/11/2026:

- **T-A** — Researcher: investigação dos produtos SPHEREx, serviços do IRSA, SIA2, cutout, épocas de observação, metadados e dos cinco objetos de teste.
- **T-B** — Data Analyst: obtenção e caracterização de arquivos FITS reais e verificação da existência de sequência temporal utilizável.
- **T-C1** — Developer: plano de implementação, esqueleto do backend FastAPI, cliente IRSA configurável, schemas e testes.
- **T-E** — Coordinator: manutenção da documentação e do quadro.

## Próximas atividades

1. Concluir T-A, T-B e T-C1 e consolidar as evidências.
2. Implementar T-C2 (cliente IRSA real, recorte real, `/api/observations` com dados reais).
3. Submeter as entregas a T-D (revisão independente).
4. Iniciar o frontend contra a API real (Integrante 3).
5. Configurar o repositório compartilhado e migrar o quadro para GitHub Issues/Projects.
6. Normalizar o esquema de permissões dos agentes (T-F), após aprovação.

---

# 14. PRIMEIRO MARCO TÉCNICO

O primeiro marco técnico não é construir a interface completa.

É comprovar que conseguimos:

1. Consultar o arquivo IRSA/SPHEREx.
2. Pesquisar uma coordenada celeste.
3. Encontrar observações disponíveis.
4. Identificar as datas e os metadados.
5. Recuperar pelo menos um recorte de imagem.
6. Verificar se existe uma sequência temporal utilizável.

Somente depois dessa comprovação devemos avançar para a implementação completa do visualizador.

---

# 15. INSTRUÇÃO AO NOVO CHAT

Continue exatamente do ponto em que o projeto parou.

Não repita a preparação já realizada.

Primeiro, considere este documento como contexto de continuidade. Em seguida, solicite ou execute a inspeção dos arquivos atuais quando necessário.

A prioridade imediata é concluir os três grupos documentais:

1. Equipe e fluxo de trabalho.
2. Pesquisa e validação científica.
3. Arquitetura e requisitos técnicos.

Trabalhe de forma progressiva, explicando:

- Qual arquivo será criado ou alterado.
- Qual é sua finalidade.
- Onde deverá ser salvo.
- Qual conteúdo deverá receber.
- Como verificar se ficou correto.

Forneça comandos compatíveis com Windows PowerShell 5.1.

Não avance para a próxima etapa sem verificar a anterior.

Mantenha o projeto tecnicamente simples, cientificamente correto e orientado à entrega de um MVP funcional.