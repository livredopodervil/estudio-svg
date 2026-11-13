# Contrato público `studio.web-player/v1`

O manifesto é um artefato estático gerado pelo Estúdio. Não pode conter scripts executáveis. `manifest.json` existe ao lado de `index.html`, `frames/` e `assets/` da publicação.

```json
{
  "schema": "studio.web-player/v1",
  "title": "Exemplo",
  "video": {"width": 720, "height": 1280},
  "source": {
    "projectVersion": "3.0.0-alpha.4",
    "projectSha256": "...",
    "estudio": {"repository": "git@github.com:livredopodervil/estudio-svg.git", "commit": null, "tracked_changes": true},
    "spatialseed": {"repository": "https://github.com/livredopodervil/SpatialSeed", "revision": null, "integration": "pre-rendered-svg-only"}
  },
  "scenes": [{
    "id": "s1", "title": "Título", "duration": 5,
    "fps": 6, "frames": ["frames/000-00000.svg"],
    "voiceText": "Texto da narração.", "voiceEnabled": true, "lang": "pt-BR",
    "clip": {}
  }],
  "resources": {"frames/000-00000.svg": {"sha256": "...", "bytes": 1000}}
}
```

Os valores de hash acima são demonstrativos. Os arquivos gerados pelo publicador contêm hashes reais. A lista `frames` contém amostras temporais calculadas a partir da cena por `graphics.visualize`; o índice `floor(t*fps)` seleciona o quadro. `duration` é expresso em segundos. Um clipe opcional tem `file`, `x`, `y`, `w`, `h`, `fit`, `opacity`, `start` e `loop`. As coordenadas são normalizadas sobre a área de vídeo.

**Compatibilidade:** contrato incompatível deve resultar em erro visível, não em tentativa de executar JS. Não interpretar `project.json` diretamente no navegador. Um atualizador futuro deverá aceitar `v1` explicitamente ou migrar publicações com ferramenta independente e testes.

**Integridade:** `sha256` e `bytes` descrevem cada recurso individual. O comando `verify` confere os arquivos publicados. O manifesto e o catálogo devem ser distribuídos via commits Git revisados; os hashes não substituem a segurança do transporte HTTPS e do repositório.

**Limite de tamanho:** no máximo 3600 quadros por publicação; cada clipe de origem/saída até 450 MB. Reduza `draw_fps` para otimizar armazenamento. O player estático pode usar cache do navegador; não inclui service worker para não conflitar com o do SpatialSeed ou do site.
