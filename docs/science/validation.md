# Plano de validação científica

## 1. Objetivo

Definir os critérios científicos e técnicos necessários para garantir que as observações utilizadas pela aplicação sejam corretamente identificadas, organizadas e apresentadas.

A validação deverá evitar interpretações incorretas causadas por diferenças de coordenadas, épocas, bandas, detectores, calibração ou qualidade das imagens.

## 2. Princípios

- Utilizar fontes científicas identificáveis.
- Preservar a origem dos dados.
- Registrar os metadados relevantes.
- Diferenciar observações de inferências.
- Não confundir variação instrumental com fenômeno astronômico.
- Não declarar movimento ou variabilidade sem evidências adequadas.
- Documentar limitações e resultados inconclusivos.

## 3. Validação astrométrica

Objetivo: garantir que a região consultada corresponda corretamente ao objeto de interesse.

Verificar:

- Coordenadas de referência.
- Sistema de coordenadas.
- Unidade angular.
- Época de referência.
- Movimento próprio.
- Paralaxe, quando relevante.
- Transformações de coordenadas.
- WCS dos produtos de imagem.

Para objetos com movimento próprio significativo, avaliar a posição esperada na época de cada observação.

Não utilizar uma única coordenada fixa como se ela representasse necessariamente a posição do objeto em todas as épocas.

## 4. Validação temporal

Objetivo: garantir que a sequência apresentada represente observações em momentos diferentes.

Verificar:

- Data e horário da observação.
- Formato e escala temporal dos metadados.
- Ordenação cronológica.
- Duplicidade de produtos.
- Distância temporal entre observações.
- Cobertura temporal disponível.

A aplicação deverá distinguir a data da observação da data de processamento ou publicação do produto, quando ambas existirem.

## 5. Validação espectral

Objetivo: evitar a mistura indevida de imagens de diferentes bandas espectrais em uma sequência apresentada como temporal.

Verificar:

- Identificação da banda.
- Comprimento de onda ou intervalo espectral.
- Convenção utilizada pelo produto.
- Compatibilidade entre observações.
- Disponibilidade de filtros na consulta.

Imagens de bandas diferentes não deverão ser tratadas como observações equivalentes sem uma justificativa científica explícita.

## 6. Validação instrumental

Objetivo: identificar diferenças que possam afetar a interpretação das imagens.

Verificar:

- Detector.
- Campo de visão.
- Orientação.
- Resolução.
- PSF, quando disponível.
- Calibração.
- Indicadores de qualidade.
- Artefatos instrumentais.
- Saturação e regiões mascaradas.
- Contaminação por fontes próximas.

Uma diferença visual entre duas imagens não deve ser atribuída automaticamente a movimento ou variabilidade do objeto.

## 7. Validação das imagens

Verificar:

- Integridade do arquivo FITS.
- Estrutura das HDUs.
- Dimensões.
- Cabeçalho.
- WCS.
- Valores ausentes ou inválidos.
- Máscaras e sinalizadores.
- Unidades.
- Processo de geração do recorte.

Registrar as transformações realizadas no processamento.

## 8. Comparabilidade fotométrica

Para testes de variação de brilho, verificar:

- Banda espectral compatível.
- Calibração fotométrica.
- Unidades dos valores.
- Efeitos instrumentais.
- Fundo do céu.
- Contaminação por fontes próximas.
- Saturação.
- Qualidade das observações.
- Método de medição utilizado.

Não comparar valores de pixels de imagens processadas de formas diferentes sem justificar e documentar o método.

A normalização visual utilizada para exibição não deverá ser confundida com uma medição fotométrica.

## 9. Validação da sequência temporal

Antes de apresentar uma sequência:

1. Identificar todas as observações.
2. Verificar suas datas.
3. Organizar cronologicamente.
4. Identificar as bandas.
5. Identificar os detectores.
6. Verificar a qualidade.
7. Identificar possíveis incompatibilidades.
8. Registrar quais observações foram incluídas ou excluídas.

A sequência deverá informar claramente quais características são comparáveis.

## 10. Classificação das evidências

Cada conclusão deverá ser classificada como:

- **Confirmada:** sustentada pelos dados e metadados examinados.
- **Indicativa:** sugere um fenômeno, mas exige análise adicional.
- **Inconclusiva:** dados insuficientes ou incompatíveis.
- **Não observada:** não foi identificada evidência no conjunto examinado.

## 11. Critérios de aprovação científica

Uma demonstração será considerada cientificamente adequada quando:

- A origem das imagens estiver identificada.
- As coordenadas forem documentadas.
- As datas forem verificáveis.
- As bandas estiverem identificadas.
- Os metadados relevantes forem preservados.
- As limitações forem apresentadas.
- A interpretação não ultrapassar o que os dados sustentam.

## 12. Registro dos testes

Para cada teste, registrar:

| Campo | Conteúdo |
|---|---|
| Identificador | Código do teste |
| Objeto | Objeto investigado |
| Coordenadas | Posição consultada |
| Época | Referência temporal |
| Fonte | Serviço ou catálogo |
| Produtos | Identificadores dos arquivos |
| Critério | O que está sendo validado |
| Resultado | Aprovado, parcial ou inconclusivo |
| Evidência | Arquivos, metadados ou registros |
| Limitações | Restrições encontradas |
| Responsável | Integrante responsável |

## 13. Responsabilidade

**Liderança científica:** Integrante 2.

**Apoio técnico:** Integrante 1.

A interface deverá apresentar os metadados e as limitações de maneira compreensível ao usuário.