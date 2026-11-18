// Estúdio SVG / RD Studio · registro de comandos textual, independente do DOM.
// Mesma convenção externa do SpatialSeed, sem importar classes internas dele.
const ID = /^[a-z][a-z0-9]*(?:[.-][a-z][a-z0-9]*)+$/;
export class StudioCommandRegistry {
  #registry = new Map();
  register(id, handler, metadata={}) {
    if (!ID.test(id) || typeof handler !== 'function' || this.#registry.has(id))
      throw new Error(`Registro inválido ou duplicado: ${id}`);
    const kind = metadata.kind;
    if (kind !== 'query' && kind !== 'command') throw new Error('Comando sem tipo válido');
    const descriptor = Object.freeze({id,kind,description:String(metadata.description||'')});
    this.#registry.set(id, Object.freeze({handler,descriptor}));
    return this;
  }
  list(kind=null) {
    return [...this.#registry.values()].map(x=>x.descriptor)
      .filter(x=>!kind||x.kind===kind).sort((a,b)=>a.id.localeCompare(b.id));
  }
  execute(kind,id,args={}) {
    const item = this.#registry.get(id);
    if (!item || item.descriptor.kind!==kind) throw new Error(`Comando desconhecido: ${kind} ${id}`);
    if (!args || typeof args!=='object' || Array.isArray(args)) throw new Error('Argumentos devem ser um objeto JSON');
    return item.handler(args);
  }
}
export function parseStudioConsoleLine(line) {
  const input=String(line||'').trim();
  if (!input || input==='help' || input==='runtime help') return {help:true};
  if (input.length>32768) throw new Error('Comando excede 32 KiB');
  const match=/^runtime\s+(query|command)\s+([a-z][a-z0-9]*(?:[.-][a-z][a-z0-9]*)+)(?:\s+([\s\S]*))?$/.exec(input);
  if (!match) throw new Error('Use: runtime query|command <id> [JSON], ou help');
  let args={};
  if (match[3]) {
    try { args=JSON.parse(match[3]); } catch { throw new Error('Argumentos JSON inválidos'); }
    if (!args || Array.isArray(args) || typeof args!=='object') throw new Error('Argumentos devem ser objeto JSON');
  }
  return {kind:match[1],id:match[2],args};
}
