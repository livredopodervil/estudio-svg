"""Extensão opt-in do projeto Estúdio SVG: definições, grupos e instâncias 2D.

Sem dependências externas. A validação de mídia existente é injetada para
manter uma única autoridade de normalização de objetos.
"""
from __future__ import annotations

import math
import re
from typing import Callable

_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_IDENTITY = [1.0, 0.0, 0.0, 1.0, 0.0, 0.0]


def _id(value, label):
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise ValueError(f"{label}: identificador inválido")
    return value


def _matrix(value):
    if value is None:
        return _IDENTITY.copy()
    if not isinstance(value, dict):
        raise ValueError("Transformação afim: objeto esperado")
    raw = value.get("matrix", _IDENTITY)
    if (not isinstance(raw, list) or len(raw) != 6
            or any(type(x) not in (float, int) or not math.isfinite(x)
                   for x in raw)):
        raise ValueError("Transformação afim: seis números finitos exigidos")
    m = [float(x) for x in raw]
    if any(abs(x) > (100 if i < 4 else 5) for i, x in enumerate(m)):
        raise ValueError("Transformação afim excede limites")
    if abs(m[0]*m[3]-m[1]*m[2]) < 1e-8:
        raise ValueError("Transformação afim singular")
    return m


def _opacity(value):
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError("Opacidade de instância inválida")
    return float(value)


def _time(value, label):
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 600:
        raise ValueError(f"{label}: tempo inválido")
    return float(value)


def _check_dag(defs):
    by_id = {d['id']: d for d in defs}
    visit = {}
    counts = {}
    def walk(key, depth):
        if depth > 12:
            raise ValueError('Profundidade de grupo excedida')
        state = visit.get(key)
        if state == 'visiting':
            raise ValueError('Grafo de instâncias contém ciclo: ' + key)
        if key not in by_id:
            raise ValueError('Referência de instância ausente: ' + key)
        if state == 'done':
            return counts[key]
        visit[key] = 'visiting'
        node = by_id[key]
        count = 1 if node['kind'] == 'media' else sum(
            walk(ch['ref'], depth+1) for ch in node['children'])
        if count > 256:
            raise ValueError('Definição de grupo excede 256 folhas')
        counts[key] = count
        visit[key] = 'done'
        return count
    for key in by_id:
        walk(key, 0)
    return counts


def normalize_library(raw, normalize_media: Callable):
    if raw is None:
        return None
    if not isinstance(raw, dict) or raw.get('format') != 'rd-instance-library-1':
        raise ValueError('Biblioteca de instâncias: formato inválido')
    definitions = raw.get('definitions')
    if not isinstance(definitions, list) or len(definitions) > 64:
        raise ValueError('Biblioteca de instâncias: até 64 definições')
    out, ids = [], set()
    for d in definitions:
        if not isinstance(d, dict):
            raise ValueError('Definição inválida')
        did = _id(d.get('id'), 'Definição')
        if did in ids:
            raise ValueError('Definição repetida: ' + did)
        ids.add(did)
        kind = d.get('kind')
        if kind == 'media':
            source = d.get('media')
            if not isinstance(source, dict) or source.get('id') != did:
                raise ValueError('ID de mídia incompatível com definição: ' + did)
            media = normalize_media([source])
            if len(media) != 1:
                raise ValueError('Mídia inválida')
            if media[0]['kind'] == 'video' and media[0].get('audio_enabled', True):
                raise ValueError('Vídeo instanciado deve ser silencioso até integrar mixagem por instância')
            out.append({'id': did, 'kind': 'media', 'media': media[0]})
        elif kind == 'group':
            children = d.get('children')
            if not isinstance(children, list) or len(children) > 32:
                raise ValueError('Grupo: até 32 arestas')
            edges, edge_ids = [], set()
            for edge in children:
                if not isinstance(edge, dict):
                    raise ValueError('Aresta de grupo inválida')
                eid = _id(edge.get('id'), 'Aresta')
                ref = _id(edge.get('ref'), 'Referência')
                if eid in edge_ids:
                    raise ValueError('Aresta repetida: ' + eid)
                edge_ids.add(eid)
                edges.append({'id': eid, 'ref': ref,
                              'transform': {'matrix': _matrix(edge.get('transform'))},
                              'opacity': _opacity(edge.get('opacity', 1))})
            out.append({'id': did, 'kind': 'group', 'children': edges})
        else:
            raise ValueError('Tipo de definição inválido: ' + str(kind))
    counts = _check_dag(out)
    return {'format': 'rd-instance-library-1', 'definitions': out}, counts


def normalize_roots(raw, counts, duration):
    if raw is None:
        return None
    if not isinstance(raw, list) or len(raw) > 32:
        raise ValueError('Cena: até 32 instâncias')
    roots, ids, total = [], set(), 0
    for entry in raw:
        if not isinstance(entry, dict):
            raise ValueError('Instância inválida')
        eid = _id(entry.get('id'), 'Instância')
        ref = _id(entry.get('ref'), 'Definição de instância')
        if eid in ids:
            raise ValueError('Instância repetida: ' + eid)
        ids.add(eid)
        if ref not in counts:
            raise ValueError('Definição de instância ausente: ' + ref)
        start = _time(entry.get('start', 0), 'Início')
        end = _time(entry.get('end', duration), 'Fim')
        if end <= start or end > duration:
            raise ValueError('Instância fora do intervalo da cena')
        total += counts[ref]
        if total > 128:
            raise ValueError('Cena excede 128 folhas de instâncias')
        roots.append({'id': eid, 'ref': ref,
                      'transform': {'matrix': _matrix(entry.get('transform'))},
                      'opacity': _opacity(entry.get('opacity', 1)),
                      'start': start, 'end': end,
                      'enabled': entry.get('enabled', True) is not False})
    return roots
