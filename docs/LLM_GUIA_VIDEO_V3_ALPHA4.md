# Estúdio SVG — manual para LLMs (V3 Alpha 4)

**Autor do projeto:** Rogério Duarte. **Estado:** V3 experimental; a versão estável é a V2.7.4.1 na branch `main`. Este arquivo orienta a produção de **JSON**, não de código executável. JSON inválido não deve ser executado ou salvo sem passar pelo normalizador `schema.normalize` do projeto.

## 1. Objeto do projeto e mídias

```json
{
  "versao": "3.0.0-alpha.4",
  "titulo": "Roteiro audiovisual",
  "video": {"width": 720, "height": 1280, "fps": 24, "draw_fps": 6, "background": "#121D25"},
  "motor_voz": "edge-tts", "voz": "pt-BR-AntonioNeural",
  "trilha": "", "trilha_continua": false,
  "cenas": []
}
```

`cenas` precisa ter **de 1 a 150** elementos; cada uma tem `tipo`, `duracao` (segundos), `titulo`, paleta em `cores`, `audio` e eventualmente `animacoes`, `imagem`, `video_clipe` e `espacial`. Formatos de vídeo válidos: 720 × 1280 (9:16), 1280 × 720 (16:9), quadrado e formatos personalizados pares entre 320 e 1920; `fps` 24, 25 ou 30. `draw_fps` é a frequência de redesenho SVG, limitada aos valores aceitos no esquema (até 24). A duração pode ser estendida pelo motor de voz se `encaixe_voz` for `estender`.

**Tipos de cena implementados:** `globo`, `linha`, `barras`, `numero`, `cartoes`, `arvore`, `svg`, `foto` e `espacial`. Os gráficos dos tipos históricos não são editáveis como objetos SVG individuais até convertidos para `svg`; animá-los normalmente por `__conteudo__`.

**Imagem de prancha:** `imagem.arquivo` é o nome simples do arquivo em `midia/` importado pelo aplicativo. O recorte `crop` usa `[x,y,w,h]` entre 0 e 1, relativo à imagem original. `modo` pode ser `quadro` ou `fundo`; `x,y` são o centro relativo do quadro e `w,h` seu tamanho relativo na cena. Não use caminho absoluto ou URL remota. O ZIP importável contém `projetos/<nome>.json` e `midia/<arquivo>`.

**Áudio:** `audio.voice_enabled` ativa locução de `voice_text`; `voice_file` é uma gravação associada; `music_file` é música específica da cena; `tracks` são faixas extras. Nunca apague `voice_text` para remover `voice_file`. Música contínua em `trilha` permanece no relógio global; `audio.muted` silencia a cena quando explicitamente requerido. Para compartilhar, use exportação MP4 ou HTML autônomo; sons dependem do gesto de reprodução permitido pelo navegador.

## 2. Design visual e ritmo

- **9:16:** reserve aproximadamente 8% de altura superior para margem da interface, 15% para título, 50–55% para mensagem visual central, 15–20% para legenda/dado, e 8–10% inferior para zona segura. As proporções são orientações, não campos do esquema.
- **16:9:** hierarquia lado a lado: narrativa e grande número à esquerda, imagem ou gráfico à direita; evite apenas ampliar a cena vertical.
- Uma cena deve defender **uma ideia principal**, com um título curto (até ~8 palavras), um dado dominante e no máximo 3 itens legíveis. Dados econômicos ou científicos incluem ano, unidade, denominador e fonte; diferencie projeção, execução e comparação.
- Contraste forte entre texto e fundo; contraste mínimo recomendado de 4,5:1 para corpo de texto e tamanho compatível com celular. Use o mesmo conjunto de cores por vídeo e reserve uma cor de destaque para a informação nova.
- Nunca posicione texto sobre o recorte sem margem/fundo suficientemente contrastante. Não faça o foco visual atravessar bordas do quadro. Use entrada de 10–25% da cena, permanência estável e saída breve; movimentos devem facilitar leitura.
- Evite looping excessivo em textos longos; com movimento repetido, prefira os objetos decorativos e mantenha títulos estáveis. Narração deve descrever os fatos, não ler literalmente cada palavra da tela.

## 3. Animações 2D determinísticas (implementadas)

Uma animação tem `alvo` (ID SVG ou um alvo especial: `__titulo__`, `__subtitulo__`, `__conteudo__`, `__imagem__`), `tipo` (`translacao`, `rotacao`, `escala`, `fade`), `inicio` e `fim` como fração **0 a 1 da duração da cena**, valores `de`/`ate` ou coordenadas `de_x`, `de_y`, `ate_x`, `ate_y` e um `easing`.

```json
{"alvo":"__titulo__", "tipo":"fade", "inicio":0, "fim":0.25,
 "de":0, "ate":1, "easing":"power2.out", "repeticoes":0, "yoyo":false}
```

**Easings aceitos:** `linear`, `suave`, `power1.in`, `power1.out`, `power1.inOut`, `power2.in`, `power2.out`, `power2.inOut`, `power3.inOut`, `sine.in`, `sine.out`, `sine.inOut`, `expo.out`, `back.out` e `bounce.out`. São interpolações **implementadas pelo Estúdio**; os nomes evocam estilos comuns de animação, mas o aplicativo **não executa GSAP** e não oferece compatibilidade universal com sua API. `back.out` pode ultrapassar brevemente a posição final.

`repeticoes` de 0 a 20 indica repetições *além da primeira passagem*; `yoyo:true` inverte a direção nos ciclos alternados. Os ciclos cabem integralmente no intervalo `[inicio,fim]`. Portanto, `repeticoes:1,yoyo:true` termina no valor de início. Para uma animação terminar no valor final, use número par de repetições com `yoyo:true` ou encerre com outra faixa.

**Sequenciamento de vários alvos (stagger)**: use `alvos` e `intervalo` em vez de `alvo` (máximo 16 alvos por faixa e 32 faixas expandidas por cena). O servidor expande em faixas individuais, deslocando `inicio` e `fim` para cada alvo pela fração `intervalo`. Os tempos que ultrapassam o fim da cena são limitados a 1. Se cada texto tiver seu próprio `id` SVG, é possível fazê-los entrar em sequência:

```json
{
  "alvos": ["linha_1", "linha_2", "linha_3"],
  "intervalo": 0.12, "tipo": "translacao", "inicio": 0, "fim": 0.22,
  "de_x": -100, "de_y": 0, "ate_x": 0, "ate_y": 0,
  "easing": "back.out"
}
```

O motor aplica as transformações a partir do **tempo absoluto**, não por um timer; prévia, apresentação HTML e quadros do MP4 compartilham o mesmo SVG calculado.

## 4. Cena espacial (experimental)

A cena `espacial` aceita até 32 objetos: `cubo`, `esfera`, `piramide`, `cilindro`, `cone`, `grupo`. Campos usuais: `id`, `tipo`, `cor`, `posicao:[x,y,z]`, `rotacao:[x,y,z]`, `escala`, `pai` e `visivel`. `grupo` permite hierarquia sem geometria visível. A câmera aceita `azimute`, `elevacao`, `distancia` e `alvo:[x,y,z]`.

Em `espacial.animacoes`, os valores de `alvo` são IDs de sólidos ou `__camera__`, e as propriedades: `rotacao_x/y/z`, `posicao_x/y/z`, `escala`, e, para câmera, `azimute`, `elevacao`, `distancia`. Seus valores são absolutos. Compartilham `inicio`, `fim`, `de`, `ate`, `easing`, `repeticoes` e `yoyo` das faixas 2D. Não há WebGL, PBR, física ou código do SpatialSeed nesta versão: a projeção é SVG gerada pelo Python.

## 5. Workflow de geração por LLM

1. Peça tema, público, duração, orientação, dados com fontes e tom. Não invente estatísticas ou direitos de uso de mídia.
2. Crie cenas com uma mensagem e um quadro principal por vez. Distribua duração pelo texto efetivo da locução (aproximadamente 2–3 palavras por segundo, conforme voz).
3. Planeje movimento como função de `inicio/fim`, sem coordenadas fora do quadro. Texto legível tende a precisar de pausas de pelo menos 2 s.
4. Gere **JSON puro**, sem comentários, sem `NaN`, sem caminhos de sistema e sem funções JavaScript.
5. Valide via editor (`POST /api/project/validate`) ou `python -c 'import json,schema;schema.normalize(json.load(open("projeto.json")))'` no diretório do projeto.
6. Importe todos os assets no editor, confira as imagens, teste na proporção final e compare quadro inicial/intermediário/final do MP4.

Veja `examples/timeline_v3_alpha4.json` e `docs/LLM_PROMPT_MESTRE_V3_ALPHA4.md`.
