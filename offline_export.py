"""Estúdio SVG M1O: exportação de quadros determinísticos, segmentada e recuperável.

Não altera projetos, não depende de MediaRecorder nem do relógio de áudio.
Um único writer local serve ao navegador através do servidor HTTP loopback.
"""
from __future__ import annotations

from array import array
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from PIL import Image
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import threading
import time
import uuid
import wave

class OfflineError(ValueError):
    pass

TOKEN_RE = re.compile(r"[0-9a-f]{32}\Z")
QUALITY_VERSION = "studio-offline-m1o-1"
MAX_FRAME_BYTES = 18_000_000
MAX_SECONDS = 900
WAVES = {"sine", "square", "sawtooth", "triangle"}


def _digest(obj):
    return sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":")).encode("utf8")).hexdigest()


def _write_json(path, value):
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, path)


def _run(args, timeout=1200):
    try:
        result = subprocess.run(args, text=True, capture_output=True,
                                timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise OfflineError("Não foi possível executar FFmpeg/FFprobe: " + str(exc)) from exc
    if result.returncode:
        raise OfflineError("Falha de mídia: " + (result.stderr or result.stdout)[-1100:])
    return result.stdout


def _probe(path, *, count=True):
    args = ["ffprobe", "-v", "error"]
    if count:
        args.append("-count_frames")
    args += ["-show_entries", "stream=codec_type,codec_name,width,height,avg_frame_rate,nb_read_frames,duration,start_time,time_base:format=duration", "-of", "json", str(path)]
    return json.loads(_run(args, timeout=150))


def _float(value, default=0.0):
    try:
        n = float(value)
    except (ValueError, TypeError):
        return default
    return n if math.isfinite(n) else default


def _validate_audio(events, duration):
    if not isinstance(events, list) or len(events) > 512:
        raise OfflineError("Eventos de áudio GIL inválidos")
    clean = []
    for event in events:
        if not isinstance(event, dict):
            raise OfflineError("Evento GIL não é objeto JSON")
        try:
            t = float(event["time"])
            length = float(event["duration"])
            hz = float(event["frequency"])
            gain = float(event["gain"])
            shape = event["wave"]
        except (ValueError, TypeError, KeyError) as exc:
            raise OfflineError("Parâmetros de áudio GIL ausentes") from exc
        if (not all(map(math.isfinite, (t, length, hz, gain))) or
            not 0 <= t < duration or not 0 < length <= 90 or
            t + length > duration + .01 or not 20 <= hz <= 18000 or
            not 0 <= gain <= 1 or shape not in WAVES):
            raise OfflineError("Evento GIL fora dos limites permitidos")
        clean.append({"time": t, "duration": min(length, duration-t),
                      "frequency": hz, "gain": gain, "wave": shape})
    return sorted(clean, key=lambda x: x["time"])


def _assets_signature(project, media_dir, voice_paths):
    """Detecta troca de mídia no mesmo nome antes de reutilizar checkpoints."""
    paths = set()
    for voice in voice_paths:
        if voice:
            paths.add(Path(voice))
    def scan(node):
        if isinstance(node, dict):
            for value in node.values():
                scan(value)
        elif isinstance(node, list):
            for value in node:
                scan(value)
        elif isinstance(node, str) and len(node) < 260 and re.fullmatch(r"[\w.\- ]+\.(?:mp3|wav|m4a|aac|ogg|flac|mp4|webm|mov|mkv|m4v|png|jpg|jpeg|webp)", node, re.I):
            paths.add(Path(media_dir) / node)
    scan(project)
    listing = []
    for p in sorted(paths, key=lambda p: str(p)):
        try:
            st = p.stat()
            if p.is_symlink() or not p.is_file():
                raise OfflineError("Mídia insegura ou ausente: " + p.name)
            listing.append([str(p), st.st_size, st.st_mtime_ns])
        except FileNotFoundError:
            listing.append([str(p), None, None])
    return _digest(listing)


def _wave_at(phase, kind):
    # Phase is a normalized oscillator cycle, not radians.
    frac = phase - math.floor(phase)
    if kind == "sine":
        return math.sin(2 * math.pi * frac)
    if kind == "square":
        return 1.0 if frac < .5 else -1.0
    if kind == "triangle":
        return 1.0 - 4.0 * abs(frac - .5)
    return 2.0 * frac - 1.0


def synth_gil_wav(path, events, duration, sample_rate=48000):
    """Escreve áudio procedural em blocos; memória O(eventos + bloco)."""
    total = round(duration * sample_rate)
    starts = [(round(e["time"] * sample_rate),
               min(total, round((e["time"] + e["duration"]) * sample_rate)), e)
              for e in events]
    with wave.open(str(path), "wb") as out:
        out.setparams((1, 2, sample_rate, total, "NONE", "not compressed"))
        for base in range(0, total, 1024):
            stop = min(total, base + 1024)
            buf = array("h")
            overlapping = [(s, x, e) for s, x, e in starts if s < stop and x > base]
            for i in range(base, stop):
                value = 0.0
                for begin, end, e in overlapping:
                    if not begin <= i < end:
                        continue
                    age = (i - begin) / sample_rate
                    duration_s = (end - begin) / sample_rate
                    env = min(1., age / .005, (duration_s - age) / .02)
                    value += e["gain"] * max(0., env) * _wave_at(age * e["frequency"], e["wave"])
                buf.append(round(max(-1., min(1., value)) * 32767))
            out.writeframesraw(buf.tobytes())


class OfflineExport:
    def __init__(self, root, output, media, *, chunk_frames=48, ffmpeg="ffmpeg"):
        self.root = Path(root)
        self.output = Path(output)
        self.media = Path(media)
        self.chunk_frames = chunk_frames
        self.ffmpeg = ffmpeg
        self.lock = threading.RLock()
        if not 8 <= chunk_frames <= 240:
            raise OfflineError("Tamanho de bloco inválido")

    def _dir(self, token):
        if not isinstance(token, str) or not TOKEN_RE.fullmatch(token):
            raise OfflineError("Identificador de renderização inválido")
        path = self.root / token
        if path.is_symlink() or not path.is_dir():
            raise OfflineError("Checkpoint não encontrado")
        return path

    def _load(self, token):
        folder = self._dir(token)
        statefile = folder / "state.json"
        if statefile.is_symlink():
            raise OfflineError("Checkpoint inseguro")
        try:
            state = json.loads(statefile.read_text("utf8"))
        except (OSError, ValueError, TypeError) as exc:
            raise OfflineError("Checkpoint corrompido") from exc
        if state.get("version") != QUALITY_VERSION or state.get("token") != token:
            raise OfflineError("Versão de checkpoint incompatível")
        return folder, state

    def _verify_state(self, folder, state, *, verify_segments=False):
        segments = state.get("segments", [])
        if not isinstance(segments, list):
            raise OfflineError("Lista de segmentos inválida")
        total = state["frames"]
        for i, seg in enumerate(segments):
            start = i * state["chunk_frames"]
            count = min(state["chunk_frames"], total - start)
            if seg.get("start") != start or seg.get("count") != count:
                raise OfflineError("Ordem dos segmentos inválida")
            path = folder / "segments" / f"{i:06d}.mp4"
            if path.is_symlink() or not path.is_file() or path.stat().st_size != seg["bytes"]:
                raise OfflineError("Segmento perdido; recuperação interrompida")
            if verify_segments and sha256(path.read_bytes()).hexdigest() != seg["sha256"]:
                raise OfflineError("Segmento modificado; recuperação interrompida")
            if verify_segments:
                # Limpeza idempotente após crash entre commit do segmento e remoção dos PNGs.
                for k in range(start, start+count):
                    old = folder / "frames" / f"{k:08d}.png"
                    if old.is_symlink():
                        raise OfflineError("Quadro do checkpoint é um symlink")
                    old.unlink(missing_ok=True)
        if not (folder / "mix.wav").is_file():
            raise OfflineError("Áudio do checkpoint ausente")
        start = sum(seg["count"] for seg in segments)
        for i in range(start, min(total, start + state["chunk_frames"])):
            path = folder / "frames" / f"{i:08d}.png"
            if not path.is_file():
                return i
            if path.is_symlink() or path.stat().st_size < 50:
                raise OfflineError("Quadro persistido inválido: " + str(i))
        # O servidor pode ter sido encerrado depois do último PNG de um bloco
        # e antes de persistir o segmento. Reconstruir o bloco, sem perder o progresso.
        if start < total:
            stop = min(total, start + state["chunk_frames"])
            self._encode_chunk(folder, state, start, stop)
            return self._verify_state(folder, state, verify_segments=verify_segments)
        return total

    def start(self, project, *, durations, voices, build_mix, gil_events, fps, width, height):
        """Inicia ou retoma mesma revisão; build_mix(path) escreve WAV sem destruir anterior."""
        with self.lock:
            if (not isinstance(durations, (list, tuple)) or
                not 1 <= len(durations) <= 150 or len(durations) != len(project.get("cenas", []))):
                raise OfflineError("Plano de áudio inválido")
            if fps not in (24, 25, 30):
                raise OfflineError("FPS final não suportado")
            if (not all(isinstance(v, int) and v % 2 == 0 and 320 <= v <= 1920 for v in (width, height))):
                raise OfflineError("Resolução deve ser par e até 1920 pixels por dimensão")
            if not all(math.isfinite(x) and .5 <= x <= MAX_SECONDS for x in durations):
                raise OfflineError("Duração de cena inválida")
            duration = sum(durations)
            if not 0 < duration <= MAX_SECONDS:
                raise OfflineError("Duração total inválida")
            count = math.ceil(duration * fps - 1e-9)
            gil = _validate_audio(gil_events, duration)
            signature = _assets_signature(project, self.media, voices)
            fingerprint = _digest({"version": QUALITY_VERSION, "project": project,
                                   "fps": fps, "width": width, "height": height,
                                   "durations": durations, "assets": signature, "gil": gil})
            self.root.mkdir(parents=True, exist_ok=True)
            if self.root.is_symlink():
                raise OfflineError("Diretório de checkpoints inseguro")
            for folder in sorted(self.root.iterdir(), reverse=True):
                if not folder.is_dir() or folder.is_symlink() or not TOKEN_RE.fullmatch(folder.name):
                    continue
                meta = folder / "state.json"
                try:
                    state = json.loads(meta.read_text("utf8"))
                except (OSError, ValueError):
                    continue
                if state.get("fingerprint") == fingerprint:
                    if state.get("status") in ("preparing", "failed-preparation") or not (folder / "mix.wav").is_file():
                        if state.get("segments"):
                            raise OfflineError("Mix ausente com segmentos já persistidos; verifique a integridade do checkpoint")
                        self._ensure_mix(folder, state, build_mix)
                    if state.get("status") == "done" and not (self.output / state.get("file", "")).is_file():
                        state["status"] = "encoding"
                        state.pop("file", None)
                        _write_json(folder / "state.json", state)
                    nextframe = self._verify_state(folder, state, verify_segments=True)
                    return self._reply(state, nextframe, resumed=True)
            token = uuid.uuid4().hex
            folder = self.root / token
            folder.mkdir(mode=0o700)
            (folder / "frames").mkdir()
            (folder / "segments").mkdir()
            state = {"version": QUALITY_VERSION, "token": token, "fingerprint": fingerprint,
                     "fps": fps, "width": width, "height": height,
                     "duration": duration, "durations": list(durations), "frames": count,
                     "chunk_frames": self.chunk_frames, "gil_events": gil,
                     "segments": [], "created": int(time.time()), "status": "preparing"}
            _write_json(folder / "state.json", state)
            self._ensure_mix(folder, state, build_mix)
            return self._reply(state, 0, resumed=False)

    def _ensure_mix(self, folder, state, build_mix):
        # Crash durante geração do WAV não torna os segmentos visuais inutilizáveis.
        temporary = folder / "mix.partial.wav"
        target = folder / "mix.wav"
        if temporary.is_symlink() or target.is_symlink():
            raise OfflineError("Mix de áudio aponta para caminho inseguro")
        temporary.unlink(missing_ok=True)
        try:
            build_mix(temporary)
            if not temporary.is_file() or temporary.stat().st_size < 44:
                raise OfflineError("Mix de áudio não foi gerado")
            measured = _float(_probe(temporary, count=False).get("format", {}).get("duration"))
            if abs(measured-state["duration"]) > .055:
                raise OfflineError("Duração do mix difere da timeline")
            temporary.replace(target)
            state["status"] = "rendering"
            _write_json(folder / "state.json", state)
        except BaseException:
            state["status"] = "failed-preparation"
            _write_json(folder / "state.json", state)
            raise

    def _reply(self, state, nextframe, *, resumed=False):
        return {"token": state["token"], "fps": state["fps"],
                "width": state["width"], "height": state["height"],
                "duration": state["duration"], "durations": state["durations"],
                "frames": state["frames"], "next_frame": nextframe,
                "chunks": len(state["segments"]), "resumed": resumed,
                "finished": state.get("status") == "done",
                "file": state.get("file"), "stats": state.get("stats", {})}

    def status(self, token):
        with self.lock:
            folder, state = self._load(token)
            return self._reply(state, self._verify_state(folder, state, verify_segments=True), resumed=True)

    def upload(self, token, index, data):
        with self.lock:
            folder, state = self._load(token)
            if state.get("status") not in ("rendering", "encoding"):
                raise OfflineError("Exportação não recebe quadros neste estado")
            nextframe = self._verify_state(folder, state)
            if index != nextframe or not 0 <= index < state["frames"]:
                raise OfflineError(f"Sequência inválida: esperado {nextframe}, recebido {index}")
            if not isinstance(data, bytes) or not 100 <= len(data) <= MAX_FRAME_BYTES:
                raise OfflineError("Imagem PNG fora do limite permitido")
            if not data.startswith(b"\x89PNG\r\n\x1a\n"):
                raise OfflineError("Imagem recebida não é PNG")
            try:
                with Image.open(BytesIO(data)) as im:
                    if im.format != "PNG" or im.size != (state["width"], state["height"]):
                        raise OfflineError("Imagem com dimensões incorretas")
                    im.verify()
            except OSError as exc:
                raise OfflineError("PNG corrompido") from exc
            frame = folder / "frames" / f"{index:08d}.png"
            temp = frame.with_suffix(".tmp")
            if frame.exists() or frame.is_symlink() or temp.is_symlink():
                raise OfflineError("Quadro duplicado ou caminho inseguro")
            # Arquivo temporário incompleto deixado por desligamento abrupto.
            temp.unlink(missing_ok=True)
            with temp.open("xb") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            temp.replace(frame)
            since = time.monotonic()
            first = index // state["chunk_frames"] * state["chunk_frames"]
            stop = min(state["frames"], first + state["chunk_frames"])
            encoded = False
            if index + 1 == stop:
                self._encode_chunk(folder, state, first, stop)
                encoded = True
            nextframe = self._verify_state(folder, state)
            result = self._reply(state, nextframe)
            result["encoded_chunk"] = encoded
            result["request_seconds"] = round(time.monotonic()-since, 3)
            return result

    def _encode_chunk(self, folder, state, start, stop):
        chunk = start // state["chunk_frames"]
        dest = folder / "segments" / f"{chunk:06d}.mp4"
        partial = dest.with_suffix(".partial.mp4")
        if dest.is_symlink() or partial.is_symlink():
            raise OfflineError("Caminho de segmento inseguro")
        if dest.exists():
            # Crash entre rename do segmento e escrita de state.json.
            # PNGs originais permanecem e possibilitam recodificar.
            if not all((folder / "frames" / f"{i:08d}.png").is_file() for i in range(start, stop)):
                raise OfflineError("Bloco existente sem manifesto e quadros incompletos")
            dest.unlink()
        partial.unlink(missing_ok=True)
        count = stop-start
        cmd = [self.ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
               "-framerate", str(state["fps"]), "-start_number", str(start),
               "-i", str(folder / "frames" / "%08d.png"),
               "-frames:v", str(count), "-an", "-c:v", "libx264", "-preset", "veryfast",
               "-crf", "16", "-pix_fmt", "yuv420p", "-profile:v", "main",
               "-g", str(state["fps"]*2), "-bf", "0", "-r", str(state["fps"]),
               "-video_track_timescale", "90000", "-movflags", "+faststart", str(partial)]
        started = time.monotonic()
        _run(cmd)
        streams = _probe(partial)["streams"]
        videos = [s for s in streams if s.get("codec_type") == "video"]
        if len(videos) != 1 or int(videos[0].get("nb_read_frames") or 0) != count:
            partial.unlink(missing_ok=True)
            raise OfflineError("FFmpeg codificou quantidade incorreta de quadros")
        partial.replace(dest)
        state["segments"].append({"start": start, "count": count, "bytes": dest.stat().st_size,
                                   "sha256": sha256(dest.read_bytes()).hexdigest(),
                                   "encode_seconds": round(time.monotonic()-started, 3)})
        _write_json(folder / "state.json", state)
        for i in range(start, stop):
            (folder / "frames" / f"{i:08d}.png").unlink(missing_ok=True)

    def finish(self, token):
        with self.lock:
            folder, state = self._load(token)
            nextframe = self._verify_state(folder, state)
            if nextframe != state["frames"]:
                raise OfflineError(f"Quadros incompletos: {nextframe}/{state['frames']}")
            if state.get("status") == "done":
                out = self.output / state["file"]
                if out.is_file():
                    return {**self._reply(state, nextframe), "url": "/api/output/"+out.name, "bytes": out.stat().st_size}
                raise OfflineError("Arquivo final ausente; não sobrescrever automaticamente")
            if state.get("status") not in ("rendering", "encoding"):
                raise OfflineError("Estado incompatível com finalização")
            state["status"] = "encoding"
            _write_json(folder / "state.json", state)
            listing = folder / "list.txt"
            lines = []
            for i in range(len(state["segments"])):
                path = folder / "segments" / f"{i:06d}.mp4"
                lines.append("file '"+str(path).replace("'", "'\\''")+"'\n")
            listing.write_text("".join(lines), encoding="utf8")
            self.output.mkdir(parents=True, exist_ok=True)
            finalname = "studio-offline-"+token[:12]+".mp4"
            final = self.output / finalname
            partial = folder / "final.partial.mp4"
            partial.unlink(missing_ok=True)
            audio = folder / "mix.wav"
            gil = state["gil_events"]
            if gil:
                effects = folder / "gil-audio.wav"
                synth_gil_wav(effects, gil, state["duration"])
            cmd = [self.ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
                   "-safe", "0", "-f", "concat", "-i", str(listing), "-i", str(audio)]
            if gil:
                cmd += ["-i", str(folder / "gil-audio.wav"), "-filter_complex",
                        "[1:a:0][2:a:0]amix=inputs=2:duration=first:normalize=0[aout]",
                        "-map", "0:v:0", "-map", "[aout]"]
            else:
                cmd += ["-map", "0:v:0", "-map", "1:a:0"]
            cmd += ["-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                    "-ac", "2", "-video_track_timescale", "90000", "-movflags", "+faststart",
                    "-avoid_negative_ts", "make_zero", str(partial)]
            started = time.monotonic()
            _run(cmd)
            actual = _probe(partial)
            vids = [s for s in actual["streams"] if s.get("codec_type") == "video"]
            auds = [s for s in actual["streams"] if s.get("codec_type") == "audio"]
            expect = state["frames"]
            length = expect / state["fps"]
            if len(vids) != 1 or len(auds) != 1:
                raise OfflineError("MP4 final sem uma faixa de vídeo e uma de áudio")
            v = vids[0]
            found = int(v.get("nb_read_frames") or 0)
            clock = _float(v.get("duration"))
            measured = _float(actual["format"].get("duration"))
            if found != expect or abs(clock-length) > 1.1/state["fps"] or abs(measured-length) > .12:
                raise OfflineError(f"Validação MP4 falhou: {found}/{expect} quadros, vídeo {clock:.3f}s, esperado {length:.3f}s")
            if final.exists():
                raise OfflineError("Arquivo final já existe; não sobrescrever")
            partial.replace(final)
            state["file"] = final.name
            state["status"] = "done"
            state["stats"] = {"encoded_frames": found, "fps": state["fps"],
                              "video_seconds": clock, "audio_seconds": _float(auds[0].get("duration")),
                              "total_seconds": measured,
                              "encoding_seconds": round(time.monotonic()-started, 3),
                              "segment_encoding_seconds": round(sum(x["encode_seconds"] for x in state["segments"]), 3)}
            _write_json(folder / "state.json", state)
            return {**self._reply(state, expect), "url": "/api/output/"+final.name,
                    "bytes": final.stat().st_size}
