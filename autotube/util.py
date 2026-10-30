import json
import re
import subprocess
import wave
from pathlib import Path


def run(cmd, cwd=None):
    """외부 명령 실행. 실패 시 stderr 마지막 부분을 포함해 예외를 던진다."""
    cmd = [str(c) for c in cmd]
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout)[-3000:]
        raise RuntimeError(f"명령 실패: {' '.join(cmd[:3])} ...\n{tail}")
    return proc.stdout


def ffmpeg(*args, cwd=None):
    return run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *args], cwd=cwd)


def probe_size(path):
    out = run(["ffprobe", "-v", "error", "-select_streams", "v:0",
               "-show_entries", "stream=width,height", "-of", "json", path])
    s = json.loads(out)["streams"][0]
    return s["width"], s["height"]


def wav_duration(path):
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / w.getframerate()


def slugify(text, maxlen=40):
    text = re.sub(r"[^\w가-힣]+", "_", text).strip("_")
    return text[:maxlen] or "video"


def resolve(path, base: Path):
    """job 파일 기준 상대경로 → 없으면 현재 폴더 기준."""
    if not path:
        return None
    p = Path(path)
    if p.is_absolute():
        return p
    if (base / p).exists():
        return (base / p).resolve()
    return p.resolve()
