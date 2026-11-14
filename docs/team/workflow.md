# Fluxo de trabalho da equipe

## 1. Objetivo

Estabelecer um processo de colaboração que permita aos três integrantes trabalhar em paralelo sem gerar conflitos desnecessários no código, na documentação ou na arquitetura.

## 2. Organização das tarefas

O projeto deverá utilizar GitHub Issues e GitHub Projects quando o repositório compartilhado estiver configurado.

Cada tarefa deverá possuir:

- Identificador ou número da Issue.
- Título objetivo.
- Descrição do problema.
- Resultado esperado.
- Responsável humano.
- Frente responsável.
- Arquivos ou módulos envolvidos.
- Dependências.
- Critérios de aceitação.
- Evidências de conclusão.

Agentes de IA poderão ser indicados como apoio, mas não como responsáveis humanos.

## 3. Etapas do quadro de tarefas

| Etapa | Significado |
|---|---|
| Backlog | Tarefas identificadas, ainda não priorizadas |
| Pronta | Tarefa definida e disponível para execução |
| Em andamento | Responsável trabalhando na tarefa |
| Em revisão | Aguardando análise e testes |
| Concluída | Critérios atendidos e alterações integradas |

## 4. Fluxo de execução

### Etapa 1 — Planejamento

Antes de começar:

1. Ler a descrição da tarefa.
2. Consultar a documentação relacionada.
3. Identificar dependências.
4. Verificar os arquivos envolvidos.
5. Confirmar os critérios de aceitação.

### Etapa 2 — Desenvolvimento

Durante a execução:

1. Trabalhar em uma branch própria da tarefa.
2. Evitar alterações não relacionadas.
3. Manter o código simples e organizado.
4. Registrar decisões importantes.
5. Executar testes.
6. Atualizar a documentação quando necessário.

### Etapa 3 — Revisão

Ao concluir:

1. Conferir os arquivos alterados.
2. Executar os testes pertinentes.
3. Registrar evidências.
4. Abrir um Pull Request.
5. Solicitar revisão de outro integrante.

### Etapa 4 — Integração

Uma tarefa só deverá ser considerada concluída depois que:

- A revisão for aprovada.
- Os testes necessários forem executados.
- Os critérios de aceitação forem atendidos.
- As alterações forem integradas à branch principal.

## 5. Estratégia de branches

A branch principal deverá conter apenas versões integradas e revisadas.

Inicialmente, o repositório utiliza a branch `master`. A equipe poderá padronizá-la como `main` quando configurar o repositório compartilhado.

Padrão recomendado:

- `feature/descricao-da-funcionalidade`
- `fix/descricao-da-correcao`
- `docs/descricao-da-documentacao`
- `test/descricao-dos-testes`

Exemplos:

- `feature/irsa-query`
- `feature/temporal-viewer`
- `feature/api-observations`
- `docs/science-validation`

Cada tarefa deverá utilizar uma branch própria quando envolver alterações no repositório.

Não trabalhar diretamente na branch principal.

## 6. Prevenção de conflitos

Antes de iniciar uma tarefa, identificar os arquivos que serão alterados.

Não permitir que dois integrantes ou agentes modifiquem simultaneamente o mesmo arquivo sem coordenação explícita.

Se duas tarefas precisarem alterar o mesmo módulo:

1. Definir a ordem de execução.
2. Estabelecer quem será responsável pela alteração principal.
3. Dividir o trabalho por arquivos ou interfaces quando possível.
4. Integrar as alterações por Pull Request.

O contrato da API e os documentos de arquitetura deverão ser tratados como referências compartilhadas.

Alterações nesses contratos exigem comunicação entre as frentes envolvidas.

## 7. Revisão técnica e científica

A revisão deverá considerar duas dimensões independentes.

### Revisão técnica

Verificar:

- Funcionamento.
- Estrutura do código.
- Tratamento de erros.
- Segurança.
- Testes.
- Compatibilidade com a arquitetura.
- Aderência aos requisitos.

### Validação científica

Verificar:

- Origem dos dados.
- Identificação dos objetos.
- Coordenadas.
- Épocas de observação.
- Bandas espectrais.
- Metadados.
- Qualidade das imagens.
- Limitações instrumentais.
- Coerência das interpretações.

Uma revisão técnica aprovada não significa automaticamente que o resultado científico está validado.

## 8. Critérios para considerar uma tarefa concluída

Uma tarefa deverá atender aos seguintes critérios:

- Resultado implementado ou documentado.
- Critérios de aceitação atendidos.
- Testes executados quando aplicáveis.
- Evidências registradas.
- Revisão realizada.
- Documentação atualizada.
- Alterações integradas.

## 9. Comunicação da equipe

Mudanças que afetem arquitetura, dados, contratos ou escopo deverão ser comunicadas aos integrantes envolvidos.

Problemas e bloqueios deverão ser registrados na Issue correspondente.

Decisões relevantes deverão ser documentadas em `docs/decisions.md`.

O progresso geral deverá ser atualizado em `docs/progress.md`.

## 10. Definition of Ready

Uma tarefa está pronta para começar quando:

- O objetivo está claro.
- O responsável humano está definido.
- Os critérios de aceitação estão definidos.
- As dependências foram identificadas.
- Os arquivos envolvidos foram conhecidos.
- Não existem dúvidas fundamentais que impeçam a execução.

## 11. Definition of Done

Uma tarefa está concluída quando:

- A entrega existe.
- Os critérios foram atendidos.
- Os testes necessários passaram.
- A revisão foi aprovada.
- A documentação foi atualizada.
- O resultado está integrado ao projeto.