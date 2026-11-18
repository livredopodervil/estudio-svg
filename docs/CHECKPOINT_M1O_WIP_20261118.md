# Checkpoint M1O — 18/11/2026

## Objetivo

Preservar no GitHub o estado real do Estúdio SVG,
incluindo M1L, M1M, M1N e M1O.

A publicação é um checkpoint experimental, não um release validado.

## Testes e pendências conhecidas

- 149 testes Python executados anteriormente: OK, 2 ignorados.
- Regressão JavaScript em tests/test_browser_render_v312.mjs.
- A publicação deste checkpoint foi autorizada sem bloquear por testes.
- A exportação M1O ainda requer validação completa no Android.
- Confirmar duração do MP4, timestamps, áudio e FPS constante.
- Confirmar retomada após interrupção da renderização.
- Auditoria de segurança M1j ainda possui pendências.

## Processo de continuidade

Ler AGENTS.md e a documentação versionada.
Confirmar branch, HEAD, remoto e modificações locais.
Testar visualmente no Android antes de novos commits.
Não usar reset, clean ou push forçado.
Preservar os backups remotos.
