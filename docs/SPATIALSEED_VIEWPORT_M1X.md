# M1X — viewport SpatialSeed WebGL dentro do Estúdio SVG

**Estado:** experimental, ainda não validado visualmente no Android. Base: `feat/studio-interface-m1b` @ `1cb222363ddc62f9096b06771c828081cd72f6e8`, com alterações locais preservadas.

## Contrato implementado

A cena pode conter `spatialseed_viewport={enabled,source,camera_keys}`. `source` é o documento `.spatialseed` JSON original (até 900 kB), não executado como JavaScript pelo servidor. A câmera usa poses `{position,quaternion,focusDistance,fov,near,far}` e a timeline em segundos relativos à cena; `smoothstep`, `linear` e `hold` são aceitos. O aspect ratio vem do projeto de vídeo. Persistência ocorre em `schema.normalize` e não altera cenas legadas.

O viewport `#ssViewportHost` fica no `#stageShell`, sobre o SVG, usa uma única instância do aplicativo SpatialSeed main no mesmo origin, já exposta pelo servidor M1W. Interações nativas no canvas `#world` modificam a câmera do renderer; `viewer.camera.snapshot` captura o estado; `viewer.camera.restore` aplica os quadros amostrados durante navegação e reprodução. Alternar de cena recarrega a instância para não reutilizar geometria de outro documento. O editor avançado M1W permanece separado e sem modificações.

## Limites explícitos

A exportação MP4/HTML/browser/offline está bloqueada para cenas com WebGL habilitado, para evitar salvar vídeos incorretos. Ainda falta interface de captura nativa do **mesmo frame** na saída final, sincronização temporal absoluta das animações de objetos e persistência automática das modificações do documento espacial feitas no painel avançado. O usuário pode usar o botão de salvamento do SpatialSeed e reimportar o `.spatialseed` no projeto. **Não há equivalência comprovada com o render especializado do urânio.**

## Validação Android

Com `RD_GIL_ROOT` e `RD_SPATIALSEED_ROOT` apontando checkouts reais, iniciar `bash iniciar.sh`, abrir `http://127.0.0.1:8771/`, ativar WebGL na cena selecionada; confirmar viewport, câmera por gesto, importação de `.spatialseed`, criação de dois keyframes em tempos diferentes, scrubbing e interpolação, salvamento e reabertura. Verificar também que uma cena SVG comum não mudou e que tentativa de exportar cena WebGL retorna erro claro sem arquivo silenciosamente errado.

Testes: `python -m unittest discover -s tests -p 'test_studio_spatialseed_viewport.py' -v`; `node --test tests/test_studio_spatialseed_camera.mjs`; `git diff --check`. Não autoriza commit ou publicação.
