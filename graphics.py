"""SVG vetorial responsivo para retrato/paisagem; mesma saída na prévia e no vídeo."""
from __future__ import annotations
import base64, html, io, math, re
from pathlib import Path
from functools import lru_cache
from PIL import Image, ImageOps
from svg_engine_legacy import safe_fragment
from svg_graphic import render_fragment
from scene_animation import animate_svg_fragment, animate_image_markup, animate_markup


def esc(x):return html.escape(str(x),quote=True)
def clamp(x,a=0,b=1):return max(a,min(b,float(x)))
def fmt(x):return f'{x:.2f}'
def label(x,y,s,size=42,fill='#fff1da',weight=500,anchor='start',opacity=1):
    return f'<text x="{fmt(x)}" y="{fmt(y)}" font-family="DejaVu Sans, sans-serif" font-size="{size}" font-weight="{weight}" fill="{esc(fill)}" text-anchor="{anchor}" opacity="{fmt(opacity)}">{esc(s)}</text>'
def wrap(s,n=41,limit=3):
    words=str(s).split();ls=[];cur=''
    for word in words:
        if len((cur+' '+word).strip())>n and cur:ls.append(cur);cur=word
        else:cur=(cur+' '+word).strip()
    if cur:ls.append(cur)
    return ls[:limit]

def _image_processing(path,fit,ax,ay,bg,crop,target_h,target_w=1280):
    with Image.open(path) as raw:
        im=ImageOps.exif_transpose(raw).convert('RGB')
    if crop and len(crop)==4:
        x,y,w,h=crop
        if w>.005 and h>.005:
            x0=int(x*im.width);y0=int(y*im.height)
            im=im.crop((x0,y0,min(im.width,x0+max(1,int(w*im.width))),min(im.height,y0+max(1,int(h*im.height)))))
    tw,th=target_w,target_h
    bgim=Image.new('RGB',(tw,th),bg)
    if fit in ('contain','pad'):
        ratio=min(tw/im.width, th/im.height)
        sz=(max(1,int(im.width*ratio)),max(1,int(im.height*ratio)))
        im=im.resize(sz,Image.Resampling.LANCZOS)
        bgim.paste(im,(int((tw-sz[0])*ax),int((th-sz[1])*ay)))
    elif fit=='stretch':bgim=im.resize((tw,th),Image.Resampling.LANCZOS)
    else:
        ratio=max(tw/im.width,th/im.height)
        sz=(max(tw,int(math.ceil(im.width*ratio))),max(th,int(math.ceil(im.height*ratio))))
        im=im.resize(sz,Image.Resampling.LANCZOS)
        off=(int((sz[0]-tw)*ax),int((sz[1]-th)*ay))
        bgim=im.crop((off[0],off[1],off[0]+tw,off[1]+th))
    buff=io.BytesIO();bgim.save(buff,'JPEG',quality=82,optimize=True)
    return 'data:image/jpeg;base64,'+base64.b64encode(buff.getvalue()).decode()

@lru_cache(maxsize=10)
def image_uri(path,stamp,fit,ax,ay,bg,crop,target_h,target_w=1280):
    return _image_processing(path,fit,ax,ay,bg,crop,target_h,target_w)



def image_element(config,media_dir,bg,view_h,full=False):
    """SVG image from a local media asset; crop and placement use normalized coordinates."""
    if not isinstance(config,dict) or not config.get('arquivo') or not media_dir:return ''
    path=Path(media_dir)/config['arquivo']
    if not path.is_file():return ''
    crop=tuple(config.get('crop') or ())
    if full:
        xx=yy=0;ww=1280;hh=view_h;radius=0
    else:
        ww=max(1,int(1280*clamp(config.get('w',.41),.08,1)))
        hh=max(1,int(view_h*clamp(config.get('h',.65),.08,1)))
        xx=int(1280*clamp(config.get('x',.73))-ww/2)
        yy=int(view_h*clamp(config.get('y',.58))-hh/2)
        radius=max(10,min(30,round(min(ww,hh)*.06)))
    uri=image_uri(str(path),path.stat().st_mtime_ns,config.get('fit','cover'),
        clamp(config.get('align_x',.5)),clamp(config.get('align_y',.5)),
        config.get('bg',bg),crop,hh,ww)
    if full:return f'<image x="0" y="0" width="1280" height="{view_h}" href="{uri}"/>'
    clip='image-frame'
    return (f'<defs><clipPath id="{clip}"><rect x="{xx}" y="{yy}" width="{ww}" height="{hh}" rx="{radius}"/></clipPath></defs>'
        + (f'<rect x="{xx-6}" y="{yy+8}" width="{ww+12}" height="{hh+8}" rx="{radius}" fill="#000" opacity=".20"/>' if config.get('frame',True) else '')
        + f'<image x="{xx}" y="{yy}" width="{ww}" height="{hh}" href="{uri}" clip-path="url(#{clip})"/>')

def visualize(c,p=0,idx=0,total=1,media_dir=None,width=1280,height=720):
    p=clamp(p);height_v=round(1280*height/width)
    vc=c.get('cores',{});bg=vc.get('fundo','#241b1a');ac=vc.get('destaque','#d99a62');fg=vc.get('texto','#fff1da')
    ty=c.get('tipo','globo');e=p*p*(3-2*p) if c.get('movimento')!='linear' else p
    tall=height_v>1100;sq=height_v>900
    header_y=100;title_y=184;sub_y=304;footer_y=height_v-110
    gap=(height_v-440 if tall else height_v-370)
    main_y=440+(height_v-720)*.36
    base=f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 1280 {height_v}">'
    a=[base,
       f'<defs><linearGradient id="wash" x1="0" y1="0" x2="1" y2="1"><stop stop-color="{esc(bg)}"/><stop offset="1" stop-color="{esc(ac)}" stop-opacity=".18"/></linearGradient><linearGradient id="shade" x1="0" y1="0" x2="0" y2="1"><stop stop-color="{esc(bg)}" stop-opacity=".04"/><stop offset="1" stop-color="{esc(bg)}" stop-opacity=".84"/></linearGradient></defs>',
       f'<rect width="1280" height="{height_v}" fill="url(#wash)"/>',
       f'<ellipse cx="{1070+52*math.sin(p*math.tau)}" cy="{350+30*math.sin(p*math.pi)}" rx="510" ry="330" fill="{esc(ac)}" opacity=".065"/>',
       f'<ellipse cx="130" cy="{height_v-110}" rx="590" ry="320" fill="{esc(ac)}" opacity=".11"/>',
       f'<path d="M0 {height_v*.75:.0f} Q300 {height_v*.65:.0f} 640 {height_v*.82:.0f} T1280 {height_v*.72:.0f}" stroke="{esc(ac)}" stroke-width="2" fill="none" opacity=".20"/>']
    config=c.get('imagem',{})
    has_image=isinstance(config,dict) and bool(config.get('arquivo'))
    if has_image and config.get('modo', 'fundo' if ty=='foto' else 'quadro')=='fundo':
        markup=image_element(config,media_dir,bg,height_v,full=True)
        a.append(animate_image_markup(markup,c.get('animacoes',[]),p,(640,height_v/2)))
        a.append(f'<rect width="1280" height="{height_v}" fill="url(#shade)"/>')
    for z in range(23):
        x=(z*193+53)%1280;y=(z*283+78)%height_v
        a.append(f'<circle cx="{x}" cy="{y}" r="{2+z%3}" fill="{esc(ac)}" opacity=".16"/>')
    content_start=len(a)
    if ty=='foto':
        if not has_image:
            a.append(label(640,main_y+85,'IMPORTE UMA IMAGEM',42,ac,700,'middle'))
    elif ty=='globo':
        cy=main_y+140 if not tall else height_v*.55
        cx=855 if not tall else 640;r=210 if not tall else 305
        a.append(f'<circle cx="{cx}" cy="{cy:.1f}" r="{r}" fill="{esc(ac)}" fill-opacity=".12" stroke="{esc(ac)}" stroke-width="5"/>')
        for k in range(1,5):
            a.append(f'<ellipse cx="{cx}" cy="{cy:.1f}" rx="{r*(.2+.19*k):.1f}" ry="{r}" fill="none" stroke="{esc(ac)}" stroke-opacity=".28" stroke-width="2" transform="rotate({p*24:.1f} {cx} {cy:.1f})"/>')
        for k in range(-2,3):a.append(f'<ellipse cx="{cx}" cy="{cy:.1f}" rx="{r}" ry="{r*(.2+abs(k)*.16):.1f}" fill="none" stroke="{esc(ac)}" stroke-opacity=".22"/>')
        for j,k in enumerate(c.get('itens',[])[:4]):
            tx=125 if not tall else 235; y=main_y+20+j*70 if not tall else height_v*.76+j*75
            a.append(label(tx,y,k,34,fg,550,opacity=min(1,p*7-j*.25)))
    elif ty in ('linha','barras'):
        pts=[]
        for d in c.get('dados',[])[:24]:
            try:
                x,y=(d['x'],d['y']) if isinstance(d,dict) else d[:2]
                pts.append((str(x),float(y)))
            except (TypeError,KeyError,ValueError,IndexError):pass
        if pts:
            left,right=135,1145;top=main_y-50;bottom=height_v-260 if tall else height_v-180
            if bottom<top+200:bottom=top+240
            lo=min(0,min(z for _,z in pts));hi=max(v for _,v in pts)
            if hi-lo<1e-6:hi=lo+1
            for i in range(5):
                y=bottom-(bottom-top)*i/4
                a.append(f'<path d="M{left} {y:.1f} H{right}" stroke="{esc(ac)}" stroke-opacity=".22"/>')
                a.append(label(left-12,y+8,f'{lo+(hi-lo)*i/4:.1f}',21,fg,400,'end'))
            coords=[]
            for i,(labelx,v) in enumerate(pts):
                x=left+(right-left)*(i+.5 if ty=='barras' else i/max(1,len(pts)-1)) / (len(pts) if ty=='barras' else 1)
                y=bottom-(v-lo)/(hi-lo)*(bottom-top)
                coords.append((x,y,labelx,v))
            if ty=='linha':
                maxseg=p*(len(coords)-1)
                points=coords[:int(maxseg)+1]
                if int(maxseg)<len(coords)-1:
                    q=maxseg-int(maxseg);aa=coords[int(maxseg)];bb=coords[int(maxseg)+1]
                    points.append((aa[0]+q*(bb[0]-aa[0]),aa[1]+q*(bb[1]-aa[1]),'',0))
                if len(points)>1:a.append(f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x,y,_,_ in points)}" stroke="{esc(ac)}" stroke-width="8" fill="none" stroke-linecap="round" stroke-linejoin="round"/>')
                for i,(x,y,z,v) in enumerate(coords):
                    if i<=maxseg+.01:a.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="{esc(ac)}"/>')
            else:
                bw=(right-left)/max(1,len(pts));bw=min(100,bw*.63)
                for x,y,z,v in coords:
                    bh=(bottom-y)*e
                    a.append(f'<rect x="{x-bw/2:.1f}" y="{bottom-bh:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="9" fill="{esc(ac)}"/>')
            for x,y,z,v in coords:
                a.append(label(x,bottom+41,z[:9],19,fg,500,'middle'))
    elif ty=='numero':
        t=str(c.get('valor',''))
        yy=main_y+30 if not tall else height_v*.55
        a.append(label(640,yy,t,150 if len(t)<9 else 94,ac,800,'middle',opacity=.15+.85*e))
        a.append(label(640,yy+90,c.get('unidade',''),48,fg,700,'middle'))
        a.append(label(640,yy+165,c.get('sufixo',''),30,fg,450,'middle'))
        a.append(f'<rect x="180" y="{yy+215}" width="920" height="20" rx="10" fill="{esc(ac)}" opacity=".15"/>')
        a.append(f'<rect x="180" y="{yy+215}" width="{920*e:.1f}" height="20" rx="10" fill="{esc(ac)}"/>')
    elif ty=='cartoes':
        items=c.get('itens',[])[:8]
        step=100 if tall else 86
        start=main_y-80 if not tall else height_v*.36
        if tall and has_image and config.get('modo')=='quadro':
            photo_start=height_v*(config.get('y',.52)-config.get('h',.34)/2)
            photo_end=height_v*(config.get('y',.52)+config.get('h',.34)/2)
            needed=max(1,len(items)-1)*step+78
            # Prefer a non-overlapping column below the photo; otherwise above it.
            if photo_end+35+needed<height_v-180:start=photo_end+35
            elif 590+needed<photo_start-20:start=590
        for i,item in enumerate(items):
            y=start+i*step
            if y>height_v-180:break
            a.append(f'<rect x="102" y="{y:.1f}" width="1070" height="72" rx="20" fill="{esc(ac)}" opacity="{.22+min(.22,max(0,(p*len(items)-i)*.3)):.2f}"/>')
            a.append(label(145,y+47,str(item)[:58],31,fg,600))
    elif ty=='arvore':
        cx=640;cy=height_v-210
        def grow(x,y,a0,L,level):
            if level<=0:return
            q=clamp(p*7-(6-level));xx=x+math.cos(a0)*L*q;yy=y-math.sin(a0)*L*q
            if q<=0:return
            a.append(f'<path d="M{x:.1f} {y:.1f} L{xx:.1f} {yy:.1f}" fill="none" stroke="{esc(ac)}" stroke-width="{3*level:.1f}" stroke-linecap="round"/>')
            if q>.95:
                grow(xx,yy,a0+.42,L*.73,level-1)
                grow(xx,yy,a0-.51,L*.73,level-1)
        grow(cx,cy,math.pi/2,160 if not tall else 245,6)
    elif ty=='svg':
        fragment=render_fragment(c.get('svg',''),str(media_dir or Path('.')))
        fragment=animate_svg_fragment(fragment,c.get('animacoes',[]),p)
        # New drawings share the FULL video canvas. Legacy 1280x720 drawings
        # remain centred and unchanged until deliberately converted in the editor.
        import xml.etree.ElementTree as ET
        root_svg=ET.fromstring(fragment)
        vb=[float(v) for v in re.split(r'[ ,]+',root_svg.get('viewBox','0 0 1280 720').strip())]
        is_full=abs(vb[3]/vb[2] - height_v/1280)<.002
        if is_full:
            a.append(fragment)
        else:
            trans=(height_v-720)/2
            a.append(f'<g transform="translate(0,{trans:.1f}) translate(640,360) scale({.86+.14*e:.3f}) translate(-640,-360)">{fragment}</g>')
    if has_image and config.get('modo','fundo' if ty=='foto' else 'quadro')=='quadro':
        markup=image_element(config,media_dir,bg,height_v,full=False)
        mx=1280*clamp(config.get('x',.73));my=height_v*clamp(config.get('y',.58))
        a.append(animate_image_markup(markup,c.get('animacoes',[]),p,(mx,my)))
    if len(a)>content_start:
        content=''.join(a[content_start:]); del a[content_start:]
        a.append(animate_markup(content,c.get('animacoes',[]),p,'__conteudo__',(640,height_v/2)))
    # Header, title and footnote overlay
    a.append(f'<rect x="0" y="0" width="1280" height="11" fill="{esc(ac)}"/>')
    a.append(label(80,header_y,c.get('categoria','ESTÚDIO SVG'),23,ac,750))
    a.append(label(1170,header_y,f'{idx+1:02d}/{total:02d}',22,fg,600,'end'))
    n=0;title_parts=[];sub_parts=[]
    for j,line in enumerate(wrap(c.get('titulo',''),28 if tall else 37,3)):
        title_parts.append(label(80,title_y+j*(60 if tall else 64),line,47 if tall else 50,fg,800));n=j+1
    a.append(animate_markup(''.join(title_parts),c.get('animacoes',[]),p,'__titulo__',(640,title_y+n*24)))
    for j,line in enumerate(wrap(c.get('subtitulo',''),43 if tall else 63,2)):
        sub_parts.append(label(82,title_y+n*(60 if tall else 64)+12+j*39,line,29 if tall else 27,fg,420))
    a.append(animate_markup(''.join(sub_parts),c.get('animacoes',[]),p,'__subtitulo__',(640,title_y+n*60+45)))
    a.append(f'<rect x="0" y="{footer_y}" width="1280" height="110" fill="{esc(bg)}" opacity=".92"/>')
    a.append(f'<rect x="80" y="{footer_y+16}" width="1120" height="6" rx="3" fill="{esc(ac)}" opacity=".28"/>')
    a.append(f'<rect x="80" y="{footer_y+16}" width="{1120*p:.1f}" height="6" rx="3" fill="{esc(ac)}"/>')
    for j,line in enumerate(wrap(c.get('fonte',''),90,2)):
        a.append(label(82,footer_y+57+j*29,line,21,fg,450))
    a.append('</svg>')
    return ''.join(a)
