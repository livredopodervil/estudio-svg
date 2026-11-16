# Estúdio SVG V3.8 experimental — RD Studio

Base: V3.7 ou ponte GIL 0.2.1 (somente conjuntos completos de hashes conhecidos). Instalação incremental, preserva repositório, projetos e mídias. Não executa commit ou push. A revisão da GIL/RD Studio permanece 0.2.1.

## Uso

Na barra principal, abaixo das abas Cenas, Prévia, Editor e Produção, ficam quatro atalhos que não dependem da aba selecionada.

- **Tempo / áudio em lote**: selecione todas as cenas, a atual ou intervalo. Operações Piso, Fixar, Multiplicar e Adequar à locução. No último modo, pressione Medir arquivos de voz, revise os resultados e aplique. Usa o arquivo gravado ou a voz sintetizada específica do texto e configuração atuais, nunca uma estimativa de TTS. Calcula duração medida + atraso + margem de 0,26 s, arredondada para cima ao milissegundo; o renderizador ainda quantiza ao FPS de desenho. Cenas sem voz válida permanecem intactas. A medição consulta somente o estado em memória, sem gravar. Para mudar a duração persistida, aplique e Salve. Desfazer último lote funciona se as cenas e durações ainda correspondem. Reduzir pode cortar visual, música, efeitos ou clipes na exportação; há confirmação. Arquivos de mídia não são cortados ou removidos; não modifica a velocidade da locução. Não há encaixe automático contínuo após cada geração de voz; repita a medição quando a locução mudar. A narração TTS diretamente no navegador não tem duração medida disponível.
- **Projetos e arquivos**: inventário de recursos explicitamente referenciados no projeto em memória (arquivo, tamanho, papéis), exportação ZIP existente, arquivar/restaurar. Arquivar move apenas o JSON bruto para `projetos/.arquivados/NOME.json`, reservando o identificador; restauração não sobrescreve. O último projeto ativo não pode ser arquivado até criar outro. Não apaga mídias, caches, derivados ou gravações. As mídias continuam compartilhadas fisicamente; não é uma migração geral do armazenamento. O inventário não lista arquivos órfãos, todos os caches ou saídas. A exportação ZIP usa o contrato de pacote existente.
- **Objetos / movimentos**: seis conjuntos vetoriais (órbita, rede, onda/sinal, fluxo de dados, radar, partículas), adicionados como cena SVG ou elementos numa cena SVG canônica. Cada forma tem ID para edição/camadas; não substitui áudio existente. Limite legado 32 faixas por cena. Cinco movimentos (entrada rápida, pulso, rotação, oscilação, elevação) utilizam `animacoes` e o mesmo interpolador canônico. A duração do movimento depende da duração da cena ao inserir; posteriormente a timeline fracionária se redimensiona junto com ela. A biblioteca não altera as cenas antigas. Não promete editor WebGL nativo.
- **Narração**: abre editor de áudio da cena com atalhos gerar voz desta cena, gerar todas as vozes e adequar tempos. Mantém gravação e controles existentes.

## GIL e SpatialSeed

A biblioteca acessa três exemplos da GIL instalada e dois novos exemplos em `examples/components/`: Rede de pulsos 3D (102 instâncias/objetos) e Campo cinemático (85). Ambos têm 12 s e fontes editáveis. Inserção usa `/api/component/gil`, o adaptador existente da ponte 0.2.1; arquivos próprios GIL ou SpatialSeed também podem ser importados. Inicie via RD Studio para disponibilizar `RD_GIL_ROOT` e `RD_SPATIALSEED_ROOT`. Clipes opacos derivados, editáveis internamente no editor GIL (via fonte); a exportação nativa HTML existente aceita essas fontes. Selecione Baixar fonte para página e abra o arquivo pelo editor GIL; exporte o componente nativo e importe o RD Patch pelo RD Studio. Não há sincronização automática de revisões entre os editores nem suporte a todos os recursos SpatialSeed.

## Validação

Testes da base e novos: `RD_GIL_ROOT="$HOME/rd_studio_gil_v01/gil" python -m unittest discover -s tests -v` e `node --test tests/test_timing_v37.mjs tests/test_media_clock_v37.mjs tests/test_layers_v36.mjs tests/test_workspace_v38.mjs`. Verifique `git diff --check`. Teste no Android: medir/reduzir/estender, desfazer, salvar/reabrir; criar e arquivar um projeto de teste, restaurar; criar objeto SVG e reproduzir; inserir GIL na cena e renderizar. A revisão visual foi simulada com APIs mockadas; as APIs novas e o renderizador foram testados separadamente. Não declare validação física do Android.

## Próximos passos

Catálogo comum com identificador de recurso e proveniência, armazenamento por projeto e pool deduplicado com migração e verificador de referências, runtime GIL nativo (não clipe) no editor e no Player, integração dos comandos canônicos do SpatialSeed, timeline em segundos, eventos sincronizados com voz e biblioteca de materiais/câmeras/luzes. Manter separação de domínio, projeção, armazenamento e apresentação.

### Correção de compatibilidade V3.8.1 (Termux)

O arquivamento não depende mais de `os.link`, ausente em algumas versões do Python Android. A transferência cria o destino em modo exclusivo, sincroniza e confere os bytes antes de remover a origem. A rota administrativa mantém os bloqueios existentes. Não execute dois servidores que escrevam no mesmo diretório nem edite os JSON externamente durante essa operação. Se houver falha ao remover a origem ou interrupção do processo, podem restar duas cópias (ou um destino incompleto se interrompido durante a escrita); inspecione os dois arquivos antes de resolver manualmente. Nenhuma mídia é removida.
