# Desert Strike Android — projeto experimental

Este repositório hospeda a adaptação Android experimental de **Desert Strike: Return to the Gulf (SNES)**.

**Estado:** desenvolvimento. O jogo ainda depende de um núcleo Snes9x/Libretro e **não** é um port nativo independente; APK e execução em aparelho ainda precisam de validação. Não há garantia de ausência de bugs.

## Objetivo

- Importação da ROM legítima pelo usuário (a ROM não será publicada neste repositório).
- Controles touch e gamepad externo, com remapeamento.
- Suporte experimental a mods por patches IPS.
- Instrumentação de RAM e engenharia reversa como caminho para estudar um motor independente.
- Build do APK ARM64 com GitHub Actions e verificação de compatibilidade com páginas de memória de 16 KiB.

O código e os testes serão integrados em uma branch de desenvolvimento, com revisão antes de mesclar à `main`.

## Créditos e licenças

O jogo e seus recursos pertencem aos respectivos titulares. O Snes9x é software de terceiros com seus próprios termos de licença. Nenhuma ROM, áudio, sprite ou mapa do jogo está incluído.
