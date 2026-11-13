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

## V2.7.3 — Regra de mídia e enquadramento

- A prancheta SVG deve ter a mesma proporção do vídeo final. Arte legada 1280 × 720 é adaptada sem mudanças de coordenadas e somente salva após aprovação explícita. Prévia e MP4 devem receber exatamente o mesmo SVG e dimensões.
- Gravações de microfone e câmera exigem gesto de usuário e permissões locais; nunca iniciar silenciosamente, nunca fazer upload remoto. Arquivos ficam em `midia/`, ignorados pelo Git.
- Videoclipes são camadas sobrepostas, sem áudio por padrão; o som precisa estar explicitamente vinculado à narração da cena. Evitar modificações no pipeline de música contínua.
- Validar o `video_clipe` em JSON, a extensão/codec do arquivo por FFprobe e o MP4 com FFmpeg; preservar a edição SVG, os projetos antigos e os testes anteriores.

## V3 experimental · separação da versão estável

- A versão estável publicada permanece na `main` (`b6f3b3e`, V2.7.4.1). Não integrar `feat/v3-espacial-alpha` nem publicar alterações sem aprovação do usuário.
- A V3 usa `spatial_scene.py` como contrato mínimo; o código do SpatialSeed **não foi copiado**. Antes de incorporar componentes reais, verificar origem, versão fixa, dependências e licenças, preservando créditos.
- Cenas `espacial` são opcionais. Todo código de importação, normalização, prévia, exportação e testes deve manter os tipos legados sem regressão.
- Script de LLM = operações tipadas validadas, sem `eval`, execução arbitrária, redes ou escrita de arquivos.
- Renderização temporal deve depender exclusivamente do projeto e do instante, não do FPS ou estado mutável acumulado.

## V3 Alpha 4 — timeline e licenças

- `timeline_easing.py` concentra as curvas, ciclos finitos e yoyo usados pela animação SVG e espacial. Não bifurcar relógios/interpoladores entre prévia e exportação.
- `alvos` e `intervalo` são expandidos por `schema.animation_dict`; a cena persistida deve ser normalizada e limitada a 32 faixas.
- GSAP não está integrado. Revisar `docs/LICENCAS_GSAP.md` antes de redistribuir qualquer arquivo GreenSock, especialmente pelas restrições a editores visuais.
- Manuais para LLMs ficam em `docs/LLM_*.md`; exemplos JSON devem passar por `schema.normalize` e regressões automatizadas antes de publicação.
