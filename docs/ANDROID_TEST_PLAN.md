# Plano de testes no Android — Desert Strike v0.11

A compilação no GitHub Actions verifica estrutura, testes automatizados e bibliotecas
ARM64; **não substitui jogar com a ROM real no smartphone**.

## 1. Instalar e executar

1. Abra o workflow **Android ARM64 debug APK** do commit atualizado e confirme
   conclusão `success`.
2. Em **Artifacts**, baixe `DesertStrike-v0.11-debug-APK`. Extraia o APK do ZIP.
3. Instale no Android ARM64. Não é necessário conceder permissão ampla aos arquivos.
4. Abra **Abrir ROM** e selecione sua ROM USA `.smc`, `.sfc` ou ZIP.
   O aplicativo confere o SHA-256 após remover um eventual cabeçalho de 512 bytes.
5. Clique em **Jogar / Continuar**. Verifique se o menu desaparece, surgem imagens,
   toca áudio e a resposta aos botões é perceptível.

## 2. Controladores e dados

- Teste direção, botões A/B/X/Y, Start e Select no overlay touch.
- Teste um gamepad USB/Bluetooth. Remapeie um botão e confirme a associação.
- Oculte os botões touch, remapeie outro botão do gamepad, feche e reabra:
  a preferência touch deve continuar oculta.
- Abra o menu durante o jogo e volte: nenhum botão deve permanecer pressionado.
- Salve o estado, altere a situação no jogo e carregue o estado salvo.
- Teste importação de um IPS ou modpack compatível; verifique ativação/desativação.
  Use primeiro um patch inofensivo criado por você. A aplicação pode mudar
  o hash da ROM e separar os arquivos de estado.

## 3. Diagnóstico sem expor ROM

Após tentar executar, abra **☰ → Diagnóstico técnico**. Consulte:
- `frames`: número de chamadas de execução do núcleo;
- `video_callbacks`: retornos de quadros válidos;
- `audio_pairs`: pares de amostras estéreo produzidos;
- `pending_audio_samples`: quantidade ainda não consumida;
- `video_width` / `video_height`: última resolução;
- `trace_frames` / `trace_active`: coleta de memória.

Depois abra **☰ → Exportar diagnóstico JSON** e salve
`desert-strike-diagnostics.json`. O arquivo não contém bytes da ROM, conteúdo
da RAM, save states nem caminhos internos. Antes de compartilhar publicamente,
revise o nome dos mods e o modelo do dispositivo, que constam no relatório.

**Interpretação:** `frames > 0` mas `video_callbacks = 0` pode indicar falta de
renderização. `audio_pairs = 0` após jogar pode indicar ausência de áudio do
núcleo. Esses indicadores são sinais de investigação, não diagnóstico definitivo.

## 4. Engenharia reversa e limitações

No jogo, use **Iniciar rastreamento de RAM**, deixe a cena alguns instantes sem
pressionar botões, em seguida pressione um comando por vez e **Exporte o JSON**.
O rastreamento limita a 600 quadros; compare controles distintos em coletas
separadas. Para análise:

```bash
python3 scripts/analyze_wram_trace.py trace.json --button 6
```

6 representa esquerda no ID Libretro. O ranking apenas correlaciona mudanças
de RAM com botões; ele não comprova as coordenadas, colisões ou motor original.

Se ocorrer crash antes de poder abrir o menu, capture o erro de Android Logcat
e informe o modelo do dispositivo e a etapa. Não compartilhe ROMs comerciais.
