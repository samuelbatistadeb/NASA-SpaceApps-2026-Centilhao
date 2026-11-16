# Continuidade — SPHEREx Explorer (NASA Space Apps 2026)

> Estado em **15/11/2026**, branch `feat/sia-integration`, commit `bc59bce`, sem push. Escrito para continuar o trabalho em outro chat.
> Antes de qualquer tarefa, leia nesta ordem: `AGENTS.md`, `docs/progress.md`, `docs/decisions.md` (DECISÕES 007–017) e `docs/architecture/api-contract.md` §13.

## 1. O que estamos fazendo

O desafio é **criar uma ferramenta web pública que exiba imagens do céu da missão SPHEREx e permita que qualquer pessoa veja rapidamente como elas mudam ao longo do tempo.**

O fluxo é este: o usuário informa RA/Dec ou escolhe um alvo de exemplo. O backend busca no IRSA as exposições SPHEREx que cobrem aquele ponto e recorta cada uma num **quadro comum** (norte para cima, centrado no alvo). O site então mostra:

- a linha do tempo das exposições;
- um comparador entre duas datas;
- a média de várias épocas (melhor sinal/ruído) e a diferença entre épocas (o que mudou);
- o espectro de um ponto;
- a contaminação de cada quadro;
- o mapa do céu.

Equipe de 3 pessoas:

| Integrante | Área |
|---|---|
| 1 | Técnica: backend e dados |
| 2 | Científica: validação |
| 3 | Interface |

O usuário escreve em pt-BR, usa Windows e trabalha com agentes em paralelo.

## 2. Ambiente e como rodar

- **Repositório:** `C:\Users\Willi\OneDrive\Área de Trabalho\nasa\NASA-SpaceApps-2026-Centilhao`
  - remote `origin` = fork `Willian-s1`;
  - remote `upstream` = `samuelbatistadeb`.
- **Python:** 3.12.10, em `.venv` (dependências da DECISÃO 005, sem jupyter). Não há scipy nem reproject.
- **Git:** `user.name` é "Willi", configurado só neste repositório.
- **Backend:**

  ```bash
  .venv/Scripts/python.exe -m uvicorn app.main:app --app-dir src/backend --port 8000
  ```

- **Frontend:**

  ```bash
  python -m http.server 5173 --directory src/frontend
  ```

  - O CORS só aceita as portas 5173, 3000 e 8000.
  - Os dois servidores também estão em `.claude/launch.json`.
- **Testes:** `.venv/Scripts/python.exe -m pytest tests/backend -q` → **198 passed, 2 skipped**. Os 2 pulados precisam do FITS completo em `data/raw/spherex/`, ausente neste clone.
- **JavaScript:** `node --check src/frontend/js/app.js`.

## 3. Como os dados funcionam (fatos verificados com dados reais)

1. **Descoberta (SIA v2):**
   - Endereço: `https://irsa.ipac.caltech.edu/SIA` (o `/SIA2` dá 404). Parâmetros: `POS=CIRCLE ra dec r`, coleções `spherex_dr1`, `spherex_qr3` e `_deep`. A resposta é uma VOTable.
   - Os FIELDs vêm com `ID="col_N"`, então é preciso ler a coluna pelo `name`.
   - Cada linha é **uma exposição (~114 s) de um detector** (D1–D6): Level 2, 2040×2040 px, 6,15″/px (~3,5°), em MJy/sr.
2. **Datas:**
   - A época vem de `t_min`, que está em MJD. Nunca use `obs_release_date`.
   - O detector sai do sufixo `/D<n>` de `obs_publisher_did`.
3. **Comprimento de onda:** varia **dentro** de cada imagem (filtro linear variável), então não existe "uma banda por imagem". Cada detector cobre uma faixa, por exemplo D3 = 1,63–2,43 µm.
4. **Recorte (IBE):**
   - Formato: `<access_url>?center=ra,decd&size=graus`, pedido com 1,5× o FOV.
   - A ordem dos HDUs é PRIMARY, IMAGE, FLAGS, VARIANCE, ZODI, EPSF (3,9 MB) e WCS-WAVE.
   - Lemos só até VARIANCE. Um recorte fica em ~1,2 s e ~32 KB por imagem.
   - Respostas especiais: 422 ou 500 = o produto não cobre o ponto; 503 = servidor ocupado (há retry).
5. **FLAGS:** 23 bits, documentados no cabeçalho e na Tabela 16 do Explanatory Supplement v2.0. O bit SOURCE é só informativo, não indica defeito.
6. **λ por pixel:**
   - Vem da tabela WCS-WAVE, que fica no fim do arquivo e é lida por HTTP Range.
   - A tabela é a mesma para todas as exposições de um par (detector, diretório `l2b-…`).
   - O cálculo segue o tutorial oficial: `WCS(hdr, fobj, key='W')` com `sip=None`. Esse λ é **aproximado** (§4.3.1 do suplemento).
7. **Estabilidade dos serviços externos:** o SIA esteve instável o dia 15/11 inteiro (502 e timeouts), enquanto o IBE funcionou. O HiPS SPHEREx do CDS também deu 404.

## 4. O que está pronto

### Backend (`src/backend/app`)

| Rota | O que faz |
|---|---|
| `GET /api/observations` | `ra_deg`, `dec_deg`, `fov_arcmin` + movimento próprio opcional (`pm_ra_cosdec_masyr`, `pm_dec_masyr`, `ref_epoch_jyear`, os três juntos). Recorta cada época na posição propagada. Filtra pelo polígono `s_region`. Informa `coverage_fraction` e `data_source` (`live`, `cache` ou `stale_cache`). |
| `GET /api/images/{id}` | PNG RGBA do quadro comum. Área fora do detector transparente; pixel inválido em #B03060. |
| `GET /api/coverage` | Quadros completos e parciais por FOV, de 1 a 30′, com FOV recomendado. |
| `GET /api/composite?op=mean\|diff&a=…&b=…` | Média ou diferença do mesmo detector, com pixels contaminados excluídos. |
| `GET /api/spectrum` | Um ponto por exposição: λ pela WCS-WAVE, abertura menos anel de fundo, erro pela VARIANCE e flags. |
| `GET /api/observations/{id}/quality` | Flags no alvo e fração de cada flag no quadro. |
| `GET /api/targets` | 5 alvos de `docs/science/target-catalog.md`, com posição e movimento próprio. |
| `GET /api/releases` | Coleções em uso. Configurado por `SPHEREX_COLLECTIONS` (lista ou `auto`, com fallback). |

Outros pontos do backend:

- **Cache em disco:** fica em `data/cache/spherex`. Imagens e quadros não expiram (a versão atual do cache é `frame-v3`). Quando o IRSA cai, a busca usa o cache vencido e informa isso.
- **Limite de concorrência:** no máximo 3 pedidos simultâneos ao IRSA. Pedidos repetidos da mesma imagem são deduplicados.
- **Módulos principais:**
  - `services/`: `irsa_client.py`, `observation_service.py`, `cutout_service.py`, `common_frame.py`, `sky_coverage.py`, `astrometry.py`, `spectral.py`, `spherex_flags.py`, `cache.py`;
  - `api/`: `observations.py`, `analysis.py`, `targets.py`, `releases.py`.

### Frontend (`src/frontend`)

- **Arquivos:** `index.html`, `termos.html`, `js/app.js`, `js/theme.js`, `js/glossary.js`, `js/glossary-data.js`, `css/styles.css`, `css/theme.css`, `css/glossary.css`, `assets/` (ícone, 3 imagens NASA/JPL-Caltech com `CREDITS.md`) e `demo/`.
- **Busca:** coordenadas ou alvos de exemplo, com "Seguir o movimento do alvo".
- **Seletor de FOV:** mostra pixels, comparação com a Lua, custo por imagem e quadros completos.
- **Detectores:** botões "Todos" + D1–D6. Clique simples isola um detector; Ctrl/⌘/Shift soma outro. Cada botão mostra a contagem e a faixa real.
- **Visualização no tempo:**
  - linha do tempo, galeria em fila, comparador de 2 datas (cortina ou piscar) e atalhos ←/→ e espaço;
  - "Combinar épocas" (média ou diferença).
- **Espectro de um ponto:** inclui o botão "Espectro do alvo"; pontos contaminados aparecem vazados.
- **Qualidade:** a contaminação no alvo aparece nos detalhes de cada observação.
- **Mapa do céu (Aladin Lite):**
  - abre em ~1,5 s;
  - fundo em cadeia SPHEREx → AllWISE → 2MASS → DSS2, com aviso de qual está em uso;
  - camadas Gaia DR3 e AllWISE (com espelho no CfA), clique para pesquisar e botão "Centralizar no alvo".
- **Resiliência:** quando a busca falha, aparece um painel com:
  - exemplos reais salvos;
  - nova tentativa automática;
  - o mapa;
  - dados fictícios.

  Se o servidor estiver inacessível, os exemplos são oferecidos logo ao abrir a página. Também há o link `?demo=<id>`.
- **Glossário:** 53 termos com ícone "?", acessível por mouse, teclado e toque.
- **Tema:** céu estrelado e menu com "feixe infravermelho" no ícone original do SPHEREx (sem logotipos da NASA nem da missão).

### Dados de demonstração (`src/frontend/demo`)

- Gerados por `data/scripts/17_export_demo.py`, com o SIA ao vivo ou com `--sia-file` apontando para uma resposta salva.
- **wise0855:** 50 observações (lista parcial, da resposta salva em `data/sia_snapshots/`), espectro com 42 pontos e 8 combinações.
- **barnard:** 354 observações (SIA ao vivo) e 11 combinações. **A diferença D1 mostra o movimento próprio**: par claro ao norte e escuro ao sul. O espectro é inválido, porque a estrela satura o detector (todos os pontos sinalizados).

## 5. Resultados científicos verificados

- **Propagação do movimento próprio:** confere com o catálogo (≤ 0,015″) e com o astropy (< 0,001″). Com a correção, a Barnard fica a ≤ 0,73 px do centro; sem ela, chega a 2,18 px.
- **λ calculado pela cauda do arquivo:** idêntico ao método oficial em 3 recortes reais (D3: 2,36218 µm).
- **FLAGS no espectro do WISE 0855:** os únicos valores anômalos estavam sinalizados. O alvo não é detectado em exposições únicas.
- **Barnard:** a diferença com céu fixo mostra o deslocamento de ~1,4 px em um ano.

## 6. Pendências (por prioridade)

1. **Conferir o visual no navegador.** As capturas de tela falharam porque a janela estava minimizada. Também não foi testada a abertura automática do mapa ao rolar a página.
2. **Revisão científica (Integrante 2):**
   - λ aproximado (os arquivos CWAVE/CBAND `spectral_wcs_N` não foram localizados);
   - fotometria por brilho superficial na abertura, sem correção de PSF;
   - fatos do glossário que vieram do agente (lista na DECISÃO 017).
3. **Alvo de brilho intermediário (não saturado)** para demonstrar um espectro com sinal.
4. **Regerar os pacotes de demonstração antes da apresentação**, com o SIA ao vivo: a lista do WISE está parcial e a cobertura da Barnard não foi exportada.
5. **Validar com o IRSA estável:**
   - a descoberta de coleções (`SPHEREX_COLLECTIONS=auto`);
   - `/api/coverage` com 30′ (deu timeout no SIA instável);
   - a ausência de produtos QR3 nas respostas.
6. **Quando a equipe aprovar:** abrir PR da `feat/sia-integration`.
7. **Arquivos fora do controle de versão:**
   - `src/frontend/.gitignore` não é rastreado (apagado de propósito num commit anterior);
   - `.claude/worktrees/` guarda os worktrees dos agentes e pode ser limpo depois dos merges.

## 7. Como trabalhamos

- **Regras do `AGENTS.md`:**
  - não inventar dados;
  - testar antes de afirmar;
  - registrar decisões em `docs/decisions.md` e o progresso em `docs/progress.md`;
  - commit a cada marco, mensagem em pt-BR com `Co-Authored-By`;
  - **sem push** sem autorização.
- **Agentes em paralelo:** cada um trabalha num git worktree próprio e com escopo de arquivos definido (frontend, glossário, tema, pesquisa). Revisamos o diff antes do merge e resolvemos os conflitos no `index.html`.
- **Dados reais sem SIA:** quando o SIA cai, a validação ao vivo usa respostas reais salvas do SIA mais o IBE real. Isso deve estar sempre declarado nos relatórios.
