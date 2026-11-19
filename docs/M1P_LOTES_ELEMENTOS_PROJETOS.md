# M1P — narração/legendas em lote, elementos e projetos

Checkpoint de desenvolvimento após M1O. Este patch **não faz commit nem push**.

## Escopo

1. **Áudio → Gerar todas as vozes + tempos:** síntese Edge-TTS das cenas habilitadas, criando MP3 e SRT no cache de cada cena e persistindo `cenas[].legendas.cues`. A operação só salva as marcações se o JSON original não mudou durante a síntese. Locuções gravadas/importadas não recebem tempos automaticamente; importe SRT/VTT.
2. **Áudio → Aplicar configuração de legendas a todas as cenas:** aplica aparência e efeito, nunca copia os tempos de uma cena para outra. Alterações do documento continuam sujeitas a salvar/desfazer.
3. **Cena → Elementos desta e de outras cenas:** escolhe a cena; permite editar/remover título, subtítulo, selo, fonte, imagens, vídeos, objetos de mídia e elementos SVG; objetos textuais GIL podem ter o texto alterado ou esvaziado, preservando a sintaxe, com compilação GIL antes de aplicar. Uma cena possui título de metadados e texto visual separados. Remover um deles não apaga automaticamente o outro.
4. **Projetos → Gerenciar:** arquivos JSON organizados em diretórios físicos `projetos/.pastas/<nome>/`, com IDs globalmente únicos; renomear, mover, criar pasta, mover para `projetos/.lixeira/` e restaurar. `projetos/.arquivados` continua funcional. Mídias compartilhadas, áudios, caches e renders não são apagados.

## Limitações

- Diretórios: **um nível**, nomes ASCII `[A-Za-z0-9_-]` até 60 caracteres.
- A lixeira é recuperável pela interface, não existe exclusão permanente automática.
- Os elementos SVG são editados individualmente; para desenhos SVG complexos, o editor vetorial continua disponível.
- A edição GIL textual atua sobre atributos `text` de objetos declarados explicitamente. Textos gerados por expressões ou recursos sem `text` local continuam exigindo ferramentas específicas.
- TTS em lote **pode regenerar locuções em cache**, para criar os SRTs na mesma síntese. Não substituir arquivos de voz gravados.
- Não foram executadas sínteses Edge-TTS reais nem testes de ponta a ponta no Android neste ambiente.

## Teste no Android/Termux

```bash
cd "$HOME/estudio_svg_v3_git" || exit 1
RD_GIL_ROOT="$HOME/rd_studio_gil_v01/gil" bash iniciar.sh
```

Confira a **porta anunciada pelo processo**. Se for 8771, abra `http://127.0.0.1:8771/` no mesmo Android. Verifique GET `/studio-m1p.mjs` retornando HTTP 200.

### Critérios de aceitação

1. Importe ou abra o ECG vertical com 10 cenas, configure o modo karaokê na primeira cena e aplique o mesmo estilo a todas. Os tempos próprios das cenas devem permanecer distintos.
2. Gere narrativas + tempos em lote. Acompanhe o progresso; salve/reabra o projeto e confira `legendas.cues` diferentes em cada cena.
3. Abra o inspector na cena que apresenta títulos duplicados e remova **apenas** o `<text>` SVG ou título da cena. Salve, reabra e confirme que a narração e os outros objetos continuam intactos.
4. Em Projetos, crie a pasta `ECG`, mova um projeto, renomeie-o, feche/reabra e verifique que a pasta é real em `projetos/.pastas/ECG/`.
5. Envie esse projeto à lixeira, restaure e abra. Confirme que imagens e vozes continuam acessíveis.
6. Rode os testes afetados: `python -B tests/test_m1p_manager.py -v` e `node --test tests/test_m1p_ui.mjs`.
7. Teste exportação de vídeo e legendas: esta mudança **não valida nem corrige** os problemas de exportação anteriores.

## Reversão

```bash
cd "$HOME/estudio_svg_v3_git"
python "$HOME/storage/downloads/rd_studio_m1p_aplicar.py" rollback --repo "$PWD"
```

A reversão atua somente sobre arquivos de código modificados pelo instalador e recusa arquivos editados depois. **Não move de volta projetos transferidos pela interface**; primeiro restaure os projetos de `projetos/.pastas`/lixeira manualmente ou através da própria interface enquanto M1P estiver ativo.

## Continuidade

Não inferir o HEAD ou o estado local a partir de conversas. Verificar Git antes de qualquer commit; manter branch e backups. Os testes M1j e regressão de exportação anteriores continuam pendentes até execução específica. Não confundir `SKIP` com aprovação.
