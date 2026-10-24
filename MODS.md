# Modding experimental (IPS e BPS)

O aplicativo importa localmente a ROM original, valida o SHA-256 e aplica modificações de dados **IPS** ou **BPS**, individualmente ou por meio de um ZIP contendo `manifest.json`. Nenhum mod é executável.

## Instalar

No menu do jogo, selecione **Adicionar IPS/BPS** e escolha um patch. O formato é identificado pelo cabeçalho interno. O arquivo é salvo no armazenamento privado do aplicativo, e você pode ativá-lo ou desativá-lo na lista.

O BPS verifica o CRC32 da ROM de entrada, do resultado e do próprio patch. Um BPS que exija outra versão ou outra modificação prévia da ROM será recusado; respeite a ordem das modificações. O IPS não traz as mesmas verificações de integridade.

## ZIP de mods

Inclua na raiz do ZIP um arquivo `manifest.json`, como:

```json
{
  "name": "Meu mod",
  "target_sha256": "606abf536440173ae36466db360c7db6b474beb7a105c8a62bc74a54cbe1c38b",
  "patches": ["alteracao.ips", "mais-alteracoes.bps"]
}
```

A lista é aplicada em ordem. Cada BPS exige a ROM resultante correta. O ZIP tem limite de tamanho e número de arquivos, e somente extensões IPS/BPS são aceitas. Não envie ROM, sprites ou recursos comerciais junto ao mod.

Faça backup dos saves antes de testar modificações. Compatibilidade entre mods e saves não é garantida.
