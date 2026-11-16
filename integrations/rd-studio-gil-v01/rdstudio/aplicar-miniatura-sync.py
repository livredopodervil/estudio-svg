#!/usr/bin/env python3
"""Conecta manipuladores da miniatura 3D ao motor principal do laboratório.

Compatível com o motor site-v10.js do site de 2026-11-07, tanto original
como adaptado pelo RD Studio 4.x. Inspeção por padrão. --apply faz backup
FORA do worktree, escreve apenas js/site-v10.js; não executa Git nem publica.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

MARKER = '/* RD-STUDIO-MINI-SYNC-V1 */'

ORIGINAL_EVENTS_START = ' const ray=new THREE.Raycaster(),mouse=new THREE.Vector2();let down=null;'
ORIGINAL_EVENTS_END = ' function size(){'
ORIGINAL_ARRANGE = 'w.goalPosition=center.clone().add(new THREE.Vector3(6.2*Math.cos(angle),4.85*Math.sin(angle),-3.5));'

EVENTS = r''' const ray=new THREE.Raycaster(),mouse=new THREE.Vector2();
 // Pointer Events: mouse, caneta e multitoque; a miniatura controla a cena pública.
 const fingers=new Map();let down=null,pinchDistance=0;
 canvas.style.touchAction='none';
 function distance(){
  if(fingers.size!==2)return 0;
  const [a,b]=Array.from(fingers.values());return Math.hypot(a.x-b.x,a.y-b.y);
 }
 function miniRotate(dx,dy){
  const speed=(typeof rdCfg==='function'?rdCfg('dragSensitivity',.008):.008)*1.5;
  const yaw=dx*speed,pitch=dy*speed;
  miniPose.yaw+=yaw;
  const nextPitch=Math.max(-1.35,Math.min(1.35,miniPose.pitch+pitch));
  const usedPitch=nextPitch-miniPose.pitch;miniPose.pitch=nextPitch;
  assembly.rotation.set(miniPose.pitch,miniPose.yaw,0,'YXZ');
  if(!worlds.length)return;
  arrange(); // Rotaciona as posições relativas; não reconstrói objetos 3D.
  worlds.forEach(w=>w.group.position.copy(w.goalPosition)); // feedback no quadro atual
  const center=worlds[active]?.group;
  if(center){
   center.rotateOnWorldAxis(new THREE.Vector3(0,1,0),yaw);
   center.rotateOnWorldAxis(new THREE.Vector3(1,0,0),usedPitch);
  }
 }
 function miniZoom(factor){
  if(!Number.isFinite(factor)||factor<=0)return;
  const low=typeof rdCfg==='function'?rdCfg('zoomMin',.72):.72;
  const high=typeof rdCfg==='function'?rdCfg('zoomMax',1.9):1.9;
  zoom=Math.min(high,Math.max(low,zoom*factor));
  miniCamera.position.z=Math.max(7,Math.min(23,13.8 * zoom));
  if(!camera||!focus)return;
  transition=null; // miniatura responde imediatamente, sem viagem animada.
  const target=new THREE.Vector3(...modules[active].position);
  const base=typeof rdCfg==='function'?rdCfg('cameraDistance',13.8):13.8;
  focus.copy(target);
  camera.position.copy(target).add(new THREE.Vector3(0,0,base*zoom));
  camera.lookAt(focus);
 }
 canvas.addEventListener('pointerdown',e=>{
  e.preventDefault();e.stopPropagation();
  fingers.set(e.pointerId,{x:e.clientX,y:e.clientY});
  if(fingers.size===1)down={sx:e.clientX,sy:e.clientY,moved:false,multi:false};
  else if(down){down.multi=true;down.moved=true;}
  miniInteracting=true;
  canvas.setPointerCapture(e.pointerId);
  pinchDistance=distance();
 });
 canvas.addEventListener('pointermove',e=>{
  const prev=fingers.get(e.pointerId);if(!prev)return;
  e.preventDefault();e.stopPropagation();
  const dx=e.clientX-prev.x,dy=e.clientY-prev.y;
  fingers.set(e.pointerId,{x:e.clientX,y:e.clientY});
  if(down&&Math.hypot(e.clientX-down.sx,e.clientY-down.sy)>6)down.moved=true;
  if(fingers.size===2){
   if(down){down.moved=true;down.multi=true;}
   const d=distance();
   if(pinchDistance>1&&d>1)miniZoom(pinchDistance/d);
   pinchDistance=d;
  }else if(fingers.size===1)miniRotate(dx,dy);
 });
 function endPointer(e,cancelled){
  if(!fingers.has(e.pointerId))return;
  e.stopPropagation();
  const tap=!cancelled&&fingers.size===1&&down&&!down.moved&&!down.multi;
  fingers.delete(e.pointerId);
  pinchDistance=distance();
  if(!fingers.size){miniInteracting=false;down=null;}
  if(!tap)return;
  const r=canvas.getBoundingClientRect();
  mouse.set((e.clientX-r.left)/r.width*2-1,-((e.clientY-r.top)/r.height*2-1));
  ray.setFromCamera(mouse,miniCamera);
  const hit=ray.intersectObjects(nodes,false)[0];
  if(hit)travel(hit.object.userData.index);
 }
 canvas.addEventListener('pointerup',e=>endPointer(e,false));
 canvas.addEventListener('pointercancel',e=>endPointer(e,true));
 canvas.addEventListener('lostpointercapture',e=>endPointer(e,true));
 canvas.addEventListener('wheel',e=>{
  e.preventDefault();e.stopPropagation();
  miniZoom(Math.exp(Math.sign(e.deltaY)*.08));
 },{passive:false});
'''


def replace_one(src: str, old: str, new: str, label: str) -> str:
    count = src.count(old)
    if count != 1:
        raise ValueError(f'Contrato do motor incompatível em {label}: {count} correspondências; nada modificado')
    return src.replace(old, new, 1)


def transform(src: str) -> str:
    if MARKER in src:
        return src
    src = replace_one(
        src, 'let mini=null;',
        MARKER + '\nlet mini=null,miniInteracting=false;\nconst miniPose={yaw:0,pitch:0};',
        'estado compartilhado da miniatura'
    )
    a = src.find(ORIGINAL_EVENTS_START)
    b = src.find(ORIGINAL_EVENTS_END, a if a >= 0 else 0)
    if a < 0 or b < 0 or b <= a or src.count(ORIGINAL_EVENTS_START) != 1:
        raise ValueError('Manipuladores da miniatura não reconhecidos; nada modificado')
    block = src[a:b]
    required = (
        "canvas.addEventListener('pointerdown'",
        "canvas.addEventListener('pointermove'",
        "canvas.addEventListener('pointerup'",
        "canvas.addEventListener('pointercancel'",
        "canvas.addEventListener('wheel'",
        "miniCamera.position.z=Math.max(9,Math.min(21",
    )
    if any(block.count(fragment)!=1 for fragment in required) or block.count('canvas.addEventListener(')!=5:
        raise ValueError('Manipuladores existentes da miniatura foram alterados por outro patch; nada modificado')
    src = src[:a] + EVENTS + src[b:]
    src = replace_one(src, ORIGINAL_ARRANGE,
        'const relative=new THREE.Vector3(6.2*Math.cos(angle),4.85*Math.sin(angle),-3.5);\n'
        '   relative.applyEuler(new THREE.Euler(miniPose.pitch,miniPose.yaw,0,\'YXZ\'));\n'
        '   w.goalPosition=center.clone().add(relative);',
        'posicionamento dos vizinhos')
    src = replace_one(src, 'if(!down)assembly.rotation.y+=dt*.075;',
                      '/* Orientação da miniatura permanece sincronizada com a cena. */',
                      'rotação automática independente da miniatura')
    src = replace_one(src, 'if(auto&&!drag&&!document.hidden)',
                      'if(auto&&!drag&&!miniInteracting&&!document.hidden)',
                      'animação principal durante interação')
    src = replace_one(src, 'miniCamera.position.set(0,0,13.8);',
                      'miniCamera.position.set(0,0,13.8 * zoom);',
                      'zoom inicial da miniatura')
    return src


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--backup-root', default=str(Path.home() / 'rd-studio-backups' / 'site-mini-sync'))
    args = parser.parse_args()
    root = Path(args.repo).expanduser().resolve(strict=True)
    if not (root / '.git').exists():
        # Worktree Git usa um arquivo .git; diretório e arquivo são suportados.
        raise SystemExit('ERRO: --repo precisa apontar para um checkout Git independente')
    target = root / 'js' / 'site-v10.js'
    if not target.is_file() or target.is_symlink():
        raise SystemExit('ERRO: js/site-v10.js ausente ou symlink')
    raw = target.read_bytes()
    try:
        before = raw.decode('utf-8')
        after = transform(before)
    except (UnicodeDecodeError, ValueError) as exc:
        raise SystemExit('ERRO: '+str(exc))
    if before == after:
        print('OK: sincronização miniatura/cena já instalada; nenhuma alteração necessária.')
        return
    original_hash = hashlib.sha256(raw).hexdigest()
    print('Motor:', target)
    print('SHA-256 original:', original_hash)
    print('Mudança: arrasto da miniatura → disposição imediata dos dodecaedros;')
    print('         pinça/roda → zoom imediato nas duas visualizações; toque → navegação.')
    print('Preserva: HTML, CSS, manifesto, módulos, outros servidores e arquivos staged.')
    if not args.apply:
        print('INSPEÇÃO: nenhum arquivo alterado. Use --apply para aplicar.')
        return
    backup_root = Path(args.backup_root).expanduser().resolve()
    if backup_root == root or root in backup_root.parents:
        raise SystemExit('ERRO: backup precisa ficar fora do worktree')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')
    dest = backup_root / stamp
    dest.mkdir(parents=True, exist_ok=False)
    backup = dest / 'site-v10.js'
    backup.write_bytes(raw)
    (dest / 'sha256.txt').write_text(original_hash+'  site-v10.js\n', encoding='ascii')
    if hashlib.sha256(target.read_bytes()).hexdigest() != original_hash:
        raise SystemExit('ERRO: motor alterado durante a preparação; backup salvo; nada aplicado')
    fd,tmp = tempfile.mkstemp(prefix='.site-v10-mini-', dir=target.parent)
    try:
        with os.fdopen(fd,'wb') as out:
            out.write(after.encode('utf-8'))
            out.flush();os.fsync(out.fileno())
        os.chmod(tmp, target.stat().st_mode & 0o777)
        os.replace(tmp, target)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)
    node = shutil.which('node')
    if node:
        result = subprocess.run([node,'--check',str(target)], text=True,capture_output=True)
        if result.returncode:
            target.write_bytes(raw)
            raise SystemExit('ERRO: sintaxe JS rejeitada; original restaurado. '+result.stderr.strip())
    print('OK: sincronização aplicada somente no worktree.')
    print('Backup externo:',backup)
    print('SHA-256 novo:',hashlib.sha256(target.read_bytes()).hexdigest())
    print('Git stage/commit/push: nenhum executado.')


if __name__ == '__main__':
    main()
