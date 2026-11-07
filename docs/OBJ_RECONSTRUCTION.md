# Reconstrução de sprites OBJ diretamente das cinco capturas PPU

O programa `rom2native.obj_reconstruct` reconstrói pixels RGBA de um conjunto
de entradas OAM, lendo os bytes da VRAM em blocos planares SNES 4bpp e as
cores reais em CGRAM. Não usa imagens de tela para gerar os pixels.

## Descoberta verificada

Para a edição USA de Desert Strike, as cinco capturas dos quadros
2027, 2244, 2632, 2751 e 3237 permitem reconstruir a silhueta do
helicóptero com `OBJNameBase=0`, `OBJNameSelect=0` e `OBJSizeSelect=0`.
Os 5 resultados corresponderam pixel a pixel à transparência das
máscaras de referência previamente extraídas das screenshots:

| Quadro | Pixels visíveis | Diferença na máscara |
|---|---:|---:|
| 2027 | 646 | 0 |
| 2244 | 636 | 0 |
| 2632 | 497 | 0 |
| 2751 | 638 | 0 |
| 3237 | 643 | 0 |

Os RGB têm pequenas diferenças de arredondamento/escala dos canais
(aproximadamente 0,35 a 0,40 unidades por canal em média) em comparação
com o recorte da saída de vídeo; isso não afeta a silhueta reconstruída.

## Como reproduzir

~~~bash
python3 -m rom2native.obj_reconstruct minhas-capturas/*.zip --out private-output/helicopter-from-vram
~~~

Saídas: PNGs com transparência `helicopter_FRAME_from_vram.png` e
`shadow_FRAME_from_vram.png`, além de `reconstruction.json`.
A identificação empírica da paleta 0 para helicóptero e da paleta 4
para sombra é específica do trecho marítimo analisado. Para outra ROM,
os parâmetros de endereçamento devem ser informados explicitamente.

É possível converter uma captura em um pacote v1 compatível com o
motor ROM2Native AI sem emulação, usando uma cópia local da mesma ROM:

~~~bash
python3 -m rom2native.obj_reconstruct minha-captura.zip --rom minha-rom.sfc --out private-output/one-frame
~~~

Use o ZIP produzido no botão 'Importar visual CGI (ZIP)' do aplicativo
`native-demo` existente. Este pacote mantém a aparência original do
SNES, **não** é arte CGI. Como é apenas um quadro, a imagem não gira
com os controles. O motor original de demonstração continua independente.

## Limitações

- Os cinco quadros pertencem a três conjuntos de tiles conhecidos.
- A orientação exata de todos os ângulos, efeitos de cor e propriedades
  da primeira missão ainda precisam de validação.
- O compositing atual assume ordem OAM inversa para objetos da mesma
  prioridade. Não reproduz máscaras de janela nem toda a PPU.
- Os arquivos gráficos são derivados da ROM do usuário e **não**
  devem ser versionados ou redistribuídos no GitHub.
