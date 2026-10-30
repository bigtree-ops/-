import copy
from pathlib import Path

import yaml

DEFAULTS = {
    "work_dir": "work",
    "output_dir": "output",
    "video": {
        "format": "shorts",          # shorts(1080x1920) | landscape(1920x1080)
        "fps": 30,
        "font_file": "C:/Windows/Fonts/malgunbd.ttf",
        "font_name": "Malgun Gothic",
        "subtitle_size": 0,          # 0 = 자동
        "max_chars_per_line": 0,     # 0 = 자동
        "avatar_layout": "auto",     # auto | full | corner
    },
    "tts": {
        "engine": "melotts",         # melotts | espeak | dummy
        "language": "KR",
        "speaker": "KR",
        "speed": 1.05,
        "device": "auto",
        "pause": 0.25,
    },
    "avatar": {
        "engine": "static",          # sadtalker | static
        "sadtalker_dir": "C:/ai/SadTalker",
        "sadtalker_python": "C:/ai/SadTalker/venv/Scripts/python.exe",
        "extra_args": ["--still", "--preprocess", "full"],
    },
    "music": {"dir": "assets/music", "volume": 0.18, "ducking": True},
    "youtube": {
        "client_secret": "secrets/client_secret.json",
        "token": "secrets/token.json",
        "default_privacy": "private",
        "category_id": "22",
        "synthetic_media": True,
    },
    "watch": {"inbox": "jobs/inbox", "interval": 30, "upload": True},
    "llm": {"ollama_url": "http://localhost:11434", "model": "qwen2.5:7b"},
}


def _merge(base, over):
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _merge(base[k], v)
        else:
            base[k] = v
    return base


def load_config(path="config.yaml"):
    cfg = copy.deepcopy(DEFAULTS)
    p = Path(path)
    if p.exists():
        _merge(cfg, yaml.safe_load(p.read_text(encoding="utf-8")))
    return cfg


def load_job(path):
    path = Path(path)
    job = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not job.get("title"):
        raise ValueError(f"{path}: title 이 필요합니다")
    if not job.get("scenes") and job.get("script"):
        job["scenes"] = [{"text": job["script"]}]
    if not job.get("scenes"):
        raise ValueError(f"{path}: scenes 또는 script 가 필요합니다")
    job["_base"] = path.parent.resolve()
    job["_path"] = path.resolve()
    return job
