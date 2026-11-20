# RD Studio AUD-U3 — Perfis declarativos de interpretação

## Objetivo

Manter **um único roteiro RD-Audio** no projeto. Separar personagem, intenção
(dramaturgia), voz, parâmetros acústicos e processamento externo, sem outra
interface ou outro mixer.

## Sintaxe

O roteiro existente (`@personagem`, `@cena`, linhas com cinco colunas)
permanece suportado. Novas definições são incorporadas **no mesmo texto**:

```text
@processador radio {"ffmpeg":["highpass=f=75","acompressor=threshold=-18dB:ratio=2.5:attack=15:release=150"]}
@perfil investigativo {"ritmo":0.95,"ganho":1,"pausa":0.35,"tom":-3,"processador":"radio"}
@personagem narrador edge:pt-BR-AntonioNeural perfil=investigativo
@cena 1
@fala 00:00 [personagem=narrador] [estilo=investigativo] Vamos compreender a dívida pública.
```

Usando o formato antigo, o terceiro campo pode ser qualquer perfil definido:

`00:10 | narrador | investigativo | ritmo=0.91,ganho=1 | Os juros influenciam o orçamento.`

Perfil básico aceito: `ritmo`, `ganho`, `pausa`, `tom`, `volume` e `processador`.
`voz` pode constar no perfil para um personagem sem voz explícita. Voz configurada
no personagem não é silenciosamente substituída pela emoção. A fala pode
solicitar `voz=<identificador>` como substituição explícita.

O `@processador` aceita lista de filtros FFmpeg com nomes permitidos:
`highpass`, `lowpass`, `acompressor`, `alimiter`, `agate`, `equalizer`,
`loudnorm`, `volume`, `atempo`, `afftdn`, `deesser`. Seus parâmetros são
passados ao FFmpeg como argumentos, **sem interpretador de comandos**. Não
são permitidos filtros que leem arquivos arbitrários ou comandos shell.
A implementação atual não aceita outras ferramentas externas além do FFmpeg;
o módulo está separado para extensão futura com executores registrados.

`ritmo` mantém o sentido legado: menor valor = fala mais rápida no Piper; a
camada Edge converte esse valor ao formato percentual correspondente.
Emoções nomeadas são metadados e aproximações acústicas, **não estilos
neurais nativos**. Não se garante que um perfil soe emocionalmente convincente.

## Testar amostras

Na aba **Áudio**, abra **Perfis de interpretação, personagens e amostras**.
Use **Adicionar/atualizar perfil**, edite o roteiro e valide. Para ouvir uma
fala sem vincular áudio ao projeto, informe o número da linha física do
roteiro (0 = primeira fala) e toque em **Gerar amostra desta fala**. A
amostra é sintetizada com o mesmo backend e filtros da exportação, mas o
arquivo `voice_file` existente é preservado.

## Limitações e escopo

Amostra de fala: não substitui nem salva áudio do projeto. A geração do
roteiro completo permanece responsável pelo WAV final da cena e pelos
`voice_file`. A lista de vozes permanece servida pelo catálogo AUD-U2.

Instalação somente na branch M2 e sobre variantes AUD-U2/HF01 com hashes
exatos. Arquivos de voz instalados no Termux não são alterados. Testes
isolados não validam timbre real ou sincronização com o vídeo.
