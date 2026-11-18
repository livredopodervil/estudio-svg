# RD Studio V3.14.5 — narração em lote e alerta de exportação

## Problema reproduzido
O projeto educativo EDO foi distribuído com `audio.voice_text` preenchido nas 16 cenas, mas com `audio.voice_enabled=false`, `audio.muted=true` e `volume_voz=0`. A síntese em cache pode existir mesmo quando o mixer produz silêncio; a prévia e o exportador usam a cópia normalizada com esses sinalizadores.

## Contrato da correção
- Em **Áudio → Ativar narração em todas as cenas** ou **Produção → Ativar narração em todas**, uma confirmação apresenta os motivos do silêncio e corrige simultaneamente `voice_enabled`, `muted`, `volume_voz` e `voice_volume` somente se necessário.
- Somente cenas com texto de voz ou `voice_file` são modificadas. Cenas sem voz, faixas e vídeos não mudam.
- A operação não gera nenhum áudio. Mantém o cache e os nomes de arquivos importados. Salva a alteração em projeto antes da prévia.
- A exportação pelo navegador e as rotinas de produção que incluem voz verificam essa condição ANTES de iniciar; se o usuário não confirmar, cancelam, em vez de gerar um arquivo silencioso inadvertidamente.
- A exportação de vídeo continua usando o mesmo `browser-render.mjs` e o mix FFmpeg existente; nenhum renderizador alternativo foi criado.

## Limitações
- O sucesso de gravação de áudio pelo `MediaRecorder` ainda depende do Chrome Android; a correção resolve o silêncio causado pela configuração do projeto. Testar a faixa final no dispositivo.
- Se o cache de voz tiver sido limpo, o servidor exigirá gerar novamente os áudios faltantes; a correção nunca sintetiza automaticamente.
- A ativação em lote preserva texto, motor e velocidade. Alterar a voz ou o texto altera a chave do cache.

## Validação manual
1. Abra o projeto EDO e clique **Áudio → Ativar narração em todas as cenas**.
2. Confirme 16 cenas e volume global zero. Clique em OK.
3. Aguarde a confirmação de salvamento; confira `voice_enabled=true`, `muted=false` e `volume_voz=1`.
4. Use reprodução e verifique áudio; se faltar áudio, em Produção acione **Áudio em lote** para gerar apenas arquivos que não estejam em cache.
5. Exporte pelo navegador e escute o arquivo final; compare com **Mixar áudio sem vídeo**.
6. Se não ouvir a locução após o passo 3, não repita a síntese: verifique status do cache e arquivo de mix antes de concluir que houve falha de síntese.

Rollback: utilize o `apply.py --revert` do mesmo ZIP, sem descartar outras modificações do repositório.
