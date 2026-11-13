"""Adaptadores da publicação V3: vídeo HTML5 e áudio gravado opcional.

Usar em novos builds de tools/estudio_svg_v3_integrador.py.
"""

MARK = 'ESTUDIO_V3_MEDIA_PATCH_2026_11'

def replace_one(s, old, new, description):
    count = s.count(old)
    if count != 1:
        raise RuntimeError(f'{description}: esperado 1 ocorrência, encontrado {count}: {old[:90]!r}')
    return s.replace(old,new,1)

def patch_player(s):
    if MARK in s:
        raise RuntimeError('player.js já possui a atualização de mídia')
    s=replace_one(s, '/* ESTUDIO_SVG_VETORIAL_AUDIO_PIVO_V2 */',
      '/* ESTUDIO_SVG_VETORIAL_AUDIO_PIVO_V2 */\n/* '+MARK+' */', 'marcador player')
    s=replace_one(s, "const path=source(c),rate=Number($('rate').value),known=window.__voiceFiles||{};",
      "const path=source(c),rate=Number($('rate').value),known=window.__voiceFiles||{};\n  const sceneFile=window.__voiceSceneFiles?.[scene];", 'fonte de voz')
    s=replace_one(s, 'if(path && known[path]){', 'if(sceneFile || (path && known[path])){', 'seleção de voz')
    s=replace_one(s, 'voiceEl=new Audio(known[path]);', 'voiceEl=voiceEl||new Audio();voiceEl.src=sceneFile || known[path];', 'reprodução de voz')
    s=replace_one(s, "voiceEl.removeAttribute('src');voiceEl.load();voiceEl=null;", "voiceEl.removeAttribute('src');voiceEl.load();", 'player de áudio persistente')
    s=replace_one(s, '  if(playing)nativeVoice(i);',
      '  window.StudioMedia?.scene(i,project.cenas[i],project.video,current-starts[i],playing);\n  if(playing)nativeVoice(i);', 'troca de cena')
    s=replace_one(s, '  playing=false;cancelAnimationFrame(raf);',
      '  playing=false;cancelAnimationFrame(raf);window.StudioMedia?.pause();', 'pausa')
    s=replace_one(s, "playing=true;origin=performance.now()-current*1000;$('play').textContent='Ⅱ Pausar';",
      "playing=true;window.StudioMedia?.play();origin=performance.now()-current*1000;$('play').textContent='Ⅱ Pausar';",'play')
    s=replace_one(s, "  stopVoice();\n  show(t).then(()=>{if(playing)nativeVoice(index)}).catch(e=>out(e.message));",
      "  stopVoice();window.StudioMedia?.seek(pick(t),t-starts[pick(t)]);\n  show(t).then(()=>{if(playing)nativeVoice(index)}).catch(e=>out(e.message));",'seek')
    # Detecta falha real de voz sem declarar sucesso silenciosamente.
    s=replace_one(s,"voiceEl.play().catch(e=>{out('Narração bloqueada: '+e.message);done();});",
      "voiceEl.play().catch(e=>{out('Áudio bloqueado neste navegador. Toque em Reproduzir ou abra no navegador externo: '+e.message);done();});",'aviso de áudio')
    return s

def patch_html(s):
    if 'media_layer.js?v=4' in s:
        raise RuntimeError('index.html já possui a camada de mídia')
    s=replace_one(s, '<script>window.__voiceFiles={};</script>',
      '<script>window.__voiceFiles={};window.__voiceSceneFiles={};</script>', 'mapa de voz')
    s=replace_one(s, '<script src="./player.js?v=3"></script>',
      '<script src="./media_layer.js?v=4"></script><script src="./player.js?v=4"></script>', 'scripts do player')
    s=replace_one(s, '<p id="status" role="status">Carregando…</p>',
      '<p id="status" role="status">Carregando…</p><p style="font:13px system-ui;color:#b8cfe0">Se o áudio não tocar no Facebook, use Reproduzir após abrir e, se necessário, o menu do aplicativo para abrir no navegador externo.</p>', 'aviso WebView')
    return s
