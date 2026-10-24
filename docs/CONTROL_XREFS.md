# Engenharia reversa: scanner de referências 65C816

A ROM comercial não deve ser colocada neste repositório. Use sua própria ROM local:

~~~bash
python3 scripts/scan_control_xrefs.py "Desert Strike - Return to the Gulf (U).smc" --expected-sha256 606abf536440173ae36466db360c7db6b474beb7a105c8a62bc74a54cbe1c38b --out references.json
~~~

O utilitário remove o cabeçalho copier de 512 bytes quando presente. Examina
possíveis operações absolutas com operandos $202A, $202C, $202E, $2030, $20E6 e $20E8.

Na ROM analisada, foram identificadas 25 correspondências de bytes. A análise
ainda **não confirma** se cada trecho é código executado: gráficos, tabelas e
operandos de outras instruções podem coincidir com esses bytes. Sem conhecer
o registrador DBR, $20E6 ainda não é um endereço físico WRAM demonstrado.
Não há comprovação de que seja coordenada ou controle do helicóptero.

Para continuar, usar o rastreador dinâmico WRAM v2 e validar os candidatos com
breakpoints de escrita e rastreamento real de execução.
