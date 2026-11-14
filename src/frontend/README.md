# SPHEREx Explorer — Frontend

Interface web (HTML, CSS e JavaScript puro, sem dependências).

## Estrutura
- `index.html`: página principal (pesquisa, visualizador e galeria)
- `termos.html`: página "Aprenda os termos" (glossário em linguagem simples)
- `css/styles.css`: estilos responsivos e acessíveis
- `js/app.js`: validação, chamadas à API, modo demonstração e visualizador temporal
- `assets/`: imagens e ícones estáticos

## Como executar
1. Inicie o backend (FastAPI) em `http://localhost:8000` com CORS habilitado.
2. Na pasta `src/frontend`, rode: `python -m http.server 5500`
3. Abra `http://localhost:5500`.

Sem backend, marque "Usar dados fictícios" para testar a interface.

## Configuração
Ajuste `CONFIG` e `normalizeObservation()` no topo de `js/app.js` conforme `docs/architecture/api-contract.md`.

## Link por coordenadas e incorporação
- `index.html?ra=133.79513&dec=-7.24515&fov=3`: abre e já executa a busca.
- Acrescente `&embed=1` para mostrar só o visualizador (use em `<iframe>`).
- RA/Dec aceitam graus ou sexagesimal (`08h55m10.831s`, `-7d14m42.53s`).
- Para apontar para outra versão dos dados, use `CONFIG.EXTRA_PARAMS` em `js/app.js`.

## Alvos de exemplo (vindos do backend)
O frontend não guarda coordenadas. Os botões de alvo são carregados de `GET /api/targets`
(`CONFIG.TARGETS_PATH`), que deve retornar, por exemplo:

```json
[{ "name": "WISE 0855", "ra": 133.79513, "dec": -7.24515, "fov": 3, "note": "opcional" }]
```
RA/Dec em graus. Se o endpoint falhar, a página avisa e a busca manual continua funcionando.

## Filtros por detector e comprimento de onda
Cada observação da API deve trazer (nomes aceitos entre parênteses):
- `detector` (ou `detector_id`): 1 a 6, também aceita "D3"
- `wavelength_um` (ou `wavelength`): comprimento de onda em micrômetros
- `band_index` (ou `band`): número da banda (1 a 102)

Sem `detector` ou sem `wavelength`, o filtro correspondente fica oculto e as observações nunca são descartadas por ele.

## Espectro de um ponto
Clique na imagem (ou foque nela, use as setas e Enter) para marcar o ponto A (alvo) e o ponto B (fundo do céu).
O frontend converte a posição clicada em RA/Dec, assumindo imagem quadrada com lado = FOV, centrada na busca,
com norte para cima e leste à esquerda (`CONFIG.IMAGE_EAST_LEFT`). Depois chama:

`GET /api/spectrum?ra=<graus>&dec=<graus>&radius=<segundos de arco>`

Resposta esperada (lista direta ou objeto com `points`):
```json
{ "unit": "MJy/sr", "points": [
  { "wavelength_um": 0.78, "flux": 12.3, "flux_err": 0.4, "detector": 1, "band_index": 1 }
] }
```
`flux_err`, `detector` e `band_index` são opcionais. O gráfico usa uma cor por detector (paleta Okabe-Ito),
círculos para A e losangos para B, e há uma tabela e um CSV com os mesmos dados.

## Mapa de observações (plano cartesiano)
Gráfico gerado só com os dados já devolvidos pela busca: eixo X = data (`obs_date`), eixo Y = comprimento de onda
(`wavelength_um`), cor = detector. Sem `wavelength_um`, o eixo Y passa a ser o detector. Clicar num ponto abre o quadro
correspondente, e o anel branco acompanha o quadro em exibição. Pontos escondidos pelos filtros ficam apagados.
Não exige endpoint novo.

## Mapa do céu (Aladin Lite)
Carregado sob demanda (botão "Carregar mapa interativo") a partir de `CONFIG.ALADIN_URL`. Mostra o retângulo do FOV,
o centro da busca, os pontos A/B e, opcionalmente, catálogos Gaia DR3 e AllWISE (via VizieR/CDS).
Depende de internet e de serviços externos do CDS. Depois de testar, troque a URL `latest` por uma versão fixa.

### Clique no mapa
O mapa abre com o céu todo (projeção AIT, `fov: 360`). Clicar num ponto (sem arrastar) preenche RA/Dec no formulário,
mantém o FOV atual e executa a busca; depois o mapa é recentrado e aproximado na região. "Ver o céu todo" volta ao zoom máximo.
Com o céu inteiro na tela, a precisão do clique é baixa: aproxime o zoom e clique de novo.

### Mapa de fundo = dados do SPHEREx
O fundo padrão do mapa são os mapas HiPS da missão publicados pelo CDS (um por detector, versão QR2):
`https://alasky.cds.unistra.fr/SPHEREx/D1` ... `D6` (`CONFIG.SPHEREX_HIPS_BASE`). Confirmados no registro VO: D1 e D3; D2, D4, D5 e D6
seguem o mesmo padrão de nome e precisam ser testados. Em novembro de 2026 saiu o Data Release 1 (DR1) no IRSA: quando houver HiPS do DR1,
troque a constante. DSS2, 2MASS e AllWISE continuam disponíveis só como comparação.
