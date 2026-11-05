# Captura real de VRAM para reconstruir gráficos de Desert Strike

## O que foi implementado

A revisão do Snes9x fixada no projeto expõe via `RETRO_MEMORY_VIDEO_RAM` (ID 3)
os 65.536 bytes da memória de vídeo. O APK auxiliar **Desert Strike Research v0.14**
exporta essa VRAM e o quadro renderizado. É um coletor temporário de
engenharia reversa; o motor ROM2Native C++ continua sem emulação.

## Como capturar no Android

1. Instale o APK da action **ROM2Native VRAM research APK** (v0.14).
2. Importe a ROM original e selecione **Jogar / Continuar**.
3. Na fase, abra o menu para pausar o jogo.
4. Toque em **Capturar VRAM + quadro (ZIP)** e salve `helicoptero-parado.zip`.
5. Retome, mova o helicóptero e repita com `helicoptero-movendo.zip`.

O ZIP contém apenas `manifest.json`, `vram.bin` (64KiB) e `frame.png`,
sem incluir a ROM completa, estados salvos ou dados de conta. Porém
VRAM e imagem ainda contêm gráficos do jogo; mantenha os arquivos privados.

## Converter capturas em atlas e comparar movimentos

Execute a partir da raiz do repositório (Python 3 padrão):

```bash
python3 -m rom2native.vram_reference helicoptero-parado.zip --out private-output/vram-parado
python3 -m rom2native.vram_reference helicoptero-parado.zip --compare helicoptero-movendo.zip --bpp 4 --out private-output/diferencas
```

O primeiro comando gera `reference-frame.png`, `atlas-index.json` e páginas
da VRAM interpretadas como tiles SNES de 2 e 4 bits/pixel, em escala de cinza.
O segundo gera `vram-diff.json`, com os índices dos tiles que mudaram.
A comparação exige capturas da mesma revisão de ROM (SHA-256 idêntico).

**Importante:** VRAM não é equivalente a sprite pronto. A API Libretro
não entrega aqui a CGRAM (paletas), a OAM (atributos de sprites) ou o
tilemap interpretado. Não sabemos ainda quais tiles pertencem ao
helicóptero, e os atlas não são automaticamente uma fase jogável.

Como a imagem PNG e a VRAM são capturadas em chamadas distintas ao
abrir o menu, podem representar quadros consecutivos próximos. O
manifesto registra essa limitação como `paused_near_same_frame_not_atomic`.

## Próxima etapa

Com dois ZIPs reais do helicóptero e suas mudanças, mapear offsets
da VRAM, descobrir paletas e posições de objetos, e somente então
reconstruir os sprites para a IA reestilizar de forma consistente.

Os testes do projeto usam uma VRAM sintética via mock JNI;
eles não equivalem a jogar Desert Strike em um aparelho real.
