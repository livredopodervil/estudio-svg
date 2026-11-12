(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const name = new URL(location.href).searchParams.get('name') || 'demo_organico';
  const audio = $('audio');
  const video = $('stageVideo');
  let currentClip = '';
  let currentScene = -1;
  let controlsTimer = null;
  let data = null;
  let playing = false;
  let preparing = false;
  let framePending = false;
  let lastUpdate = 0;
  let epoch = 0;
  let raf = 0;

  const say = message => { $('msg').textContent = message; };
  const api = async (url, options = {}) => {
    const response = await fetch(url, options);
    const body = await response.json();
    if (!response.ok) throw Error(body.error || `HTTP ${response.status}`);
    return body;
  };
  const post = (url, body) => api(url, {
    method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)
  });

  const duration = () => data.durations.reduce((sum, n) => sum + n, 0);
  function sceneAt(t) {
    let at = 0;
    for (let i = 0; i < data.durations.length; i++) {
      const seconds = data.durations[i];
      if (t < at + seconds || i === data.durations.length - 1) {
        const sceneTime = Math.max(0, t - at);
        return {i, sceneTime, progress: Math.max(0, Math.min(1, sceneTime / Math.max(.001, seconds)))};
      }
      at += seconds;
    }
    return {i: 0, sceneTime: 0, progress: 0};
  }

  function fitFrame() {
    if (!data) return;
    const {width, height} = data.project.video;
    const bounds = $('screen').getBoundingClientRect();
    const scale = Math.min(bounds.width / width, bounds.height / height);
    if (!Number.isFinite(scale) || scale <= 0) return;
    $('visualFrame').style.width = `${width * scale}px`;
    $('visualFrame').style.height = `${height * scale}px`;
  }

  function syncVideo(i, sceneTime) {
    const clip = data.project.cenas[i]?.video_clipe || {};
    if (!clip.arquivo) {
      video.pause();
      video.hidden = true;
      if (currentClip) {video.removeAttribute('src'); video.load();}
      currentClip = '';
      currentScene = -1;
      return;
    }
    if (currentClip !== clip.arquivo || currentScene !== i) {
      video.pause();
      currentClip = clip.arquivo;
      currentScene = i;
      video.src = '/api/media/clip?file=' + encodeURIComponent(clip.arquivo);
      video.load();
    }
    const x = Number(clip.x ?? .5), y = Number(clip.y ?? .56);
    const w = Number(clip.w ?? .7), h = Number(clip.h ?? .4);
    Object.assign(video.style, {
      left: `${100 * (x - w / 2)}%`, top: `${100 * (y - h / 2)}%`,
      width: `${100 * w}%`, height: `${100 * h}%`,
      objectFit: clip.fit === 'contain' ? 'contain' : 'cover',
      opacity: String(clip.opacidade ?? 1)
    });
    video.muted = true; // A trilha da apresentação é reproduzida pelo mix de áudio.
    video.loop = !!clip.repetir;
    const clipTime = Number(clip.inicio || 0) + Math.max(0, sceneTime);
    const length = video.duration;
    if (!clip.repetir && Number.isFinite(length) && length > 0 && clipTime >= length) {
      video.pause(); video.hidden = true; return;
    }
    video.hidden = false;
    const target = clip.repetir && Number.isFinite(length) && length > 0
      ? clipTime % length : clipTime;
    if (video.readyState >= 1 && Number.isFinite(target) && Math.abs(video.currentTime - target) > .45) {
      try { video.currentTime = target; } catch (_) { /* metadata pode não estar pronta */ }
    }
    if (playing && video.paused) video.play().catch(() => {});
    if (!playing && !video.paused) video.pause();
  }

  async function frame(t) {
    if (framePending || !data) return;
    framePending = true;
    const {i, progress, sceneTime} = sceneAt(t);
    try {
      const response = await fetch('/api/preview', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({scene: data.project.cenas[i], video: data.project.video,
          progress, index: i, total: data.project.cenas.length})
      });
      if (!response.ok) throw Error(`HTTP ${response.status}: ${await response.text()}`);
      const svg = await response.text();
      $('stage').innerHTML = svg;
      const element = $('stage').firstElementChild;
      if (element) {
        element.style.width = '100%';
        element.style.height = '100%';
        element.setAttribute('preserveAspectRatio', 'xMidYMid meet');
      }
      syncVideo(i, sceneTime);
    } catch (error) {
      stop();
      say('Erro na prévia: ' + error.message);
    } finally {
      framePending = false;
    }
  }

  async function refresh() {
    data = await api('/api/presentation?name=' + encodeURIComponent(name));
    fitFrame();
    $('prepare').disabled = preparing;
    if (!preparing) {
      say(data.mix_ready
        ? `${data.project.cenas.length} cenas, ${duration().toFixed(1)}s. Áudio pronto para reprodução.`
        : `${data.project.cenas.length} cenas. Áudio não preparado. Toque em Preparar áudio.`);
    }
    frame(0);
  }

  async function prepareAudio() {
    if (!data || preparing || playing) return;
    preparing = true;
    $('prepare').disabled = true;
    $('start').disabled = true;
    try {
      say('Preparando narração e música no Termux…');
      const task = await post('/api/job', {name, mode: 'apresentacao-audio'});
      let finished = false;
      for (let attempt = 0; attempt < 2400; attempt++) {
        await new Promise(resolve => setTimeout(resolve, 950));
        const job = await api('/api/job/' + encodeURIComponent(task.job));
        say(`Áudio: ${job.phase || 'Processando'} (${Math.round((job.progress || 0) * 100)}%)`);
        if (job.status === 'error') throw Error(job.error || 'Falha ao preparar áudio');
        if (job.status === 'done') { finished = true; break; }
      }
      if (!finished) throw Error('Preparação excedeu o tempo limite de consulta');
      await refresh();
      if (!data.mix_ready) throw Error('O mix não foi reconhecido após a produção.');
      say('Áudio pronto. Toque em Iniciar para apresentar com som.');
    } catch (error) {
      say('Não foi possível preparar o áudio: ' + error.message);
    } finally {
      preparing = false;
      $('prepare').disabled = false;
      $('start').disabled = false;
    }
  }

  function tick(now) {
    if (!playing) return;
    const withAudio = $('usemix').checked;
    if (withAudio && audio.error) {
      stop();
      say('Falha ao reproduzir áudio. Verifique as permissões e o navegador.');
      return;
    }
    const t = withAudio ? audio.currentTime : (now - epoch) / 1000;
    if (t >= duration()) { stop(); return; }
    if (now - lastUpdate >= 90) {
      lastUpdate = now;
      frame(t);
    }
    raf = requestAnimationFrame(tick);
  }

  async function start() {
    if (!data || playing || preparing) return;
    const withAudio = $('usemix').checked;
    if (withAudio) {
      if (!data.mix_ready) {
        say('Ainda não existe áudio pronto. Toque em Preparar áudio e depois em Iniciar.');
        return;
      }
      audio.pause();
      audio.src = data.audio_url || '/api/presentation/audio?name=' + encodeURIComponent(name);
      audio.currentTime = 0;
      try {
        // Called from the user's tap, not automatically after an asynchronous job.
        await audio.play();
      } catch (error) {
        say('O navegador bloqueou a reprodução: ' + error.message + '. Toque novamente em Iniciar.');
        return;
      }
    } else {
      audio.pause();
    }
    playing = true;
    epoch = performance.now();
    lastUpdate = 0;
    document.activeElement?.blur?.(); // O foco anterior não pode reexibir a barra.
    document.body.classList.add('presenting');
    document.body.classList.remove('controls-visible');
    frame(0);
    raf = requestAnimationFrame(tick);
  }

  function stop() {
    playing = false;
    cancelAnimationFrame(raf);
    audio.pause();
    video.pause();
    if (controlsTimer) clearTimeout(controlsTimer);
    document.body.classList.remove('presenting', 'controls-visible');
    say('Apresentação parada.');
  }

  audio.addEventListener('ended', () => { if (playing) stop(); });
  $('prepare').onclick = prepareAudio;
  $('start').onclick = start;
  $('stop').onclick = stop;
  $('full').onclick = () => {
    const element = document.documentElement;
    if (!document.fullscreenElement) element.requestFullscreen?.().catch(error => say(error.message));
    else document.exitFullscreen?.();
  };
  $('screen').addEventListener('click', () => {
    if (!playing) return;
    // Ocultos durante toda a apresentação, salvo pedido explícito por toque.
    document.body.classList.add('controls-visible');
    if (controlsTimer) clearTimeout(controlsTimer);
    controlsTimer = setTimeout(() => document.body.classList.remove('controls-visible'), 3500);
  });
  window.addEventListener('resize', fitFrame);
  window.visualViewport?.addEventListener('resize', fitFrame);

  refresh().catch(error => say('Falha ao carregar apresentação: ' + error.message));
})();
