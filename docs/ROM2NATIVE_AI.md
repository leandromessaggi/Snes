# ROM2Native AI — projeto iniciado (prova de conceito v0.1)

Meta: partir da ROM original de SNES, fazer engenharia reversa dos dados e regras
e entregar um motor Android/C++ sem emulação. Na fase visual, uma IA refaz
sprites e cenários no estilo de CGI pré-renderizado de PS1 (1995–1998).

## Entregue na primeira etapa

- rom2native/romtool.py — verifica SHA-256, título e cabeçalho LoROM; lê
  .smc/.sfc/ZIP; decodifica blocos candidatos de tiles SNES 2bpp e 4bpp
  para atlas PNG; produz manifest e fila de jobs de IA.
- rom2native/ai_bridge.py — conector real para a API de um ComfyUI
  imagem-para-imagem, com modelo e workflow fornecidos pelo usuário.
  Valida as dimensões da imagem retornada e salva metadados.
- native-demo/ — APK separado do app com Snes9x: renderização pelo motor
  C++ próprio, helicóptero demonstrativo, movimento, tiros e controles
  touch/gamepad. Usa a ROM fornecida para validar a revisão e criar
  uma semente de cenário. **Sem Snes9x nem Libretro**.
- GitHub Actions — teste de C++/Python e build de APK ARM64 separado.

## Limitações essenciais

O mapa e a física do motor ainda são demonstrativos; NÃO representam
uma missão fiel de Desert Strike. A busca de tiles não localiza automaticamente
dados comprimidos nem sprites de personagens: o offset da ROM ainda tem
de ser identificado por engenharia reversa. O motor ainda não carrega
sprites convertidos pela IA; integração visual e animações virão após
a validação dos assets. A inferência de IA **não ocorre no Android**.

## Como executar a extração de sua própria ROM

No diretório raiz do repositório, use Python 3:

~~~bash
python3 -m rom2native.romtool "Desert Strike - Return to the Gulf (U).zip" --inspect

python3 -m rom2native.romtool "Desert Strike - Return to the Gulf (U).zip" --offset 0x10000 --tiles 128 --bpp 4 --out private-output
~~~

O offset 0x10000 é **exploratório**. O atlas pode mostrar bytes que não
são sprites. O diretório private-output é ignorado pelo Git.

## Como usar a IA (ComfyUI local)

Instale ComfyUI, selecione um modelo de imagem-para-imagem e exporte
um workflow em formato API com nós LoadImage, CLIPTextEncode e SaveImage.
Identifique os IDs dos nós da imagem e do prompt positivo, então:

~~~bash
python3 -m rom2native.ai_bridge --input private-output/candidate_atlas.png --output private-output/atlas_cgi_ps1.png --workflow meu_workflow_api.json --image-node 10 --text-node 20
~~~

O programa faz upload ao ComfyUI indicado, executa o workflow e valida
se o tamanho da imagem resultante é igual ao do atlas. Requer
**revisão humana** de alinhamento, ângulos e consistência. O CLI permite
apenas localhost, exceto com consentimento expresso --allow-remote.

Não há modelo IA incluído no pacote; o conector só funciona se o
ComfyUI, workflow e modelo já estiverem configurados.

## Gerar o protótipo Android independente

Actions -> ROM2Native AI - Android prototype -> branch feature/rom2native-ai.

Baixe o artefato ROM2NativeAI-Android-native-prototype.
O package ID é br.com.rom2native, assim o app novo pode coexistir
com Desert Strike Android (que usa Snes9x).

Abra o APK e importe a ROM original para iniciar a demonstração nativa.
A ROM fica somente nos arquivos privados do aparelho; não é
distribuída no APK.

## V0.2: sprite visual importável no jogo

O renderizador C++ aceita uma imagem RGBA do helicóptero, com transparência, importada de um ZIP validado no Android. O pipeline de IA ainda depende de um ComfyUI configurado e de aprovação humana. Veja [VISUAL_PACKS.md](VISUAL_PACKS.md).

## Roadmap técnico

1. Extrair VRAM/paletas em execução para comprovar o formato dos sprites reais.
2. Reconstruir um helicóptero completo com todos os ângulos e animações.
3. Produzir o conjunto CGI-PS1 com geração e curadoria consistentes.
4. Mapear scripts de missão, colisões, armas e inteligência artificial.
5. Integrar assets revisados no motor nativo e completar a primeira missão.

Nunca inclua ROM comercial, áudio ou gráficos extraídos no GitHub.
Revise autorização de uso da ROM e as políticas do provedor de IA.

## Animação direcional v0.3

O motor agora aceita folhas de sprites com oito orientações e suporta disparo direcional. O pacote visual v2 é vinculado ao SHA-256 da ROM. Pacotes v1 de imagem única ainda funcionam. Consulte [o guia de sprites de oito ângulos](ANIMATED_SPRITES_V03.md). O teste usa arte procedural, não gerada por IA ou extraída do jogo.

## Busca automática de candidatos gráficos na ROM

Ferramenta: rom2native/scan_tiles.py. Exemplo:

    python3 -m rom2native.scan_tiles "Desert Strike - Return to the Gulf (U).zip" --out private-output/tile-candidates --step 0x2000 --top 24

Gera candidate-contact.png (miniaturas dos 24 candidatos mais bem pontuados) e candidate-index.json (offsets, 2/4bpp, proporção de tiles vazios e similaridade entre pixels adjacentes). Essa análise é apenas heurística. Dados comprimidos, código e tabelas podem produzir falsos positivos; nenhuma sprite de helicóptero foi identificada ou descomprimida com segurança nessa etapa. Não publique arquivos derivados da ROM comercial.

## v0.4 — busca gráfica + pacote CGI experimental

- Scanner local novo: `python3 -m rom2native.scan_tiles ...` procura dados brutos 2bpp/4bpp por toda a ROM e grava uma folha de contato e um índice com posições e scores. O resultado é **heurístico**, ainda não confirma gráficos reais do jogo.
- Pacote visual CGI experimental gerado à parte: oito quadros do helicóptero adaptados de arte conceitual gerada por IA. O arquivo ZIP utiliza o formato `rom2native-visual-v2` já aceito pelo Android, sem incluir dados da ROM.
- O protótipo nativo mantém mapa, movimento e projéteis demonstrativos; a recriação fiel da campanha e a geração de gráficos de todas as fases continuam pendentes.
- O APK v0.4 compila o motor independente da ROM, não inclui Snes9x e continua exigindo importação local da ROM para ativar a demonstração.

## v0.5 — exportação de referência visual do jogo original

A ferramenta auxiliar **Desert Strike Research v0.14** (Snes9x somente durante a engenharia reversa) exporta os 64KiB da VRAM e o quadro atual PNG em um ZIP. O conversor `rom2native.vram_reference` analisa as páginas de tiles 2/4bpp e compara capturas para descobrir áreas que mudam. Não há CGRAM/OAM nem reconstrução fiel das missões nesta etapa. Instruções: [Captura de VRAM](VRAM_CAPTURE.md).
