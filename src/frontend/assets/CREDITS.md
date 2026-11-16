# Créditos das imagens e ícones

Data de acesso de todas as fontes abaixo: **2026-11-15**.

## Imagens da NASA (pasta `nasa/`)

Todas as imagens foram baixadas na versão "width-1024" publicada pelo JPL
e redimensionadas/recomprimidas com Pillow (JPEG q82). Nenhum outro
tratamento foi aplicado.

| Arquivo | Título oficial | Crédito | Página de origem |
|---|---|---|---|
| `nasa/spherex-all-sky-map-pia26600.jpg` (960×540) | SPHEREx's First All-Sky Map (PIA26600), 18 dez. 2025 | NASA/JPL-Caltech | https://www.jpl.nasa.gov/images/pia26600-spherexs-first-all-sky-map/ |
| `nasa/spherex-first-images-pia26280.jpg` (800×518) | First Images From NASA's SPHEREx (PIA26280) | NASA/JPL-Caltech | https://www.jpl.nasa.gov/images/pia26280-first-images-from-nasas-spherex/ |
| `nasa/spherex-in-orbit-pia26531.jpg` (800×450) | SPHEREx in Orbit (Artist's Concept) (PIA26531), 23 jan. 2025 | NASA/JPL-Caltech | https://www.jpl.nasa.gov/images/pia26531-spherex-in-orbit-artists-concept/ |

Arquivos baixados de:

- https://d2pn8kiwq2w21t.cloudfront.net/images/e1a-SPHEREx_all_sky_stars_and_gas-dust.width-1024.jpg
- https://d2pn8kiwq2w21t.cloudfront.net/images/jpegPIA26280.width-1024.jpg
- https://d2pn8kiwq2w21t.cloudfront.net/images/jpegPIA26531.width-1024.jpg

Fatos usados nas legendas (das páginas acima):

- PIA26600: primeiro mapa do céu inteiro em infravermelho, em 102 cores,
  com observações de maio a dezembro de 2025; azul = gás hidrogênio
  quente, vermelho = poeira; a faixa central é a Via Láctea.
- PIA26280: primeiras exposições, de 27 de março de 2025, ainda não
  calibradas; seis imagens por exposição, uma por detector.
- PIA26531: ilustração (conceito artístico); os escudos fotônicos
  cônicos bloqueiam luz e calor do Sol e da Terra.

### Condições de uso verificadas

- Diretrizes de mídia da NASA (https://www.nasa.gov/nasa-brand-center/images-and-media/):
  conteúdo da NASA em geral não está sujeito a copyright nos EUA e pode ser
  usado para fins educacionais/informativos, com a NASA reconhecida como
  fonte; insígnia e logotipos da NASA são protegidos e não podem ser usados;
  não se pode sugerir endosso da NASA.
- Política de uso de imagens do JPL (https://www.jpl.nasa.gov/jpl-image-use-policy/):
  imagens podem ser usadas sem permissão prévia, com linha de crédito
  (por exemplo "Courtesy NASA/JPL-Caltech" ou o crédito da legenda);
  logotipos da NASA e do JPL exigem aprovação; sem sugerir endosso.
- As três páginas de origem indicam o crédito "NASA/JPL-Caltech" e não
  apontam detentor de direitos de terceiros. Nenhuma das imagens contém
  logotipo da NASA ou da missão (conferido visualmente).

O site exibe o crédito "NASA/JPL-Caltech" junto de cada imagem, com link
para a página de origem. O projeto não é endossado pela NASA, pelo JPL
nem pelo Caltech.

## Sonda SPHEREx da barra de navegação (`nasa/spherex-probe-cutout.png` e `@2x`)

| Item | Valor |
|---|---|
| Arquivos | `nasa/spherex-probe-cutout.png` (256×193, ~15 KB) e `nasa/spherex-probe-cutout@2x.png` (512×386, ~40 KB) |
| Título oficial | Sectional View of the SPHEREx Spacecraft (Transparent), arte de 2 jun. 2022 (id `spherex02062022b`) |
| Página de origem | https://spherex.caltech.edu/image/spherex02062022b-sectional-view-of-the-spherex-spacecraft-transparent |
| Arquivo baixado | https://spherex.caltech.edu/system/avm_images/binaries/4/original/SPHEREx_March2022_Update_Still01_R08_TransparentBackground_5760x3240.png (PNG RGBA 5760×3240, 5,96 MB) |
| Crédito | Courtesy NASA/JPL-Caltech (linha de crédito padrão da política do site; a página não traz outro crédito) |
| Acesso | 2026-11-15 |

O que é: render oficial da equipe do SPHEREx (Caltech SPHEREx Science
Center), em **vista em corte** ("sectional view"): parte dos escudos
fotônicos aparece aberta para mostrar o telescópio. Não é foto. É a versão
oficial já publicada **com fundo transparente**, então não foi preciso
recortar o fundo à mão.

Processo (Pillow + numpy, script fora do repositório):

1. leitura do PNG original (canal alfa original, nenhuma máscara criada por nós);
2. corte na caixa delimitadora dos pixels com alfa > 8, com margem de 8 px
   (caixa 918,521–4057,2890 → 3139×2369 px);
3. redução por Lanczos para 256 e 512 px de largura;
4. quantização para 256 cores com alfa (FASTOCTREE, sem pontilhado) e
   gravação PNG otimizada.

Nenhuma alteração de cor ou de conteúdo. A rotação (telescópio apontando
para a direita no computador e para baixo no celular) é feita só por CSS.
O "feixe infravermelho" é um efeito de interface: o SPHEREx não emite
laser; ele só recebe luz.

Condições de uso: política de imagens do Caltech SPHEREx Science Center
(https://spherex.caltech.edu/page/image-use-policy, consultada em
2026-11-15): imagens do site podem ser usadas para qualquer fim sem
permissão prévia, com a linha de crédito "Courtesy NASA/JPL-Caltech"
salvo indicação em contrário; logotipos da NASA e do JPL exigem
aprovação; não se pode sugerir endosso de NASA, JPL ou Caltech. A imagem
não contém logotipo da NASA nem da missão (conferido visualmente). O
crédito aparece no rodapé do site.

## Ícone do site (`favicon.svg`, `favicon-32.png`, `apple-touch-icon.png`)

Desenho original do projeto, uma estilização da forma da sonda SPHEREx
(escudo fotônico cônico em camadas sobre o corpo). Não é o logotipo
oficial da missão nem da NASA. Os PNGs foram gerados com Pillow a partir
da mesma geometria do SVG.

## Fundo estrelado

Gerado proceduralmente (CSS + canvas em `js/theme.js`). Não representa
posições reais de estrelas.
