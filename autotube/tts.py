"""로컬 TTS(음성 합성). 문장 단위로 합성해서 자막 타이밍을 정확히 맞춘다."""
import re
import shutil
import wave
from pathlib import Path

from .util import ffmpeg, run, wav_duration

SAMPLE_RATE = 44100


def split_sentences(text):
    """문장 단위로 자르기 (. ! ? … 와 줄바꿈 기준)."""
    parts = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        parts += [s.strip() for s in re.split(r"(?<=[.!?…~])\s+", line) if s.strip()]
    return parts


class MeloTTS:
    """MeloTTS (MIT 라이선스, 한국어 지원, CPU 동작). 최초 1회 모델 다운로드 후 오프라인 동작."""

    def __init__(self, cfg):
        from melo.api import TTS
        self.model = TTS(language=cfg["language"], device=cfg["device"])
        self.speaker = self.model.hps.data.spk2id[cfg["speaker"]]
        self.speed = cfg["speed"]

    def synth(self, text, out):
        self.model.tts_to_file(text, self.speaker, str(out), speed=self.speed, quiet=True)


class EspeakTTS:
    """espeak-ng (품질은 낮지만 설치가 매우 가벼움). 예비용."""

    def __init__(self, cfg):
        self.exe = shutil.which("espeak-ng") or shutil.which("espeak")
        if not self.exe:
            raise RuntimeError("espeak-ng 가 설치되어 있지 않습니다")
        self.rate = int(170 * cfg["speed"])

    def synth(self, text, out):
        run([self.exe, "-v", "ko", "-s", self.rate, "-w", out, text])


class DummyTTS:
    """테스트용: 글자 수에 비례하는 길이의 무음에 가까운 톤을 만든다."""

    def __init__(self, cfg):
        pass

    def synth(self, text, out):
        dur = max(0.8, len(text) * 0.11)
        ffmpeg("-f", "lavfi", "-i", f"sine=frequency=220:duration={dur}",
               "-af", "volume=0.05", out)


ENGINES = {"melotts": MeloTTS, "espeak": EspeakTTS, "dummy": DummyTTS}


def build_narration(scenes, cfg, work: Path):
    """모든 장면의 문장을 합성 → 하나의 narration.wav + 문장별 타이밍 반환.

    반환: (wav 경로, 전체 길이, cues[{start,end,text,scene}], 장면별 길이 리스트)
    """
    engine = ENGINES[cfg["engine"]](cfg)
    pause = float(cfg["pause"])
    tts_dir = work / "tts"
    tts_dir.mkdir(parents=True, exist_ok=True)

    clips, cues = [], []
    t = 0.0
    scene_durs = []
    idx = 0
    for si, scene in enumerate(scenes):
        scene_start = t
        for sent in split_sentences(scene["text"]):
            raw = tts_dir / f"{idx:03d}_raw.wav"
            std = tts_dir / f"{idx:03d}.wav"
            engine.synth(sent, raw)
            # 엔진마다 샘플레이트가 달라서 44.1kHz 모노 16bit 로 통일
            ffmpeg("-i", raw, "-ar", SAMPLE_RATE, "-ac", 1, "-sample_fmt", "s16", std)
            d = wav_duration(std)
            cues.append({"start": t, "end": t + d, "text": sent, "scene": si})
            clips.append(std)
            t += d + pause
            idx += 1
        scene_durs.append(t - scene_start)

    out = work / "narration.wav"
    silence = b"\x00\x00" * int(SAMPLE_RATE * pause)
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        for c in clips:
            with wave.open(str(c), "rb") as r:
                w.writeframes(r.readframes(r.getnframes()))
            w.writeframes(silence)
    return out, wav_duration(out), cues, scene_durs
