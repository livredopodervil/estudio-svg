# Estúdio SVG — contrato de desenvolvimento

Autor: Rogério Duarte. Respeite licenças e créditos das dependências.

- Antes de alterar, confirme repositório, branch, HEAD, diff, testes e ambiente.
- `main` é a base canônica; trabalhe em branch/worktree isolado. Nunca sobrescreva arquivos locais de projeto, mídia, cache, backup ou credenciais.
- Modifique somente o necessário. Preserve o Ateliê SVG, suas camadas, undo/redo, salvamento e renderização existente.
- Use um dedo para edição e dois dedos para navegação na prancheta; gestos não alteram o SVG serializado.
- Teste compatibilidade dos JSONs antigos e novos, renderizador SVG e formatos 16:9 e 9:16.
- Valide no navegador mobile e, antes da integração, no Android/Termux real.
- Reporte objetivamente testes executados, hipóteses, limitações e rollback.
- Não faça push, merge, reset destrutivo nem publicação sem autorização.
- Conserve os módulos externos em `web/vendor/` fora do controle de versão até auditoria explícita de licenças.

- Na V2.7.2, animações são determinísticas e devem produzir os mesmos estados SVG na prévia e no MP4; nenhuma interpolação deve depender de timers do navegador.
- Música global contínua é opção explícita e deve preservar os arquivos de áudio e o comportamento dos JSONs antigos.
