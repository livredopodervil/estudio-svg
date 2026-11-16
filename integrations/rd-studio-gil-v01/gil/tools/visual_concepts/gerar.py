#!/usr/bin/env python3
"""Projeto de demonstração; compila com Roteiro 0.1 já existente."""
from conceitos import *
import argparse
parser=argparse.ArgumentParser();parser.add_argument("--output",required=True,type=Path);args=parser.parse_args();ROOT=args.output.resolve();ROOT.mkdir(parents=True,exist_ok=True)
if any((ROOT/name).exists() for name in ("datacenter_base.gil","datacenter.roteiro","plano_editorial.json")):parser.error("Saída existente: use outro diretório")
DURATIONS=[4.0,3.5,3.1,4.2,3.8,3.0,4.0,3.3,3.6,3.5]
T=round(sum(DURATIONS),2)
b=Builder(DURATIONS)
# 1: terrain planning; grid, utility corridors and selected footprint.
p,s=b.shot('ANTES DO PRIMEIRO SERVIDOR','Terreno, energia, fibra e risco ambiental','Tudo começa com terreno, energia disponível, fibra e avaliação de riscos.',['mapa','rede','seleção','fluxo'])
for x in range(-5,6):b.line(p,x,-2,x,2,BLUE,.025)
for y in range(-2,3):b.line(p,-5,y,5,y,BLUE,.025)
site=b.group(p,x=0,y=0,opacity=0);b.rect(site,0,0,4.7,2.3,'#1b5b60',2);b.rect(site,0,0,4.1,1.8,DARK,3);b.text(site,0,0,'TERRENO',25,CYAN);b.reveal(s,site,.38,.35);b.pulse(s,site,.95,.35)
for x,y,lab,c in [(-5,1.65,'REDE ELÉTRICA',GOLD),(5,1.65,'FIBRA',CYAN),(-5,-1.65,'ACESSO',GREEN),(5,-1.65,'RISCO',RED)]:
 b.dot(p,x,y,.3,c);b.text(p,x,y-.37,lab,15,c);b.line(p,x,y,math.copysign(2.4,x),0,c,.045)
b.flow(p,s,(-5,1.65),(-2.4,0),3,GOLD,.3,2.3);b.flow(p,s,(5,1.65),(2.4,0),3,CYAN,.4,2.2)
# 2: assembly with 3D boxes, staggered rise by vertical displacement.
p,s=b.shot('OBRA E MONTAGEM','Fundação / estrutura / módulos técnicos','A obra prepara fundações, estrutura e áreas técnicas para receber os equipamentos.',['montagem','instância','3D','stagger'])
g=b.group(p,rx=16,ry=-24);b.box(g,0,-1.9,0,8,.28,4,'#345061')
for i,(x,z) in enumerate([(-2.7,-1),(-.9,-1),(.9,-1),(2.7,-1),(-2.7,1),(-.9,1),(.9,1),(2.7,1)]):
 q=b.box(g,x,3.4,z,1.62,2.6,1.65,'#4695a1' if i<4 else '#738ba1',opacity=0);b.reveal(s,q,.12+i*.18,.25);b.slide(s,q,x,-.4,z,.12+i*.18,.62)
b.action(s,f'girar {g} para [16,18,0] durante 3.4s');b.action(s,'mover cam para [0,0,12.8] durante 3.2s')
# 3: electric path, clear topological movement.
p,s=b.shot('INFRAESTRUTURA ELÉTRICA','Subestação, transformação e distribuição','A energia passa pela subestação e por sistemas de distribuição dimensionados para a carga.',['fluxo','pipeline','destaque'])
for x,label in [(-4.65,'REDE'),(-1.55,'SUBESTAÇÃO'),(1.55,'QUADROS'),(4.65,'RACKS')]:b.card(p,x,.4,2.65,1.25,label,GOLD)
for a,c in [((-3.27,.4),(-2.92,.4)),((-.22,.4),(.22,.4)),((2.92,.4),(3.27,.4))]:b.flow(p,s,a,c,2,GOLD,.42,2.1)
b.line(p,-4.65,-.65,4.65,-.65,GOLD,.06);b.text(p,0,-1.28,'CAPACIDADE  •  PROTEÇÃO  •  REDUNDÂNCIA',20,GOLD)
# 4: contingency branches with two feeds, fail signal and reroute.
p,s=b.shot('QUANDO A REDE FALHA','UPS sustenta a carga enquanto a reserva entra','Baterias sustentam a carga crítica até a entrada da fonte de emergência.',['redundância','falha','comutação','fluxo'])
for x,y,lab,c in [(-4,1.15,'REDE',RED),(-4,-1.15,'GERADOR',GREEN),(0,0,'UPS',GOLD),(4,0,'CARGA',CYAN)]:b.card(p,x,y,2.65,1,lab,c)
b.line(p,-2.6,1.15,-1.4,0,RED,.07);b.flow(p,s,(-2.65,-1.15),(-1.4,0),4,GREEN,.55,1.9);b.flow(p,s,(1.4,0),(2.65,0),3,CYAN,.3,2.35)
fail=b.group(p,x=-2.0,y=1.9,opacity=0);b.text(fail,0,0,'FALHA',22,RED);b.reveal(s,fail,.13,.2)
# 5: thermal circulation, schematic and repeated packets.
p,s=b.shot('O CALOR PRECISA SAIR','Captação de calor / rejeição ao ambiente','O sistema de refrigeração remove o calor produzido pelos servidores.',['ciclo','fluxo térmico','contraste'])
b.rack(p,-3.45,0,CYAN,.9);b.card(p,3.45,0,3.2,1.6,'RESFRIAMENTO',CYAN)
for yy,c,src,dst in [(1.45,RED,(-2.5,1.45),(2.5,1.45)),(-1.45,CYAN,(2.5,-1.45),(-2.5,-1.45))]:
 b.flow(p,s,src,dst,5,c,.1,2.7)
b.text(p,0,2.0,'CALOR',20,RED);b.text(p,0,-1.95,'RETORNO FRIO',20,CYAN)
# 6: racks installed in sequence with moving camera proxy, modular layout.
p,s=b.shot('RACKS E SERVIDORES','Equipamentos, cabeamento e alimentação','Racks recebem servidores, armazenamento, cabos e alimentação redundante.',['prefab','instância','montagem','detalhe'])
for i,x in enumerate([-4.4,-2.2,0,2.2,4.4]):
 g=b.rack(p,x,-.15, GREEN if i==2 else CYAN,.94);# initial invisible, reveal staggered
 idx=next(j for j,r in enumerate(b.objects) if r.startswith('object '+g+' '));b.objects[idx]=b.objects[idx].replace('"sy":0.94}', '"sy":0.94,"opacity":0}')
 b.reveal(s,g,.12+i*.23,.4)
b.text(p,0,-2.22,'COMPUTAÇÃO     /     ARMAZENAMENTO     /     REDE',17,DIM)
# 7: spine/leaf network diagram and packets moving down several branches.
p,s=b.shot('A REDE INTERLIGA TUDO','Fibra e switches conectam os equipamentos','Switches e enlaces de fibra interligam servidores, outras redes e a internet.',['grafo','roteamento','fluxo','repetição'])
for x in [-2.6,2.6]:b.card(p,x,1.55,2.2,.66,'SPINE',GOLD)
for i,x in enumerate([-4.5,-1.5,1.5,4.5]):
 b.card(p,x,-.1,1.85,.65,'LEAF',CYAN);b.card(p,x,-1.55,1.85,.66,'SERVIDORES',GREEN)
 for xx in [-2.6,2.6]:b.line(p,xx,1.18,x,.24,BLUE,.04)
 b.flow(p,s,(x,-.48),(x,-1.16),2,GREEN,.3+i*.16,2.0)
 b.flow(p,s,(-2.6 if i<2 else 2.6,1.18),(x,.24),2,CYAN,.2+i*.12,2.0)
# 8: staged tests, visible green checks represented by simple glyphs.
p,s=b.shot('COMISSIONAMENTO','Testar antes de colocar serviços em produção','Antes de operar, testes validam energia, refrigeração, rede e respostas a falhas.',['sequência','validação','mudança de estado'])
for i,(lab,detail) in enumerate([('ENERGIA','Transferência de fonte'),('TÉRMICA','Carga e temperatura'),('REDE','Perda de enlace'),('SEGURANÇA','Alarmes e acesso')]):
 y=1.75-i*1.08;b.rect(p,0,y,10.3,.86,DARK);b.text(p,-3.6,y,lab,20);b.text(p,.4,y,detail,19,DIM);q=b.group(p,x=4.25,y=y,opacity=0);b.dot(q,0,0,.47,GREEN);b.text(q,0,0,'OK',13,BG);b.reveal(s,q,.25+i*.61,.30)
# 9: moving work distribution, different from infrastructure topology.
p,s=b.shot('SERVIÇOS ENTRAM NO AR','Provisionamento e distribuição de carga','Com a infraestrutura validada, serviços são provisionados e a carga é distribuída.',['distribuição','instância','fluxo'])
b.card(p,-4.35,0,2.25,1.05,'PEDIDOS',GOLD);b.card(p,-.8,0,2.55,1.05,'ORQUESTRAÇÃO',CYAN)
b.flow(p,s,(-3.1,0),(-2.15,0),5,GOLD,.1,2.35)
for i,y in enumerate([1.58,0,-1.58]):b.card(p,4.4,y,2.6,.78,'NÓ '+str(i+1),GREEN);b.flow(p,s,(.55,0),(3.0,y),3,CYAN,.3+i*.17,2.1)
# 10: living telemetry and human monitoring.
p,s=b.shot('O TRABALHO CONTINUA','Monitorar, manter e expandir com segurança','Na operação, monitoramento e manutenção sustentam a disponibilidade e orientam a expansão.',['telemetria','gráfico','painel','conclusão'])
for x,lab,val,c in [(-4.6,'ENERGIA','CARGA',GOLD),(0,'TÉRMICA','TEMPERATURA',CYAN),(4.6,'REDE','TRÁFEGO',GREEN)]:
 b.rect(p,x,.65,3.8,2.65,DARK);b.text(p,x,1.61,lab,21,c);b.text(p,x,-.45,val,15,DIM)
 for i in range(6):
  gg=b.group(p,x=v(x-1.25+.5*i),y=.48);hh=.65+.13*(i%3);b.rect(gg,0,0,.28,hh,c);b.expr(gg,'sy',f'0.82+0.24*sin(t*{2.2+i*.2}+{i*1.3+x})')
b.text(p,0,-1.99,'DISPONIBILIDADE É UM PROCESSO CONTÍNUO',22,WHITE)
base,script=b.output();(ROOT/'datacenter_base.gil').write_text(base,encoding='utf-8');(ROOT/'datacenter.roteiro').write_text(script,encoding='utf-8')
metadata={'title':'Como se implanta um data center','duration':T,'format':'16:9','author_system':'Rogério Duarte','language':'Roteiro 0.1 + GIL timeline 0.1','shots':[{k:v for k,v in s.items() if k!='actions'} for s in b.shots]}
(ROOT/'plano_editorial.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n');print(f'{len(b.objects)} objetos; {len(b.tracks)} faixas analíticas; {len(b.shots)} planos; {T}s')
