# M3-A — Suíte RD: status local e navegação (experimental)

**Base protegida:** Estúdio SVG `feat/studio-shared-scene-m2`, `6eaacb06dff74f88d34b5b92598be1f33822380b`. Site publicado validado em `8e8554f81a20...`; `update-social.yml` desativado; Pages ativo. O branch do SpatialSeed tem modificação não confirmada em `CollisionWorld.js` e oito arquivos de áudio do Estúdio estão não rastreados. Nenhum é modificado pelo M3-A.

## Contrato mínimo

- `studio_suite_m3a.py`: `snapshot()` realiza inspeções somente de leitura; `GET /api/suite/status` produz `{"schema":1,"read_only":true,"ports":...,"services":[...]}`. Não aceita URL, token, comandos ou caminhos do cliente. Não invoca `POST`, não salva arquivos nem consulta rede pública.
- Consulta a API **já existente** do RD Studio 4.4.2 em `http://127.0.0.1:8885/api/state` por servidor Python, e a prévia `http://127.0.0.1:8886/laboratorio/`. Portas configuráveis com `RD_SUITE_ADMIN_PORT` e `RD_SUITE_PREVIEW_PORT`; rejeita valores não numéricos ou fora de 1–65535. `RD_SUITE_EXPECTED_SITE_ROOT` opcional alerta quando o administrador aponta a um checkout diferente da referência.
- SpatialSeed e GIL são detectados pelas variáveis já existentes `RD_SPATIALSEED_ROOT` e `RD_GIL_ROOT`. São verificados arquivos essenciais. Status `presente` **não confirma** execução WebGL, GIL nem síntese. Uma eventual modificação de `CollisionWorld.js` é apenas anunciada, nunca corrigida automaticamente.
- UI: botão **Suíte RD** na barra existente e drawer compacto. O JS `studio-suite-m3a.mjs` exibe seis serviços com `textContent`, sem interpolação HTML; usa os botões já existentes para SpatialSeed, GIL e narração. O administrador/site abrem em outra aba porque `RD Studio 4.4.2` responde com `X-Frame-Options: DENY`; não mudar essa proteção. O projeto aberto no Studio não é descarregado ao abrir o drawer ou a aba externa.
- Segurança: nenhuma credencial do administrador é armazenada ou exposta. Não adicionar funções administrativas de escrita no M3-A. Não criar novo servidor, renderizador, mecanismo de áudio, relógio ou fluxo de publicação.

## Testar no Termux após aplicação do patch

```bash
cd "$HOME/.local/share/rd-studio/worktrees/studio-shared-scene-m2" || exit 1
python -m unittest discover -s tests -p test_studio_suite_m3a.py -v
node --test tests/test_studio_suite_m3a.mjs
python -m unittest discover -s tests -p test_workspace_v38.py -v
node --test tests/test_workspace_v38.mjs tests/test_studio_shared_scene.mjs
python -m py_compile studio_suite_m3a.py app.py
node --check web/app.js
```

Reiniciar o servidor M2 após o patch, preservando `RD_SPATIALSEED_ROOT="$HOME/SpatialSeed-0054xx"` e `RD_GIL_ROOT="$HOME/rd_studio_gil_v01/gil"`. Se o script local de inicialização estiver disponível e já configurado, reutilizá-lo. Consultar `GET http://127.0.0.1:8771/api/suite/status` e abrir `http://127.0.0.1:8771/` no Chrome do Android. O RD Studio administrativo permanece em 8885/8886, usando o clone de site verificado.

## Checklist visual

- [ ] Abrir projeto com edições ainda não salvas; abrir e fechar **Suíte RD** sem perda de edição, cena ou posição na timeline.
- [ ] Status Studio, site, SpatialSeed, GIL, RD-Audio com legendas coerentes; não inferir disponibilidade funcional a partir de arquivos encontrados.
- [ ] Abrir o administrador em outra aba sem quebrar a interface original; verificar `root` na API administrativa. Testar prévia do site.
- [ ] Ações dos botões SpatialSeed, GIL e narração reutilizam seus editores existentes.
- [ ] Em retrato móvel, nenhuma sobreposição permanente do drawer ou barra de ferramentas; testar foco de teclado e rolagem.
- [ ] Fechar servidor admin e atualizar status: mostrar indisponível sem travar editor audiovisual; reiniciar e atualizar.
- [ ] Verificar novamente os oito arquivos de áudio untracked e a modificação de `CollisionWorld.js`. Nenhum commit/push.

## Reversão

Com o patch distribuído: `git apply -R --check CAMINHO.patch && git apply -R CAMINHO.patch`, **somente se os arquivos criados pelo patch não tiverem recebido alterações posteriores**. Não remover outros trabalhos locais. O pacote de aplicação deve fazer backup externo dos arquivos rastreados antes de aplicar.

## Limitações

O painel M3-A é um diagnóstico e navegação integrada, não uma migração de assets, edição do site embutida, catálogo unificado ou sincronização de estado entre motores. Essas funções pertencem aos próximos marcos e exigem contratos e testes específicos. A política `X-Frame-Options: DENY` impede iframe administrativo, sem prejuízo da abertura segura em nova aba.
