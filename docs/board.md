# Quadro de tarefas — SPHEREx Explorer

Este documento substitui provisoriamente o quadro hospedado no GitHub Issues/Projects, previsto em `docs/team/workflow.md` §2, enquanto o repositório compartilhado não é configurado (não há remote no repositório local e commits/push não estão autorizados nesta fase).

**Marco atual:** Primeiro marco técnico — *prova de viabilidade com dados reais do SPHEREx*.

---

## 1. Estados utilizados

| Estado | Significado |
|---|---|
| Pendente | Ainda não iniciada |
| Em andamento | Em execução por um agente ou humano |
| Bloqueada | Dependência externa não satisfeita |
| Em revisão | Entrega produced, aguardando validação |
| Concluída | Critérios de conclusão atendidos **com evidência anexada** |

---

## 2. Quadro

| ID | Objetivo | Agente | Responsável humano | Arquivos exclusivos | Dependências | Critério de conclusão | Estado |
|---|---|---|---|---|---|---|---|
| **T-A** | Investigar produtos SPHEREx, serviços IRSA, SIA2, cutout, épocas, metadados, 5 objetos de teste, limitações | `researcher` | Integrante 2 — Liderança científica | `docs/research.md`, `docs/science/data-sources.md`, `docs/science/target-catalog.md` | — | Endpoint verificado ou marcado como não verificado; 5 objetos com coordenadas, época e movimento próprio ou "não verificado"; hipótese temporal testada | Em andamento |
| **T-B** | Obter FITS reais e caracterizá-los: HDUs, WCS, metadados, bandas, detectores, qualidade, recorte, compatibilidade | `data-analyst` | Integrante 1 + Integrante 2 | `data/**`, `docs/science/data-analysis-report.md` | T-A (parcial — pode descobrir o caminho por conta própria) | Relatório com estrutura real do FITS, metadados extraídos e resposta com evidência à pergunta temporal | Em andamento |
| **T-C1** | Plano de implementação + esqueleto FastAPI + cliente IRSA configurável + schemas + testes + `requirements.txt` pinado | `developer` | Integrante 1 — Liderança técnica | `src/backend/**`, `tests/backend/**`, `requirements.txt`, `docs/architecture/implementation-plan.md` | — | `pytest` passando com saída real anexada; nenhum endpoint inventado | Em andamento |
| **T-C2** | Cliente IRSA real + recorte real + `/api/observations` funcionando contra o SPHEREx | `developer` | Integrante 1 | `src/backend/**`, `tests/backend/**` | T-A, T-B | Consulta real retornando observações reais ordenadas cronologicamente + 1 recorte processado | Pendente |
| **T-D** | Revisão independente de T-A, T-B e T-C2 | `reviewer` | Integrante 1 / 2 / 3 | nenhum — somente leitura | T-A, T-B, T-C2 | Laudo com problemas classificados em CRITICAL / HIGH / MEDIUM / LOW | Pendente |
| **T-E** | Manter `docs/progress.md`, `docs/decisions.md`, `docs/continuity.md` e este quadro atualizados | `coordinator` | Integrante 1 | `docs/progress.md`, `docs/decisions.md`, `docs/continuity.md`, `docs/board.md` | contínuo | Documentação reflete o estado real do projeto | Em andamento |
| **T-F** | Normalizar o esquema de permissões dos agentes para o formato V2 | `coordinator` | Integrante 1 | `.opencode/agents/*.md` | — | Todos os 5 agentes usando `permissions:` (lista action/resource/effect) | Pendente — aguarda aprovação |
| **T-G** | Frontend: formulário RA/Dec/FOV, visualizador temporal, controles de reprodução, metadados | a definir com Integrante 3 | Integrante 3 — Liderança de interface | `src/frontend/**` | T-C2 (API real) | Interface integrada à API com dados reais | Pendente |

---

## 3. Critérios de conclusão do marco (prova de viabilidade)

| ID | Critério | Evidência exigida |
|---|---|---|
| M1 | Endpoint IRSA verificado | URL real + resposta do serviço + data da consulta |
| M2 | Consulta espacial por RA/Dec executada | Comando/URL + saída real com produto retornado |
| M3 | Épocas de observação identificadas | Palavra-chave FITS real com valores |
| M4 | Recorte de imagem obtido | FITS real + registro das HDUs + WCS |
| M5 | Recorte processado | PNG gerado via Astropy, dimensões verificadas |
| M6 | Existência de sequência temporal verificada | ≥2 épocas distintas da mesma região com banda fixada, **ou** resultado negativo documentado com o registro da consulta |
| M7 | Testes automatizados | Saída real de `pytest` |
| M8 | Revisão independente | Laudo do `reviewer` |
| M9 | Rastreabilidade | Cada observação referencia o identificador original do produto |

Regra: nenhum critério é considerado cumprido sem evidência real anexada. Se M6 for negativo, isso é **resultado científico legítimo** e será documentado como tal — nunca substituído por dados simulados.

---

## 4. Registro de inconsistências da auditoria

| ID | Sev. | Inconsistência | Encaminhamento |
|---|---|---|---|
| I-01 | ALTA | `researcher.md` usa esquema de permissões V1 legado (`permission:` / `bash`), os outros 4 agentes usam V2 (`permissions:`). O esquema legado é deprecado na V2 do OpenCode e pode não aplicar o *scoping* de edição do researcher. | T-F — aguarda aprovação |
| I-02 | ALTA | `docs/continuity.md` desatualizado: §9 omite `docs/architecture`, `docs/science`, `docs/team`, `docs/interface`, `requirements.txt` e os diretórios vazios; §10 lista 2 comandos mas existem 3; §13 aponta como "próxima atividade" um trabalho já concluído. | T-E — corrigido nesta revisão |
| I-03 | ALTA | `docs/progress.md` desatualizado: mantém como pendentes itens já concluídos (documentar desafio, registrar fluxo, documentar fontes, definir arquitetura, estabelecer contrato). | T-E — corrigido nesta revisão |
| I-04 | MÉDIA | Estrutura de dados divergente: `docs/architecture/system.md` §9 propõe `data/{samples,cache,raw,temporary}`; o repositório tem `data/{raw,processed,temporary}`. §8 propõe `frontend/src/css/`; o repositório tem `frontend/assets/css/`. | T-C1 deve reconciliar em `docs/architecture/implementation-plan.md`; consolidação final fica com o coordinator |
| I-05 | MÉDIA | `.gitignore` cobre `data/raw/` e `data/temporary/`, mas não `data/processed/` nem cache, embora `system.md` §9 exija proteger cache e raw. | T-E — corrigir `.gitignore` |
| I-06 | MÉDIA | DECISÃO 003 registra "Git e GitHub" e `workflow.md` §2 exige GitHub Issues/Projects, mas não existe remote e commits não estão autorizados. | Resolvido por este quadro local (DECISÃO 006) |
| I-07 | BAIXA | `requirements.txt` na raiz versus `backend/requirements.txt` proposto em `system.md` §7. | Consolidar na DECISÃO 007 |
| I-08 | BAIXA | `requirements.txt` inclui `jupyterlab`/`ipykernel`, desnecessários ao MVP. | T-C1 remove e registra |
| I-09 | BAIXA | `api-contract.md` §11 autoriza respostas simuladas para o frontend. Rotuladas corretamente, mas é porta de entrada para o risco proibido pela missão. | Rótulo "dados fictícios" obrigatório em qualquer mock |

---

## 5. Riscos científicos e técnicos

| ID | Risco | Status |
|---|---|---|
| R-01 | **Crítico.** A premissa de "sequência temporal" exige re-observações da mesma região em épocas distintas. Se o SPHEREx oferecer apenas varredura espectral ampla, o visualizador temporal não se sustenta na maior parte do céu. | Em verificação (T-A, T-B) |
| R-02 | Objetos com movimento próprio (Barnard, WISE 0855): deslocamento entre épocas pode ser inferior à PSF, ou o alvo pode sair do campo de visão sem correção de época. | Em verificação (T-A) |
| R-03 | Epsilon Indi B: separação de componentes próxima de poucos arcsegundos pode ser indistinguível na PSF do SPHEREx. | Em verificação (T-A) |
| R-04 | RW Aurigae e R Draconis: variação real pode se confundir com mudança de detector, calibração, unidade ou pipeline. `docs/science/validation.md` §8 exige compatibilidade fotométrica antes de comparar. | Em verificação (T-B) |
| R-05 | Escala de fluxo pode ser relativa, não absoluta — nenhum valor de brilho deve ser apresentado como medida calibrada sem verificação. | Em verificação (T-B) |
| R-06 | Máscaras, saturação, PSF variável e ruído podem produzir sequência visualmente convincente e cientificamente inválida. | Em verificação (T-B) |
| R-07 | Época de referência das coordenadas: uma única coordenada fixa é inadequada para objetos com movimento próprio entre observações distantes. | Em verificação (T-A) |
| R-08 | Distinguir data de observação de data de publicação/processamento do produto. | Em verificação (T-B) |
| R-09 | Proveniência: cada produto exibido deve manter referência ao identificador original (RNF-007). | Em implementação (T-C2) |
| R-10 | Técnico: compatibilidade de `astroquery`/`pyvo` com os serviços SIA2 do IRSA ainda não testada. | Em verificação (T-B) |

---

## 6. Registro de evidências verificadas

### 6.1 Sonda de serviços do IRSA (14/11/2026) — T-B

Evidência bruta: `data/scripts/00_probe_services.py` → `data/processed/service_probe.json`.

| Endpoint sondado | HTTP | Observação |
|---|---|---|
| `https://irsa.ipac.caltech.edu/TAP/` | **200** (text/xml) | TAP do IRSA responde |
| `https://irsa.ipac.caltech.edu/TAP/sync` | **200** (text/xml) | consulta síncrona disponível |
| `https://irsa.ipac.caltech.edu/TAP/async` | **200** (text/xml) | consulta assíncrona disponível (retorna URL de job) |
| `https://irsa.ipac.caltech.edu/SIA?` | **200** (text/xml) | serviço de imagem responde |
| `https://irsa.ipac.caltech.edu/SIA2?` | 404 | caminho SIA2 inexistente neste host |
| `https://irsa.ipac.caltech.edu/Siap?` | 404 | inexistente |
| `https://irsa.ipac.caltech.edu/cgi-bin/nph-cutout?` | 404 | caminho legado de cutout inexistente |
| `https://irsa.ipac.caltech.edu/cutout?` | 404 | caminho de cutout inexistente |
| `https://irsa.ipac.caltech.edu/Missions/spherex.html` | 200 | página da missão ("SPHEREx: An All-Sky Spectral Survey") |

### 6.2 Correções e complementações do Coordinator (14/11/2026)

Duas leituras da §6.1 estavam **erradas** e foram corrigidas pelo Researcher (T-A) e confirmadas pela verificação independente do Coordinator (§6.3):

1. **`/SIA` É o serviço SIA v2**, não SIA1. O caminho `/SIA2` nunca existiu no IRSA — 404 é o comportamento esperado, não uma lacuna. Evidência: o auto-descritivo de `/SIA?MAXREC=0` lista parâmetros **exclusivos da v2** (`BAND`, `CLOSEST`, `DPTYPE`, `POS`, `TIME`, `RESPONSEFORMAT`, `UPLOAD`) e **nenhum** exclusivo da v1.
2. **O serviço de recorte existe** e não é um CGI. O IBE (Image Back End) gera o recorte **acrescentando uma query string ao `access_url` do próprio FITS**:
   `<access_url>?center=<ra>,<dec>d&size=<graus>` → HTTP 200, `application/fits`.

Consequência: a estratégia de consulta passa a ser **SIA2 (`/SIA`) como consulta principal + TAP como complemento** (mais fresco e com URL de recorte já montada), e **nada** depende de um endpoint de cutout autônomo.

### 6.3 Verificação independente do Coordinator (14/11/2026) — evidência primária

Scripts: `C:\Users\Samuel\AppData\Local\Temp\opencode\verify_sia2.py` e `diagnose_cutout_overlap.py` (fora do repositório, por não pertencerem a nenhuma faixa de agente).

| Afirmação | Verificação | Resultado |
|---|---|---|
| `/SIA` serve SIA v2 | `GET /SIA?MAXREC=0` | params v2-only: `BAND, CLOSEST, DPTYPE, POS, TIME, RESPONSEFORMAT` · params v1-only: **nenhum** ✔ |
| SIA2 retorna produtos reais | `POS=circle 133.795129 -7.245147 0.05`, 4 coleções | **HTTP 200**, 51 colunas, **282 linhas** (WISE 0855) em 2,8 s |
| Existem épocas distintas | contagem de `t_min` distintos | WISE 0855 = **143 épocas** · Barnard = **192 épocas** ✔ coincide com T-A |
| `energy_bandpassname` = detector | distribuição | `SPHEREx-D1..D6` (46–50 por detector em WISE 0855) ✔ |
| SPHEREx não marca alvos móveis | `target_moving` | `0` em **todas** as linhas ✔ → propagação é responsabilidade da aplicação |
| Escala e campo | `s_pixel_scale` / `s_fov` | `6.150 "/px` · `3.485°` ✔ |
| Recorte IBE funciona | cutout `size=0.02` | **HTTP 200**, `application/fits`, **4.037.760 bytes**, 9,3 s, 7 HDUs (IMAGE 12×12 … EPSF 451×11, WCS-WAVE) ✔ |
| Época no cabeçalho | `DATE-OBS` / `MJD-OBS` / `MJD-END` | `2025-05-05T16:48:02.459` / `60800.700028461` / `60800.701360839` ✔ |
| Armadilha da keyword `DATE` | `DATE` vs `DATE-OBS` | `DATE = 2026-07-17T10:16:06.188` (criação do HDU) ≠ observação ✔ |
| FWHM real da PSF | `PSF_FWHM` | `7.448130062949859` ✔ (e `s_resolution = 3.075` = metade do pixel, **não** a resolução) |

### 6.4 Achados operacionais NOVOS (não documentados por T-A nem T-B) — Coordinator

1. **Sobreposição do recorte (422 "Arrays do not overlap").** O SIA2 devolve imagens cuja **pegada celeste INTERSECTA** o cone, não imagens que **CONTÊM** o centro. Medido em 378 linhas de Barnard: **301 (79,6%)** contêm o alvo (separação angular ≤ `s_fov`/2 = 1,742°) e **77 (20,4%)** não. Um recorte centrado no alvo em uma imagem que não o contém devolve **HTTP 422 "Arrays do not overlap."**; a mesma imagem recortada no **centro da imagem** (`s_ra`,`s_dec`) devolve **200**. Separações observadas: 0,0238° (mín) · 1,1848° (mediana) · 2,3806° (máx).
   - **Regra para o backend:** aplicar pré-filtro `angsep(alvo, s_ra/s_dec) ≤ s_fov/2` e, ainda assim, tratar 422/500 como "produto sem sobreposição" — **pulando-o**, sem quebrar a resposta. A regra é aproximativa: uma linha com separação 1,7526° (ligeiramente fora de `fov/2`) ainda recortou com 200, logo o filtro é pré-filtro, não garantia.
2. **`503 "Server busy, retry later."` é FREQUENTE.** Em 12 tentativas de recorte encadeadas, **4 devolveram 503 (~33%)**. → retry com backoff exponencial é **obrigatório**, não opcional.
3. **Concorrência deve ser limitada.** As falhas 503 se intensificam com requisições encadeadas. O tutorial oficial sugere 7–12 workers para 8 núcleos; o observado sugere começar **conservador** (3–5) e subir com medição.
4. **O volume do recorte é dominado pelo `EPSF`** (451×11 sobreamostrada) — 4 MB para 12×12 pixels de `IMAGE`. O backend deve extrair apenas `IMAGE` + `WCS-WAVE` e descartar o resto.

⚠️ M1–M9 **continuam abertos**: até aqui foi provado que o serviço responde e devolve produtos reais com épocas distintas. Falta o backend realmente consumindo isso (T-C2) e a revisão independente (T-D).

---

## 7. Decisões pendentes de validação humana

1. **T-F** — autorizar a normalização do esquema de permissões dos agentes para V2.
2. **Quadro de tarefas** — confirmar o uso de `docs/board.md` até a criação do repositório compartilhado.
3. **R-01** — se a verificação refutar a cobertura temporal repeatida ampla, o produto deve pivotar para honestidade científica (exibir épocas quando existirem, tratar a varredura espectral explicitamente como não-tempo) em vez de simulação. Requer validação da Integrante 2 (Liderança científica).
