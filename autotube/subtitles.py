"""ASS 자막 생성 (영상에 직접 입히는 용도) + SRT (유튜브 자막 업로드용)."""


def _ts_ass(t):
    cs = int(round(t * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def _ts_srt(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def wrap(text, max_chars):
    """한국어 기준 한 줄 최대 글자 수로 줄바꿈 (띄어쓰기 단위)."""
    lines, cur = [], ""
    for word in text.split():
        if cur and len(cur) + 1 + len(word) > max_chars:
            lines.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}" if cur else word
    if cur:
        lines.append(cur)
    return lines


def write_ass(cues, path, W, H, font_name, size, max_chars, align, margin_v):
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,{max(3, size // 12)},2,{align},60,60,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    rows = []
    for c in cues:
        lines = wrap(c["text"], max_chars)
        # 2줄씩 끊어서 순서대로 보여주기
        chunks = [lines[i:i + 2] for i in range(0, len(lines), 2)] or [[""]]
        span = (c["end"] - c["start"]) / len(chunks)
        for i, ch in enumerate(chunks):
            s, e = c["start"] + span * i, c["start"] + span * (i + 1)
            txt = r"\N".join(ch).replace("{", "(").replace("}", ")")
            rows.append(f"Dialogue: 0,{_ts_ass(s)},{_ts_ass(e)},Default,,0,0,0,,{txt}")
    path.write_text(header + "\n".join(rows) + "\n", encoding="utf-8")


def write_srt(cues, path):
    out = []
    for i, c in enumerate(cues, 1):
        out.append(f"{i}\n{_ts_srt(c['start'])} --> {_ts_srt(c['end'])}\n{c['text']}\n")
    path.write_text("\n".join(out), encoding="utf-8")
