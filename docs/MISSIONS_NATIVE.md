# Missões configuráveis no ROM2Native AI v0.8

O motor de combate do port C++ agora carrega uma lista de unidades a partir
de um arquivo JSON selecionado no Android. Essa é uma **ferramenta de
reconstrução de missões**, não a conversão automática de scripts do SNES.

## Jogar uma missão personalizada

1. Instale o APK ROM2Native AI v0.8 (motor nativo).
2. Importe a ROM Desert Strike USA conhecida, se ainda não estiver salva.
3. Importe o mesmo pacote visual CGI v3 utilizado na versão v0.6/v0.7.
4. Toque em **Importar missão JSON** e escolha
   `examples/rom2native-mission-demo.json`, disponível no repositório.
5. No alto da tela, acompanhe VIDA e ALVOS. Use FIRE e o direcional.
6. Toque em REINICIAR (ou START no controle) para reiniciar a missão.
7. Para remover a personalização, toque em **Missão padrão**.

O aplicativo mantém a última missão JSON no armazenamento privado
e a restaura automaticamente depois de reiniciar. A ROM e o ZIP visual
também permanecem no armazenamento privado, quando já importados.

## Esquema aceito

~~~json
{
  "format": "rom2native-mission-v1",
  "rom_sha256": "606abf536440173ae36466db360c7db6b474beb7a105c8a62bc74a54cbe1c38b",
  "title": "Meu treinamento",
  "goal": "destroy_all",
  "targets": [
    {"id": "torre-norte", "type": "turret", "x": 60, "y": 63, "hp": 2},
    {"id": "patrulha-sul", "type": "patrol", "x": 180, "y": 190, "hp": 3, "patrol_range": 22},
    {"id": "deposito", "type": "depot", "x": 250, "y": 70, "hp": 1}
  ]
}
~~~

Os valores `x` e `y` usam coordenadas do motor virtual de **320×240**
pixels, não coordenadas geográficas ou do mapa original do SNES.
`hp` varia de 1 a 9. Somente `patrol` aceita `patrol_range`, entre 8 e 32.
Os alvos devem ter centros espaçados por pelo menos 26 pixels.
As posições devem estar dentro de x=22..298 e y=34..218.
A faixa horizontal inteira da patrulha precisa permanecer visível.
O objetivo suportado é somente `destroy_all` (destruir todos).
O app aceita 1 a 12 alvos e limita JSONs a 32 KiB.

## Validar antes de importar

~~~bash
python3 -m rom2native.mission_schema examples/rom2native-mission-demo.json
~~~

Esse validador aplica as mesmas regras numéricas principais da interface
Android; o motor C++ verifica novamente posições, vida, tipos e intervalos.
Arquivos inválidos são rejeitados, preservando a missão carregada.

## Limitações e próximo marco

- Alvos e deslocamentos são protótipos desenhados pelo próprio motor.
- Veículos e edifícios que aparecem na imagem CGI de fundo são
  somente decoração; não são alvos ou mapas de colisão.
- Não há ainda mapas, unidades, scripts de campanha ou IA extraídos
  fielmente do Desert Strike original.
- As cinco capturas PPU existentes documentam o helicóptero no mar,
  mas não bastam para mapear os inimigos de uma fase terrestre.
- O objetivo de médio prazo é converter metadados confirmados de
  missão da ROM para esse formato, preservando a engine nativa.

Direitos: não coloque ROM comercial nem imagens extraídas do jogo
em arquivos públicos do GitHub.
