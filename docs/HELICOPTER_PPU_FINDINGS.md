# Resultados das cinco capturas reais de PPU — Desert Strike

Capturas recebidas: frames **2027, 2244, 2632, 2751 e 3237**.
Todas passaram pelas verificações SHA-256 e vieram da mesma revisão da ROM
(`606abf536440173ae36466db360c7db6b474beb7a105c8a62bc74a54cbe1c38b`).

## Descobertas sustentadas pelo cruzamento de OAM, CGRAM e screenshots

- Na sequência marítima, as entradas de **paleta OBJ 0** acompanham o helicóptero.
- As entradas de **paleta OBJ 4** acompanham a sombra.
- Quantidade de entradas paleta 0 por frame: **14, 22, 14, 22, 14**.
- Quantidade de entradas paleta 4 por frame: **3, 5, 9, 5, 5**.
- As listas de IDs de tiles OBJ usadas no helicóptero formam **três famílias**:
  - Família 1: frames **2027 e 3237**;
  - Família 2: frames **2244 e 2751**;
  - Família 3: frame **2632**.
- A CGRAM ficou idêntica até o frame 2751; do frame 2751 ao 3237
  mudaram apenas os índices de paleta **44, 45 e 46**.
- As diferenças sucessivas de VRAM totalizaram **1452, 1364, 1543 e 1782 bytes**.

Essas famílias são **configurações de tiles** e não prova matemática de um
ângulo específico. O movimento foi comparado com screenshots, mas ainda
falta recuperar registradores de base OBJ, tamanho dos sprites e
eventuais alterações de tiles por rotor/animação para reconstrução exata.

## Ferramenta reproduzível

~~~bash
python3 -m rom2native.capture_series captura1.zip captura2.zip captura3.zip captura4.zip captura5.zip --out private-output/serie.json
~~~

O utilitário usa apenas os dados dos ZIPs e não salva a ROM ou seus pixels.
É específico para a sequência observada; outras fases podem utilizar
paletas OBJ diferentes.

Os PNGs de referência do helicóptero foram gerados **privadamente** a
partir das screenshots e de uma máscara de cores da CGRAM. Não foram
adicionados ao repositório. Também não são ainda gráficos CGI gerados por IA.

## Próxima meta

Capturar os registradores PPU relevantes para endereço/base OBJ,
modo/tamanho do sprite e compor cada sprite diretamente da VRAM.
Depois comparar a composição com o PNG capturado e preparar um atlas
de oito direções com somente três configurações agora comprovadas.
