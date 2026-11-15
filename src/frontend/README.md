# SPHEREx Explorer — Frontend

Interface web (HTML, CSS e JavaScript puro, sem dependências).

## Estrutura
- `index.html`: página principal (pesquisa, visualizador e galeria)
- `termos.html`: página "Aprenda os termos" (glossário em linguagem simples)
- `css/styles.css`: estilos responsivos e acessíveis
- `js/app.js`: validação, chamadas à API, modo demonstração e visualizador temporal
- `assets/`: imagens e ícones estáticos

## Como executar
1. Na raiz do repositório, inicie o backend:
   `.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir src/backend --port 8000`
2. Na pasta `src/frontend`, rode: `python -m http.server 5173`
3. Abra `http://localhost:5173`.

Use a porta **5173** (ou 3000): o CORS do backend só libera `localhost`/`127.0.0.1` nas portas
5173, 3000 e 8000. Para outra porta, defina `SPHEREX_CORS_ORIGINS=http://localhost:<porta>` antes de
subir o backend. Abrir `index.html` direto do disco (`file://`) não funciona.

Sem backend, marque "Usar dados fictícios" para testar a interface.

## Contrato com o backend
`GET /api/observations?ra_deg=&dec_deg=&fov_arcmin=` devolve `{ observations: [...] }` em ordem
cronológica. Cada observação é **uma exposição de um detector**: `id`, `observed_at` (UTC),
`detector` ("D1".."D6"), `band`, `image_url` (`/api/images/{id}`, PNG) e `metadata`
(`product_id`, `wavelength_min_nm`/`wavelength_max_nm`, `exposure_time_s`, `data_release`...).
Erros chegam como `{ error: { code, message } }`. A conversão para o formato interno está em
`normalizeObservation()` (`js/app.js`).

Cada imagem é recortada no IRSA sob demanda (~10–15 s na primeira vez, depois fica em cache);
por isso a galeria mostra só as `CONFIG.GALLERY_MAX` primeiras e as baixa em fila:
- no máximo `CONFIG.THUMB_CONCURRENCY` (2) miniaturas por vez (o IRSA responde 503 com muitos pedidos simultâneos);
- a fila só avança quando a imagem principal termina de carregar (ou falha); ao trocar de quadro ela volta a ter prioridade.
  Miniaturas já em download não são interrompidas;
- nova busca ou filtro descarta a fila anterior: miniaturas antigas que ainda não começaram nunca são pedidas;
- miniatura com erro mostra "falha ao carregar" e a fila segue;
- no modo fictício (imagens `data:`) as miniaturas carregam direto, sem fila.

## Link por coordenadas e incorporação
- `index.html?ra=133.79513&dec=-7.24515&fov=3`: abre e já executa a busca.
- Acrescente `&embed=1` para mostrar só o visualizador (use em `<iframe>`).
- RA/Dec aceitam graus ou sexagesimal (`08h55m10.831s`, `-7d14m42.53s`).
- Para apontar para outra versão dos dados, use `CONFIG.EXTRA_PARAMS` em `js/app.js`.

## Alvos de exemplo (vindos do backend)
O frontend não guarda coordenadas. Os botões de alvo são carregados de `GET /api/targets`
(`CONFIG.TARGETS_PATH`, implementado em `src/backend/app/api/targets.py`), que retorna:

```json
{ "targets": [{ "name": "WISE 0855", "ra": 133.737467, "dec": -7.240406, "fov": 3,
  "position_epoch": "2025.35", "note": "...", "source": "docs/science/target-catalog.md §3.3 ..." }] }
```
RA/Dec em graus. Para objetos de alto movimento próprio, a posição já vem propagada para as
épocas SPHEREx (WISE 0855 se deslocou ~3,5′ desde a coordenada J2000 do desafio).
Se o endpoint falhar, a página avisa e a busca manual continua funcionando.

### Movimento próprio
Se o alvo trouxer `pm_ra_cosdec_masyr`, `pm_dec_masyr` (mas/ano) e `ref_epoch_jyear` (ano juliano),
todos numéricos, o clique no botão guarda esse movimento (`state.motion`) e a busca envia os três
parâmetros a `/api/observations`; o backend recorta cada observação na posição propagada para a data dela.
- O movimento só vale para as coordenadas exatas do alvo: editar RA ou Dec, clicar no mapa do céu ou
  abrir uma URL sem os três parâmetros o descarta. Mudar só o FOV o mantém.
- A URL compartilhada inclui os três parâmetros (mais `alvo`, o nome exibido) e os restaura ao abrir.
- Os detalhes do quadro mostram "Centro do recorte" (`metadata.cutout_center_ra_deg/dec_deg`) e indicam
  quando `position_source` é `"proper_motion"`. A mensagem de status só cita a correção se o backend
  confirmar em pelo menos uma observação. Sem esses campos (backend antigo), nada muda na interface.
- No modo de dados fictícios o movimento é ignorado.

### Seguir o alvo
Com movimento próprio, aparece o checkbox "Seguir o movimento do alvo" (marcado por padrão). Desmarcado,
a busca **não** envia os três parâmetros: o quadro fica fixo no céu e dá para ver o alvo se deslocar.
Mudar o checkbox refaz a busca; a URL guarda `seguir=0` quando desmarcado.

## Seletor de FOV e cobertura
Régua logarítmica (0,5′ a 30′) sincronizada com o campo numérico (que continua sendo validado no envio),
com paradas 1′ Detalhe, 3′ Objeto, 5′ Vizinhança, 10′ Região e 30′ Campo amplo. Mostra ao vivo o lado em
pixels SPHEREx (6,15″/px), a comparação com a Lua (~31′) e, quando houver, os números de
`GET /api/coverage?ra_deg=&dec_deg=[&pm_ra_cosdec_masyr=&pm_dec_masyr=&ref_epoch_jyear=]`
(`{ fovs: [{ fov_arcmin, pixels, observations, complete, partial, estimated_kb_per_image }], recommended_fov_arcmin,
motion_arcsec_over_survey, pixel_scale_arcsec }`). O pedido sai 600 ms depois de RA/Dec ficarem válidos, cancela o
anterior e falha em silêncio. Os parâmetros de movimento só vão quando "Seguir o alvo" está marcado (mesmo
quadro que a busca usará). Para FOV fora da lista, o custo por imagem é escalado pela área a partir do FOV
listado mais próximo e marcado com "≈". O retângulo do FOV no mapa do céu acompanha a régua.

## Quadros parciais e área sem dados
- `metadata.coverage_fraction` (0–1) vira `coverage`; quadro parcial = `< 0,999` (mesmo limiar do backend).
- Legenda e detalhes mostram "Cobertura do quadro: 72%"; a galeria marca o quadro com o selo "parcial".
- "Só quadros completos" (nos filtros, desligado a cada busca) esconde os parciais; quadros sem a informação ficam visíveis.
- Imagens e miniaturas têm fundo hachurado: pixel transparente = fora do detector. Pixels na cor #B03060
  são inválidos dentro do detector (núcleo saturado, pixel defeituoso). A legenda abaixo da imagem explica.

## Combinar épocas
`GET /api/composite?op=mean&a=ids` e `?op=diff&a=ids&b=ids` (PNG). Exige um único detector ativo no filtro.
- Somar: até 40 observações visíveis do detector; com mais, prioriza as de maior `coverage`.
- Diferença: A = metade mais recente, B = metade mais antiga (até 20 cada, as mais distantes no tempo).
  Claro = mais brilho em A, escuro = mais brilho em B, cinza = sem mudança.
- Erros `{ error: { code, message } }` aparecem na seção; em modo fictício nada é pedido (aviso).
- Os cabeçalhos `X-SpherEx-*` só são usados se o CORS os expuser; a legenda não depende deles.

## Filtros por detector e comprimento de onda
- O filtro por detector usa `detector` ("D1".."D6"). Para comparar épocas, deixe um detector só:
  cada detector vê outra faixa do infravermelho.
- O filtro de comprimento de onda fica oculto com dados reais: cada imagem SPHEREx cobre uma
  **faixa** (o comprimento de onda varia ao longo do detector), não um valor único. A faixa do
  detector aparece nos detalhes do quadro.

## Espectro de um ponto
> **Ainda não implementado no backend.** Com dados reais a página informa que o espectro não está
> disponível; com "dados fictícios" a seção funciona. Atenção: os recortes reais vêm na orientação
> do detector (não norte para cima), então a conversão clique → RA/Dec abaixo ainda não vale para eles.

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
Gráfico gerado só com os dados já devolvidos pela busca: eixo X = data (`observed_at`), eixo Y = detector,
cor = detector. Clicar num ponto abre o quadro
correspondente, e o anel branco acompanha o quadro em exibição. Pontos escondidos pelos filtros ficam apagados.
Não exige endpoint novo.

## Mapa do céu (Aladin Lite)
Carregado sob demanda (botão "Carregar mapa interativo") a partir de `CONFIG.ALADIN_URL`. Mostra o retângulo do FOV,
o centro da busca, os pontos A/B e, opcionalmente, catálogos Gaia DR3 e AllWISE (via VizieR/CDS).
Depende de internet e de serviços externos do CDS. Depois de testar, troque a URL `latest` por uma versão fixa.

Gaia/AllWISE (testado em 2026-11-15): `A.catalogFromVizieR` do Aladin 3.8.1 consulta `vizier.unistra.fr`,
domínio que não resolve no DNS, então as camadas vinham vazias. Agora o frontend monta a consulta VOTable e usa o
primeiro espelho que responder em `CONFIG.VIZIER_HOSTS` (CDS, depois CfA/Harvard, que tem CORS). No teste, para
RA 269.446358, Dec 4.767053 e FOV 3′: Gaia DR3 = 300 fontes (limite `-out.max`), AllWISE = 91, via CfA.
Nesse dia o CDS (alasky, alaskybis, vizier.cds) respondia "Page unavailable": os fundos DSS2/2MASS/AllWISE passaram
a usar os espelhos do IRSA, mas os mapas SPHEREx (só no CDS) ficaram indisponíveis enquanto o CDS estiver fora.

### Clique no mapa
O mapa abre com o céu todo (projeção AIT, `fov: 360`). Clicar num ponto (sem arrastar) preenche RA/Dec no formulário,
mantém o FOV atual e executa a busca; depois o mapa é recentrado e aproximado na região. "Ver o céu todo" volta ao zoom máximo.
Com o céu inteiro na tela, a precisão do clique é baixa: aproxime o zoom e clique de novo.

### Mapa de fundo = dados do SPHEREx
O fundo padrão do mapa são os mapas HiPS da missão publicados pelo CDS (um por detector, versão QR2):
`https://alasky.cds.unistra.fr/SPHEREx/D1` ... `D6` (`CONFIG.SPHEREX_HIPS_BASE`). Confirmados no registro VO: D1 e D3; D2, D4, D5 e D6
seguem o mesmo padrão de nome e precisam ser testados. Em novembro de 2026 saiu o Data Release 1 (DR1) no IRSA: quando houver HiPS do DR1,
troque a constante. DSS2, 2MASS e AllWISE continuam disponíveis só como comparação.
