# RD Studio — Roteiro 0.3 e planos declarativos para agentes

Autoria do Estúdio: **Rogério Duarte**. Incremento experimental M1e, baseado na V3.14.3 (M1d), sem substituir o runtime GIL, compositor, mixador nem HTML autônomo.

## Falha corrigida

Em `web/roteiro-editor.mjs`, a V3.14.3 recebia `seek` como parâmetro de `installRoteiroEditor` e o redeclarava como constante local para o slider. O módulo não carregava, e o importador de `scene-object-editor.mjs` notificava `Identifier 'seek' has already been declared`. O nome `seekScene` passa a representar o cursor da cena; `seekSlider`, a prévia do roteiro. Teste de sintaxe obrigatório antes da instalação.

## O que já é operável

Na tela **Composição → Roteiro**, a seção **Plano de edição · clipes, transições e áudio** aceita dois formatos compatíveis com a edição automatizada:

1. `roteiro 0.3` em texto, com as diretivas temporais GIL das versões 0.1 e 0.2 e novas diretivas **na raiz** para modificações do documento;
2. um JSON `rd-studio-plan-0.3` com operações tipadas (útil para geração e revisão por agentes). Se o campo JSON estiver preenchido, ele tem prioridade sobre as diretivas de documento no texto do roteiro.

**Simular alterações** avalia o conjunto completo contra uma cópia isolada da cena e produz uma descrição das operações. **Aplicar alterações à cena** requer confirmação, só se habilita após simulação válida e recusa alterações posteriores no roteiro ou na cena. O documento atual só é modificado após a confirmação. O botão **Exportar JSON** permite salvar uma proposta, e **Importar JSON** permite abri-la e revisá-la. O recurso não executa JavaScript de terceiros, não abre URLs, não baixa mídia e não edita projetos por conta própria.

## Sintaxe da linguagem 0.3

A fonte GIL de base mantém objetos, grupos e textos; as animações continuam compiladas pelo compilador GIL 0.2. Exemplo de roteiro para uma cena que já contenha uma camada de vídeo com `id=film1` e duração de 8 segundos:

```text
roteiro 0.3 {
  marca inicio 0s
  em inicio {
    entrada titulo esquerda durante 1.1s
  }
  clipe film1 entre 0s e 8s
  clipe film1 quadro [0.5,0.5,0.8,0.6]
  clipe film1 audio volume 0.8 entrada 0.3s saida 0.5s
  transicao film1 entrada dissolver durante 0.5s
  transicao film1 saida esquerda durante 0.7s
  audio cena entrada 0.2s saida 0.3s
  audio voz volume 1 atraso 0.2s
  audio faixa 0 inicio 0.5s volume 0.6 entrada 0.3s saida 0.5s
  texto cena titulo "Título para a cena"
}
```

Todas as instruções referentes ao documento (`clipe`, `transicao`, `audio cena`, `audio voz`, `audio faixa`, `texto cena`) são permitidas somente no nível externo; não participam da compilação GIL e não são inseridas automaticamente ao pressionar **Inserir GIL**. Para aplicá-las, use **Simular** e **Aplicar**. A distinção impede efeitos colaterais durante a prévia. Emissões de `audio faixa` exigem uma faixa previamente existente; o índice começa em zero.

As transições de objetos usam os estilos `dissolver`, `esquerda`, `direita`, `zoom` nos modos `entrada` e `saida`, durações entre 0,05 e 5 s; são geradas como `motion_programs` pela mesma sintaxe GIL de movimento, sem um segundo interpolador. Respeitam os intervalos `start`/`end` dos objetos e o limite de oito programas adicionais por objeto. Não alteram o arquivo de vídeo. O áudio é sincronizado ao mesmo `start`, `end`, `offset` e fades que o mixer do projeto usa.

## Contrato de agente: operações aceitas

```json
{
  "format": "rd-studio-plan-0.3",
  "operations": [
    { "type": "clip.time", "id": "film1", "start": 0, "end": 8 },
    { "type": "clip.frame", "id": "film1", "x": 0.5, "y": 0.5, "w": 0.8, "h": 0.6 },
    { "type": "clip.audio", "id": "film1", "volume": 0.8, "fade_in": 0.3, "fade_out": 0.5 },
    { "type": "object.transition", "id": "film1", "phase": "entrada", "style": "dissolver", "duration": 0.5 },
    { "type": "object.transition", "id": "film1", "phase": "saida", "style": "esquerda", "duration": 0.7 },
    { "type": "audio.scene", "fade_in": 0.2, "fade_out": 0.3 },
    { "type": "audio.voice", "volume": 1, "delay": 0.2 },
    { "type": "audio.track", "index": 0, "start": 0.5, "volume": 0.6, "fade_in": 0.3, "fade_out": 0.5 },
    { "type": "scene.text", "field": "titulo", "text": "Título para a cena" }
  ]
}
```

Os valores de posição/dimensões são frações normalizadas da composição; tempos em segundos; áudio e velocidade não são inventados. O agente pode gerar esse JSON e o usuário importá-lo e revisar seu impacto antes de aplicar. As operações são atômicas; a presença de uma ação inválida aborta o plano inteiro sem alterar a cena. Só IDs existentes são aceitos. Não há autorização para comandos shell, URLs, sobrescrita de mídia, remoção de cenas ou execução de scripts arbitrários.

## Limites honestos

- **Clipe legado:** `video_clipe` ainda precisa de conversão explícita pela ferramenta do Estúdio para `objetos_midia`. Esta etapa não faz migração silenciosa.
- **Transição entre cenas:** não há crossfade com sobreposição de imagens e áudios de cenas distintas. A transição deste marco atua *sobre a camada selecionada*; o fade do áudio da cena suaviza cortes mas não faz sobreposição real. O bug histórico de congelamento visual 2→3 permanece em investigação.
- **Páginas animadas:** as mesmas cenas e GIL podem alimentar o HTML autônomo do Estúdio. O agente consegue propor alterações de cena e texto/animação GIL que chegarão a esse HTML, mas **não** edita DOM de páginas externas, CSS arbitrário nem publica sites. Essa evolução depende de contratos adicionais de páginas e assets.
- **Sincronismo por palavra:** não foi implementado alinhamento automático a fonemas/legendas; os parâmetros atualmente expostos são início, fim, volume, atraso e fades da cena, faixa e clipe.
- **Voz:** não usa nem instala eSpeak. Nenhum áudio é sintetizado por este módulo.
- **Permissões:** o agente entrega somente o plano, a aplicação exige aprovação humana.

## Gates para Android

1. Abrir Composição e confirmar que ferramentas de objetos e o botão Roteiro aparecem, sem erro de `seek`.
2. Selecionar clipe convertido em objeto, abrir Roteiro e clicar Exemplo seguro → Simular → Aplicar; verificar fade e volume.
3. Importar JSON com um ID inexistente; verificar recusa sem modificar a cena. Testar plano válido com enquadramento e transição.
4. Criar GIL com título arbitrário no painel esquerdo, compilar e inserir, verificando a animação no tempo local.
5. Salvar/reabrir e validar que o mesmo objeto/clipe usa posições, programas e áudio aplicados; conferir o projeto também na exportação e no HTML autônomo.
6. Conferir a passagem entre três cenas; reportar congelamentos e divergências, sem considerar resolvida a transição real.
7. Executar `python -m unittest discover -s tests` e `RD_GIL_ROOT=<diretório verificado> node --test tests/*.mjs` antes de qualquer commit. Não fazer push sem consentimento.
