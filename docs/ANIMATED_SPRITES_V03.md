# ROM2Native AI v0.3 — atlas CGI de oito ângulos

Esta versão suporta importar imagens personalizadas do helicóptero em oito
direções para o motor Android/C++ independente. **Não foram ainda reconstruídos
os sprites originais do jogo SNES.**

## Especificação

- Formato: PNG RGBA de 8 bits com transparência
- 8 quadros horizontais, cada um de tamanho igual, de até 128x128 pixels
- Ordem exata: N, NE, E, SE, S, SW, W, NW (sentido horário)
- Exemplo: 96x96 por quadro => atlas 768x96
- Todas as oito células precisam conter pixels visíveis
- Direção e disparos no motor seguem o controle; sem comando, conserva direção
- O ZIP contém apenas helicopter.png e manifest.json, sem a ROM comercial

## Gerar ZIP visual a partir de um atlas revisado

~~~bash
python3 -m rom2native.visual_pack \
  --rom "Desert Strike - Return to the Gulf (U).smc" \
  --sprite helicopter_8_angles_rgba.png \
  --frames 8 \
  --out helicopter_cgi.zip
~~~

O programa verifica dimensões, CRC PNG, SHA-256 e revisão da ROM. O manifesto
v2 registra frames=8, layout=horizontal, frame_width, frame_height e a ordem
das direções. O importador Android confirma esses campos e todos os quadros.

## Como testar

1. Instale o APK ROM2Native AI v0.3.
2. Importe sua ROM original.
3. Selecione Importar visual CGI (ZIP) e escolha o pacote de oito ângulos.
4. Mova em oito direções e teste disparar. Feche e reabra o app para testar
   a persistência do pacote.
5. Os pacotes v1 de um único sprite continuam compatíveis.

## IA e engenharia reversa

O adaptador ComfyUI executa geração img2img mediante workflow/modelo próprios.
Apenas preservar dimensões não garante identidade e alinhamento entre quadros.
É necessário revisar manualmente todas as poses antes de empacotar.

O atlas demonstrativo criado para testes foi desenhado de modo procedural:
**não é gerado por IA** e não foi extraído de Desert Strike.
A física, o cenário e as missões do motor ainda são demonstrativos.

Próximas etapas: confirmar sprites reais via VRAM/CG-RAM, gerar e revisar imagens
CGI coerentes a partir deles, reconstituir entidades e regras de missão no C++.
