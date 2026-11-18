# M1i — Console incremental do Estúdio SVG

Autoria do projeto: Rogério Duarte. Implementação experimental de interface por comandos; compatível conceitualmente com o contrato textual do SpatialSeed. Não importa código interno do SpatialSeed nem substitui sua `CommandRegistry`.

## Base

- Checkpoint `feat/studio-interface-m1b` / `01b5761` da auditoria de 17/11/2026.
- Integração após M1h em `app.py` e `web/roteiro-v04-ui.mjs` (verificadas por SHA-256).
- A barra atual `✧` abre Catálogo + Agente. O console fica dentro do mesmo diálogo, não cria aba nem altera `web/index.html`.
- O editor atual continua autoritativo: `validateProjectPlan` valida; `previewProjectPlan` simula; `commit` aplica uma transação com o histórico nativo. O console chama esses handlers da própria UI; não tem outro reducer.

## Sintaxe e uso

`runtime query <id> [JSON]` inspeciona sem alterar; `runtime command <id> [JSON]` prepara ou solicita alterações. `help` lista os comandos. JSON sempre é objeto, sem JavaScript arbitrário.

Exemplo, primeiro obtenha o ID real da cena:

```text
runtime query studio.scenes
runtime query studio.scene {"id":"cena-real"}
runtime command studio.scene.text {"id":"cena-real","field":"subtitulo","text":"Um novo subtítulo"}
runtime command studio.scene.duration {"id":"cena-real","seconds":8}
runtime query studio.plan
runtime command studio.plan.preview
runtime command studio.plan.apply
```

`studio.plan.apply` só funciona após simulação e abre a confirmação já existente. O projeto permanece local até salvar pelo editor. Desfazer/refazer é feito pelos controles já existentes da interface; não foi criado comando novo de histórico sem auditar a API. A recusa de confirmação não altera o documento.

Comandos adicionais: `studio.project`, `studio.commands`, `studio.plan.add` (aceita uma operação no esquema 0.4), `studio.plan.replace` (documento integral 0.4), `studio.plan.clear` (descarta apenas o rascunho), `studio.plan` (consulta).

## Contrato arquitetural

- `StudioCommandRegistry` contém IDs, handlers e descritores; barra, console e LLM futuramente podem compartilhar IDs.
- Plano 0.4 é a **única fonte do rascunho**; o console modifica a mesma caixa de plano do Catálogo + Agente.
- Consultas não alteram o documento. Comandos de edição acrescentam operações a um rascunho; simulação nunca comita; aplicação exige confirmação e descarta propostas se houve alterações desde o preview.
- GIL e SpatialSeed mantêm responsabilidades próprias. A extensão futura poderá mapear comandos canônicos para adaptadores, sem executar scripts ou importar o sandbox do SpatialSeed no navegador do Studio.
- Sem upload de dados para serviços de IA, sem endpoints remotos, sem manipulação de arquivos ou shell.

## Limites e validação

Comandos de objeto e propriedades físicas não foram conectados nesta etapa porque os contratos e o histórico do `scene-object-editor.mjs` atual não constam integralmente da auditoria. Também não foi integrado cliente LLM remoto nem macros. A implementação atual abrange consultas de cena e as operações do plano 0.4 que o motor já entende.

Testes automáticos: `node tests/test_studio_console_m1i.mjs`. Testes HTTP, visual no celular, atualização no editor, undo e salvamento exigem validação na instalação Android. Com `node --check`, também verificar `web/studio-console-v1.mjs` e `web/studio-command-registry-v1.mjs`.

## Reversão

O instalador cria um ZIP de backup em Downloads. Para reverter, executar `python /CAMINHO/rd_m1i_instalar.py --revert /CAMINHO/BACKUP.zip`. A reversão recusa arquivos modificados depois da instalação; não apaga alterações novas.

Não executar commit/push sem revisão do autor.
