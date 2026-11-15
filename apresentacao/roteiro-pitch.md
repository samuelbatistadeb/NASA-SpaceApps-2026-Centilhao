# Roteiro do pitch — Centilhão (SPHEREx Explorer)

Deck: https://claude.ai/artifact/DyDHftpLqn1KEri4nH4onB (11 slides principais + 3 de apêndice, que só se mostram se a banca perguntar).

---

## 1. Entenda o assunto (leia isto primeiro)

Se você entender estas 7 ideias, consegue responder qualquer pergunta com as próprias palavras.

| Ideia | Em palavras simples | Analogia |
|---|---|---|
| **SPHEREx** | Telescópio espacial da NASA que fotografa o céu inteiro várias vezes, em luz infravermelha. | Uma câmera que vê calor, não cor. |
| **Infravermelho** | Luz que nossos olhos não enxergam. Atravessa poeira e mostra o que a luz comum esconde. | Visão térmica de um filme. |
| **Observação / exposição** | Uma foto tirada em um momento. Cada uma dura cerca de 2 minutos (~114 s, segundo nossa documentação). | Um clique da câmera. |
| **Detector (D1 a D6)** | O SPHEREx tem 6 sensores. Cada um enxerga uma faixa diferente de luz infravermelha. | 6 filtros de cor numa câmera. |
| **Época** | A data em que a foto foi feita. É o que usamos para mostrar o céu *mudando*. | Cada foto de um álbum de família. |
| **Movimento próprio** | Algumas estrelas se movem devagar no céu, ano após ano. A Estrela de Barnard é uma das que mais andam (≈10,4″ por ano, do nosso catálogo). | Um carro visto de muito longe: parece parado, mas anda. |
| **Espectro** | O brilho de um ponto em cada "cor" de luz. Serve como impressão digital: indica do que o objeto é feito. | Prisma separando a luz em cores. |

**Importante (distinção que o desafio exige):** cores diferentes (detectores) **não** são datas diferentes. Nossa linha do tempo usa **datas**. As cores aparecem à parte, no espectro.

**O que a nossa ferramenta faz, em uma frase:**
> Você escolhe um ponto do céu; ela busca as fotos reais da NASA desse lugar, ordena por data e deixa você assistir como um filme, comparar duas datas e ver o que mudou.

**O que NÃO é (diga com clareza se perguntarem):** não é uma descoberta nova de astronomia. Mostra fenômenos conhecidos (como o movimento da Estrela de Barnard) de forma que qualquer pessoa consiga ver.

---

## 2. Roteiro de 3 minutos (~400 palavras, ritmo calmo)

Tempo por slide entre parênteses. Fale devagar: o slide tem poucas palavras de propósito, você conta a história.

**Slide 1 — Capa (0:00–0:10)**
"Olá, somos a equipe Centilhão. Nosso projeto tem três verbos: apontar, assistir, descobrir. Ele permite que qualquer pessoa veja o céu mudar, sem ser cientista."

**Slide 2 — O telescópio (0:10–0:30)**
"A NASA tem um telescópio chamado SPHEREx. Ele fotografa o céu inteiro, várias vezes, em luz infravermelha, aquela que nossos olhos não veem. Os dados são públicos."

**Slide 3 — O problema (0:30–0:45)**
"Só que, na prática, só especialistas conseguem usar. É preciso programar e entender formatos difíceis. Então quase ninguém vê como o céu muda de uma data para outra."

**Slide 4 — A solução (0:45–1:05)**
"Nossa solução é o SPHEREx Explorer, um site. Você aponta para uma estrela, assiste às fotos reais como um filme e descobre o que mudou entre duas datas."

**Slide 5 — Demo em vídeo (1:05–1:35)**
Deixe o vídeo rodar (28 s). Narre por cima, sem ler o slide: "Escolho a Estrela de Barnard. Cada foto real vira um quadro do filme. Subtraio duas datas. E aparece o que se moveu."

**Slide 6 — Uma estrela que anda (1:35–1:50)**
"Essa mancha clara com uma escura ao lado mostra que a estrela se mexeu entre as duas datas. É a Estrela de Barnard, uma das que mais se movem no céu."

**Slide 7 — 76 anos (1:50–2:05)**
"Também colocamos fotos antigas, de 1950, e de outros satélites na mesma região. Dá para ver uma estrela andando por 76 anos."

**Slide 8 — Luz de cada ponto (2:05–2:15)** *(opcional: se estiver estourando o tempo, pule)*
"E clicando num ponto vemos a impressão digital da luz dele. Quando o dado não é confiável, o site avisa."

**Slide 9 — Confiança (2:15–2:35)**
"Tudo vem do arquivo oficial da NASA, o código tem 199 testes automáticos e a ferramenta é honesta sobre os próprios limites."

**Slide 10 — Open source (2:35–2:50)**
"E o projeto é aberto: qualquer pessoa pode usar, copiar e melhorar o código."

**Slide 11 — Fecho (2:50–3:00)**
"Para estudantes, professores e curiosos do céu. Apontar, assistir, descobrir. Obrigado!"

> Se tiver 2 pessoas falando: uma conduz slides 1–5, outra 6–11. Ensaiem a troca.

---

## 3. Perguntas prováveis e respostas

### De uma pessoa comum / jurado leigo

**O que é infravermelho?**
É uma luz que existe, mas nossos olhos não veem. A gente sente como calor. Ela atravessa poeira, então mostra coisas que a luz normal esconde.

**Por que isso importa para mim?**
Porque o céu é de todos. Hoje esses dados são grátis, mas inacessíveis. Nossa ferramenta deixa um estudante ou professor explorar sem saber programar.

**Isso é uma foto de verdade?**
Sim. São imagens reais do arquivo público da NASA. Na ferramenta, só existe modo com dados fictícios como opção explícita e identificada para testar a interface, nunca apresentado como real.

**O que significa a mancha clara e a escura?**
Duas fotos de datas diferentes, uma subtraída da outra. Onde a estrela está agora fica clara; onde estava antes fica escura. Ou seja, ela se moveu.

**Para quem serve?**
Estudantes, professores, curiosos e também pesquisadores que querem uma primeira olhada rápida.

**Como vocês ganhariam dinheiro?**
Não é o objetivo. É open source e educacional. (Ponto forte: sustentabilidade pelo uso aberto e comunidade.)

### Da banca técnica / científica

**De onde vêm os dados?**
Do SPHEREx Archive, no IRSA/IPAC (Caltech/NASA). Usamos o serviço SIA v2 para buscar as exposições que cobrem o ponto e o serviço de recorte para baixar só o pedaço da imagem.

**Cores (bandas) são o mesmo que tempo?**
Não, e tomamos cuidado com isso. Cada imagem do SPHEREx já traz várias faixas de cor no mesmo quadro. A linha do tempo usa a **data** (época) da observação. As cores aparecem à parte, no espectro.

**Como vocês garantem que a estrela está no mesmo lugar em todas as imagens?**
Usamos o movimento próprio do catálogo para calcular onde a estrela estava em cada data e recortamos ali. Com isso, a Barnard fica a no máximo 0,73 pixel do centro (sem correção chegava a 2,18).

**Por que o espectro da Barnard não aparece?**
Porque ela é tão brilhante que satura o detector; todos os pontos saem sinalizados como não confiáveis. Preferimos mostrar o aviso do que um gráfico falso. Esse é um comportamento intencional.

**O que é a diferença de datas, exatamente?**
Subtraímos duas imagens do mesmo detector, depois de remover o brilho de fundo, e excluímos pixels marcados como contaminados.

**O WISE 0855 aparece?**
É muito fraco: nas exposições individuais ele não é detectado. Está no pacote como exemplo, mas dizemos isso abertamente.

**Que limitações existem?**
(1) O comprimento de onda de cada pixel é aproximado. (2) A fotometria não tem correção de PSF. (3) Ainda precisa de revisão científica final. (4) O serviço do IRSA ficou instável durante o desenvolvimento, então temos cache e exemplos reais salvos.

**Por que comparar com 1950/WISE/DSS?**
Para dar contexto de tempo: são outras missões, com outra sensibilidade, usadas só como comparação visual, não para medir.

**É diferente de ferramentas que já existem (ex.: Aladin, IRSA Viewer)?**
Elas são poderosas, mas exigem conhecimento. Nosso foco é uma só tarefa: ver o tempo passar numa região, com poucos cliques e vocabulário simples (inclui um glossário de 53 termos).

**Qual a licença do código?**
[Definam e preencham antes do pitch — hoje o repositório não tem arquivo LICENSE.]

**O que viria depois?**
Mais alvos, revisão científica completa, mais comparações entre épocas, uma versão hospedada publicamente.

---

## 4. Dicas para apresentar

1. **Ensaie em voz alta 5 vezes com cronômetro.** 3 minutos passam rápido; o que você corta, corta de verdade.
2. **Não leia os slides.** Eles têm 3 palavras porque você é quem conta. Olhe para a banca.
3. **Abra com a pergunta:** "Quando foi a última vez que você viu o céu *mudar*?" (opcional, mas prende).
4. **Demo de 28 s é seu momento forte.** Narre por cima do vídeo e não fique em silêncio.
5. **Tenha um plano B para o vídeo:** o arquivo está em `apresentacao/centilhao-demo-barnard.mp4`; abra no celular ou no computador se a internet falhar.
6. **Leve os números de cabeça:** 354 fotos reais da Barnard, 6 sensores, 5 alvos, 76 anos, 199 testes.
7. **Diga "não sabemos" quando for o caso.** Banca valoriza honestidade científica mais do que resposta inventada.
8. **Vocabulário:** troque "detector" por "sensor", "época" por "data", "espectro" por "impressão digital da luz" com leigos.
9. **Combinem quem responde o quê:** técnica (backend), ciência (validação), interface (demo).

---

## 5. Autoavaliação crítica (o que melhorar)

**O que está forte:**
- História clara em três verbos (apontar, assistir, descobrir).
- Dados 100% reais e honestos sobre limites, algo raro em pitch.
- Demo visual curta e imagens do próprio projeto.
- Open source e acessível a não-especialistas.

**Fragilidades que a banca pode explorar (ordenadas por risco):**
1. **Só um alvo está plenamente demonstrado (Barnard).** Os outros quatro têm pacote, mas o espectro da Barnard é inválido e o WISE 0855 não é detectado em exposição única. *Melhoria: ter um segundo exemplo pronto para o Q&A.*
2. **"Descubra" promete mais do que entrega.** Mostramos fenômenos já conhecidos, não novas descobertas. *Melhoria: no discurso, dizer "tornar visível o conhecido" em vez de "descobrir".*
3. **Demo gravada, não ao vivo.** O IRSA esteve instável, então a ferramenta usa dados salvos. *Melhoria: dizer claramente que o vídeo usa dados reais salvos; se houver rede, preparar um ao-vivo curto.*
4. **Vídeo com legendas em inglês** e site em português. *Melhoria: regravar legendas em português ou avisar.*
5. **Sem teste com usuários não técnicos.** Não temos evidência de que um leigo entende o site sozinho. *Melhoria: pedir a 3 pessoas de fora para usar por 2 min e anotar dúvidas.*
6. **Pendências de revisão científica** (comprimento de onda aproximado, sem correção de PSF, fatos do glossário). *Melhoria: ter a Integrante 2 conferindo antes do pitch.*
7. **Licença indefinida e nomes da equipe em branco** no deck. *Melhoria: preencher antes de apresentar.*
8. **O nome "Centilhão" não é explicado.** Se a banca perguntar o significado, vocês precisam de uma resposta pronta.
9. **Sem métrica de impacto** (ex.: quantos usuários, feedback). *Melhoria: mesmo que pequeno, um depoimento ou teste vale muito.*
10. **Visual do deck ainda não conferido** em tela cheia/projetor: texto pode quebrar ou imagem cortar. *Melhoria: abrir em modo apresentação e passar slide a slide.*

**Nota geral honesta:** história e honestidade científica fortes (8/10); linguagem agora acessível, mas falta prova de que leigos entendem (6/10); demonstração impressionante, porém gravada e com um único alvo completo (7/10).
