# Estúdio Player Web v1.0 — experimento integrado

Player web estático e publicador de apresentações do Estúdio SVG, destinado a integração gradual com o site rogerioduarte.org e, em fase posterior, o SpatialSeed.

**Status:** primeira implementação testada isoladamente. Nenhum push, merge ou publicação de site foi feito. O site ativo não foi modificado.

## Entrega

- `web_player/estudio-player.js` — Web Component com navegação, quadros SVG, vídeos sobrepostos, legendas, síntese de voz opcional pelo navegador, controles auto-ocultáveis e modal.
- `tools/estudio_web_publish.py` — gerador do manifesto, frames SVG, mídias e catálogo estático. Reutiliza `graphics.visualize`, `schema.normalize`, `studio_core.scene_length`.
- `tools/auditar_integracao.py` — comparação somente leitura dos repositórios locais e verificação de integridade.
- `tools/instalar_no_site.sh` — instalação em worktree separada do site; nunca edita a `main`.
- `tests/test_publicador.py` — testes de regressão de contrato, segurança, verificação de hashes, sem sobrescrita e mídia.
- `docs/` — especificação de contrato e manual de integração com os três projetos.

## Testes no pacote

```bash
python -m unittest discover -s tests -p 'test_publicador.py' -v
node --check web_player/estudio-player.js
python -m compileall -q tools/
```

## Aplicar ao Estúdio

```bash
cd "$HOME/storage/downloads/estudio_player_web_v1"
bash instalar_no_estudio.sh --check
bash instalar_no_estudio.sh --apply
```

Veja `docs/INTEGRACAO_TRES_PROJETOS.md` para gerar conteúdo e preparar uma branch do site. Tudo funciona em GitHub Pages por arquivos estáticos; a voz depende da síntese de voz do dispositivo visitante, que pode ser local ou remota.
