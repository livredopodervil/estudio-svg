# RD Suite M3-A — correção do botão no layout unificado (NAV-1)

**Causa reproduzida a partir do CSS do dispositivo:** `studio-layout-v1.css` oculta `.rdStudioUnified .workspaceTools` com `display:none!important`. O primeiro M3-A adicionava `#openSuiteM3A` dentro dessa barra oculta. A existência do botão no HTML e `GET /api/suite/status` não verificava a visibilidade.

**Correção:** `web/studio-suite-m3a.mjs` localiza `.rdStudioUnified .rdComposeNav` e move (sem clonar) `#openSuiteM3A` para o início dessa navegação. Mantém o mesmo ID, eventos, `aria-controls`, resposta da API e drawer já existentes. Se a navegação for criada depois do módulo, um `MutationObserver` a espera até localizá-la. Se o layout unificado não estiver ativo, não interfere na barra legada.

**Limitações:** esta correção não muda o texto antigo `M1b experimental · base V3.13.4`, nem reativa outras barras ocultas. A captura fornecida mostra sobreposição clara na lateral durante a localização do navegador, não constitui evidência de que haja um componente do projeto nessa faixa.

**Pré-requisitos:** patch M3-A status-readonly presente; worktree de `feat/studio-shared-scene-m2` no HEAD `6eaacb06`. Preservar 8 arquivos de áudio não rastreados, `AGENTS.md`, o checkout SpatialSeed com edição em `CollisionWorld.js`, o site publicado e o RD Studio administrativo. Nenhuma publicação ou commit.

**Teste automatizado:** `node --test tests/test_studio_suite_m3a_nav.mjs tests/test_studio_suite_m3a.mjs` e `node --check web/studio-suite-m3a.mjs`.

**Aceitação Android:** abrir `http://127.0.0.1:8771/?m3a_nav=1` com servidor reiniciado; botão `Suíte RD` deve aparecer no início da barra horizontal de composição junto a `Cenas`/`Biblioteca`/`Roteiro`; clicar deve revelar seis serviços, permitir fechar e manter o projeto ativo. Se não aparecer, verificar presença de `.rdComposeNav` e classes do layout. Não usar reinicializações indiscriminadas.

**Reversão:** controlador `rd-suite-package.py reverter` reconhece exatamente os hashes posteriores e não sobrescreve alterações feitas depois. O módulo original volta à barra oculta e o comportamento M3-A anterior é restaurado; registrar a reversão.
