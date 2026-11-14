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
