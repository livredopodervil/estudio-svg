"""Conexão SVG-Edit -> Estúdio: sanitização, camadas e imagens locais.

SVG não é HTML: nunca permita scripts, foreignObject, URLs externas ou
atributos on* em arte importada. Arquivos raster são embutidos com data URI
apenas na edição e convertidos em arquivos locais imutáveis ao salvar.
"""
from __future__ import annotations
from pathlib import Path
import base64, hashlib, io, re, xml.etree.ElementTree as ET
from functools import lru_cache
from PIL import Image, ImageOps

SVG_NS='http://www.w3.org/2000/svg'
XLINK_NS='http://www.w3.org/1999/xlink'
ET.register_namespace('',SVG_NS)
ET.register_namespace('xlink',XLINK_NS)
TAGS={
 'svg','g','defs','title','desc','path','circle','ellipse','rect','line','polyline','polygon',
 'text','tspan','textPath','use','image','linearGradient','radialGradient','stop','clipPath',
 'mask','pattern','marker','symbol','filter','feGaussianBlur','feOffset','feMerge',
 'feMergeNode','feColorMatrix','feBlend','feComposite','feFlood','feMorphology',
 'animate','animateTransform','animateMotion','set'
}
ATTR={
 'id','class','data-name','data-locked','d','pathLength','cx','cy','r','rx','ry','x','y','x1','x2','y1','y2',
 'dx','dy','width','height','viewBox','preserveAspectRatio','points','fill','fill-rule',
 'fill-opacity','stroke','stroke-width','stroke-opacity','stroke-linecap','stroke-linejoin',
 'stroke-dasharray','stroke-dashoffset','stroke-miterlimit','opacity','transform',
 'style','font-size','font-family','font-weight','font-style','letter-spacing','word-spacing',
 'text-anchor','dominant-baseline','alignment-baseline','baseline-shift','text-decoration',
 'offset','stop-color','stop-opacity','gradientUnits','gradientTransform','spreadMethod',
 'patternUnits','patternContentUnits','patternTransform','maskUnits','maskContentUnits',
 'clipPathUnits','clip-path','mask','filter','marker-start','marker-mid','marker-end',
 'href','display','visibility','overflow','vector-effect','shape-rendering','paint-order',
 'color','color-interpolation-filters','flood-color','flood-opacity','in','in2',
 'result','stdDeviation','operator','k1','k2','k3','k4','mode','type','values',
 'scale','xChannelSelector','yChannelSelector','numOctaves','seed','baseFrequency',
 'begin','dur','end','repeatCount','repeatDur','attributeName','attributeType',
 'from','to','by','keyTimes','keySplines','calcMode','additive','accumulate',
 'rotate','origin','restart','min','max','fill',
}
LOCAL_REF=re.compile(r'^#[a-zA-Z_][\w.:-]*$')
URL_LOCAL=re.compile(r'url\(\s*["\']?#[A-Za-z_][\w.:-]*["\']?\s*\)',re.I)
ASSET=re.compile(r'^asset:([0-9a-f]{16}\.(?:png|jpg))$')
DATA_IMAGE=re.compile(r'^data:image/(png|jpeg|jpg|webp);base64,([a-zA-Z0-9+/=]+)$',re.I|re.S)
DANGEROUS=re.compile(r'javascript:|vbscript:|@import|expression\s*\(|-moz-binding|behavior\s*:|<|>',re.I)


def _node_local(tag):
    if '}' in tag:
        ns,local=tag[1:].split('}',1)
        if ns!=SVG_NS:return None
        return local
    return tag

def _url_references_safe(value):
    # Allow only url(#localId), not remote CSS/image references.
    v=URL_LOCAL.sub('',value)
    return not re.search(r'url\s*\(',v,re.I)

def _allowed_attr(tag,key,val):
    if key.startswith('on') or key not in ATTR or len(val)>4_000_000:return False
    if DANGEROUS.search(val) or not _url_references_safe(val):return False
    if key=='href':
        if LOCAL_REF.fullmatch(val):return True
        if tag=='image' and (ASSET.fullmatch(val) or DATA_IMAGE.fullmatch(val)):return True
        return False
    return True

def _decode_image(uri,media_dir):
    m=DATA_IMAGE.fullmatch(uri)
    if not m:raise ValueError('Formato de imagem incorporada não permitido')
    payload=m.group(2)
    if len(payload)>8_000_000:raise ValueError('Imagem maior que o limite de 6 MB')
    raw=base64.b64decode(payload,validate=True)
    if len(raw)>6_000_000:raise ValueError('Imagem incorporada maior que 6 MB')
    try:
        with Image.open(io.BytesIO(raw)) as loaded:
            im=ImageOps.exif_transpose(loaded)
            im.thumbnail((1600,1600),Image.Resampling.LANCZOS)
            rgba='A' in im.getbands() or 'transparency' in im.info
            if rgba:im=im.convert('RGBA');ext='png'
            else:im=im.convert('RGB');ext='jpg'
            output=io.BytesIO()
            if rgba:im.save(output,'PNG',optimize=True)
            else:im.save(output,'JPEG',quality=87,optimize=True)
            raw=output.getvalue()
    except (OSError,ValueError) as e:raise ValueError('Imagem inválida: '+str(e))
    stem=hashlib.sha256(raw).hexdigest()[:16]
    filename=f'{stem}.{ext}'
    target=Path(media_dir)/filename
    if not target.exists():target.write_bytes(raw)
    return 'asset:'+filename

def _inflate_image(asset_uri,media_dir):
    m=ASSET.fullmatch(asset_uri)
    if not m:return ''
    f=Path(media_dir)/m.group(1)
    if not f.is_file() or f.stat().st_size>4_000_000:return ''
    mime='image/png' if f.suffix=='.png' else 'image/jpeg'
    return 'data:'+mime+';base64,'+base64.b64encode(f.read_bytes()).decode('ascii')

def parse_svg(svg):
    if not isinstance(svg,str) or len(svg)>6_000_000:
        raise ValueError('SVG deve ser texto de no máximo 6 MB')
    if re.search(r'<!\s*(?:DOCTYPE|ENTITY)',svg,re.I):
        raise ValueError('DOCTYPE/ENTITY não permitidos no SVG')
    try:
        root=ET.fromstring(svg.strip())
        if _node_local(root.tag)=='svg':return root
    except ET.ParseError:pass
    try:
        root=ET.fromstring(f'<svg xmlns="{SVG_NS}" viewBox="0 0 1280 720">'+svg+'</svg>')
    except ET.ParseError as e:raise ValueError('SVG inválido: '+str(e))
    return root

def clean_svg(svg,media_dir,storage=True):
    root=parse_svg(svg)
    counter=[0]
    def clean(src):
        tag=_node_local(src.tag)
        if tag not in TAGS:return None
        counter[0]+=1
        if counter[0]>15000:raise ValueError('SVG contém objetos demais (máximo 15000)')
        node=ET.Element('{'+SVG_NS+'}'+tag)
        for k,v in src.attrib.items():
            key=k.split('}')[-1] if '}' in k else k
            if not _allowed_attr(tag,key,v):continue
            if key=='href' and tag=='image':
                if storage and DATA_IMAGE.fullmatch(v):v=_decode_image(v,media_dir)
                elif not storage and ASSET.fullmatch(v):v=_inflate_image(v,media_dir)
                if not v:continue
            node.set('href' if key=='href' else key,v)
        if tag in ('text','tspan','textPath','title','desc'):node.text=(src.text or '')[:10000]
        for ch in src:
            c=clean(ch)
            if c is not None:
                node.append(c)
                if tag in ('text','tspan','textPath'):c.tail=(ch.tail or '')[:10000]
        return node
    cleaned=clean(root)
    if cleaned is None or _node_local(cleaned.tag)!='svg':raise ValueError('O arquivo deve conter um SVG')
    vb=cleaned.get('viewBox','')
    try:
        nums=[float(x) for x in re.split(r'[ ,]+',vb.strip())]
        valid=len(nums)==4 and all(abs(x)<1e7 for x in nums) and nums[2]>0 and nums[3]>0
    except ValueError:valid=False
    if not valid:
        nums=[0.,0.,1280.,720.]
        cleaned.set('viewBox','0 0 1280 720')
    # The nested SVG viewport must reflect the artwork's actual canvas aspect
    # ratio, otherwise the video crops or stretches portrait drawings.
    logical_h=round(1280*nums[3]/nums[2])
    if not 320<=logical_h<=4800:raise ValueError('Altura lógica SVG inválida')
    cleaned.set('width','1280');cleaned.set('height',str(logical_h))
    return ET.tostring(cleaned,encoding='unicode')

@lru_cache(maxsize=8)
def render_fragment(fragment,media_dir):
    # Keep full nested SVG: layer names, groups and vector styles stay intact.
    # Calls repeat per video frame, so sanitize and inflate only once per unique fragment.
    return clean_svg(fragment,media_dir,storage=False)
