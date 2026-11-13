# GSAP — compatibilidade funcional e verificação de licença

**Estado V3 Alpha 4:** o Estúdio SVG não embute, baixa, executa nem redistribui GSAP. `timeline_easing.py` implementa matematicamente interpoladores e sequenciamento de forma própria, em Python. A V3 não se apresenta como plugin GSAP nem como substituto de sua API completa.

A página oficial da licença **Standard "No Charge"** de GSAP/GreenSock (Webflow) permite muitos usos, inclusive comerciais, mas restringe determinados produtos que ajudem usuários a criar animações visuais sem código em concorrência com as capacidades de animação do Webflow. O Estúdio SVG é um editor visual de animações e vídeo; embora seu foco não seja um construtor de sites, há potencial sobreposição que precisa ser confirmada antes de distribuir GSAP no repositório.

- Licença: https://gsap.com/standard-license/
- Visão geral: https://gsap.com/docs/v3/
- Timelines: https://gsap.com/docs/v3/GSAP/Timeline/
- Instalação: https://gsap.com/docs/v3/Installation/

**Decisão:** não incorporar arquivos GSAP nem plugins até haver clareza sobre a permissão para esta modalidade de produto, obtida com o titular da licença se necessário. Não alterar avisos de terceiros nem afirmar que GSAP é MIT ou open-source permissivo. Os recursos realizados aqui não dependem de autorização de GSAP por não usarem seu código.

**Recursos locais já presentes:** `linear`, `suave`, curvas `power`, `sine`, `expo`, `back`, `bounce`, repetição finita, reversão yoyo, expansão de animações em sequência e timeline por tempo absoluto. **Não implementados:** MorphSVG, DrawSVG, MotionPath, ScrollTrigger, Draggable, Flip, física, editor de keyframes GSAP, compilação GSAP em MP4 ou runtime JavaScript GSAP.

**Publicação:** mantenha autor e créditos do Estúdio; esta funcionalidade deve entrar em branch de candidata (`release/v3-alpha4-rc1`) e não na `main` estável. Não inclua `web/vendor/` e outros artefatos de licença ainda não auditada.
