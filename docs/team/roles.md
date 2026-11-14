# Organização da equipe e responsabilidades

## 1. Objetivo

Definir as responsabilidades humanas e as funções de apoio dos agentes de IA durante o desenvolvimento do NASA Space Apps Challenge 2026.

A equipe possui três integrantes e será organizada em três frentes principais.

Cada frente possui um responsável humano. Os agentes de IA podem auxiliar na pesquisa, planejamento, implementação e revisão, mas não substituem a responsabilidade dos integrantes.

## 2. Estrutura da equipe

### Integrante 1 — Liderança técnica

**Responsável:** Integrante 1.

**Frente:** Backend, dados e integração.

**Objetivo:** Construir a infraestrutura responsável por consultar os dados científicos do SPHEREx, processar as imagens e disponibilizar os resultados ao frontend.

Responsabilidades:

1. Definir e manter a arquitetura técnica.
2. Desenvolver o backend utilizando Python e FastAPI.
3. Investigar e implementar consultas ao arquivo IRSA.
4. Recuperar imagens e recortes FITS.
5. Processar imagens e metadados utilizando ferramentas adequadas.
6. Desenvolver os endpoints da API.
7. Definir contratos de comunicação com o frontend.
8. Integrar os módulos desenvolvidos.
9. Executar testes de integração.
10. Documentar decisões técnicas e limitações.

Entregas esperadas:

- Backend funcional.
- Integração com o arquivo científico.
- Processamento de imagens.
- API documentada.
- Testes técnicos.
- Integração final da aplicação.

Agentes de apoio:

- coordinator.
- developer.
- data-analyst.
- reviewer.

### Integrante 2 — Liderança científica

**Responsável:** Integrante 2.

**Frente:** Astronomia, pesquisa e validação científica.

**Objetivo:** Garantir que os dados utilizados sejam apropriados e que as interpretações apresentadas pela aplicação sejam cientificamente justificáveis.

Responsabilidades:

1. Estudar a missão SPHEREx e seus produtos científicos.
2. Investigar os formatos e metadados dos arquivos disponibilizados.
3. Identificar as coordenadas dos objetos de teste.
4. Verificar as épocas de referência das coordenadas.
5. Investigar movimento próprio dos objetos.
6. Consultar a disponibilidade de observações.
7. Identificar bandas, detectores e datas.
8. Avaliar a compatibilidade entre observações.
9. Identificar limitações instrumentais e científicas.
10. Validar resultados e documentar as fontes utilizadas.

Entregas esperadas:

- Catálogo dos objetos de teste.
- Registro de fontes científicas.
- Levantamento de observações disponíveis.
- Relatório de validação.
- Identificação de limitações.
- Evidências de que as imagens podem ser utilizadas na exploração temporal.

Agentes de apoio:

- researcher.
- data-analyst.
- reviewer.

### Integrante 3 — Liderança de interface

**Responsável:** Integrante 3.

**Frente:** Frontend, visualização e experiência do usuário.

**Objetivo:** Desenvolver uma interface acessível para pesquisar coordenadas e explorar imagens astronômicas ao longo do tempo.

Responsabilidades:

1. Planejar a experiência do usuário.
2. Desenvolver a estrutura HTML.
3. Implementar os estilos CSS.
4. Desenvolver funcionalidades JavaScript.
5. Criar o formulário de coordenadas.
6. Criar a seleção do campo de visão.
7. Desenvolver o visualizador de imagens.
8. Implementar controles de reprodução temporal.
9. Exibir metadados das observações.
10. Integrar o frontend com a API.

Entregas esperadas:

- Interface funcional.
- Formulário de pesquisa.
- Visualizador temporal.
- Controles de navegação.
- Exibição de metadados.
- Integração com a API.

Agentes de apoio:

- developer.
- reviewer.
- rapid-prototyping.

## 3. Responsabilidades compartilhadas

Todos os integrantes devem participar de:

- Planejamento geral.
- Discussões sobre o escopo.
- Revisão das entregas.
- Testes da aplicação.
- Preparação da demonstração.
- Elaboração do pitch.
- Apresentação do projeto.

Cada integrante deverá compreender e conseguir explicar sua própria frente de trabalho.

## 4. Responsabilidade humana e apoio dos agentes

Os agentes de IA são ferramentas auxiliares.

Cada tarefa deverá possuir:

- Um responsável humano.
- Um objetivo definido.
- Critérios de aceitação.
- Evidências de conclusão.
- Um agente de apoio opcional.

O responsável humano deverá revisar o resultado produzido pelo agente antes de considerá-lo concluído.

## 5. Limites de responsabilidade

A liderança técnica não deverá alterar decisões científicas sem validação da liderança científica.

A liderança científica não deverá presumir que uma implementação técnica funciona sem testes.

A liderança de interface não deverá definir contratos de API incompatíveis com a arquitetura acordada.

Alterações que afetem mais de uma frente deverão ser discutidas antes da implementação.

## 6. Ajustes futuros

A divisão atual é uma organização inicial.

As responsabilidades poderão ser redistribuídas caso a equipe identifique diferenças relevantes de experiência, disponibilidade ou necessidade técnica.

Toda alteração significativa deverá ser registrada em `docs/decisions.md`.