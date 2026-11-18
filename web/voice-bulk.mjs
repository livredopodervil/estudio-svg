// RD Studio · auditoria declarativa de narração. Não sintetiza áudio e não altera mídias.
export function inspectNarrations(project) {
  const scenes = Array.isArray(project?.cenas) ? project.cenas : [];
  const eligible = [], disabled = [], muted = [], zeroSceneVolume = [];
  scenes.forEach((scene, index) => {
    const a = scene?.audio || {};
    const text = String(a.voice_text || scene?.fala || '').trim();
    if (!text && !a.voice_file) return;
    eligible.push(index);
    if (a.voice_enabled !== true) disabled.push(index);
    if (a.muted === true) muted.push(index);
    if (!(Number(a.voice_volume ?? 1) > 0)) zeroSceneVolume.push(index);
  });
  const zeroGlobalVolume = eligible.length > 0 && !(Number(project.volume_voz ?? 1) > 0);
  return {
    total: scenes.length, eligible, disabled, muted, zeroSceneVolume, zeroGlobalVolume,
    needsFix: disabled.length > 0 || muted.length > 0 || zeroSceneVolume.length > 0 || zeroGlobalVolume,
  };
}
export function enableNarrations(project) {
  const before = inspectNarrations(project);
  if (!before.eligible.length) return {changed: false, before, after: before};
  for (const index of before.eligible) {
    const a = project.cenas[index].audio;
    a.voice_enabled = true;
    a.muted = false;
    if (!(Number(a.voice_volume ?? 1) > 0)) a.voice_volume = 1;
  }
  if (before.zeroGlobalVolume) project.volume_voz = 1;
  return {changed: before.needsFix, before, after: inspectNarrations(project)};
}
