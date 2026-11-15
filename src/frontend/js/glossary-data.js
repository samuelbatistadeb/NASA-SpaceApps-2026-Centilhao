/* SPHEREx Explorer — dados do glossário (ajuda contextual).
 *
 * Cada chave tem:
 *   titulo  — nome do termo, como aparece no balão;
 *   curto   — 1 ou 2 frases em linguagem simples (pt-BR);
 *   detalhe — opcional, um complemento curto;
 *   ancora  — id em termos.html para o link "Saiba mais".
 *
 * Fontes: docs/decisions.md (DECISÕES 007, 010, 015 e 016), docs/science/data-sources.md,
 * a página da missão no IRSA e o SPHEREx Explanatory Supplement v2.0
 * (https://irsa.ipac.caltech.edu/data/SPHEREx/docs/SPHEREx_Expsupp_QR.pdf).
 * Valores aproximados estão marcados como tal no próprio texto.
 */
(function () {
  "use strict";

  const detector = (n, faixa, extra) => ({
    titulo: `Detector ${n} (D${n})`,
    curto: `O detector D${n} registra luz infravermelha de aproximadamente ${faixa}. ${extra}`,
    detalhe: "Faixa aproximada, conforme a página da missão no IRSA. Dentro do detector, cada parte da imagem vê um comprimento de onda um pouco diferente.",
    ancora: "termo-detector",
  });

  window.SPHEREX_GLOSSARY = {
    spherex: {
      titulo: "SPHEREx",
      curto: "Telescópio espacial da NASA que mapeia o céu inteiro em luz infravermelha, separando essa luz em 102 “cores” (bandas).",
      detalhe: "Como ele passa várias vezes pela mesma região, dá para comparar imagens de datas diferentes.",
      ancora: "termo-spherex",
    },
    infravermelho: {
      titulo: "Infravermelho",
      curto: "Luz com comprimento de onda maior que o da luz vermelha, que nossos olhos não enxergam. Revela objetos frios e regiões escondidas por poeira.",
      detalhe: "As imagens deste site são convertidas para tons que a tela consegue mostrar.",
      ancora: "termo-infravermelho",
    },
    ra: {
      titulo: "Ascensão reta (RA, α)",
      curto: "A “longitude” do céu: diz a posição de um ponto no sentido leste–oeste. Vai de 0° a 360°.",
      detalhe: "Também pode ser escrita em horas (0 h a 24 h), onde 1 h = 15°. Ex.: 08h55m10.831s.",
      ancora: "termo-ra",
    },
    dec: {
      titulo: "Declinação (Dec, δ)",
      curto: "A “latitude” do céu: vai de −90° (polo sul celeste) a +90° (polo norte celeste); 0° é o equador celeste.",
      ancora: "termo-dec",
    },
    sexagesimal: {
      titulo: "Graus decimais e sexagesimal",
      curto: "Dois jeitos de escrever a mesma posição: em graus com casas decimais (133.795) ou em partes de 60, como num relógio (08h55m10.8s ou −07°14′42″).",
      detalhe: "Na RA, 1 h = 15°, 1 minuto de tempo = 15′ e 1 segundo de tempo = 15″. O site aceita os dois formatos.",
      ancora: "termo-ra",
    },
    fov: {
      titulo: "Campo de visão (FOV)",
      curto: "O tamanho da região quadrada recortada ao redor do ponto escolhido, medido em minutos de arco (′). Aqui vai de 0,5′ a 30′.",
      detalhe: "Quanto maior o FOV, mais céu aparece, mas cada pixel continua cobrindo 6,15″: o detalhe não aumenta.",
      ancora: "termo-fov",
    },
    arcmin: {
      titulo: "Minuto de arco (′)",
      curto: "Unidade de ângulo: 1 grau tem 60 minutos de arco. A Lua cheia tem cerca de 30′ de largura no céu.",
      ancora: "termo-arcmin",
    },
    arcsec: {
      titulo: "Segundo de arco (″)",
      curto: "Unidade de ângulo ainda menor: 1 minuto de arco tem 60 segundos de arco (1″ = 1/3600 de grau).",
      detalhe: "Cada pixel das imagens do SPHEREx cobre cerca de 6,15″ do céu.",
      ancora: "termo-arcmin",
    },
    pixel: {
      titulo: "Pixel SPHEREx (6,15″)",
      curto: "Cada pixel das imagens do SPHEREx cobre cerca de 6,15 segundos de arco do céu. Um FOV de 3′ tem só uns 29 × 29 pixels.",
      detalhe: "Por isso as estrelas aparecem como poucos pontos, e não como fotos nítidas.",
      ancora: "termo-resolucao",
    },
    detector: {
      titulo: "Detector (D1 a D6)",
      curto: "O SPHEREx tem seis detectores; cada um registra uma parte do infravermelho. D1 vê as “cores” mais curtas (≈0,75 µm) e D6 as mais longas (≈5 µm).",
      detalhe: "Faixas aproximadas: D1 0,75–1,1 µm · D2 1,1–1,6 · D3 1,6–2,4 · D4 2,4–3,8 · D5 3,8–4,4 · D6 4,4–5,0 µm.",
      ancora: "termo-detector",
    },
    "detector-d1": detector(1, "0,75 a 1,1 µm", "É a parte do infravermelho mais próxima da luz vermelha visível."),
    "detector-d2": detector(2, "1,1 a 1,6 µm", "Infravermelho próximo."),
    "detector-d3": detector(3, "1,6 a 2,4 µm", "Infravermelho próximo."),
    "detector-d4": detector(4, "2,4 a 3,8 µm", "Inclui a região perto de 3 µm onde o gelo de água absorve luz."),
    "detector-d5": detector(5, "3,8 a 4,4 µm", "Inclui a região perto de 4,3 µm onde o gelo de gás carbônico (CO₂) absorve luz."),
    "detector-d6": detector(6, "4,4 a 5,0 µm", "Inclui a região perto de 4,7 µm onde o gelo de monóxido de carbono (CO) absorve luz."),
    banda: {
      titulo: "Banda espectral (102 bandas)",
      curto: "Uma faixa estreita de comprimento de onda, como uma “cor” do infravermelho. O SPHEREx divide 0,75–5 µm em 102 bandas, 17 por detector.",
      detalhe: "Bandas diferentes não são momentos diferentes: o site nunca as mostra como passagem de tempo. A numeração 1 a 102 é uma convenção deste projeto.",
      ancora: "termo-banda",
    },
    lvf: {
      titulo: "Filtro linear variável",
      curto: "Um filtro sobre o detector em que a “cor” que passa muda aos poucos de uma ponta à outra. Assim, cada faixa da imagem vê um comprimento de onda diferente.",
      detalhe: "Conforme o telescópio aponta para posições diferentes, o mesmo objeto cai em faixas diferentes e o espectro é montado exposição por exposição.",
      ancora: "termo-espectro",
    },
    micrometro: {
      titulo: "Micrômetro (µm)",
      curto: "Um milionésimo de metro. É a unidade usada para o comprimento de onda da luz infravermelha.",
      detalhe: "A luz visível vai de cerca de 0,4 µm (violeta) a 0,7 µm (vermelho); o SPHEREx observa de 0,75 a 5 µm.",
      ancora: "termo-comprimento-onda",
    },
    "comprimento-onda": {
      titulo: "Comprimento de onda (λ)",
      curto: "A distância entre duas cristas da onda de luz. Na prática, é a “cor” da luz; no infravermelho é medido em micrômetros (µm).",
      ancora: "termo-comprimento-onda",
    },
    epoca: {
      titulo: "Época / data de observação",
      curto: "O momento em que a imagem foi registrada. Cada quadro da sequência é uma época diferente, da mais antiga para a mais recente.",
      detalhe: "A data vem do início da exposição informado pelo arquivo (t_min, em MJD), convertida para UTC.",
      ancora: "termo-epoca",
    },
    exposicao: {
      titulo: "Exposição",
      curto: "O intervalo em que o detector fica coletando luz para formar uma imagem. Cada exposição do SPHEREx dura poucos minutos.",
      detalhe: "Uma observação aqui é uma exposição de um detector; várias exposições podem cair no mesmo dia.",
      ancora: "termo-epoca",
    },
    utc: {
      titulo: "UTC",
      curto: "Tempo Universal Coordenado: o horário de referência mundial. O horário de Brasília é UTC − 3 horas.",
      ancora: "termo-epoca",
    },
    mjd: {
      titulo: "MJD (Data Juliana Modificada)",
      curto: "Uma contagem contínua de dias usada na astronomia, a partir da meia-noite de 17/11/1858. Facilita fazer contas com datas.",
      detalhe: "MJD = Data Juliana − 2 400 000,5. O site converte o MJD do arquivo para data e hora UTC.",
      ancora: "termo-epoca",
    },
    "movimento-proprio": {
      titulo: "Movimento próprio",
      curto: "O deslocamento aparente de uma estrela no céu ao longo dos anos, por ela se mover em relação ao Sol. Costuma ser medido em milissegundos de arco por ano.",
      detalhe: "A Estrela de Barnard, uma das mais rápidas, anda cerca de 10″ por ano: em um ano, mais de um pixel do SPHEREx.",
      ancora: "termo-movimento-proprio",
    },
    seguir: {
      titulo: "Seguir o movimento do alvo",
      curto: "Marcado: cada quadro é centrado onde o alvo estava naquela data, calculado pelo movimento próprio. Desmarcado: o quadro fica fixo no céu e o alvo se desloca.",
      ancora: "termo-quadro-comum",
    },
    "quadro-comum": {
      titulo: "Quadro comum",
      curto: "Todas as imagens são redesenhadas na mesma grade, com norte para cima, leste à esquerda e pixel de 6,15″. Assim, o mesmo pixel é o mesmo ponto do céu em todas as datas.",
      detalhe: "Leste fica à esquerda porque olhamos o céu “de dentro”, como num mapa do céu visto de baixo. Cada exposição original tem outra orientação.",
      ancora: "termo-quadro-comum",
    },
    cobertura: {
      titulo: "Cobertura do quadro",
      curto: "A fração do quadro que caiu dentro do detector naquela exposição. 100% é um quadro completo.",
      detalhe: "Um quadro parcial tem uma parte sem dados, mostrada hachurada.",
      ancora: "termo-cobertura",
    },
    "quadro-parcial": {
      titulo: "Quadro parcial",
      curto: "Um quadro em que parte da região pedida ficou fora do detector naquela exposição. Essa parte não tem dados.",
      detalhe: "“Só quadros completos” esconde esses quadros da sequência.",
      ancora: "termo-cobertura",
    },
    "fora-detector": {
      titulo: "Fora do detector (hachurado)",
      curto: "Área do quadro que não foi observada naquela exposição. Aparece transparente ou hachurada: não é céu escuro, é ausência de dados.",
      ancora: "termo-cobertura",
    },
    "pixel-invalido": {
      titulo: "Pixel inválido (vinho)",
      curto: "Pixel dentro do detector sem valor confiável, pintado de vinho (#B03060). Em geral é o centro saturado de uma estrela muito brilhante ou um pixel defeituoso.",
      ancora: "termo-contaminacao",
    },
    normalizacao: {
      titulo: "Normalização visual",
      curto: "O brilho de cada quadro é ajustado só para ficar visível na tela. Não é uma medição de brilho (fotometria).",
      detalhe: "Um objeto parecer mais claro num quadro do que em outro não prova que ele mudou.",
      ancora: "termo-brilho",
    },
    flags: {
      titulo: "Contaminação (flags)",
      curto: "Cada imagem vem com uma máscara que marca pixels problemáticos: raio cósmico, saturação, pixel morto ou quente, reflexo (ghost), persistência, rastro de satélite e outros.",
      detalhe: "Medidas com esses pixels merecem desconfiança. A marca SOURCE (fonte conhecida) é só informativa e não conta como contaminação.",
      ancora: "termo-contaminacao",
    },
    "media-epocas": {
      titulo: "Somar (média de) épocas",
      curto: "Junta várias observações do mesmo detector numa só imagem. O ruído aleatório diminui, e objetos fracos ficam mais visíveis.",
      detalhe: "Em média, o ruído aleatório cai com a raiz quadrada do número de quadros (aproximação). A média mistura bandas vizinhas do detector.",
      ancora: "termo-quadro-comum",
    },
    "sinal-ruido": {
      titulo: "Sinal-ruído",
      curto: "Compara a luz do objeto (sinal) com as flutuações aleatórias da imagem (ruído). Quanto maior, mais confiável é ver o objeto.",
      ancora: "termo-quadro-comum",
    },
    diferenca: {
      titulo: "Diferença entre épocas",
      curto: "Subtrai a média das observações antigas da média das recentes. Claro = mais brilho nas recentes; escuro = mais brilho nas antigas; cinza = sem mudança.",
      detalhe: "Mostra mudança aparente: diferenças de foco entre exposições e restos do fundo também aparecem, então não é uma detecção automática.",
      ancora: "termo-quadro-comum",
    },
    espectro: {
      titulo: "Espectro",
      curto: "Gráfico do brilho de um ponto em cada comprimento de onda. Mostra “de que cores infravermelhas” o objeto é feito.",
      detalhe: "Cada ponto do gráfico vem de uma exposição diferente; o comprimento de onda de cada medida é aproximado.",
      ancora: "termo-espectro",
    },
    abertura: {
      titulo: "Abertura e anel de fundo",
      curto: "A abertura é o círculo ao redor do ponto clicado onde o brilho é medido. O anel em volta (de 2 a 3 vezes o raio) mede o fundo do céu, que é subtraído.",
      detalhe: "Raio padrão de 9″. Um círculo maior capta mais luz, mas também mais ruído e estrelas vizinhas.",
      ancora: "termo-abertura",
    },
    fundo: {
      titulo: "Fundo do céu",
      curto: "Uma região sem o objeto de interesse. Comparar o alvo (A) com o fundo (B) mostra o que vem do objeto e o que vem do céu ao redor.",
      ancora: "termo-fundo-ceu",
    },
    "mjy-sr": {
      titulo: "MJy/sr (brilho superficial)",
      curto: "Megajansky por esferorradiano: quanta luz chega de cada pedacinho do céu. É a unidade das imagens do SPHEREx.",
      detalhe: "O fluxo aqui é a média na abertura menos o fundo, sem correções de fotometria: serve para comparar a forma do espectro, não o brilho absoluto.",
      ancora: "termo-espectro",
    },
    erro: {
      titulo: "Erro / barra de erro",
      curto: "A incerteza de uma medida, calculada a partir da variância que acompanha cada imagem. A barra vai de fluxo − erro a fluxo + erro.",
      detalhe: "Se as barras de dois pontos se sobrepõem, a diferença entre eles pode ser só ruído.",
      ancora: "termo-espectro",
    },
    irsa: {
      titulo: "IRSA/IPAC",
      curto: "O Arquivo Científico de Infravermelho da NASA, mantido pelo IPAC/Caltech. É onde os dados oficiais do SPHEREx ficam guardados.",
      ancora: "termo-irsa",
    },
    sia: {
      titulo: "SIA (Simple Image Access)",
      curto: "Um padrão internacional para perguntar a um arquivo “quais imagens cobrem este ponto do céu?”. O site usa o SIA v2 do IRSA.",
      ancora: "termo-irsa",
    },
    ibe: {
      titulo: "IBE (recorte)",
      curto: "Serviço do IRSA que entrega só um pedaço (recorte) de uma imagem, centrado nas coordenadas pedidas, sem baixar o arquivo inteiro.",
      detalhe: "Cada recorte leva alguns segundos; por isso o site guarda os recortes em cache.",
      ancora: "termo-recorte",
    },
    recorte: {
      titulo: "Recorte e centro do recorte",
      curto: "Um pedaço da imagem original do SPHEREx ao redor das coordenadas pedidas. O centro é o ponto onde o recorte foi centrado naquela data.",
      detalhe: "Com “Seguir o movimento do alvo”, o centro é propagado pelo movimento próprio.",
      ancora: "termo-recorte",
    },
    releases: {
      titulo: "DR1 e QR3 (releases)",
      curto: "Conjuntos de dados publicados pela missão. QR é uma liberação rápida (Quick Release); DR1 é a primeira liberação de dados (Data Release 1).",
      detalhe: "Podem ter processamentos diferentes: comparar brilho entre DR1 e QR3 não é garantido. Coleções “deep” vêm dos campos profundos da missão.",
      ancora: "termo-dr1-qr3",
    },
    colecao: {
      titulo: "Coleção",
      curto: "O grupo de produtos do arquivo de onde veio a imagem, por exemplo spherex_dr1 ou spherex_qr3.",
      ancora: "termo-dr1-qr3",
    },
    produto: {
      titulo: "Identificador do produto",
      curto: "O código do arquivo original no IRSA. Permite conferir de onde veio cada imagem.",
      ancora: "termo-produto",
    },
    gaia: {
      titulo: "Gaia DR3",
      curto: "Catálogo da missão Gaia (Agência Espacial Europeia), com posição e movimento de cerca de 1,8 bilhão de estrelas. Aqui serve só para comparação.",
      ancora: "termo-gaia-wise",
    },
    allwise: {
      titulo: "AllWISE",
      curto: "Catálogo do telescópio infravermelho WISE, da NASA, em 3,4, 4,6, 12 e 22 µm. Ajuda a ver se algo no SPHEREx já é um objeto conhecido.",
      ancora: "termo-gaia-wise",
    },
    hips: {
      titulo: "HiPS / Aladin",
      curto: "HiPS é um formato de mapa do céu em ladrilhos, que permite dar zoom do céu todo até regiões pequenas. Aladin Lite é o visualizador do CDS (Estrasburgo) que mostra esses mapas.",
      ancora: "termo-hips",
    },
    "mapa-observacoes": {
      titulo: "Mapa de observações",
      curto: "Gráfico em que cada ponto é uma observação: a data no eixo horizontal e o comprimento de onda no vertical. A cor indica o detector.",
      ancora: "termo-mapa-observacoes",
    },
    mock: {
      titulo: "Dados fictícios",
      curto: "Imagens inventadas, só para testar a interface. Sempre aparecem com aviso e nunca representam observações científicas.",
      ancora: "termo-ficticios",
    },
  };
})();
