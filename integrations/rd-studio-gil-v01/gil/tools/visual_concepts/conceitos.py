#!/usr/bin/env python3
"""Biblioteca experimental de conceitos visuais → fonte GIL e Roteiro 0.1.
Autoria principal do sistema: Rogério Duarte. Assistência: OpenAI.
Sem dependências externas; não modifica o Workspace.
"""
import json, math
from pathlib import Path
from collections import Counter

ROOT=Path(__file__).resolve().parent
BG='#0b1724'; WHITE='#e9f5f7'; DIM='#86a5b7'; CYAN='#52d9df'; GOLD='#ffbe68'; GREEN='#80e2aa'; RED='#f07878'; BLUE='#284655'; DARK='#162d3e'
def js(x):return json.dumps(x,ensure_ascii=False,separators=(',',':'))
def v(x):return round(x,4)
class Builder:
 def __init__(self,durations):
  self.durations=list(durations);self.n=len(durations);self.duration=round(sum(durations),2)
  self.resources=[];self.objects=[];self.tracks=[];self.shots=[];self.count=Counter();self.ids=set();self.initial={}
  for id,typ,props in [('grp','group',{}),('rect','shape.rect',{'width':1,'height':1,'color':WHITE,'layer':2}),('dot','shape.circle',{'size':.2,'color':CYAN,'layer':3}),('label','text',{'text':'','fontSize':24,'color':WHITE,'layer':8}),('box','mesh.box',{'size':1,'color':BLUE,'layer':1}),('camera','camera',{'z':15,'fov':45}),('light','light.directional',{'x':-5,'y':7,'z':9,'intensity':1}),('click','audio.tone',{'frequency':330,'gain':.045,'wave':'triangle'})]:self.resources.append(f'resource {id} {typ} {js(props)}')
  self.obj('cam','camera');self.obj('sun','light');self.obj('tick','click')
  self.txt('eyebrow','-',0,3.73,'ENGENHARIA  /  INFRAESTRUTURA DIGITAL',15,DIM)
 def obj(self,id,res,parent='-',**props):
  assert id not in self.ids,id;self.ids.add(id);self.initial[id]=props.copy();self.objects.append(f'object {id} {res} {parent} {js(props)}');return id
 def gid(self,p,kind):self.count[p,kind]+=1;return f'{p}_{kind}{self.count[p,kind]}'
 def group(self,p,**props):return self.obj(self.gid(p,'g'),'grp',p,**props)
 def rect(self,p,x,y,w,h,color=BLUE,layer=2,**kw):return self.obj(self.gid(p,'r'),'rect',p,x=v(x),y=v(y),width=w,height=h,color=color,layer=layer,**kw)
 def dot(self,p,x,y,size=.19,color=CYAN,layer=4,**kw):return self.obj(self.gid(p,'d'),'dot',p,x=v(x),y=v(y),size=size,color=color,layer=layer,**kw)
 def txt(self,id,p,x,y,text,size=22,color=WHITE,**kw):return self.obj(id,'label',p,x=x,y=y,text=text,fontSize=size,color=color,**kw)
 def text(self,p,x,y,text,size=22,color=WHITE,**kw):return self.txt(self.gid(p,'t'),p,x,y,text,size,color,**kw)
 def line(self,p,x1,y1,x2,y2,color=BLUE,width=.055,layer=1):
  return self.rect(p,(x1+x2)/2,(y1+y2)/2,round(math.hypot(x2-x1,y2-y1),4),width,color,layer,rz=v(math.degrees(math.atan2(y2-y1,x2-x1))))
 def box(self,p,x,y,z,sx,sy,sz,color=BLUE,**kw):return self.obj(self.gid(p,'b'),'box',p,x=x,y=y,z=z,sx=sx,sy=sy,sz=sz,color=color,**kw)
 def expr(self,id,prop,expr):self.tracks.append(f'animate {id} {prop} {js({"expr":expr})}')
 def shot(self,title,caption,voice,concept):
  i=len(self.shots);id=f's{i+1:02d}';s={'id':id,'start':round(sum(self.durations[:i]),2),'duration':self.durations[i],'title':title,'caption':caption,'voice':voice,'concepts':concept,'actions':[]};self.shots.append(s)
  self.obj(id,'grp','-',opacity=1 if i==0 else 0)
  self.text(id,0,3.12,title,38);self.text(id,0,-3.18,caption,19,DIM)
  self.text(id,6.32,3.73,f'{i+1:02d} / {self.n:02d}',15,CYAN)
  return id,s
 def action(self,s,code,delay=0):s['actions'].append((delay,code))
 def reveal(self,s,id,delay=.2,dur=.45):self.action(s,f'aparecer {id} durante {dur}s',delay)
 def slide(self,s,id,x,y,z=0,delay=0,dur=.65):
  self.action(s,f'deslizar {id} para {js([x,y,z])} durante {dur}s',delay)
 def pulse(self,s,id,delay=.25,dur=.35):
  self.action(s,f'pulso {id} para [1.13,1.13,1] durante {round(2*dur,6)}s',delay)
 # Concrete visual concepts, composed from the existing GIL primitives.
 def card(self,p,x,y,w,h,title,accent=CYAN):
  g=self.group(p,x=x,y=y);self.rect(g,0,0,w,h,DARK);self.rect(g,-w/2+.055,0,.11,h,accent);self.text(g,0,0,title,19);return g
 def flow(self,p,s,a,b,n=4,accent=CYAN,delay=.2,dur=2.6):
  self.line(p,*a,*b,BLUE,.075)
  # All packets start at the origin, leave at staggered times and vanish upon arrival.
  for i in range(n):
   z=self.dot(p,*a,.18,accent,5,opacity=0);dt=delay+i*.25
   self.action(s,f'paralelo {{\n aparecer {z} durante 0.12s\n mover {z} para [{b[0]},{b[1]},0] durante {dur-i*.28}s\n}}',dt)
   self.action(s,f'desaparecer {z} durante 0.12s',round(dt+dur-i*.28,4))
 def rack(self,p,x,y,color=CYAN,scale=1):
  g=self.group(p,x=x,y=y,sx=scale,sy=scale);self.rect(g,0,0,1.35,3.1,DARK,2);self.rect(g,0,1.47,1.35,.15,DIM,3)
  for j in range(6):
   yy=1.12-j*.44;self.rect(g,0,yy,1.12,.33,BLUE,3);self.dot(g,.41,yy,.10,color,4);self.rect(g,-.22,yy,.42,.045,DIM,4)
  return g
 def output(self):
  base='gil timeline 0.1 {\n'+f'stage {js(dict(width=960,height=540,duration=self.duration,background=BG,camera="cam"))}\n'+'\n'.join(self.resources+self.objects+self.tracks)+'\n}\n'
  script=['roteiro 0.1 {','// Roteiro nativo 0.1; marcadores em segundos. Cortes de 0,04 s.']
  for s in self.shots:
   p=s['id'];i=int(p[1:])-1;script.append(f'marca {p} {s["start"]}s')
   script.extend([f'em {p} {{',' paralelo {'])
   if i:script.append(f' corte s{i:02d} para {p} durante 0.04s')
   script.append(' efeito tick durante 0.10s')
   for delay,code in s['actions']:
    if delay:
     script.extend([' sequencia {',f' esperar {v(delay)}s',code,' }'])
    else:script.append(code)
   script.extend([' }','}'])
  script.append('}');script='\n'.join(script)+'\n'
  assert len(self.objects)<=512,len(self.objects)
  return base,script
