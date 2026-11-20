# RD Studio M2.3 — Preparação WebGL e Piper local

## Referências de base

- Branch prevista: `feat/studio-shared-scene-m2`, HEAD `a47d2c8` (confirmar no worktree).
- Renderização: 3 módulos fornecidos no diagnóstico do usuário, com SHA-256 no manifesto.
- UI/API: base M2.2 previamente enviada, identificada pelos hashes do manifesto.
- Não tocar em `AGENTS.md`, `main`, clone SpatialSeed, GIL, wrapper Piper ou modelos.

## Diagnóstico

O texto `Preparando cena 2/2...` é emitido antes de `await prepareEntry(...)` em
`web/offline-render.mjs`. Esse preparador começa solicitando `/api/preview`, inclusive
para a cena WebGL com SVG sobreposto. A chamada HTTP e a leitura do corpo não tinham
um prazo abrangente; ausência de resposta pode produzir espera indefinida. A M2.3
acrescenta prazo/cancelamento e reporta a fase. Isso identifica a causa concreta
no dispositivo; **não prova que o HTTP é sempre o gargalo**.

A demo anterior usa `spatialseed_viewport.source=""` na cena 2. O canvas pode
mostrar uma sessão prévia não salva. A exportação offline passa a recusar
explicitamente o documento vazio antes de abrir sessão, sem inventar um estado 3D.

## Voz Piper

`POST /api/tts/piper` aceita exclusivamente texto (até 3000 caracteres), vozes
`faber`/`edresson`, `length_scale` 0.70–1.30 e `sentence_silence` 0–1.
Lê modelos de `~/piper_tts`, usa o wrapper `piper` do PATH, produz WAV mono PCM
16-bit a 22050/16000 Hz, valida o WAV e o guarda em `MEDIA` com nome estável por
hash (inclui parâmetros e metadados do modelo).

O botão em Áudio gera e vincula a locução em `cenas[i].audio.voice_file`, ativando
a voz. Usa a infraestrutura de mixagem/preview existente. Não usa eSpeak para
gerar som (a biblioteca espeak-ng interna do Piper é apenas fonemização).

## Limitações

- A captura WebGL por MediaStream ainda não assegura estado determinístico por quadro.
- A M2.3 não oferece alinhamento automático de palavras para legendas Piper.
- A exportação offline ainda precisa de documento SpatialSeed salvo; a demo anterior
  contém fonte vazia.
- Medir tempo HTTP/quadros e inspecionar o MP4 em Android antes de commit/push.
