# NASA Space Apps Challenge 2026

## 1. Desafio selecionado

Desafio avançado relacionado à criação de uma ferramenta web pública para exploração temporal de imagens da missão SPHEREx.

**Título oficial:** A confirmar conforme o enunciado original do desafio.

## 2. Contexto científico

A missão SPHEREx realiza levantamentos de todo o céu em diferentes faixas do infravermelho próximo.

O arquivo científico disponibiliza produtos de observação que podem ser utilizados para investigar diferentes objetos e regiões celestes.

A aplicação deverá permitir que usuários explorem imagens de uma mesma região do céu obtidas em diferentes momentos.

É fundamental distinguir:

- **Bandas espectrais:** diferentes intervalos de comprimento de onda.
- **Épocas de observação:** momentos distintos em que uma região foi observada.

As bandas espectrais não devem ser tratadas automaticamente como quadros de uma sequência temporal.

## 3. Problema que queremos resolver

A exploração de observações astronômicas pode exigir conhecimento de ferramentas especializadas, formatos científicos e procedimentos de consulta a arquivos de dados.

Nossa proposta é oferecer uma interface acessível para que usuários possam pesquisar coordenadas celestes e explorar visualmente observações disponíveis ao longo do tempo.

## 4. Solução proposta

Desenvolver uma aplicação web que permita:

1. Informar Ascensão Reta (RA).
2. Informar Declinação (Dec).
3. Selecionar o campo de visão.
4. Consultar o arquivo científico SPHEREx.
5. Organizar as observações disponíveis cronologicamente.
6. Exibir as imagens em um visualizador.
7. Reproduzir, pausar e navegar entre as observações.
8. Consultar os metadados de cada imagem.

## 5. Objetos de teste

A aplicação deverá ser investigada utilizando os objetos mencionados no desafio:

- Estrela de Barnard.
- Epsilon Indi B.
- WISE 0855.
- RW Aurigae.
- R Draconis.

A disponibilidade de observações úteis para cada objeto ainda precisa ser verificada.

## 6. Requisitos científicos

- Utilizar fontes oficiais e registrar referências.
- Identificar corretamente os produtos científicos.
- Registrar datas e metadados das observações.
- Distinguir épocas de observação de bandas espectrais.
- Considerar movimento próprio dos objetos.
- Verificar compatibilidade entre imagens antes de compará-las.
- Não interpretar diferenças instrumentais como fenômenos astronômicos sem validação.
- Identificar limitações e ausência de dados.

## 7. Escopo do MVP

### Essencial

- Busca por coordenadas.
- Seleção de campo de visão.
- Consulta a imagens reais.
- Organização temporal.
- Visualizador com controles.
- Metadados.
- Testes com os objetos indicados.

### Evolução

- Comparação entre duas épocas.
- Subtração de imagens.
- Seleção de bandas espectrais.
- Exploração de espectros.
- Sobreposição de catálogos externos.

### Fora do escopo inicial

Detecção automática de novos objetos e funcionalidades que não sejam necessárias para demonstrar o fluxo principal.

## 8. Critério de sucesso

A solução deverá demonstrar que um usuário consegue pesquisar uma região do céu, encontrar observações reais disponíveis, explorar sua sequência temporal e compreender os metadados associados.

A aplicação não deverá apresentar dados simulados como se fossem observações reais.

## 9. Fontes de referência

- SPHEREx Archive — IRSA/IPAC: https://irsa.ipac.caltech.edu/Missions/spherex.html
- Tutoriais IRSA: https://caltech-ipac.github.io/irsa-tutorials/spherex/

As fontes, versões dos produtos, datas de consulta e descobertas deverão ser documentadas em `docs/research.md` e nos documentos científicos específicos.