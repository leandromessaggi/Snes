# Desert Strike Android v0.8 (experimental)

Projeto de pesquisa e adaptação do jogo **Desert Strike: Return to the Gulf (SNES)** para Android ARM64.

> **Não é ainda um port nativo independente.** A ROM é executada pelo Snes9x/Libretro por meio de uma ponte Android em C++/JNI. O projeto ainda precisa compilar no GitHub Actions e ser testado no aparelho antes de ser considerado jogável.

## Componentes

- Android Kotlin: importação da ROM por seletor de arquivos, overlay multitoque, gamepad USB/Bluetooth e remapeamento persistente.
- C++/JNI: carregamento de Snes9x Libretro, quadros ARGB, áudio PCM estéreo, SRAM e save states.
- Mods: patches IPS e pacotes ZIP com `manifest.json`, com validação de SHA-256 da ROM.
- Ferramenta de pesquisa: exporta diffs de WRAM por quadro, até 600 quadros (quando o núcleo expõe a memória).
- CI: compilação do núcleo ARM64 com Android NDK, build Gradle e verificação de ELF com alinhamento de 16 KiB.

## Como gerar o APK

1. Abra **Actions** neste repositório e escolha **Android ARM64 debug APK**.
2. Execute **Run workflow** na branch `feature/desert-strike-android`. Se a opção não aparecer, o workflow precisa existir na branch padrão ou ser incorporado à `main`.
3. Após concluir com **sucesso**, baixe o artefato `DesertStrike-v0.8-debug-APK`.
4. Instale o APK em dispositivo Android ARM64 e use **Abrir ROM**. A ROM **não está incluída** no repositório nem no APK.

O aplicativo verifica se a ROM, depois de remover eventual cabeçalho copier de 512 bytes, tem SHA-256:
`606abf536440173ae36466db360c7db6b474beb7a105c8a62bc74a54cbe1c38b`.

### Testes disponíveis

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
g++ -std=c++17 -Wall -Wextra -Werror app/src/main/cpp/tests/test_native.cpp -o /tmp/desert-test
/tmp/desert-test
kotlinc app/src/main/java/br/com/desertstrike/IpsPatcher.kt tests/TestIps.kt -include-runtime -d /tmp/test-ips.jar
java -jar /tmp/test-ips.jar
```

## Mods e pesquisa

- [Guia de mods IPS](MODS.md)
- [Notas da engenharia reversa](docs/engenharia-reversa.md)

Não há garantias de funcionamento integral, compatibilidade com todos os aparelhos, preservação de saves ou ausência de bugs. A reprodução fiel e a eventual reconstrução do motor original exigem instrumentação e testes adicionais.

## Direitos e licenças

A ROM, gráficos, músicas e outros recursos do jogo não são distribuídos. Todos os direitos pertencem aos seus respectivos titulares. A compilação utiliza [Snes9x](https://github.com/snes9xgit/snes9x), que possui condições próprias de licença; consulte-as antes de distribuir binários.
