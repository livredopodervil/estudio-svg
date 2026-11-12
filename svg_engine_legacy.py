#!/usr/bin/env python3
"""Motor de composição determinística: mesmo SVG na prévia e no MP4."""
from __future__ import annotations
import base64, html, io, math, mimetypes, re
from functools import lru_cache
from pathlib import Path

W0,H0=1280,720

def h(s): return html.escape(str(s),quote=True)
def nf(n): return f'{float(n):.2f}'
def clamp(x,a=0,b=1): return max(a,min(b,float(x)))
def ease(p,mode='suave'):
    p=clamp(p)
    if mode=='linear': return p
    if mode=='entrada': return p*p*p
    if mode=='saida': return 1-(1-p)**3
    return p*p*(3-2*p)
def text(x,y,s,size=30,color='#f3fafc',weight=400,opacity=1,anchor='start',extra=''):
    return f'<text x="{nf(x)}" y="{nf(y)}" font-family="DejaVu Sans, sans-serif" font-size="{int(size)}" font-weight="{int(weight)}" fill="{h(color)}" opacity="{nf(opacity)}" text-anchor="{anchor}" {extra}>{h(s)}</text>'
def lines(txt,max_chars=47,max_lines=3):
    words=str(txt).split(); out=[]; current=''
    for w in words:
        if len((current+' '+w).strip())>max_chars and current:
            out.append(current);current=w
        else: current=(current+' '+w).strip()
    if current:out.append(current)
    return out[:max_lines]

def safe_fragment(value):
    """Permite apenas elementos SVG declarativos; remove atributos perigosos."""
    import xml.etree.ElementTree as ET
    try:
        root=ET.fromstring('<root>'+str(value)[:150000]+'</root>')
    except ET.ParseError: return ''
    allowed={'svg','g','path','circle','ellipse','rect','line','polyline','polygon','text','tspan','defs','linearGradient','radialGradient','stop','clipPath','use'}
    attrs={'d','cx','cy','r','rx','ry','x','y','x1','x2','y1','y2','width','height','viewBox','points','fill','stroke','stroke-width','stroke-linecap','stroke-linejoin','stroke-dasharray','opacity','transform','style','font-size','font-family','font-weight','text-anchor','offset','stop-color','stop-opacity','id','href'}
    def sanit(el):
        tag=el.tag.split('}')[-1]
        if tag not in allowed:return ''
        props=[]
        for k,v in el.attrib.items():
            k=k.split('}')[-1]
            if k not in attrs: continue
            if any(bad in v.lower() for bad in ('javascript:','url(', 'data:', 'http:', 'https:', 'expression', '@import')):continue
            if k=='href' and not v.startswith('#'):continue
            if k=='style':
                if re.search(r'(?:url|expression|@import|behavior|\\|<|>)',v,re.I):continue
            props.append(f'{k}="{h(v[:1000])}"')
        inside=h(el.text or '') if tag in {'text','tspan'} else ''
        inside+=''.join(sanit(ch) for ch in el)
        return f'<{tag} {" ".join(props)}>{inside}</{tag}>'
    return ''.join(sanit(e) for e in root)

@lru_cache(maxsize=64)
def image_data(path):
    path=Path(path)
    if not path.is_file() or path.stat().st_size>8*1024*1024:return ''
    from PIL import Image
    with Image.open(path) as im:
        im.thumbnail((1700,1000)); im=im.convert('RGB')
        f=io.BytesIO();im.save(f,format='JPEG',quality=83)
    return 'data:image/jpeg;base64,'+base64.b64encode(f.getvalue()).decode('ascii')

def scene_svg(c,p=0,idx=0,total=1,media_dir=None,w=1280,hh=720):
    p=clamp(p);scene_type=c.get('tipo','globo')
    alias={'intro':'globo','linha':'linha','indicador':'numero','bibliografia':'cartoes'}
    scene_type=alias.get(scene_type,scene_type)
    colors=c.get('cores',{}) if isinstance(c.get('cores',{}),dict) else {}
    bg=str(colors.get('fundo','#071a27'));ac=str(colors.get('destaque','#42e5b4'));fg=str(colors.get('texto','#f2fbfc'))
    # Todas as posições usam coordenadas 1280x720. O viewBox escala sem reformatar.
    head=f'''<svg xmlns="http://www.w3.org/2000/svg" width="{int(w)}" height="{int(hh)}" viewBox="0 0 1280 720">
    <defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="{h(bg)}"/><stop offset="1" stop-color="#123a52"/></linearGradient>
    <linearGradient id="fade" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#04101c" stop-opacity="0.1"/><stop offset="1" stop-color="#04101c" stop-opacity="0.9"/></linearGradient>
    <radialGradient id="planet"><stop stop-color="#1db2b8"/><stop offset="0.85" stop-color="#145c84"/><stop offset="1" stop-color="#052942"/></radialGradient>
    </defs><rect width="1280" height="720" fill="url(#bg)"/>'''
    a=[head]
    # Grade sutil e fundo animado determinístico
    for k in range(0,1281,80):a.append(f'<path d="M{k} 0 V720" stroke="#d3f7fc" stroke-opacity="0.036"/>')
    for k in range(0,721,80):a.append(f'<path d="M0 {k} H1280" stroke="#d3f7fc" stroke-opacity="0.036"/>')
    for j in range(22):
        x=(j*197+81+11*math.sin(2*math.pi*p+j))%1280;y=(j*137+43)%720
        a.append(f'<circle cx="{nf(x)}" cy="{y}" r="{2+j%3}" fill="{h(ac)}" opacity="0.18"/>')
    motion=c.get('movimento','suave');e=ease(p,motion if motion in ('linear','entrada','saida','suave') else 'suave')
    if scene_type=='globo':
        x,y,r=870,400,169
        a.append(f'<circle cx="{x}" cy="{y}" r="{r+31}" fill="none" stroke="{h(ac)}" stroke-opacity="0.2" stroke-width="2"/>')
        a.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="url(#planet)" stroke="{h(ac)}" stroke-width="3"/>')
        a.append(f'<g transform="rotate({nf(p*25)} {x} {y})">')
        for k in (-2,-1,0,1,2):
            rw=r*(1-(abs(k)*.16))
            a.append(f'<ellipse cx="{x}" cy="{y}" rx="{nf(rw)}" ry="{r}" fill="none" stroke="#b9e8de" stroke-opacity="0.21"/>')
        for k in (-2,-1,0,1,2):
            a.append(f'<ellipse cx="{x}" cy="{y}" rx="{r}" ry="{nf(30+k*28 if 30+k*28>0 else 28)}" fill="none" stroke="#b9e8de" stroke-opacity="0.13"/>')
        a.append('</g>')
        a.append(f'<g transform="translate({nf(15*math.sin(p*6.28))},0)" fill="#60d39c" opacity=".9">')
        a.append('<path d="M 804 284 L 861 267 L 900 304 L 889 346 L 846 365 L 835 403 L 802 386 L 777 348 Z"/>')
        a.append('<path d="M 922 376 L 986 359 L 1010 403 L 977 460 L 944 495 L 915 463 Z"/>')
        a.append('</g>')
        for j in range(4):
            ang=(j/4+p*.35)*math.tau
            xx=x+(r+37)*math.cos(ang); yy=y+(r+37)*.28*math.sin(ang)
            a.append(f'<circle cx="{nf(xx)}" cy="{nf(yy)}" r="5" fill="{h(ac)}"/>')
        for j,msg in enumerate(c.get('itens', ['POPULAÇÃO','RECURSOS','TECNOLOGIA'])[:4]):
            a.append(text(80,343+j*61,msg,36,ac,700,0.55+0.45*min(1,p*4)))
    elif scene_type in ('linha','barras'):
        dat=c.get('dados',[])
        pts=[]
        for it in dat[:24]:
            try:
                if isinstance(it,dict): lab=str(it['x']);val=float(it['y'])
                else:lab=str(it[0]);val=float(it[1])
                pts.append((lab,val))
            except (TypeError,ValueError,KeyError,IndexError):pass
        if len(pts)>0:
            top,bottom,left,right=281,555,135,1185
            lo=min(0,min(v for _,v in pts));hi=max(v for _,v in pts)
            if hi<=lo:hi=lo+1
            yrange=hi-lo
            for j in range(5):
                yy=bottom-(bottom-top)*j/4
                a.append(f'<line x1="{left}" y1="{nf(yy)}" x2="{right}" y2="{nf(yy)}" stroke="#b0e2eb" stroke-opacity=".18"/>')
                a.append(text(62,yy+7,f'{lo+yrange*j/4:.1f}',18,'#afcdd9'))
            n=len(pts)
            def coord(j,val):return (left+(right-left)*j/max(1,n-1), bottom-(val-lo)/yrange*(bottom-top))
            if scene_type=='linha':
                series=[coord(j,v) for j,(_,v) in enumerate(pts)]
                cut=p*(n-1);ix=int(cut);pointlist=series[:ix+1]
                if ix<n-1: pointlist.append((series[ix][0]*(1-(cut-ix))+series[ix+1][0]*(cut-ix),series[ix][1]*(1-(cut-ix))+series[ix+1][1]*(cut-ix)))
                if len(pointlist)>1:
                    a.append(f'<polyline points="{" ".join(f"{nf(x)},{nf(y)}" for x,y in pointlist)}" stroke="{h(ac)}" stroke-width="7" stroke-linejoin="round" fill="none"/>')
                for j,((lab,v),(x,y)) in enumerate(zip(pts,series)):
                    if j<=cut+.001:
                        a.append(f'<circle cx="{nf(x)}" cy="{nf(y)}" r="7" fill="{h(ac)}" stroke="white" stroke-width="2"/>')
                        a.append(text(x, y-20,f'{v:g}',22,ac,700,anchor='middle'))
                        a.append(text(x,bottom+40,lab,18,'#b6d3dd',anchor='middle'))
            else:
                ww=(right-left)/max(1,n);bar_w=max(14,min(95,ww*.58))
                for j,(lab,v) in enumerate(pts):
                    x=left+ww*j+(ww-bar_w)/2;y=bottom-(v-lo)/yrange*(bottom-top)*e
                    a.append(f'<rect x="{nf(x)}" y="{nf(y)}" width="{nf(bar_w)}" height="{nf(bottom-y)}" rx="6" fill="{h(ac)}" opacity="{nf(.75+.2*j/max(1,n))}"/>')
                    a.append(text(x+bar_w/2,y-17,f'{v:g}',22,ac,700,anchor='middle'))
                    a.append(text(x+bar_w/2,bottom+36,lab[:14],18,'#b6d3dd',anchor='middle'))
    elif scene_type=='numero':
        val=c.get('valor',1.73);unit=c.get('unidade','TERRAS');suffix=c.get('sufixo','')
        try:num=float(val); value=(f'{num*e:.2f}' if isinstance(val,float) or '.' in str(val) else f'{num*e:.0f}').replace('.',',')
        except(ValueError,TypeError):value=str(val)
        a.append(text(160,459,value,134,ac,800))
        a.append(text(640,454,str(unit),51,fg,700))
        a.append(f'<rect x="160" y="506" width="960" height="27" rx="14" fill="#265266"/>')
        a.append(f'<rect x="160" y="506" width="{nf(960*e)}" height="27" rx="14" fill="{h(ac)}"/>')
        if suffix:a.append(text(164,581,suffix,25,'#bed8de'))
    elif scene_type=='cartoes':
        items=c.get('itens',[])[:5]
        if not items:items=['Adicione informações aos cartões']
        for j,item in enumerate(items):
            yy=256+j*min(84,342/max(1,len(items)))
            visibility=clamp((p*(len(items)+.4)-j)*2)
            a.append(f'<rect x="100" y="{nf(yy)}" width="1080" height="{min(71,305/max(1,len(items))):.1f}" rx="12" fill="#18506a" opacity="{nf(.30+.55*visibility)}"/>')
            a.append(f'<rect x="100" y="{nf(yy)}" width="7" height="{min(71,305/max(1,len(items))):.1f}" fill="{h(ac)}" opacity="{nf(visibility)}"/>')
            a.append(text(131,yy+42,str(item)[:98],min(26,32),fg,600,visibility))
    elif scene_type=='arvore':
        # Fractal recursivo: nascimento progressivo dos ramos de 0 a 1
        def branch(x,y,ang,l,depth,k):
            if depth==0:return
            q=clamp(p*7-(6-depth))
            if q<=0:return
            x2=x+math.cos(ang)*l*q;y2=y-math.sin(ang)*l*q
            a.append(f'<line x1="{nf(x)}" y1="{nf(y)}" x2="{nf(x2)}" y2="{nf(y2)}" stroke="{h(ac)}" stroke-width="{nf(max(2,depth*2.3))}" stroke-linecap="round" opacity="{nf(.4+.6*q)}"/>')
            if q>0.94:
                branch(x2,y2,ang+.35,l*.75,depth-1,k+1);branch(x2,y2,ang-.47,l*.73,depth-1,k+2)
        branch(880,605,math.pi/2,105,6,0)
        a.append(text(100,455,c.get('destaque','CRESCIMENTO'),44,ac,700))
    elif scene_type=='svg':
        safe=safe_fragment(c.get('svg','<circle cx="640" cy="400" r="130" fill="#42e5b4"/>'))
        sc=0.70+0.34*e
        dx=(1-e)*-48
        a.append(f'<g transform="translate({nf(dx)},0) translate(640,400) scale({nf(sc)}) translate(-640,-400)">{safe}</g>')
    elif scene_type=='foto':
        im_name=str(c.get('imagem',''))
        if media_dir and re.fullmatch(r'[a-zA-Z0-9_.-]+',im_name):
            uri=image_data(str(Path(media_dir)/im_name))
            if uri:
                sc=1.04+.08*e; tx=-1280*(sc-1)/2+15*math.sin(p*math.pi)
                a.append(f'<image href="{uri}" width="1280" height="720" preserveAspectRatio="xMidYMid slice" transform="translate({nf(tx)} {-720*(sc-1)/2:.2f}) scale({nf(sc)})"/>')
                a.append('<rect width="1280" height="720" fill="url(#fade)"/>')
    # Tipografia consistente
    a.append(f'<rect x="0" y="0" width="1280" height="11" fill="{h(ac)}"/>')
    a.append(text(72,54,c.get('categoria','ESTÚDIO SVG  /  DOCUMENTÁRIO'),19,ac,700,0.92))
    a.append(text(1172,54,f'{idx+1:02d} / {total:02d}',18,'#c0dbe2',700,anchor='end'))
    ttl=lines(c.get('titulo','CENA SEM TÍTULO'),40,2)
    for j,line in enumerate(ttl): a.append(text(74,118+j*55,line.upper(),43,fg,800))
    sy=118+55*(len(ttl)-1)+45
    for j,line in enumerate(lines(c.get('subtitulo',''),78,2)):
        a.append(text(76,sy+j*30,line,23,'#b3d5e1'))
    # Fonte pequena sobre fundo opaco
    a.append('<rect x="0" y="633" width="1280" height="87" fill="#061927" fill-opacity=".88"/>')
    a.append(f'<rect x="71" y="642" width="1140" height="4" rx="2" fill="#285368"/>')
    a.append(f'<rect x="71" y="642" width="{nf(1140*p)}" height="4" rx="2" fill="{h(ac)}"/>')
    fonte=c.get('fonte','')
    if fonte:a.append(text(72,681,str(fonte)[:145],18,'#bad2dc'))
    a.append('</svg>')
    return ''.join(a)
