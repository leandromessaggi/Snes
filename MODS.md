# Modding experimental (IPS)

O aplicativo carrega a ROM localmente, exige SHA-256 da versão analisada e aceita patches IPS (ou pacotes ZIP com manifest.json). Mods não são executáveis: alteram bytes da ROM antes do início da emulação.

## Modpack ZIP

Inclua manifest.json na raiz, com este formato:

```json
{
  "name": "Meu mod",
  "target_sha256": "606abf536440173ae36466db360c7db6b474beb7a105c8a62bc74a54cbe1c38b",
  "patches": ["alteracao.ips"]
}
```

Não inclua a ROM, sprites ou outros ativos protegidos por direitos de terceiros. Faça backup dos saves antes de testar mods. A compatibilidade entre mods, tamanho da ROM e saves não é garantida.
