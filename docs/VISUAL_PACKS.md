# Pacotes visuais ROM2Native v0.2

A v0.2 aceita imagens customizadas do helicóptero no motor Android/C++.
O visual pode ser desenhado manualmente ou criado por IA, com aprovação
humana. Isso ainda NÃO reconstrói o mapa ou o motor real de Desert Strike.

## Requisitos

- Um PNG RGBA de 8 bits, sem entrelaçamento, com fundo transparente.
- Dimensões de 1x1 até 128x128; recomendado 64x64 ou 96x96.
- Um único quadro centralizado com a perspectiva superior.
- Imagens RGB com fundo opaco precisam de remoção de fundo antes de empacotar.
- O pacote contém somente manifest.json e helicopter.png e NÃO contém a ROM.
- Atlas de múltiplos ângulos/animações ainda não foram integrados à v0.2.

## Preparar pacote usando a ROM original

No diretório raiz do repositório:

    python3 -m rom2native.visual_pack --rom "Desert Strike - Return to the Gulf (U).zip" --sprite helicopter_cgi_rgba.png --out helicopter_visual.zip

A ferramenta inspeciona o PNG, valida os CRCs e as dimensões, e associa
o SHA-256 da imagem e da ROM ao manifesto. Só aceita sprites de até 128
pixels de lado, e no máximo 512 KiB.

## Importar no aplicativo Android nativo

1. Instale o APK da v0.2 ROM2NativeAI.
2. Em Importar minha ROM SNES, escolha sua cópia original.
3. Em Importar visual CGI (ZIP), selecione helicopter_visual.zip.
4. O motor C++ desenha a imagem em vez do helicóptero provisório.
5. Ao reabrir o app, o pacote é revalidado e reaplicado automaticamente.

O aplicativo rejeita pacotes com ROM incompatível, hash errado, arquivo
inesperado, imagem inválida ou dimensões diferentes do manifesto.

## Modo de desenvolvimento e limites

Um sprite procedural de teste (não gerado por IA nem extraído da ROM)
serve para testar o fluxo de importação e transparência.

A IA de imagem-para-imagem é executada separadamente no ComfyUI; não
é executada no Android. Um modelo e workflow do usuário são necessários.
Os mapas, sons, missões e física originais não foram reconstruídos.
