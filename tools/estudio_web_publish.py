#!/usr/bin/env python3
"""Export an Estúdio SVG JSON project as a static web-player publication.

Author: Rogério Duarte (Estúdio SVG). Integration helper, no remote actions.
The JSON schema and SVG visuals come from the installed Estúdio code. The
browser receives pre-rendered SVG frames, so it never executes arbitrary
project scripts or requires Three.js/Termux to play the publication.

Usage from the Estúdio checkout:
  python tools/estudio_web_publish.py export --project projetos/demo.json \
      --media-dir midia --output-root /tmp/site-stage --slug demo
  python tools/estudio_web_publish.py verify --output-root /tmp/site-stage

The tool adds files only to the explicitly selected output directory. Existing
publication directories are never overwritten.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# Running `python tools/estudio_web_publish.py` must resolve sibling Studio modules.
STUDIO_ROOT = Path(__file__).resolve().parents[1]
if str(STUDIO_ROOT) not in sys.path:
    sys.path.insert(0, str(STUDIO_ROOT))

SCHEMA = "studio.web-player/v1"
CATALOG = "studio.web-catalog/v1"
MAX_FRAMES = 3600
MAX_MEDIA_BYTES = 450 * 1024 * 1024
SAFE_SLUG = re.compile(r"^[a-z0-9][a-z0-9_-]{0,62}$")
DATA_RE = re.compile(r"data:image/(png|jpeg|webp);base64,([A-Za-z0-9+/=]+)")
EXT = {"png": ".png", "jpeg": ".jpg", "webp": ".webp"}
PLAYER_NAME = "estudio-player-v1.js"


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def atomic_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.parent / ("." + path.name + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


def git_info(root: Path) -> dict:
    def run(*args):
        p = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=10)
        return p.stdout.strip() if p.returncode == 0 else None
    rev = run("rev-parse", "HEAD")
    remote = run("remote", "get-url", "origin")
    diff = run("status", "--porcelain", "--untracked-files=no")
    return {"commit": rev, "repository": remote, "tracked_changes": bool(diff) if diff is not None else None}


def safe_media(media_dir: Path, filename: str) -> Path:
    if not isinstance(filename, str) or not filename or filename != Path(filename).name or filename.startswith("."):
        raise ValueError("Nome de mídia inseguro: " + repr(filename))
    p = media_dir / filename
    if p.is_symlink() or not p.is_file():
        raise FileNotFoundError("Mídia ausente ou link simbólico: " + filename)
    if p.stat().st_size > MAX_MEDIA_BYTES:
        raise ValueError("Mídia muito grande: " + filename)
    return p


def prepare_frames(project: dict, media_dir: Path, dest: Path, resources: dict) -> list:
    from graphics import visualize
    from studio_core import scene_length
    scenes = []
    total = 0
    asset_map = {}
    for i, scene in enumerate(project["cenas"]):
        fps = float(project["video"].get("draw_fps", 6))
        duration = float(scene_length(scene, project, voice=False))
        if not math.isfinite(duration) or duration <= 0 or not math.isfinite(fps) or fps <= 0:
            raise ValueError("Duração ou draw_fps inválidos")
        count = max(1, math.ceil(duration * fps))
        total += count
        if total > MAX_FRAMES:
            raise ValueError("Limite de 3600 quadros excedido; reduza draw_fps")
        frames = []
        for n in range(count):
            t = min(1.0, n / (fps * duration))
            svg = visualize(scene, t, i, len(project["cenas"]), media_dir,
                            project["video"]["width"], project["video"]["height"])
            if not isinstance(svg, str) or "<svg" not in svg:
                raise ValueError(f"Renderizador não retornou SVG na cena {i+1}")
            if re.search(r"<\s*(?:script|foreignobject)\b|javascript\s*:", svg, re.I):
                raise ValueError(f"SVG inseguro na cena {i+1}")
            def replace_image(m):
                kind, payload = m.groups()
                binary = base64.b64decode(payload, validate=True)
                digest = sha256(binary)
                name = f"assets/{digest}{EXT[kind]}"
                if name not in asset_map:
                    path = dest / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(binary)
                    resources[name] = {"sha256": digest, "bytes": len(binary)}
                    asset_map[name] = True
                return "../" + name
            svg = DATA_RE.sub(replace_image, svg)
            frame = f"frames/{i:03d}-{n:05d}.svg"
            data = svg.encode("utf-8")
            target = dest / frame
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            resources[frame] = {"sha256": sha256(data), "bytes": len(data)}
            frames.append(frame)
        audio = scene.get("audio", {}) or {}
        clip = scene.get("video_clipe", {}) or {}
        scenes.append({
            "id": scene.get("id") or f"cena-{i+1}",
            "title": scene.get("titulo", ""),
            "duration": duration,
            "fps": fps,
            "frames": frames,
            "voiceText": audio.get("voice_text", "") if audio.get("voice_enabled", False) else "",
            "voiceEnabled": bool(audio.get("voice_enabled", False)) and not audio.get("muted", False),
            "lang": "pt-BR",
            "clip": normalize_clip(clip),
        })
    return scenes


def normalize_clip(clip):
    if not clip or not clip.get("arquivo"):
        return {}
    return {
        "original": clip["arquivo"],
        "x": float(clip.get("x", .5)), "y": float(clip.get("y", .56)),
        "w": float(clip.get("w", .7)), "h": float(clip.get("h", .4)),
        "fit": clip.get("fit", "cover"),
        "opacity": float(clip.get("opacidade", 1)),
        "start": float(clip.get("inicio", 0)),
        "loop": bool(clip.get("repetir", False)),
    }


def attach_videos(scenes, media_dir: Path, dest: Path, resources: dict, video_mode: str) -> None:
    cache = {}
    for scene in scenes:
        clip = scene["clip"]
        if not clip:
            continue
        original = clip.pop("original")
        if original in cache:
            clip["file"] = cache[original]
            continue
        source = safe_media(media_dir, original)
        raw_name = sha256(source.read_bytes())[:20]
        target_name = f"media/{raw_name}.mp4"
        target = dest / target_name
        target.parent.mkdir(parents=True, exist_ok=True)
        if video_mode == "h264":
            command = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
                       "-i", str(source), "-map", "0:v:0", "-an",
                       "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast",
                       "-crf", "25", "-movflags", "+faststart", str(target)]
            p = subprocess.run(command, capture_output=True, timeout=420)
            if p.returncode or not target.is_file():
                raise RuntimeError("FFmpeg não conseguiu converter clipe: " + original + " " + p.stderr.decode(errors="replace")[-200:])
        else:
            if source.suffix.lower() != ".mp4":
                raise ValueError("Vídeo não-MP4 precisa de --video h264")
            shutil.copy2(source, target)
        content = target.read_bytes()
        if len(content) > MAX_MEDIA_BYTES:
            raise ValueError("Clipe convertido excede limite de tamanho")
        resources[target_name] = {"sha256": sha256(content), "bytes": len(content)}
        cache[original] = target_name
        clip["file"] = target_name


def build_catalog(root: Path) -> Path:
    parent = root / "apresentacoes"
    if not parent.exists():
        raise FileNotFoundError("Nenhuma publicação no diretório de saída")
    entries = []
    for path in sorted(parent.glob("*/manifest.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("schema") != SCHEMA:
            continue
        entries.append({"id": path.parent.name, "title": data.get("title", path.parent.name),
                        "manifest": f"{path.parent.name}/manifest.json",
                        "source": data.get("source", {})})
    data = {"schema": CATALOG, "publications": entries}
    out = parent / "catalog.json"
    atomic_text(out, json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    return out


def export_project(project_file: Path, media_dir: Path, root: Path, slug: str,
                   video_mode="h264", spatial_dir=None, require_clean=False) -> Path:
    if not SAFE_SLUG.fullmatch(slug):
        raise ValueError("Slug inválido: use letras minúsculas ASCII, números, hífen e sublinhado")
    if not project_file.is_file():
        raise FileNotFoundError("Projeto JSON não encontrado")
    raw = project_file.read_bytes()
    from schema import normalize
    parsed = json.loads(raw.decode("utf-8"))
    project = normalize(parsed)
    # A missing referenced image must fail: never publish a visual placeholder.
    for scene in project.get("cenas", []):
        image = scene.get("imagem") or {}
        if image.get("arquivo"):
            safe_media(media_dir, image["arquivo"])
        audio = scene.get("audio") or {}
        if audio.get("voice_enabled") and audio.get("voice_file") and not (audio.get("voice_text") or "").strip():
            raise ValueError("Locução gravada sem texto na cena " + str(scene.get("id", "?")) +
                             ": player v1 exige texto para TTS")
    studio_git = git_info(STUDIO_ROOT)
    spatial_git = git_info(Path(spatial_dir)) if spatial_dir else None
    if require_clean:
        if not studio_git["commit"] or studio_git["tracked_changes"]:
            raise ValueError("A publicação final exige commit do Estúdio e arquivos rastreados limpos")
        if spatial_dir and (not spatial_git["commit"] or spatial_git["tracked_changes"]):
            raise ValueError("SpatialSeed sem commit limpo; publicação final interrompida")
    pub_root = root / "apresentacoes"
    pub_root.mkdir(parents=True, exist_ok=True)
    destination = pub_root / slug
    if destination.exists():
        raise FileExistsError("Publicação já existe; use um novo slug ou revise manualmente")
    script_root = Path(__file__).resolve().parents[1]
    player_src = script_root / "web_player" / PLAYER_NAME
    if not player_src.is_file():
        # In a development copy the file can have an unversioned name.
        player_src = script_root / "web_player" / "estudio-player.js"
    if not player_src.is_file():
        raise FileNotFoundError("Arquivo web_player/estudio-player.js ausente")
    install_player = root / "assets" / "estudio-player" / PLAYER_NAME
    if install_player.exists() and sha256(install_player.read_bytes()) != sha256(player_src.read_bytes()):
        raise FileExistsError("Player instalado é diferente: não sobrescrever automaticamente")
    # Commit publication only after successful rendering, validation and conversion.
    tmp = Path(tempfile.mkdtemp(prefix=".estudio-player-", dir=pub_root))
    try:
        resources = {}
        scenes = prepare_frames(project, media_dir, tmp, resources)
        attach_videos(scenes, media_dir, tmp, resources, video_mode)
        info = studio_git
        manifest = {
            "schema": SCHEMA,
            "title": project.get("titulo", slug),
            "video": {"width": int(project["video"]["width"]), "height": int(project["video"]["height"])},
            "source": {"projectVersion": parsed.get("versao"), "projectSha256": sha256(raw),
                       "estudio": info, "spatialseed": {"repository": "https://github.com/livredopodervil/SpatialSeed",
                                             "revision": spatial_git["commit"] if spatial_git else None,
                                             "tracked_changes": spatial_git["tracked_changes"] if spatial_git else None,
                                             "integration": "pre-rendered-svg-only"}},
            "capabilities": {"narration": "browser-tts-optional", "spatial": "pre-rendered-svg", "videos": "muted-clips"},
            "limitations": ["music-and-effects-not-included"] if (project.get("trilha") or any((s.get("audio") or {}).get("music_file") or (s.get("audio") or {}).get("tracks") for s in project["cenas"])) else [],
            "scenes": scenes,
            "resources": resources,
        }
        (tmp / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        (tmp / "projeto.json").write_text(json.dumps(project, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        template = """<!doctype html><html lang=\"pt-BR\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>Estúdio Player</title><style>body{margin:0;background:#0d1319;color:white;font-family:system-ui;display:grid;min-height:100dvh;place-items:center;padding:12px}estudio-player{display:block;width:min(100%,780px);height:min(92dvh,850px)}</style></head><body><estudio-player src=\"manifest.json\"></estudio-player><script type=\"module\" src=\"../../assets/estudio-player/estudio-player-v1.js\"></script></body></html>"""
        (tmp / "index.html").write_text(template, encoding="utf-8")
        # Atomic directory adoption, then common assets and a fresh catalog.
        tmp.rename(destination)
        if not install_player.exists():
            install_player.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(player_src, install_player)
        build_catalog(root)
        return destination
    finally:
        if tmp.exists():
            shutil.rmtree(tmp)


def verify_root(root: Path) -> list:
    parent = root / "apresentacoes"
    catalog = json.loads((parent / "catalog.json").read_text(encoding="utf-8"))
    if catalog.get("schema") != CATALOG:
        raise ValueError("Catálogo incompatível")
    result = []
    for entry in catalog["publications"]:
        slug = entry["id"]
        if not SAFE_SLUG.fullmatch(slug):
            raise ValueError("Slug inválido no catálogo")
        pub = parent / slug
        manifest = json.loads((pub / "manifest.json").read_text(encoding="utf-8"))
        if manifest.get("schema") != SCHEMA:
            raise ValueError("Contrato inválido: " + slug)
        for rel, meta in manifest["resources"].items():
            path = pub / rel
            if path.is_symlink() or not path.is_file() or sha256(path.read_bytes()) != meta["sha256"]:
                raise ValueError("Checksum divergente: " + slug + "/" + rel)
        for scene in manifest["scenes"]:
            for f in scene["frames"]:
                if f not in manifest["resources"]:
                    raise ValueError("Quadro sem hash: " + f)
            c = scene.get("clip", {})
            if c and c.get("file") not in manifest["resources"]:
                raise ValueError("Vídeo sem hash")
        result.append(slug)
    player = root / "assets" / "estudio-player" / PLAYER_NAME
    if not player.is_file():
        raise ValueError("Módulo JS do player ausente")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sp = parser.add_subparsers(dest="command", required=True)
    exp = sp.add_parser("export")
    exp.add_argument("--project", type=Path, required=True)
    exp.add_argument("--media-dir", type=Path, required=True)
    exp.add_argument("--output-root", type=Path, required=True)
    exp.add_argument("--slug", required=True)
    exp.add_argument("--video", choices=["h264", "copy-mp4"], default="h264")
    exp.add_argument("--spatial-dir", type=Path, help="Checkout verificado do SpatialSeed para registrar commit")
    exp.add_argument("--require-clean", action="store_true", help="Rejeita estado Git rastreado não confirmado")
    check = sp.add_parser("verify")
    check.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command=="export":
            dest=export_project(args.project,args.media_dir,args.output_root,args.slug,args.video,
                                args.spatial_dir, args.require_clean)
            print("Publicação criada:", dest)
            print("Catálogo:", dest.parent / "catalog.json")
        else:
            print("Publicações verificadas:", ", ".join(verify_root(args.output_root)))
    except Exception as exc:
        print("ERRO:",exc,file=sys.stderr)
        return 1
    return 0

if __name__=="__main__":
    raise SystemExit(main())
