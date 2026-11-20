"""Modelo explícito e auditável das vozes: sem inferir emoção nativa.

Compatível com Python 3.10+; sem dependências de terceiros para o catálogo.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import os
import json
import re
from typing import Any, Mapping

CATALOG_PATH = Path(__file__).with_name('catalogo_edge_20261119.json')
LIVE_CATALOG_PATH = Path(os.environ.get('RD_EDGE_CATALOG_PATH', str(Path.home() / '.cache' / 'rd-studio' / 'edge' / 'catalogo_edge_latest.json')))
SHORT_NAME = re.compile(r'^[a-z]{2,3}(?:-[A-Za-z0-9]{2,12})+-[A-Za-z0-9]+Neural$')


def capabilities(provider: str) -> dict:
    """Somente os controles conhecidos do provedor; não adivinha estilos."""
    if provider in ('edge', 'edge-tts'):
        return {'rate_percent': True, 'pitch_hz': True, 'volume_percent': True,
                'native_style': False, 'native_emotion': False,
                'file_export': True, 'online': True}
    if provider == 'browser':
        return {'rate_ratio': True, 'pitch_ratio': True, 'volume_ratio': True,
                'native_style': False, 'native_emotion': False,
                'file_export': False, 'online': None}
    return {'parameters': 'provider-specific', 'file_export': None, 'online': None}


class Catalog:
    def __init__(self, payload: Mapping[str, Any]):
        voices = payload.get('vozes')
        if not isinstance(voices, list) or payload.get('quantidade') != len(voices):
            raise ValueError('Catálogo: quantidade inconsistente')
        ids = [x.get('ShortName') for x in voices if isinstance(x, dict)]
        if len(ids) != len(voices) or any(not isinstance(x, str) or not x for x in ids):
            raise ValueError('Catálogo: vozes inválidas')
        if len(set(ids)) != len(ids):
            raise ValueError('Catálogo: identificadores duplicados')
        self.raw = dict(payload)
        self.voices = [dict(x) for x in voices]
        self.by_id = {x['ShortName']: x for x in self.voices}

    @classmethod
    def load(cls, path: Path | None = None) -> 'Catalog':
        selected = Path(path) if path is not None else (LIVE_CATALOG_PATH if LIVE_CATALOG_PATH.is_file() else CATALOG_PATH)
        return cls(json.loads(selected.read_text(encoding='utf-8')))

    @classmethod
    async def refresh(cls, dest: Path | None = None) -> 'Catalog':
        try:
            import edge_tts
        except ImportError:
            raise RuntimeError('Instale edge-tts no Python do Estúdio') from None
        raw = await edge_tts.list_voices()
        updated = cls({'provider': 'edge-tts', 'quantidade': len(raw), 'vozes': raw})
        save_to = Path(dest or LIVE_CATALOG_PATH)
        save_to.parent.mkdir(parents=True, exist_ok=True)
        import tempfile
        with tempfile.NamedTemporaryFile(dir=save_to.parent, prefix='.rd_edge_', suffix='.json',mode='w',encoding='utf-8',delete=False) as temp:
            tmp=Path(temp.name)
            from datetime import datetime,timezone
            json.dump({'provider':'edge-tts','quantidade':len(raw),'obtido_em_utc':datetime.now(timezone.utc).isoformat(),'vozes':raw}, temp,ensure_ascii=False,indent=2)
        try:
            tmp.replace(save_to)
        finally:
            tmp.unlink(missing_ok=True)
        return cls.load(save_to)

    def require(self, short_name: str) -> dict:
        try:
            return self.by_id[short_name]
        except KeyError:
            raise ValueError(f'Voz Edge não registrada no catálogo: {short_name}') from None

    def normalized(self) -> dict:
        return {
            'version': 1,
            'source': self.raw.get('obtido_em_utc'),
            'count': len(self.voices),
            'provider': 'edge',
            'capabilities': capabilities('edge'),
            'voices': [
                {'provider': 'edge', 'voice_id': v['ShortName'],
                 'id': 'edge:' + v['ShortName'],
                 'name': v.get('FriendlyName') or v['ShortName'],
                 'locale': v.get('Locale', ''),
                 'gender': v.get('Gender'),
                 'personalities': v.get('VoiceTag', {}).get('VoicePersonalities', []),
                 'categories': v.get('VoiceTag', {}).get('ContentCategories', []),
                 'raw': v}
                for v in self.voices
            ]
        }


def normalize_voice(value: Any) -> dict:
    """Reconhece identidade do provedor sem reescrever identidades antigas."""
    if isinstance(value, str):
        if value.startswith('edge:'):
            return {'provider': 'edge', 'voice_id': value[5:]}
        if value.startswith('browser:'):
            return {'provider': 'browser', 'voice_id': value[8:]}
        if value.startswith('piper:'):
            return {'provider': 'piper', 'voice_id': value[6:]}
        if value.startswith('kokoro:'):
            return {'provider': 'kokoro', 'voice_id': value[7:]}
        # Sem marcador: preserva valor; NÃO presumir Edge.
        return {'provider': 'legacy', 'voice_id': value}
    if not isinstance(value, Mapping):
        raise ValueError('Voz deve ser identificador ou objeto')
    provider = str(value.get('provider', 'legacy'))
    voice_id = str(value.get('voice_id') or value.get('id') or '')
    if not voice_id:
        raise ValueError('Voz sem voice_id')
    if voice_id.startswith(provider + ':'):
        voice_id = voice_id[len(provider) + 1:]
    return {'provider': provider, 'voice_id': voice_id}


def resolve_voice(*, project: Mapping, scene: Mapping | None = None,
                  character: Mapping | None = None, line: Mapping | None = None) -> dict:
    """Prioridade explícita: fala > cena > personagem > projeto.

    Em cada nível, aceita `voice` ou `voz`. Valores legados não são alterados.
    """
    for obj in (line, scene, character, project):
        if not isinstance(obj, Mapping):
            continue
        candidate = obj.get('voice') if obj.get('voice') is not None else obj.get('voz')
        if candidate:
            return normalize_voice(candidate)
    raise ValueError('Nenhuma voz configurada; proibido fallback implícito')


# Intenções dramatúrgicas para edição, NÃO emoções nativas Edge. Aplicação opt-in.
# Representam aproximações por parâmetros suportados; a voz pode não soar emocional.
EXPRESSIVE_PRESETS = {
    'neutro': (0, 0, 0),
    'calmo': (-12, -4, -5),
    'alegre': (12, 8, 0),
    'solene': (-15, -6, 3),
    'tenso': (8, 5, 0),
    'triste': (-18, -8, -6),
}


def _number(obj: Mapping, key: str, limit: tuple[int, int]) -> int:
    value = obj.get(key, 0)
    if isinstance(value, bool):
        raise ValueError(f'Parâmetro {key} inválido')
    try:
        n = int(value)
    except (ValueError, TypeError, OverflowError):
        raise ValueError(f'Parâmetro {key} inválido') from None
    if str(value).strip() not in (str(n), f'+{n}') and not isinstance(value, (int,float)):
        raise ValueError(f'Parâmetro {key} inválido')
    if not limit[0] <= n <= limit[1]:
        raise ValueError(f'{key} fora do intervalo {limit[0]}..{limit[1]}')
    return n


def edge_parameters(config: Mapping) -> dict:
    """Transforma apenas rate/pitch/volume no formato aceito por edge_tts.Communicate.

    `emotion` (intenção) é guardada, mas nunca passada como `style`/SSML não suportado.
    Preset só é aplicado com explicitamente `apply_intention_preset=true`.
    """
    prosody = dict(config.get('prosody') or {})
    intention = str(config.get('intention') or config.get('emotion') or 'neutro')
    if bool(config.get('apply_intention_preset')):
        if intention not in EXPRESSIVE_PRESETS:
            raise ValueError('Intenção expressiva desconhecida')
        rate, pitch, volume = EXPRESSIVE_PRESETS[intention]
        prosody = {'rate_pct': rate, 'pitch_hz': pitch, 'volume_pct': volume, **prosody}
    rate = _number(prosody, 'rate_pct', (-90,100))
    pitch = _number(prosody, 'pitch_hz', (-100,100))
    volume = _number(prosody, 'volume_pct', (-100,100))
    fmt = lambda x, suffix: f'{x:+d}{suffix}'
    return {'rate': fmt(rate, '%'), 'pitch': fmt(pitch, 'Hz'), 'volume': fmt(volume, '%'),
            'intention': intention, 'native_style_supported': False}


def resolve_voice_config(*, project: Mapping, scene: Mapping | None = None,
                         character: Mapping | None = None, line: Mapping | None = None) -> dict:
    """Produz configuração da fala sem perder prosódia, intenção nem configurações legadas.

    Escopos: projeto -> personagem -> cena -> fala. A identidade da voz só muda
    quando explicitamente informada. Não altera os objetos originais.
    """
    config: dict[str, Any] = {'prosody': {}}
    for obj in (project, character, scene, line):
        if not isinstance(obj, Mapping):
            continue
        voice = obj.get('voice') if obj.get('voice') is not None else obj.get('voz')
        if voice:
            config.update(normalize_voice(voice))
            if isinstance(voice, Mapping):
                if voice.get('prosody'):
                    config['prosody'] = {**config['prosody'], **voice['prosody']}
                for field in ('intention', 'emotion', 'browser', 'apply_intention_preset'):
                    if field in voice:
                        config[field] = voice[field]
        if isinstance(obj.get('prosody'), Mapping):
            config['prosody'] = {**config['prosody'], **obj['prosody']}
        for field in ('intention', 'emotion', 'browser', 'apply_intention_preset'):
            if field in obj:
                config[field] = obj[field]
    if not config.get('voice_id'):
        raise ValueError('Nenhuma voz configurada; proibido fallback implícito')
    return config


def make_voice_plan(project: Mapping) -> list[dict]:
    """Transforma esquema *explicitamente declarado* em roteiro para geração.

    Entrada: {voice, characters:{id:{voice,..}}, scenes:[{id,voice,..,lines:[{
      id,character_id,text,voice,prosody,intention}]}]}. Não presume formato
    dos projetos antigos. Integração requer adaptador de migração do Estúdio.
    """
    if not isinstance(project.get('scenes'), list):
        raise ValueError('Esperado project.scenes como lista')
    chars = project.get('characters') or {}
    if not isinstance(chars, Mapping):
        raise ValueError('characters deve ser objeto de identificadores')
    plan=[]
    for scene in project['scenes']:
        if not isinstance(scene, Mapping) or not isinstance(scene.get('lines', []),list):
            raise ValueError('Cena inválida')
        for idx,line in enumerate(scene.get('lines', [])):
            if not isinstance(line, Mapping):
                raise ValueError('Fala inválida')
            character = chars.get(str(line.get('character_id','')))
            config = resolve_voice_config(project=project, character=character,scene=scene,line=line)
            plan.append({'scene_id':scene.get('id'), 'line_id':line.get('id', idx),
                         'character_id':line.get('character_id'), 'text':line.get('text',''),
                         'config':config})
    return plan
