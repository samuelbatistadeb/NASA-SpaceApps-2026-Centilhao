# SPHEREx Explorer — Frontend

Interface web (HTML, CSS e JavaScript puro, sem dependências).

## Estrutura
- `index.html`: estrutura semântica da página
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
