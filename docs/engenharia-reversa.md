# Engenharia reversa 65C816 — estado da investigação

A ROM de referência é **Desert Strike: Return to the Gulf (USA), SNES, LoROM**, com tamanho de 1 MiB sem o cabeçalho opcional de 512 bytes. O SHA-256 da ROM original está registrado no README.

## Evidências anteriores

- Entrada inicial observada no vetor SNES e rotina de inicialização dos registradores gráficos.
- Rotina de leitura do controle identificada nas análises anteriores em **$02:8362**, com comparações de máscaras de botões.
- No intervalo **$02:A27E–$02:A2F5**, surgem máscaras de Start, Y, B, A, esquerda e direita.
- Alguns caminhos fazem alterações em operandos **$20E6** e **$20E8**. A interpretação mais conservadora é navegação/menu, ainda não movimentos do helicóptero.

Esses endereços não foram validados ainda por rastreamento real durante uma partida e **não** identificam a física de voo nem a IA de combate.

## Próximos experimentos

1. Construir e executar o APK em um dispositivo ARM64; confirmar áudio, vídeo, input, save state e SRAM.
2. Iniciar o rastreamento de WRAM parado e repetir manobras de voo isoladamente, usando Start/A/B/D-pad como controles.
3. Comparar as alterações com execuções sem input para obter endereços candidatos.
4. Confirmar os candidatos em disassembly e tracing 65C816 antes de transcrever qualquer subsistema para C++ nativo.

O rastreador atual exporta **apenas um preview limitado às primeiras 32 alterações de cada quadro**. A análise completa de todos os endereços observados e a classificação estatística existente na linha de pesquisa v0.5 devem ser reintegradas em uma próxima revisão do aplicativo; isto é uma limitação da v0.8 publicada aqui.

Este repositório não contém a ROM original nem seu código binário.
