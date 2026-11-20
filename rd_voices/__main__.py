"""Utilitário local: python -m rd_voices list|speak|inspect."""
import argparse
import asyncio
import json
from pathlib import Path
from .core import Catalog, edge_parameters
from .edge_engine import synthesize_edge, CACHE_DIR

def main():
    p=argparse.ArgumentParser()
    sub=p.add_subparsers(dest='command', required=True)
    li=sub.add_parser('list'); li.add_argument('--locale', default='')
    sp=sub.add_parser('speak'); sp.add_argument('--voice', required=True);sp.add_argument('--text', required=True)
    sp.add_argument('--rate', type=int, default=0);sp.add_argument('--pitch', type=int, default=0);sp.add_argument('--volume', type=int, default=0)
    sub.add_parser('info')
    sub.add_parser('refresh')
    args=p.parse_args()
    cat=Catalog.load()
    if args.command == 'refresh':
        cat=asyncio.run(Catalog.refresh())
        print('Catálogo Edge atualizado:',len(cat.voices),'vozes')
    elif args.command == 'list':
        selected=[v for v in cat.voices if not args.locale or v.get('Locale','').lower()==args.locale.lower()]
        print(f'{len(selected)} vozes; total {len(cat.voices)}')
        for v in selected:
            print(f"{v['ShortName']:<40} {v.get('Locale',''):<10} {v.get('VoiceTag',{}).get('VoicePersonalities',[])}")
    elif args.command == 'info':
        print(json.dumps({'count':len(cat.voices),'locales':len(set(v.get('Locale') for v in cat.voices)),
                          'cache':str(CACHE_DIR)},ensure_ascii=False,indent=2))
    else:
        req={'text':args.text,'voice':'edge:'+args.voice,
             'prosody':{'rate_pct':args.rate,'pitch_hz':args.pitch,'volume_pct':args.volume}}
        result=asyncio.run(synthesize_edge(req))
        print(json.dumps(result,ensure_ascii=False,indent=2))
        print('Arquivo:',CACHE_DIR/(result['cache_key']+'.mp3'))
if __name__ == '__main__': main()
