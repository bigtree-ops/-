"""전체 영상 제작 파이프라인: 대본 → 음성 → 인물 → 배경 → 자막 → 음악 → 최종 mp4."""
import json
import random
import shutil
from datetime import datetime
from pathlib import Path

from .avatar import make_avatar
from .subtitles import write_ass, write_srt
from .tts import build_narration
from .util import ffmpeg, resolve, slugify

MUSIC_EXT = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac"}
TAIL = 0.8  # 마지막 멘트 뒤 여유(초)


def layout(fmt, mode):
    """화면 배치. 숫자는 픽셀 단위."""
    if fmt == "shorts":
        W, H = 1080, 1920
        if mode == "full":
            return dict(W=W, H=H, sub_size=78, sub_chars=14, sub_align=2, sub_margin=420)
        return dict(W=W, H=H, sub_size=70, sub_chars=15, sub_align=8, sub_margin=1020,
                    box=(40, 96, 1000, 900), S=640, ax=(W - 652) // 2, ay=H - 652 - 50)
    W, H = 1920, 1080
    if mode == "full":
        return dict(W=W, H=H, sub_size=64, sub_chars=26, sub_align=2, sub_margin=60)
    return dict(W=W, H=H, sub_size=60, sub_chars=28, sub_align=2, sub_margin=50,
                box=(60, 50, 1180, 790), S=500, ax=W - 512 - 60, ay=120)


def pick_music(job, cfg):
    m = job.get("music")
    if m in (False, "none", "off"):
        return None
    if m:
        return resolve(m, job["_base"])
    d = Path(cfg["music"]["dir"])
    tracks = [p for p in d.glob("*") if p.suffix.lower() in MUSIC_EXT] if d.exists() else []
    return random.choice(tracks) if tracks else None


def build_background(scenes, scene_durs, L, fps, base, work):
    """장면별 상품 이미지 배경 클립을 만들고 하나로 이어붙인다."""
    images = [resolve(s.get("image"), base) for s in scenes]
    # 이미지 없는 장면은 앞(없으면 뒤) 장면 이미지를 이어서 사용
    last = next((i for i in images if i), None)
    for i, img in enumerate(images):
        if img:
            last = img
        else:
            images[i] = last

    W, H = L["W"], L["H"]
    bx, by, bw, bh = L["box"]
    clips = []
    for i, (img, d) in enumerate(zip(images, scene_durs)):
        if i == len(scenes) - 1:
            d += TAIL
        clip = work / f"bg_{i:02d}.mp4"
        flt = (f"[0:v]split[a][b];"
               f"[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
               f"boxblur=30:2,eq=brightness=-0.12[bg];"
               f"[b]scale={bw}:{bh}:force_original_aspect_ratio=decrease[fg];"
               f"[bg][fg]overlay={bx}+({bw}-w)/2:{by}+({bh}-h)/2,fps={fps},format=yuv420p")
        ffmpeg("-loop", 1, "-i", img, "-t", f"{d:.3f}", "-filter_complex", flt,
               "-c:v", "libx264", "-preset", "veryfast", "-crf", 18, clip)
        clips.append(clip)
    lst = work / "bg_list.txt"
    lst.write_text("".join(f"file '{c.name}'\n" for c in clips), encoding="utf-8")
    out = work / "bg.mp4"
    ffmpeg("-f", "concat", "-safe", 0, "-i", lst.name, "-c", "copy", out.name, cwd=work)
    return out


def make_video(job, cfg):
    vcfg = cfg["video"]
    fmt = job.get("format", vcfg["format"])
    fps = int(vcfg["fps"])
    scenes = job["scenes"]
    base = job["_base"]

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = f"{stamp}_{slugify(job['title'])}"
    work = (Path(cfg["work_dir"]) / name).resolve()
    out_dir = (Path(cfg["output_dir"]) / name).resolve()
    work.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[1/5] 음성 합성 ({cfg['tts']['engine']})")
    tts_cfg = {**cfg["tts"], **job.get("tts", {})}
    narration, n_dur, cues, scene_durs = build_narration(scenes, tts_cfg, work)
    total = n_dur + TAIL

    has_images = any(s.get("image") for s in scenes)
    mode = job.get("avatar_layout", vcfg["avatar_layout"])
    if mode == "auto" or (mode == "corner" and not has_images):
        mode = "corner" if has_images else "full"
    L = layout(fmt, mode)
    W, H = L["W"], L["H"]

    print(f"[2/5] 인물 영상 ({cfg['avatar']['engine']})")
    avatar_img = resolve(job.get("avatar_image") or "assets/avatar/host.png", base)
    if not avatar_img or not avatar_img.exists():
        raise FileNotFoundError(f"인물 사진이 없습니다: {avatar_img}")
    avatar = make_avatar(avatar_img, narration, total, cfg["avatar"], fps, work)

    print("[3/5] 배경/자막 준비")
    bg = build_background(scenes, scene_durs, L, fps, base, work) if mode == "corner" else None
    size = int(vcfg["subtitle_size"]) or L["sub_size"]
    chars = int(vcfg["max_chars_per_line"]) or L["sub_chars"]
    write_ass(cues, work / "subs.ass", W, H, vcfg["font_name"], size, chars,
              L["sub_align"], L["sub_margin"])
    write_srt(cues, out_dir / "subtitles.srt")
    fonts = work / "fonts"
    fonts.mkdir(exist_ok=True)
    font_file = Path(vcfg["font_file"])
    if font_file.exists():
        shutil.copy(font_file, fonts / font_file.name)
    else:
        print(f"  ! 폰트 파일 없음({font_file}) - 시스템 기본 폰트 사용")

    print("[4/5] 음악 선택")
    music = pick_music(job, cfg)
    print(f"  - {music.name if music else '음악 없음'}")

    print("[5/5] 최종 합성")
    inputs, fc = [], []
    hold = f"tpad=stop_mode=clone:stop_duration={total:.2f}"
    subs = "subtitles=subs.ass:fontsdir=fonts"
    if mode == "corner":
        inputs += ["-i", bg, "-i", avatar]
        S = L["S"]
        fc.append(f"[1:v]scale={S}:{S}:force_original_aspect_ratio=increase,crop={S}:{S},"
                  f"pad={S + 12}:{S + 12}:6:6:white,{hold},fps={fps}[av]")
        fc.append(f"[0:v]{hold}[bgv]")
        fc.append(f"[bgv][av]overlay={L['ax']}:{L['ay']},{subs},format=yuv420p[v]")
        ai = 2
    else:
        inputs += ["-i", avatar]
        fc.append(f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                  f"{hold},fps={fps},{subs},format=yuv420p[v]")
        ai = 1
    inputs += ["-i", narration]
    fmt_a = "aformat=sample_rates=44100:channel_layouts=stereo"
    fade = f"afade=t=out:st={max(0, total - 1.5):.2f}:d=1.5"
    if music:
        inputs += ["-stream_loop", "-1", "-i", music]
        vol = float(job.get("music_volume", cfg["music"]["volume"]))
        fc.append(f"[{ai + 1}:a]{fmt_a},volume={vol}[bgm]")
        if cfg["music"]["ducking"]:
            # 목소리가 나올 때 배경음악을 자동으로 줄임
            fc.append(f"[{ai}:a]{fmt_a},asplit=2[vo][sc]")
            fc.append("[bgm][sc]sidechaincompress=threshold=0.02:ratio=6:attack=15:release=350[bgd]")
        else:
            fc.append(f"[{ai}:a]{fmt_a}[vo]")
            fc.append("[bgm]anull[bgd]")
        fc.append(f"[vo]apad[vop];[vop][bgd]amix=inputs=2:duration=longest:normalize=0,{fade}[a]")
    else:
        fc.append(f"[{ai}:a]{fmt_a},apad,{fade}[a]")

    final = out_dir / "final.mp4"
    ffmpeg(*inputs, "-filter_complex", ";".join(fc), "-map", "[v]", "-map", "[a]",
           "-t", f"{total:.3f}", "-r", fps, "-c:v", "libx264", "-preset", "medium",
           "-crf", 20, "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
           "-movflags", "+faststart", final, cwd=work)

    meta = {k: v for k, v in job.items() if not k.startswith("_")}
    meta.update(video=str(final), duration=round(total, 2), format=fmt, layout=mode)
    (out_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2),
                                       encoding="utf-8")
    if not cfg.get("keep_work"):
        shutil.rmtree(work, ignore_errors=True)
    print(f"완료: {final} ({total:.1f}초)")
    return out_dir
