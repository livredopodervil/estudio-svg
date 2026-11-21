/** M3-A: local status and navigation ONLY; no credentials, POST or project changes. */
export const SERVICE_IDS = Object.freeze(['studio','admin','site','spatialseed','gil','audio']);
const names = new Set(SERVICE_IDS);
export function checkedStatus(data) {
  if (!data || data.schema !== 1 || data.read_only !== true || !Array.isArray(data.services))
    throw new TypeError('Contrato de serviços incompatível');
  const ids = new Set();
  const services = data.services.map(item => {
    if (!item || !names.has(item.id) || ids.has(item.id) ||
        typeof item.label !== 'string' || typeof item.state !== 'string' ||
        typeof item.detail !== 'string') throw new TypeError('Serviço inválido ou duplicado');
    ids.add(item.id);
    return {id:item.id, label:item.label.slice(0,100), state:item.state.slice(0,50), detail:item.detail.slice(0,300)};
  });
  const port = key => {
    const value = data.ports?.[key];
    return Number.isInteger(value) && value >= 1 && value <= 65535 ? value : null;
  };
  return {services, ports:{admin:port('admin'),preview:port('preview')}};
}
/**
 * The unified viewport layout hides .workspaceTools with !important.
 * Move the EXISTING button (and its event handler) into the visible
 * composition navigation; do not duplicate IDs or unhide the legacy bar.
 */
export function placeSuiteButtonInComposeNav(doc) {
  const button = doc.getElementById('openSuiteM3A');
  const nav = doc.querySelector('.rdStudioUnified .rdComposeNav');
  if (!button || !nav) return false;
  if (button.parentElement !== nav) nav.prepend(button);
  return true;
}

const targets = Object.freeze({
  admin: 'RD Studio 4.4.2', site: 'Prévia do site',
  spatialseed: 'Editor SpatialSeed', gil: 'Objetos / GIL', audio: 'Editor de narração'
});
function mount() {
  const get = id => document.getElementById(id);
  const panel=get('workspaceSuiteM3A'), open=get('openSuiteM3A');
  if (!panel || !open) return;
  const output=get('suiteServicesM3A'), summary=get('suiteSummaryM3A');
  let pending = false;
  function show() {
    for (const id of ['timingDialog','workspaceProjects','workspaceLibrary','workspaceSuiteM3A']) {
      const element=get(id); if(element) element.hidden = id!=='workspaceSuiteM3A';
    }
    open.setAttribute('aria-expanded','true');
    panel.scrollIntoView({block:'start',behavior:'smooth'});
    void refresh();
  }
  function close() {
    panel.hidden=true;
    open.setAttribute('aria-expanded','false');
    open.focus();
  }
  function addAction(parent, item, ports) {
    if (!Object.hasOwn(targets,item.id)) return;
    const label=targets[item.id];
    if ((item.id==='admin' || item.id==='site') && ports[item.id==='admin'?'admin':'preview']) {
      const port=ports[item.id==='admin'?'admin':'preview'];
      const a=document.createElement('a');
      a.href=`http://127.0.0.1:${port}/${item.id==='site'?'laboratorio/':''}`;
      a.target='_blank'; a.rel='noopener noreferrer'; a.textContent='Abrir '+label+' ↗';
      parent.append(a);
    } else if (['spatialseed','gil','audio'].includes(item.id)) {
      const target={spatialseed:'openSpatialSeedMain',gil:'openLibrary',audio:'quickNarration'}[item.id];
      const button=document.createElement('button');button.type='button';button.textContent=label;
      button.addEventListener('click',()=>{close();get(target)?.click();});
      parent.append(button);
    }
  }
  function render(data) {
    const result=checkedStatus(data);
    output.replaceChildren();
    for(const item of result.services) {
      const row=document.createElement('div');row.className='rd-suite-entry';
      const desc=document.createElement('div');
      const title=document.createElement('strong');title.textContent=item.label+' · '+item.state;
      const detail=document.createElement('small');detail.textContent=item.detail;
      desc.append(title,detail);row.append(desc);
      addAction(row,item,result.ports);output.append(row);
    }
    summary.textContent=result.services.length+' serviços listados · diagnóstico sem alterações';
  }
  async function refresh() {
    if(pending)return;
    pending=true;get('suiteRefreshM3A').disabled=true;
    summary.textContent='Consultando serviços locais…';
    try {
      const res=await fetch('/api/suite/status',{cache:'no-store'});
      if(!res.ok)throw Error('HTTP '+res.status);
      render(await res.json());
    } catch (err) {
      summary.textContent='Falha ao consultar a suíte: '+String(err.message||err).slice(0,140);
    } finally {
      pending=false;get('suiteRefreshM3A').disabled=false;
    }
  }
  // studio-layout-v1.js may create the navigation after our module loads.
  // Watch only until the first successful placement; no polling or new toolbar.
  if (!placeSuiteButtonInComposeNav(document) && typeof MutationObserver !== 'undefined') {
    const observer = new MutationObserver(() => {
      if (placeSuiteButtonInComposeNav(document)) observer.disconnect();
    });
    observer.observe(document.documentElement, {childList:true, subtree:true, attributes:true, attributeFilter:['class']});
  }
  open.addEventListener('click',show);
  get('closeSuiteM3A').addEventListener('click',close);
  get('suiteRefreshM3A').addEventListener('click',refresh);
}
if (typeof document !== 'undefined') {
  if (document.readyState==='loading') document.addEventListener('DOMContentLoaded',mount,{once:true});
  else mount();
}
