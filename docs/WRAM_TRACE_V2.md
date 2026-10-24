# Rastreamento de RAM (WRAM) v2

O aplicativo usa Libretro/Snes9x para observar modificações na RAM. Isto **não** é a reimplementação do motor do jogo.

## Como coletar dados

1. Importe a ROM suportada e inicie o jogo.
2. Abra **☰ → Iniciar rastreamento de RAM**.
3. Mantenha o jogo imóvel por alguns segundos (referência).
4. Repita um teste pressionando **somente um botão**, por exemplo esquerda.
5. Exporte o rastreamento JSON no menu, até o limite de 600 quadros.
6. Execute, no computador com Python 3:

    python3 scripts/analyze_wram_trace.py trace.json --button 6 --top 12

Índices: 6=esquerda, 7=direita, 4=cima, 5=baixo, 0=B, 8=A, 3=Start. São IDs Libretro, não máscaras 65C816.

## Campos

- frames[].changes: amostra das primeiras 32 mudanças por quadro para inspeção.
- frames[].changed_total: quantidade completa de mudanças no quadro.
- rankings[].top: candidatos calculados a partir de **todas** as mudanças, inclusive fora da amostra.
- top[]: [offset WRAM, alterações quando botão pressionado, alterações sem botão, score]. O score é numerador da diferença entre as taxas; não é coordenada de jogo.

São offsets relativos ao bloco RETRO_MEMORY_SYSTEM_RAM e não endereços 65C816. A correlação de alterações não demonstra causalidade nem identifica automaticamente a física de voo.

Use testes separados para esquerda, direita, disparo, menu e jogo parado. Não altere a ROM durante a coleta. O rastreamento é experimental e a execução em Android real ainda precisa ser validada.
