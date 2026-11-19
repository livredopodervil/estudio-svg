# Continuidade verificável — Estúdio SVG / RD Studio / GIL / SpatialSeed

**Checkpoint registrado em 18/11/2026.** Este arquivo preserva decisões e resultados
comunicados, mas não substitui a inspeção do Git e dos serviços em execução.
Se o HEAD avançar, registrar novo checkpoint sem apagar este histórico.

## 1. Objetivo e fronteiras

Workspace único no Android/Termux para projeto audiovisual: viewport,
ferramentas imediatas, hierarquia, inspector, timeline, catálogo, roteiro,
console/assistente, áudio, composição 2D/3D e publicação.
O Estúdio SVG é autoridade dos documentos audiovisuais e exportação;
GIL é autoridade da fonte procedural/timeline; SpatialSeed é motor 3D,
física/interatividade; RD Studio orquestra. Integrar por contratos/adapters,
sem reimplementações concorrentes nem repositórios fundidos incidentalmente.

## 2. Checkpoint Git CONFIRMADO PELO TERMINAL DO USUÁRIO

- Checkout: `~/estudio_svg_v3_git` (confirmar `pwd -P`).
- Branch: `feat/studio-interface-m1b`.
- Commit local e remoto: `fb3d580` (`feat(studio): consolidate M1 interface and incremental console`).
- Remoto: `git@github.com:livredopodervil/estudio-svg.git`.
- Backup ANTERIOR: `backup/studio-before-m1k-20261118T123108Z-01b5761d`.
- Backup POSTERIOR: `backup/studio-after-m1k-20261118T123108Z-fb3d580f`.
- `main` preservada, sem merge nem publicação do site.
- Não versionados ao final do push: `docs/CONSOLE_M1I.md` e
  `standalone_html.py.before-v34-browservoice.bak.sha256`. **Preservar ambos**;
  não executar `git clean` nem adicioná-los indiscriminadamente.

## 3. Histórico recente e artefatos

- M1h: ajustes localizados de botões do catálogo e encerramento do servidor.
- M1i: console incremental em torno de operações de cena e planos JSON;
  consultar código atual antes de inferir comandos suportados.
- M1j: auditoria heurística de segurança em Estúdio SVG, RD Studio e GIL;
  alertas `high`/`review` ainda exigem análise dos achados individuais.
- M1k: laboratório GIL importado no Studio; `arbitrary.telemetry` foi
  incompatível na prévia nativa, removido da variante compatível.
- Projeto de demonstração `Arcabouço Fiscal / Janones x Jones Manoel V3`:
  8 cenas, 2 composições GIL, uma prancha SVG, textos de narração;
  campo `velocidade_voz: "+0%"` após corrigir erro Edge-TTS.
  O script de commit selecionou `examples/arcabouco-fiscal-rebote-2026-v3.zip`;
  verificar o arquivo no checkout. A narração sintetizada e a exportação
  MP4 ainda precisam de validação real no Android.
- Testes relatados durante preparação: 149 Python, `OK (skipped=2)`;
  amostra Node anterior: 7 aprovados, 6 ignorados e nenhum falho.
  Isso **não** significa que os testes ignorados foram aprovados.
- Erros do processo anterior: import Node para `web/gil-runtime/src/model.mjs`
  sem vínculo local; etapa `git diff --cached --check` bloqueada por espaço
  na linha 52; retry não idempotente bloqueado porque stage já existia.
  A recuperação inspecionou a seleção do índice e concluiu commit e push.

## 4. Contrato obrigatório para a próxima conversa

1. Antes de editar: conferir repositório, branch, HEAD, `git status --short`,
   `git diff`, `git diff --cached`, remotos, scripts de inicialização e testes.
2. Consultar este documento e `AGENTS.md` antes de propor um patch.
3. Não pressupor que M1i/M1k, voz, console ou novas integrações estejam
   plenamente funcionais apenas pelo commit. Testar o comportamento real.
4. Preservar todas as alterações locais, histórico e autoria; patches pequenos
   e reversíveis; não `reset`, `clean`, merge, push ou publicação sem autorização.
5. Manter a GIL fora do repositório: normalmente
   `~/rd_studio_gil_v01/gil`; verifique a pasta. Para o servidor, usar
   `RD_GIL_ROOT` quando requerido. Para testes Node de imports relativos,
   vínculo `web/gil-runtime` **temporário** e removido depois, nunca staged.
6. Tratar testes `SKIP` como cobertura pendente, documentando a condição
   exata. Não trocar Python por Node: Node testa módulos JavaScript;
   Python permanece responsável pelo serviço audiovisual.
7. Não gerar narrações eSpeak. Preservar narração Edge-TTS ou deixar
   ausência de voz explícita. Validar áudio na prévia e no MP4.
8. Criar documentação de decisões em `AGENTS.md` e `docs/`, atualizar este
   registro nos checkpoints, sem arquivar credenciais ou dados privados.
9. Android é critério de aceite visual; apresentar comando de inicialização
   e URL somente após verificar a porta real no script/terminal.
10. Separar preparação, teste visual, commit e push. Não forçar publicação
    de trabalho não revisado. Manter `main` independente da branch experimental.

## 5. Comandos de inspeção e teste visual no Android

```bash
cd "$HOME/estudio_svg_v3_git" || exit 1
pwd -P
git status --short
git branch --show-current
git log -1 --oneline
git remote -v
sed -n '1,100p' iniciar.sh
ls -l "$HOME/rd_studio_gil_v01/gil/src/model.mjs"
export RD_GIL_ROOT="$HOME/rd_studio_gil_v01/gil"
bash iniciar.sh
```

O `iniciar.sh` inspecionado na auditoria anterior invocava
`python app.py servir --port 8771`. **Confirmar o script atual**. Se continuar
usando 8771, abrir `http://127.0.0.1:8771/` no navegador do *mesmo* Android;
não inventar endereços de rede externos. Testar visualmente antes de tocar no Git.

Critérios de aceite: ferramentas visíveis sem sobreposição em tela estreita,
seleção e edição no viewport, catálogo/console, timeline, importação do ZIP,
oito cenas, duas animações GIL, prancha sem cortes de texto, narração Edge-TTS,
sincronização áudio-vídeo, exportação MP4 e reprodução no aparelho.
Registrar falha e captura ou traceback, sem presumir resultados.

## 6. Próximas etapas (PLANEJADAS, NÃO IMPLEMENTADAS)

- Validar visualmente o checkpoint `fb3d580` no Android.
- Inspecionar a razão dos `SKIP` JS, a segurança M1j e a documentação
  `docs/CONSOLE_M1I.md` não versionada, sem apagar arquivos.
- Tornar edição de objetos/faixas GIL acessível diretamente no Studio
  via contratos tipados, prévia, undo/redo e única autoridade do documento.
- Evoluir integração com SpatialSeed através de adaptadores e testes.
- Em cada novo avanço, atualizar este arquivo e documentar hash, testes,
  pendências, aceitação humana e rollback. Commit/push somente autorizados.

## 7. Verificação no começo de novas conversas

Leia primeiro `AGENTS.md` e este arquivo. Peça somente o estado local
estritamente necessário (sem repetir informações já fornecidas), por exemplo:

```bash
cd "$HOME/estudio_svg_v3_git" && \
printf 'BRANCH=' && git branch --show-current && \
printf 'HEAD=' && git rev-parse HEAD && \
git status --short && \
git log -3 --oneline
```

Nenhum código, teste, backup ou serviço deve ser declarado validado se não
foi de fato verificado na versão concreta em análise.

<!-- studio-m1m-continuity-note-v1 -->
## Atualização 18/11/2026 — M1L/M1M: observar antes de publicar

- Pedido confirmado: toda versão deve vir com comando completo de servidor, URL testável no próprio Android e checklist de revisão visual; registrar em `AGENTS.md`.
- M1L: catálogo em famílias com variações nos parâmetros, legendas estimadas. Usuário informou que as legendas **não apareciam** apesar de habilitadas.
- M1M: foi identificada ausência de `/subtitle-frame.mjs` na allowlist HTTP. Primeiro instalador bloqueou em `app.py:644`; foi fornecido M1M v2, mas sua instalação e a efetiva exibição/sincronização das legendas ainda **não estão confirmadas** no Android.
- Sincronização objetiva: preferir timestamps Edge-TTS capturados junto à síntese; aceitar importação SRT/VTT/JSON conforme módulo instalado. Medir quadros 16:9 e 9:16, áudio e exportação pelo navegador.
- Serviço inspecionado no snapshot: `cd "$HOME/estudio_svg_v3_git" && RD_GIL_ROOT="$HOME/rd_studio_gil_v01/gil" bash iniciar.sh`; verificar se a porta continua 8771, então abrir `http://127.0.0.1:8771/` no mesmo Android.
- Próximo checkpoint somente após revisão visual, testes pertinentes e autorização explícita de commit/push.
<!-- /studio-m1m-continuity-note-v1 -->

## M1V — SpatialSeed para GIL nativa
Integração experimental sem MP4 intermediário para novas importações; base 1cb2223. Ver docs/SPATIALSEED_GIL_NATIVA_M1V.md. Validação Android pendente; não publicar.
