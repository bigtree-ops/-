"""인물(아바타) 영상 생성.

- sadtalker: 사진 1장 + 음성 → 입이 움직이는 말하는 인물 영상 (로컬 GPU 권장)
- static   : 사진에 천천히 줌인하는 효과만 (GPU 없어도 동작, 빠름)
"""
import time
from pathlib import Path

from .util import ffmpeg, probe_size, run


def make_avatar(image: Path, audio: Path, duration, cfg, fps, work: Path):
    engine = cfg["engine"]
    if engine == "sadtalker":
        return _sadtalker(image, audio, cfg, work)
    if engine == "static":
        return _static(image, duration, fps, work)
    raise ValueError(f"알 수 없는 avatar.engine: {engine}")


def _static(image, duration, fps, work):
    out = work / "avatar.mp4"
    w, h = probe_size(image)
    scale = min(1.0, 1080 / max(w, h))
    w, h = int(w * scale) // 2 * 2, int(h * scale) // 2 * 2
    frames = int(duration * fps) + 1
    zoom = f"1+0.08*on/{frames}"  # 영상 길이 동안 8% 천천히 줌인
    ffmpeg("-loop", 1, "-i", image, "-t", f"{duration:.3f}",
           "-vf", f"scale={w * 2}:{h * 2},zoompan=z='{zoom}':d=1:"
                  f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}:fps={fps}",
           "-pix_fmt", "yuv420p", "-c:v", "libx264", "-preset", "veryfast", out)
    return out


def _sadtalker(image, audio, cfg, work):
    sad_dir = Path(cfg["sadtalker_dir"])
    result_dir = (work / "sadtalker").resolve()
    result_dir.mkdir(parents=True, exist_ok=True)
    started = time.time()
    run([cfg["sadtalker_python"], "inference.py",
         "--driven_audio", Path(audio).resolve(),
         "--source_image", Path(image).resolve(),
         "--result_dir", result_dir,
         *cfg.get("extra_args", [])], cwd=sad_dir)
    vids = [p for p in result_dir.rglob("*.mp4") if p.stat().st_mtime >= started - 1]
    if not vids:
        raise RuntimeError("SadTalker 결과 영상을 찾지 못했습니다")
    return max(vids, key=lambda p: p.stat().st_mtime)
