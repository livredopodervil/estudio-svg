"""Editor espacial, publicador assistido e recuperação do RD Studio.

Não executa código de aplicativos importados. Alterações são exclusivamente no worktree.
"""
from __future__ import annotations
import hashlib
import html
import json
import math
from pathlib import Path
import re
from datetime import datetime, timezone

ID_RE = re.compile(r'^[a-z0-9][a-z0-9-]{0,70}$')
NUMBER = r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?'
POS_RE = re.compile(r'(?<![\w$])(?P<prefix>(?:position|"position"|\'position\')\s*:\s*)\[\s*(?P<x>'+NUMBER+r')\s*,\s*(?P<y>'+NUMBER+r')\s*,\s*(?P<z>'+NUMBER+r')\s*\]')
DEFAULT_SCENE = dict(cameraDistance=13.8, zoomMin=0.72, zoomMax=1.9, zoomStep=0.08, rotationFocus=0.13, rotationNeighbors=0.075, rotationTilt=0.045, dragSensitivity=0.008, autoplay=True)
RANGES = dict(cameraDistance=(8,30), zoomMin=(0.4,1.3), zoomMax=(1.1,3.0), zoomStep=(0.02,.25), rotationFocus=(0,.8), rotationNeighbors=(0,.5), rotationTilt=(0,.3), dragSensitivity=(.002,.03))
ENGINE_MARKER = '/* RD-STUDIO-SPATIAL-CONFIG-V1 */'
CREATED_MARKER = '/* RD-STUDIO-PORTFOLIO-GENERATED-V1 */'


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_bytes(data):
    return (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


class SpatialOps:
    def __init__(self, studio, error):
        self.s = studio
        self.error = error
        self.root = studio.root

    def fail(self, msg, status=400):
        raise self.error(msg, status)

    def manifest(self):
        rel='modules/manifest.json'
        path=self.s.resolve(rel)
        raw=path.read_bytes()
        try: m=json.loads(raw)
        except (ValueError,UnicodeError): self.fail('Manifesto não é JSON válido')
        if m.get('schemaVersion')!=1 or not isinstance(m.get('modules'),list) or not isinstance(m.get('links'),list):
            self.fail('Manifesto não possui o contrato esperado')
        ids=[x.get('id') for x in m['modules']]
        if not all(isinstance(x,str) and ID_RE.fullmatch(x) for x in ids) or len(set(ids))!=len(ids):
            self.fail('IDs de módulos inválidos ou repetidos')
        return m,digest(raw)

    def _sync_graph_mirror(self,manifest):
        """Update optional legacy graph.js as a mirror, preserving the manifest as authority."""
        file=self.root/'modules/graph.js'
        if not file.is_file():return
        old=file.read_text('utf-8')
        if old.count('export const links')!=1 or not re.match(r'(?s)^\s*(?:/\*.*?\*/\s*)?export const links\s*=.*?;\s*$',old):
            self.fail('Espelho modules/graph.js possui código adicional desconhecido; sincronize manualmente',409)
        content='/* Espelho declarativo de modules/manifest.json; o motor carrega o manifesto. */\nexport const links = '+json.dumps(manifest['links'],ensure_ascii=False,indent=2)+';\n'
        self.s.atomic_write('modules/graph.js',content.encode('utf-8'),digest(file.read_bytes()),allowed_suffixes={'.js'})

    def scene_config(self):
        path=self.root/'config/spatial.json'
        if not path.is_file():return DEFAULT_SCENE.copy(),None
        try:r=json.loads(path.read_text('utf-8'))
        except (ValueError,UnicodeError):self.fail('Configuração espacial contém JSON inválido')
        return {**DEFAULT_SCENE, **r},digest(path.read_bytes())

    def overview(self):
        m,version=self.manifest()
        nodes=[]
        for entry in m['modules']:
            mid=entry['id'];source=entry.get('src','')
            if source!=f'./modules/{mid}.js':self.fail('Fonte do módulo inconsistente: '+mid)
            path=self.root/f'modules/{mid}.js'
            position=None
            if path.is_file():
                txt=path.read_text('utf-8')
                match=POS_RE.search(txt)
                if match:position=[float(match.group(k)) for k in ('x','y','z')]
            nodes.append({'id':mid,'position':position,'source':f'modules/{mid}.js','editable':position is not None})
        config,config_sha=self.scene_config()
        engine=self.root/'js/site-v10.js'
        supported=engine.is_file() and (ENGINE_MARKER in engine.read_text('utf-8') or self._adapt_engine(engine.read_text('utf-8'), check_only=True))
        return {'nodes':nodes,'links':m['links'],'manifest_sha':version,'settings':config,'settings_sha':config_sha,
                'mini_sync_installed':engine.is_file() and '/* RD-STUDIO-MINI-SYNC-V1 */' in engine.read_text('utf-8'),
                'adapter_installed':engine.is_file() and ENGINE_MARKER in engine.read_text('utf-8'),
                'adapter_supported':bool(supported), 'projects':self.s.catalog()['projects'],
                'preview':f'http://127.0.0.1:{self.s.preview_port}/laboratorio/'}

    def save_links(self,d):
        if d.get('confirm')!='SALVAR GRAFO':self.fail('Confirmação SALVAR GRAFO necessária')
        m,version=self.manifest()
        if version!=d.get('expected_sha256'):self.fail('Manifesto alterado; recarregue o grafo',409)
        links=d.get('links')
        if not isinstance(links,list) or len(links)>300:self.fail('Lista de ligações inválida')
        ids={x['id'] for x in m['modules']};normalized=[];seen=set()
        for edge in links:
            if not isinstance(edge,list) or len(edge)!=2 or not all(isinstance(x,str) and x in ids for x in edge):
                self.fail('Ligação aponta para módulo inexistente')
            if edge[0]==edge[1]:self.fail('Não é permitido conectar módulo a si mesmo')
            key=tuple(sorted(edge))
            if key in seen:self.fail('Ligação duplicada entre '+edge[0]+' e '+edge[1])
            seen.add(key);normalized.append(edge)
        m['links']=normalized
        result=self.s.atomic_write('modules/manifest.json',json_bytes(m),version,allowed_suffixes={'.json'})
        self._sync_graph_mirror(m)
        return {'message':'Ligações salvas no manifesto. Recarregue a prévia 3D.','links':normalized,'manifest_sha':result['sha256']}

    def save_position(self,d):
        mid=d.get('id');coords=d.get('position')
        m,_=self.manifest()
        if mid not in [x['id'] for x in m['modules']]:self.fail('Módulo não encontrado')
        if not isinstance(coords,list) or len(coords)!=3 or any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) or abs(x)>300 for x in coords):
            self.fail('Posição deve conter três números entre -300 e 300')
        rel=f'modules/{mid}.js';path=self.s.resolve(rel);raw=path.read_bytes()
        if digest(raw)!=d.get('expected_sha256'):self.fail('Arquivo do módulo mudou; recarregue',409)
        text=raw.decode('utf-8');found=list(POS_RE.finditer(text))
        if len(found)!=1:self.fail('Não consegui identificar com segurança a posição no módulo; edite manualmente')
        v=[round(float(x),3) for x in coords]
        new=text[:found[0].start()]+found[0].group('prefix')+json.dumps(v)+text[found[0].end():]
        self.s.atomic_write(rel,new.encode(),digest(raw),allowed_suffixes={'.js'})
        return {'message':f'Posição de {mid} atualizada. A prévia 3D utiliza a nova posição após recarregar.','position':v}

    def _cards(self):
        projects=[p for p in self.s.catalog()['projects'] if p.get('status') in ('publicado','demonstracao')]
        projects=sorted(projects,key=lambda x:str(x.get('title','')).casefold())
        if (self.root/'projetos/telemedicina/index.html').exists() and not any(x.get('id')=='telemedicina' for x in projects):
            projects.append({'id':'telemedicina','title':'Telemedicina','summary':'Acervo técnico e demonstrativo.','url':'/projetos/telemedicina/','color':'#16a9a4','status':'demonstracao'})
        return projects

    def expose(self,d):
        """Gera portfólio convencional e o dodecaedro de catálogo com 12 faces úteis."""
        if d.get('confirm')!='INTEGRAR':self.fail('Confirme com INTEGRAR')
        if d.get('destination') not in ('portfolio','home','spatial'):self.fail('Destino inválido')
        projects=self._cards()
        if not projects:self.fail('Nenhum projeto publicado/demonstração no catálogo')
        result=self.s.discovery.portfolio_generate({'confirm':'GERAR PORTFOLIO','link_home':d.get('destination') in ('home','spatial')})
        if d['destination']!='spatial':
            return {**result,'message':'Portfólio atualizado em /projetos/. Abra a prévia local.','url':'/projetos/'}
        m,manifest_sha=self.manifest()
        project_entries=projects[:11] if len(projects)>12 else projects[:12]
        entries=[]
        for p in project_entries:
            url=p.get('url') or '/projetos/'
            if not isinstance(url,str) or not ((url.startswith('/') and not url.startswith('//')) or url.startswith('https://')):url='/projetos/'
            title=str(p.get('title') or p['id'])[:75]
            entries.append({'label':title[:30],'title':title,'description':str(p.get('summary') or 'Aplicativo e projeto do portfólio.')[:500], 'url':url})
        while len(entries)<12:
            entries.append({'label':'Mais projetos','title':'Catálogo de projetos',
                            'description':'Explore a lista completa de projetos e aplicações.', 'url':'/projetos/'})
        if len(projects)>12:
            entries[-1]={'label':'Catálogo completo','title':'Todos os projetos', 'description':f'{len(projects)} registros disponíveis no portfólio.', 'url':'/projetos/'}
        old=self.root/'modules/portfolio.js'
        if old.is_file() and not old.read_text('utf-8').startswith(CREATED_MARKER):
            self.fail('Já existe um módulo portfolio.js não gerado pelo Studio. Não sobrescrevo arquivos manuais.',409)
        defs={
            'id':'portfolio','name':'Projetos','color':'#36c8c4','rgb':'54,200,196',
            'title':'Projetos <em>e aplicações.</em>',
            'intro':'Aplicativos, experimentos e documentação reunidos num catálogo navegável.',
            'subtitle':'Catálogo · Ferramentas · Exploração',
            'position':[11,2,-14],
            'texturePath':'./assets/modules/portfolio/face-{n}.svg',
            'menu':[x['label'] for x in entries],
            'pages':[{'title':x['title'],'description':x['description'],'url':x['url']} for x in entries],
            'feeds':[],
        }
        if old.is_file():
            match=POS_RE.search(old.read_text('utf-8'))
            if match:defs['position']=[float(match.group(k)) for k in ('x','y','z')]
        text=CREATED_MARKER+'\nexport default '+json.dumps(defs,ensure_ascii=False,indent=2)+';\n'
        self.s.atomic_write('modules/portfolio.js',text.encode('utf-8'),digest(old.read_bytes()) if old.exists() else None,allowed_suffixes={'.js'})
        # Texturas vetoriais leves editáveis; sem dependências adicionais.
        palette=['#e1faf9','#d4f1ef','#e7f5ed','#effaf3']
        for i,item in enumerate(entries,1):
            a=html.escape(item['label']);b=html.escape(item['title'][:44]);fill=palette[(i-1)%len(palette)]
            svg=(f'<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512">'
                 f'<rect width="512" height="512" fill="{fill}"/><rect x="28" y="28" width="456" height="456" rx="28" fill="#073f4d"/>'
                 f'<circle cx="398" cy="120" r="104" fill="#0e7886" opacity=".55"/>'
                 f'<path d="M35 362 Q250 205 477 360" fill="none" stroke="#38bda2" stroke-width="5"/>'
                 f'<text x="46" y="90" fill="#7ce2d0" font-family="sans-serif" font-size="23">PROJETO / {i:02}</text>'
                 f'<text x="46" y="280" fill="white" font-family="sans-serif" font-weight="bold" font-size="27" textLength="420" lengthAdjust="spacingAndGlyphs">{a}</text>'
                 f'<text x="46" y="436" fill="#bad9d5" font-family="sans-serif" font-size="20">RD · PORTFÓLIO</text></svg>')
            rel=f'assets/modules/portfolio/face-{i:02}.svg';file=self.root/rel
            self.s.atomic_write(rel,svg.encode(),digest(file.read_bytes()) if file.is_file() else None,allowed_suffixes={'.svg'})
        if 'portfolio' not in [x['id'] for x in m['modules']]:
            m['modules'].append({'id':'portfolio','src':'./modules/portfolio.js'})
        for peer in ('nucleo','sistemas'):
            if peer in [x['id'] for x in m['modules']] and not any(set(x)=={peer,'portfolio'} for x in m['links']):m['links'].append([peer,'portfolio'])
        self.s.atomic_write('modules/manifest.json',json_bytes(m),manifest_sha,allowed_suffixes={'.json'})
        self._sync_graph_mirror(m)
        return {'message':'Catálogo e dodecaedro Projetos integrados. Recarregue /laboratorio/ para ver as novas faces.','url':'/laboratorio/','count':len(projects),'faces':12}

    def _adapt_engine(self,text,*,check_only=False):
        if ENGINE_MARKER in text:return text if not check_only else True
        patterns=[
          ('const links=manifest.links||[];', 'const links=manifest.links||[];\n'+ENGINE_MARKER+'\n'+
            'const rdScene = await fetch(\'./config/spatial.json\',{cache:\'no-store\'}).then(r=>r.ok?r.json():{}).catch(()=>({}));\n'+
            'const rdCfg = (key, fallback) => typeof rdScene[key] === \'number\' && Number.isFinite(rdScene[key]) ? rdScene[key] : fallback;\n'+
            'zoom = rdCfg(\'initialZoom\', 1); auto=rdScene.autoplay!==false;\n'+
            '$(\'#pause\').textContent=auto?\'Ⅱ Pausar\':\'▶ Animar\';\n'),
          ('13.8*zoom','rdCfg(\'cameraDistance\',13.8)*zoom'),
          ('Math.max(.72,zoom-.12)','Math.max(rdCfg(\'zoomMin\',.72),zoom-.12)'),
          ('Math.min(1.9,zoom+.12)','Math.min(rdCfg(\'zoomMax\',1.9),zoom+.12)'),
          ('Math.min(1.9,Math.max(.72,zoom+Math.sign(e.deltaY)*.08))','Math.min(rdCfg(\'zoomMax\',1.9),Math.max(rdCfg(\'zoomMin\',.72),zoom+Math.sign(e.deltaY)*rdCfg(\'zoomStep\',.08)))'),
          ('dt*(i===active?.13:.075)','dt*(i===active?rdCfg(\'rotationFocus\',.13):rdCfg(\'rotationNeighbors\',.075))'),
          ('dt*.045','dt*rdCfg(\'rotationTilt\',.045)'),
          ('dx*.008','dx*rdCfg(\'dragSensitivity\',.008)'),
          ('dy*.008','dy*rdCfg(\'dragSensitivity\',.008)'),
          ('camera.position.set(0,0,13.8)','camera.position.set(0,0,rdCfg(\'cameraDistance\',13.8)*zoom)')
        ]
        for needle,_ in patterns:
            if text.count(needle)!=1:return False if check_only else self.fail('Motor 3D fora do contrato conhecido; adaptação automática bloqueada em: '+needle)
        if check_only:return True
        for needle,replacement in patterns:text=text.replace(needle,replacement,1)
        return text

    def save_settings(self,d):
        if d.get('confirm')!='APLICAR CENA':self.fail('Confirme com APLICAR CENA')
        source=d.get('settings')
        if not isinstance(source,dict):self.fail('Parâmetros inválidos')
        settings={}
        for key,default in DEFAULT_SCENE.items():
            val=source.get(key,default)
            if key=='autoplay':
                if not isinstance(val,bool):self.fail('autoplay deve ser booleano')
            elif key=='initialZoom':
                if isinstance(val,bool) or not isinstance(val,(int,float)) or not .5<=val<=2:self.fail('Zoom inicial inválido')
            else:
                low,high=RANGES[key]
                if isinstance(val,bool) or not isinstance(val,(int,float)) or not math.isfinite(val) or not low<=val<=high:self.fail('Valor inválido: '+key)
            settings[key]=val
        iz=source.get('initialZoom',1)
        if isinstance(iz,bool) or not isinstance(iz,(int,float)) or not math.isfinite(iz) or not 0.5<=iz<=2:
            self.fail('Zoom inicial inválido')
        settings['initialZoom']=iz
        if not settings['zoomMin']<settings['zoomMax'] or not settings['zoomMin']<=settings['initialZoom']<=settings['zoomMax']:
            self.fail('Limites de zoom inválidos')
        current,config_sha=self.scene_config()
        if config_sha!=d.get('expected_sha256'):self.fail('A configuração foi alterada; recarregue',409)
        engine=self.s.resolve('js/site-v10.js');raw=engine.read_bytes();txt=raw.decode('utf-8')
        if ENGINE_MARKER not in txt:
            adapted=self._adapt_engine(txt)
            self.s.atomic_write('js/site-v10.js',adapted.encode('utf-8'),digest(raw),allowed_suffixes={'.js'})
        self.s.atomic_write('config/spatial.json',json_bytes(settings),config_sha,allowed_suffixes={'.json'})
        return {'message':'Parâmetros salvos. Recarregue a prévia 3D; o motor usa o arquivo de configuração sem futuras edições de código.'}

    def repair_minimap(self, data):
        """Restaurar controles táteis preservando o restante do motor.

        Somente worktree; backup automático no histórico do Studio e nunca push.
        """
        if data.get('confirm')!='REPARAR MINIATURA':
            self.fail('Confirme com REPARAR MINIATURA')
        engine=self.s.resolve('js/site-v10.js')
        raw=engine.read_bytes()
        text=raw.decode('utf-8')
        import importlib.util
        patch=Path(__file__).resolve().parent/'aplicar-miniatura-sync.py'
        spec=importlib.util.spec_from_file_location('rd_minimap_guard',patch)
        helper=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(helper)
        try: after=helper.transform(text)
        except ValueError as exc:self.fail('Motor não reconhecido: '+str(exc),409)
        if after==text:
            return {'message':'Miniatura já sincronizada. Nenhuma alteração realizada.','changed':False}
        # Vistoria sintática ANTES de gravar.
        import shutil, subprocess, tempfile
        node=shutil.which('node')
        if node:
            with tempfile.TemporaryDirectory() as temp:
                f=Path(temp)/'motor.js';f.write_text(after,encoding='utf-8')
                check=subprocess.run([node,'--check',str(f)],capture_output=True,text=True)
                if check.returncode:self.fail('JavaScript inválido: '+check.stderr[:800],409)
        self.s.atomic_write('js/site-v10.js',after.encode('utf-8'),digest(raw),allowed_suffixes={'.js'})
        self.s.last_validation=None;self.s.validation_fingerprint=None
        return {'message':'Miniatura sincronizada com a cena principal. Backup automático criado; não houve publicação.','changed':True}

    def _miniature_publication_guard(self):
        """Não permite remover acidentalmente função já publicada no GitHub."""
        path=self.root/'js/site-v10.js'
        if not path.is_file():
            if (self.root/'laboratorio/index.html').is_file():
                self.fail('Motor 3D ausente',409)
            return  # Repositórios estáticos sem laboratório 3D não usam esta proteção.
        local=path.read_text('utf8')
        try: remote=self.s._git_run(['show','origin/main:js/site-v10.js'],timeout=15)
        except self.error as exc:self.fail('Não foi possível inspecionar motor remoto: '+str(exc),409)
        marker='RD-STUDIO-MINI-SYNC-V1'
        if marker in remote and marker not in local:
            self.fail('REGRESSÃO BLOQUEADA: a versão publicada possui miniatura 3D sincronizada, '
                      'mas a cópia local não. Use «Reparar miniatura 3D» e execute Vistoria antes de publicar.',409)
        if marker in local:
            required=['miniRotate(dx,dy)','fingers.size===2','transition=null;',
                      'miniInteracting','w.group.position.copy(w.goalPosition)']
            if any(key not in local for key in required):
                self.fail('REGRESSÃO BLOQUEADA: miniatura marcada como sincronizada, mas controles incompletos.',409)
        if (self.root/'modules/content-pages.js').exists() and 'RD-EDITORIAL-LINKFIX-V1' not in local:
            self.fail('REGRESSÃO BLOQUEADA: conteúdo editorial existe, mas motor não integra artigos às faces.',409)

    def publish_plan(self):
        self.s.sync_fetch()
        self._miniature_publication_guard()
        info=self.s.sync_info()
        if not info['branch'].startswith('studio/'):
            self.fail('Assistente disponível somente na branch studio/ de teste')
        if info['behind'] or info['ahead'] is None:
            self.fail('O GitHub está adiante ou há divergência; reconcilie antes de publicar',409)
        if not self.s.last_validation or self.s.validation_fingerprint!=self.s.fingerprint() or self.s.last_validation.get('errors'):
            self.fail('Execute Vistoria sem erros antes de preparar a publicação',409)
        files=self.s.git()['status']
        if len(files)>650:self.fail('Mais de 650 arquivos alterados: divida a atualização e execute Vistoria novamente')
        sensitive=re.compile(r'(^|/)(\.env|\.ssh|id_rsa|id_ed25519|[^/]*\.pem|[^/]*\.key|config\.local)(/|$)',re.I)
        if any(sensitive.search(x['path']) for x in files):self.fail('Arquivo potencialmente sensível detectado: revise a árvore antes de publicar',409)
        internal=re.compile(r'(?:^|/)(?:agentes?|backup|backups|export|private|secrets)(?:/|$)|(?:^|/)(?:prompt_[^/]*|historico_[^/]*|tarefas_pendentes\.md|[^/]*\.bak(?:\.html)?)(?:$|/)',re.I)
        private=[x['path'] for x in files if internal.search(x['path'])]
        if private:self.fail('Publicação bloqueada: arquivos internos de agentes, prompts ou backups: '+', '.join(private[:5])+'. Use um pacote público mínimo.',409)
        return {'status':info,'files':files,'head':info['local'],'remote':info['remote'],
                'fingerprint':self.s.fingerprint(),'message':'Revise os arquivos e confirme a mensagem do commit. Nenhum arquivo foi publicado.'}

    def publish_apply(self,d):
        if d.get('confirm')!='PUBLICAR':self.fail('Digite PUBLICAR')
        plan=self.publish_plan()
        if d.get('expected_head')!=plan['head'] or d.get('expected_remote')!=plan['remote'] or d.get('expected_fingerprint')!=plan['fingerprint']:
            self.fail('Arquivos ou GitHub mudaram após a revisão. Gere o plano novamente.',409)
        message=str(d.get('message') or '').strip()
        if not 8<=len(message)<=150 or '\n' in message:self.fail('Mensagem de commit inválida (8-150 caracteres)')
        selected=d.get('paths')
        files={x['path'] for x in plan['files']}
        if not files and plan['status']['ahead']:
            info=self.s.sync_info()
            result=self.s.sync_publish({'confirm':'PUBLICAR','expected_head':info['local'],'expected_remote':info['remote'],'expected_origin':info['origin']})
            return {'committed':False,'published':True,'message':result['message'],'backup_tag':result.get('backup_tag')}
        if not isinstance(selected,list) or not selected or len(selected)>650 or len(set(selected))!=len(selected) or not set(selected)<=files:
            self.fail('Seleção de arquivos inválida')
        # Arquivos já preparados no índice são válidos quando também estão selecionados.
        # Nunca incluir silenciosamente um caminho que o usuário desmarcou.
        staged = set(filter(None,self.s._git_run(['diff','--cached','--name-only','-z'],timeout=10).split('\0')))
        extra_staged = sorted(staged - set(selected))
        if extra_staged:
            names = ', '.join(extra_staged[:8])
            more = ' (e outros)' if len(extra_staged)>8 else ''
            self.fail('Há arquivos previamente preparados no Git, mas NÃO selecionados na revisão: '
                      + names + more + '. Selecione-os ou retire apenas esses arquivos do stage. '
                      + 'Nenhuma alteração foi descartada.',409)
        # git add -A atualiza a versão completa dos arquivos selecionados, inclusive os já staged.
        # Commit de arquivos escolhidos + publicação linear; falhas não fazem reset nem push com força.
        self.s.stage(selected)
        self.s._git_run(['diff','--cached','--check'],timeout=15)
        self.s._git_run(['commit','-m',message],timeout=50)
        # Se não selecionou tudo, ainda há mudanças locais. Não autoriza push inadvertido.
        # Commit já criado localmente: não reverte de modo destrutivo; usuário pode terminar depois.
        remaining=self.s._git_run(['status','--porcelain=v1','--untracked-files=all'],timeout=10)
        if remaining:
            return {'committed':True,'published':False,'message':'Commit local criado. Restaram arquivos não selecionados; publicação bloqueada para revisão. Use o painel Git após resolver essas mudanças.'}
        # Commit e validação devem ser rechecados: fingerprint considera mtimes e não necessariamente muda no commit.
        self.s.last_validation=None;self.s.validation_fingerprint=None
        checks=self.s.validate()
        if checks.get('errors'):
            return {'committed':True,'published':False,'message':'Commit local criado, mas a vistoria após commit encontrou erros. Push bloqueado.'}
        info=self.s.sync_info()
        result=self.s.sync_publish({'confirm':'PUBLICAR','expected_head':info['local'],'expected_remote':info['remote'],'expected_origin':info['origin']})
        return {'committed':True,'published':True,'message':result['message'],'backup_tag':result.get('backup_tag')}

    def restore_fetch(self):
        self.s.sync_fetch()
        # Consulta tags de backup do próprio RD Studio, sem tocar nos arquivos locais.
        for family in ('site-pre-rdstudio-*','site-pre-home-*'):
            try:
                self.s._git_run(['fetch','origin',f'refs/tags/{family}:refs/tags/{family}'],timeout=70)
            except self.error as exc:
                if 'couldn\'t find remote ref' not in str(exc) and 'no such ref' not in str(exc):
                    raise
        return self.restore_plan()

    def restore_plan(self):
        info=self.s.sync_info()
        # Busca apenas backups gerados pelo RD Studio, não tags arbitrárias.
        tags=(self.s._git_run(['tag','-l','site-pre-rdstudio-*'],timeout=10).splitlines()+self.s._git_run(['tag','-l','site-pre-home-*'],timeout=10).splitlines())
        out=[]
        for tag in tags[-25:][::-1]:
            if not re.fullmatch(r'site-pre-(?:rdstudio|home)-[0-9-]{10,40}',tag):continue
            sha_=self.s._git_run(['rev-parse',tag+'^{commit}'],timeout=10)
            out.append({'tag':tag,'sha':sha_})
        return {'tags':out,'status':info,'message':'Reversão cria um novo commit, sem reescrever o histórico.'}

    def restore_apply(self,d):
        tag=d.get('tag','')
        if not isinstance(tag,str) or not re.fullmatch(r'site-pre-(?:rdstudio|home)-[0-9-]{10,40}',tag):self.fail('Tag de backup inválida')
        if d.get('confirm')!='REVERTER':self.fail('Confirme com REVERTER')
        # Exige decisão deliberada: não tentar merge automático nem sobrescrever alterações locais.
        self.s.sync_fetch()
        info=self.s.sync_info()
        if not info['branch'].startswith('studio/') or not info['clean'] or info['local']!=info['remote']:
            self.fail('Reversão exige branch studio/ limpa e alinhada exatamente com origin/main',409)
        if d.get('expected_remote')!=info['remote']:
            self.fail('O GitHub mudou desde a revisão. Recarregue.',409)
        if tag not in [x['tag'] for x in self.restore_plan()['tags']]:self.fail('Backup não encontrado')
        # A restauração somente afeta arquivos rastreados por Git, mantendo originais na tag.
        self.s._git_run(['restore','--source='+tag,'--staged','--worktree','--','.'],timeout=60)
        if not self.s._git_run(['diff','--cached','--name-only'],timeout=15):
            return {'message':'O backup já corresponde à versão publicada; nada a restaurar.'}
        self.s._git_run(['commit','-m',f'revert(site): restaurar snapshot {tag}'],timeout=40)
        self.s.last_validation=None;self.s.validation_fingerprint=None
        checks=self.s.validate()
        if checks.get('errors'):
            return {'message':'Commit de reversão criado localmente, mas a vistoria falhou: push bloqueado. Confira os arquivos.', 'published':False}
        # Tag preserva a versão que será substituída.
        updated=self.s.sync_info()
        r=self.s.sync_publish({'confirm':'PUBLICAR','expected_head':updated['local'],'expected_remote':updated['remote'],'expected_origin':updated['origin']})
        return {'message':'Reversão publicada com novo commit. '+r['message'],'published':True,'backup_tag':r.get('backup_tag')}
