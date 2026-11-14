# SPHEREx Explorer — Frontend

Interface web (HTML, CSS e JavaScript puro, sem dependências).

## Estrutura
- `index.html`: estrutura semântica da página
- `css/styles.css`: estilos responsivos e acessíveis
- `js/app.js`: validação, chamadas à API, modo demonstração e visualizador temporal
- `assets/`: imagens e ícones estáticos

## Como executar
1. Inicie o backend (FastAPI) em `http://localhost:8000`.
2. Na pasta `src/frontend/src/frontend`, rode: `python -m http.server 5173`
3. Abra `http://localhost:5173`.

O CORS padrão do backend só aceita `http://localhost` e `http://127.0.0.1`
nas portas 5173, 3000 e 8000. Abrir o `index.html` direto (`file://`) não
funciona. Para usar outra porta, defina `SPHEREX_CORS_ORIGINS` no backend.

Sem backend, marque "Usar dados fictícios" para testar a interface.

## Contrato usado
- `GET /api/observations?ra_deg=&dec_deg=&fov_arcmin=`
  (0 ≤ RA < 360, −90 ≤ Dec ≤ 90, 0,1 ≤ FOV ≤ 120 minutos de arco).
- Cada observação: `id`, `observed_at` (ISO UTC ou `null`), `band`, `detector`,
  `image_url` (relativo, ex. `/api/images/{id}`) e `metadata`.
- Observações com `observed_at` nulo são omitidas da sequência; a interface
  informa quantas foram omitidas.
- Vários detectores podem compartilhar o mesmo instante: o filtro "Detector"
  permite ver a sequência temporal de um só detector.
- A galeria mostra no máximo `CONFIG.GALLERY_MAX` miniaturas (carregamento lazy).
- Erros no envelope `{"error": {"code", "message"}}`: `NO_OBSERVATIONS_FOUND`
  e `SOURCE_UNAVAILABLE` têm mensagens próprias; os demais exibem a `message`
  do backend.

## Configuração
Ajuste `CONFIG` no topo de `js/app.js` (URL do backend, timeout, limites e
tamanho da galeria).
