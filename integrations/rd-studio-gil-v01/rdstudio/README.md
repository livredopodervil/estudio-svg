# RD Studio 4.4.2 — correção do autoteste de pacotes

- Corrige o falso erro em `test_archives_list` causado pelos pacotes reais presentes nos Downloads Android.
- Os testes agora pesquisam somente uma pasta temporária isolada, sem depender de `/sdcard/Download`.
- O atualizador executa o código da nova versão explicitamente via `PYTHONPATH`, antes de substituir o programa instalado.
- Nenhuma modificação no site, nos arquivos publicados, nos patches de conteúdo nem no gerenciador `patches.py`.

# RD Studio 4.4 — gerenciamento de patches localizados

# RD Studio 4.3 — proteção da miniatura e editor editorial

Mantém todos os recursos do 4.2: exploração, catálogo, editor do grafo, ajustes paramétricos, publicação seletiva e reversão.

**Novo:** botão «Reparar miniatura 3D» em *Organizar e publicar → Parâmetros do navegador 3D*. O motor recebe a integração da miniatura somente quando reconhecido, com backup externo à árvore Git e sem publicação.

**Publicação de acervos:** o assistente aceita até 650 arquivos selecionados, apresenta controles de seleção total/nenhuma e bloqueia caminhos típicos de agentes, prompts e backups privados.

**Trava de regressão:** antes do assistente de publicação o Studio consulta `origin/main:js/site-v10.js`. Se a versão publicada possui `RD-STUDIO-MINI-SYNC-V1` e a cópia local não, bloqueia o push e explica como reparar. Se a cópia local contém o caderno editorial mas não a navegação das faces, também bloqueia.

As vistorias do editor devem ser executadas novamente após qualquer reparo. A publicação ainda exige confirmação `PUBLICAR` e tag remota de backup; nenhuma instalação faz push.

Instale usando `atualizar-termux.sh` e inicie o Studio com `iniciar-termux.sh` informando o **worktree desejado**. Não confunda o worktree antigo do Studio com o da v5.2.

# RD Studio 4.2 — Miniatura 3D vinculada à cena

Inclui os recursos da v4.1: editor do grafo, catálogo, vistoria, publicação seletiva e reversão com tag remota. Corrige também a miniatura tridimensional que antes girava independentemente dos dodecaedros na tela.

## Atualizar Studio v4.x e motor de teste em um único procedimento

Acesse o Terminal onde o Studio está rodando e interrompa com `Ctrl+C`. Baixe `rd-studio-termux-v4.2.zip` em Downloads. Execute:

```bash
set -e
ZIP="$HOME/storage/downloads/rd-studio-termux-v4.2.zip"
[ -f "$ZIP" ] || ZIP="/sdcard/Download/rd-studio-termux-v4.2.zip"
[ -f "$ZIP" ] || { echo 'ZIP ausente em Downloads' >&2; exit 1; }
TMP="$(mktemp -d "$HOME/rd-studio-v4.2.XXXXXX")"
python -m zipfile -e "$ZIP" "$TMP"
bash "$TMP/instalar-com-miniatura.sh" "$HOME/rd-studio" "$HOME/rogerioduarte-studio-teste"
RD_STUDIO_PORT=8875 RD_STUDIO_PREVIEW_PORT=8876 bash "$HOME/rd-studio/iniciar-termux.sh"
```

Prévia: <http://127.0.0.1:8876/laboratorio/>. Painel: <http://127.0.0.1:8875/>.

### Controles

- **Arraste com um dedo na molécula em miniatura:** modifica a orientação da miniatura e imediatamente a disposição de seus dodecaedros vizinhos na cena principal; também gira o nó ativo.
- **Pinça na miniatura:** aproxima/afasta a câmera principal e a própria miniatura, sem interpolação de viagem.
- **Roda do mouse na miniatura:** mesma alteração de zoom.
- **Toque curto em um nó da miniatura:** viaja até o módulo selecionado como antes.
- **Arraste no dodecaedro principal:** comportamento original preservado.

O mapa e a cena não têm a mesma disposição geométrica: a miniatura representa todos os módulos, enquanto a cena mostra o módulo ativo e seus vizinhos. O patch sincroniza movimento angular e zoom, não copia literalmente as coordenadas dos nós do minimapa.

### Segurança

- O patch altera **somente `js/site-v10.js`** no worktree de teste indicado. Os outros arquivos do site permanecem intactos.
- Cria backup em `~/rd-studio-backups/site-mini-sync/<timestamp>/site-v10.js`, fora da árvore Git.
- Se o motor for desconhecido, aborta antes da aplicação.
- Não retira arquivos já staged e não executa stage, commit, push ou alterações DNS.
- A aplicação é repetível: um motor já alterado não recebe patch duplicado.
- No RD Studio, o painel **Editor 3D e publicação** indica se a sincronização está instalada.
- A alteração é visível no Git e poderá ser publicada seletivamente depois de Vistoria e confirmação explícita.

### Verificar e reverter **apenas** o patch

```bash
python "$HOME/rd-studio/aplicar-miniatura-sync.py" --repo "$HOME/rogerioduarte-studio-teste"
git -C "$HOME/rogerioduarte-studio-teste" diff -- js/site-v10.js
```

Para reverter manualmente o motor ao backup, copie o arquivo escolhido da pasta `~/rd-studio-backups/site-mini-sync/` após comparar com a versão atual. **Não use `git reset --hard`**; pode apagar outras modificações.

## Limites

A validação sintática é executada quando Node.js está disponível; Node.js não é requisito para usar o painel. O Three.js continua carregado por CDN na página pública. O comportamento tátil precisa ser conferido no Android. Se outros patches alteraram os manipuladores originais da miniatura, a instalação interrompe em vez de sobrescrever código desconhecido.

# RD Studio 4.4 — Pacotes localizados e removíveis

A aba **Pacotes IA** permite revisar, aplicar e desfazer atualizações encapsuladas em `*.rdpatch.zip`, sem reconstruir nem substituir o repositório inteiro. O Studio verifica SHA-256 da versão anterior e da nova versão, recusa divergências e salva backups fora do site em `~/.rd-studio/pacotes/<id-do-worktree>/<id-do-pacote>/`.

## Fluxo

1. Copie o arquivo `.rdpatch.zip` para `~/storage/downloads/` (ou `/sdcard/Download`). O Studio não precisa receber o arquivo por upload HTTP.
2. Abra **Pacotes IA**, selecione o pacote e clique **Examinar alterações**; veja exatamente os arquivos afetados.
3. Clique **Aplicar no worktree** e confira a rota na aba **Prévia**.
4. Execute **Vistoria**, confira o diff em Git e publique somente os arquivos declarados.
5. Para remover, abra a mesma aba, selecione o pacote instalado, faça **Verificar remoção** e **Remover pacote selecionado**. Isso restaura o estado pré-patch se ninguém modificou esses arquivos depois da instalação.

Se o patch já tiver sido publicado, a remoção **local** precisa ser seguida por novo commit e push para reverter também o GitHub Pages. A atualização do Studio não muda o site nem publica nada.

## Segurança

- O pacote contém um manifesto declarativo, arquivos e documentação; **scripts dentro do ZIP não são executados**.
- Paths absolutos, `..`, links simbólicos, entradas duplicadas, hashes incorretos, tipos de arquivo inesperados e alterações concorrentes são rejeitados.
- Operações permitidas: `add` e `replace`. Não há exclusão arbitrária. A desinstalação só remove arquivos declarados como novos, e restaura os anteriores pelo backup.
- Uma alteração feita posteriormente em um arquivo do patch bloqueia a remoção automática para evitar perda de trabalho.
- O backup fica fora da árvore Git e não entra na publicação. Não publique backups com dados pessoais.
- O gerenciador de patches não acessa GitHub, não faz commit e não altera controles de câmera/3D.

## Compatibilidade e limites

O pacote de demonstração **APS aprofundada** foi feito para os arquivos editoriais da série v5/v5.1/v5.2. Caso o artigo tenha sido alterado localmente, a aplicação é bloqueada por hash; revise/mescle as alterações em vez de forçar a substituição.

Para salvar edições posteriores de um artigo já instalado e continuar tendo remoção reversível, primeiro remova o patch; depois prepare nova versão do pacote com hashes e backups correspondentes. Como alternativa, após publicação, use o Git para restaurar um estado anterior por novo commit.


RD Studio 4.4.2: suporte a vídeo MP4 em pacotes RD Patch, limitado a 8 MiB por arquivo e validado por assinatura ftyp.
