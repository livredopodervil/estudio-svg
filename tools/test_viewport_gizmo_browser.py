#!/usr/bin/env python3
# Optional isolated Chromium test; requires Playwright and installed Chromium.
from playwright.sync_api import sync_playwright
from pathlib import Path
w=Path(__file__).resolve().parents[1]/'web';a=(w/'viewport-affine.mjs').read_text().replace('export ','');g=(w/'viewport-gizmo.mjs').read_text().split('\n',1)[1].replace('export ','');css=(w/'style.css').read_text()
with sync_playwright() as p:
 b=p.chromium.launch(executable_path=__import__('os').environ.get('CHROMIUM') or None,args=['--no-sandbox','--disable-dev-shm-usage']);page=b.new_page(viewport={'width':740,'height':480},has_touch=True);page.set_content('<style>'+css+'\n#stageShell{position:relative;width:560px;height:315px;margin:65px auto;background:#12292b}#media{position:absolute;background:#558995;touch-action:none;left:28%;top:25%;width:44%;height:50%;}</style><div id="stageShell"><div id="media" data-scene-object-id="one"></div></div>')
 page.add_script_tag(content=a+'\n'+g+'''\nconst shell=document.querySelector('#stageShell'),el=document.querySelector('#media');let o={x:.5,y:.5,w:.44,h:.5,rotation:0},active=false,commits=0;const stage=()=>shell.getBoundingClientRect();function paintMedia(){const r=stage();Object.assign(el.style,{left:(o.x-o.w/2)*100+'%',top:(o.y-o.h/2)*100+'%',width:o.w*100+'%',height:o.h*100+'%',transform:`matrix(${affine({...o,rz:o.rotation},r.width*o.w,r.height*o.h).join(',')})`});}const giz=installGizmo(shell,{read:()=>active?{object:o,pose:{...o,rz:o.rotation},stage:stage()}:null,select:()=>{active=true;giz.paint()},preview:paintMedia,commit:()=>{commits++},cancel:paintMedia});window.state=()=>({...o,commits});''')
 r=page.locator('#media').bounding_box();x=r['x']+r['width']*.6;y=r['y']+r['height']*.6;page.mouse.move(x,y);page.mouse.down();page.mouse.move(x+40,y+20,steps=8);page.mouse.up();page.wait_for_timeout(100);s=page.evaluate('state()');assert s['x']>.56 and s['commits']==1,s
 def drag(h,dx,dy):
  r=page.locator(f'[data-handle="{h}"] .rdGizmoFace').bounding_box();x=r['x']+r['width']/2;y=r['y']+r['height']/2;page.mouse.move(x,y);page.mouse.down();page.mouse.move(x+dx,y+dy,steps=6);page.mouse.up();page.wait_for_timeout(60)
 drag('1,1',20,12);s=page.evaluate('state()');assert s['w']>.44,s
 drag('rotate',35,10);s=page.evaluate('state()');assert abs(s['rotation'])>10,s
 drag('shear',20,0);s=page.evaluate('state()');assert abs(s['shear'])>.1,s
 drag('pivot',15,7);s=page.evaluate('state()');assert abs(s['pivot_x'])>.01,s
 print('Chromium isolated DOM: move, scale, rotate, shear, pivot:',s);b.close()
