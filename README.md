# AutoTube — 내 컴퓨터에서 영상 제작 + 유튜브 자동 업로드

대본(글)만 넣으면 **인물 + 목소리 + 자막 + 배경음악**이 들어간 영상을 내 컴퓨터에서 만들고,
유튜브에 자동으로 올려주는 프로그램입니다. 상품 판매용 쇼츠(세로)와 일반 가로 영상 모두 지원합니다.

```
job 파일(대본+상품사진)
   │
   ├─ ① 목소리   MeloTTS  (로컬 한국어 음성 합성)
   ├─ ② 인물     SadTalker(사진이 말하는 영상) 또는 사진+줌 효과
   ├─ ③ 배경     상품 이미지 (블러 배경 + 상품 중앙 배치)
   ├─ ④ 자막     문장별 음성 길이에 맞춰 정확히 싱크
   ├─ ⑤ 음악     assets/music 에서 랜덤, 말할 때 자동으로 볼륨 낮춤
   └─ ⑥ 업로드   YouTube API (제목/설명/태그/자막/예약공개)
```

> **외부 서비스 없이 동작**: 음성·인물·자막·합성은 모두 내 PC에서 처리합니다.
> 인터넷은 ① 처음 설치할 때 프로그램/AI 모델 다운로드, ② 유튜브에 업로드할 때만 사용합니다.

---

## 1. 화면 구성

| 상품 이미지가 있을 때 (쇼츠) | 상품 이미지가 없을 때 |
|---|---|
| 위: 상품 이미지 / 가운데: 자막 / 아래: 말하는 인물 | 인물이 화면 가득 + 자막 |

`config.yaml` 의 `video.format` 을 `landscape` 로 바꾸면 가로 영상(1920x1080)이 됩니다.

---

## 2. 설치 (Windows 기준)

**필요한 것**: Windows 10/11, 여유 공간 10GB+, (인물 입 움직임을 원하면) NVIDIA 그래픽카드

1. **Python 3.10** 설치 — https://www.python.org/downloads/release/python-31011/
   (설치 화면에서 `Add python.exe to PATH` 체크)
2. 이 폴더에서 **`setup.bat` 더블클릭** → 패키지, 한국어 음성(MeloTTS), ffmpeg 자동 설치
3. 첫 영상을 만들 때 음성 모델(약 200MB)을 1회 다운로드하고, 이후에는 오프라인으로 동작합니다.

### (선택) 입이 움직이는 인물 — SadTalker
사진 1장으로 실제로 말하는 듯한 영상을 만듭니다. NVIDIA GPU 권장 (CPU는 매우 느림).

```bat
cd C:\ai
git clone https://github.com/OpenTalker/SadTalker.git
cd SadTalker
py -3.10 -m venv venv
venv\Scripts\activate
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install -r requirements.txt
REM 모델 파일: SadTalker README 의 "Download Models" 안내대로 checkpoints, gfpgan 폴더에 넣기
```
그 다음 `config.yaml` 에서:
```yaml
avatar:
  engine: sadtalker
  sadtalker_dir: C:/ai/SadTalker
  sadtalker_python: C:/ai/SadTalker/venv/Scripts/python.exe
```
GPU가 없다면 `engine: static`(기본값)으로 두세요. 사진에 천천히 줌인되는 효과로 만들어집니다.

---

## 3. 준비물 넣기

| 폴더 | 넣을 것 |
|---|---|
| `assets/avatar/` | 인물 정면 사진 (`host.png`) — 얼굴이 크고 선명할수록 좋음 |
| `assets/products/` | 상품 사진 |
| `assets/music/` | 배경음악 mp3 (여러 개 넣으면 랜덤 선택) |

> ⚠️ **저작권**: 음악은 [YouTube 오디오 보관함](https://studio.youtube.com) 등 무료 사용 가능한 곡만,
> 인물 사진은 본인 사진이거나 사용 허락받은 사진만 쓰세요. 타인 얼굴 무단 사용은 채널 정지 사유입니다.

---

## 4. 영상 만들기

영상 1개 = **job 파일(.yaml) 1개**. `jobs/example.yaml` 을 복사해서 수정하세요.

```yaml
title: "아직도 손목 아프게 칼질하세요? 3초 만에 끝나는 다지기"
description: |
  손목 아픈 칼질은 이제 그만!
  #주방템 #살림템
tags: [주방용품, 살림템]
privacy: private                         # private | unlisted | public
# publish_at: "2026-11-01T19:00:00+09:00"  # 예약 공개
avatar_image: ../assets/avatar/host.png
scenes:
  - text: 아직도 마늘 하나하나 칼로 다지세요?      # 대사 = 자막 = 목소리
    image: ../assets/products/1.jpg               # 이 장면에 보일 상품 사진
  - text: 손목 아프고, 설거지도 한가득이잖아요.    # 이미지 생략 시 앞 장면 사진 유지
```

명령어 (이 폴더에서 `venv\Scripts\activate` 후):

```bat
python -m autotube make jobs\example.yaml     :: 영상만 만들기 → output\날짜_제목\final.mp4
python -m autotube run  jobs\example.yaml     :: 만들고 바로 유튜브 업로드
python -m autotube upload jobs\example.yaml output\폴더이름   :: 확인 후 업로드
```

결과 폴더에는 `final.mp4`, `subtitles.srt`(자막), `meta.json` 이 저장됩니다.

---

## 5. 완전 자동 모드

**`start_watch.bat` 실행** → `jobs/inbox` 폴더를 30초마다 확인해서
yaml 파일이 들어오면 **자동으로 영상 제작 → 유튜브 업로드** 합니다.

- 성공한 job → `jobs/done/`, 실패 → `jobs/failed/` (오류 로그 함께 저장)
- 같은 영상이 두 번 올라가지 않도록 업로드 기록(`upload.json`)을 남깁니다.
- PC 켤 때 자동 시작: `Win+R` → `shell:startup` → `start_watch.bat` 바로가기 넣기
- 정해진 시간에만 처리: 작업 스케줄러에 `python -m autotube watch --once` 등록

---

## 6. YouTube API 설정 (최초 1회)

1. https://console.cloud.google.com 접속 → 새 프로젝트 만들기
2. **API 및 서비스 → 라이브러리** → `YouTube Data API v3` 사용 설정
3. **OAuth 동의 화면** → 외부 → 앱 이름 입력 → **테스트 사용자에 내 구글 계정 추가**
4. **사용자 인증 정보 → OAuth 클라이언트 ID → 데스크톱 앱** → JSON 다운로드
5. 받은 파일을 `secrets/client_secret.json` 으로 저장
6. `python -m autotube auth` → 브라우저에서 로그인/허용 → 이후 자동 로그인

> **꼭 알아두세요**
> - 구글 심사(API Audit)를 받지 않은 프로젝트로 올린 영상은 **비공개로 고정**됩니다.
>   심사 전에는 업로드 후 YouTube 스튜디오에서 직접 공개로 바꾸거나,
>   [감사 신청서](https://support.google.com/youtube/contact/yt_api_form)를 제출하세요.
> - 하루 할당량 10,000 유닛, 영상 1개 업로드 ≈ 1,600 유닛 → **하루 약 6개**까지 업로드 가능
> - AI 인물/음성을 사용하므로 `synthetic_media: true`(AI 콘텐츠 고지)가 기본으로 켜져 있습니다.
> - 썸네일 업로드는 채널 전화번호 인증 후 가능합니다.

---

## 7. (선택) 로컬 AI로 판매 대본 자동 작성

[Ollama](https://ollama.com) 설치 후 `ollama pull qwen2.5:7b` 를 해두면,
상품 정보만으로 **훅 → 공감 → 해결 → 장점 3가지 → 신뢰 → 구매 유도** 구조의 숏폼 대본을 만들어줍니다.

```bat
python -m autotube write --product "무선 미니 다지기 / 300ml / USB-C 충전 / 물세척 가능 / 정가 29,900원 → 19,900원 / 누적 판매 2만개" ^
  --image assets\products\1.jpg --image assets\products\2.jpg --avatar assets\avatar\host.png
```
→ `jobs/inbox/` 에 job 파일이 생성됩니다. **내용을 꼭 확인/수정한 뒤** 처리하세요
(AI가 사실과 다른 문구를 쓸 수 있습니다).

---

## 8. 판매 영상 잘 만드는 팁

- **첫 문장(3초)이 전부**입니다. 질문형("아직도 ~하세요?")이나 숫자("3초 만에")로 시작
- 한 문장은 **25자 이내**, 장면 6~8개, 전체 **30~45초**가 쇼츠에 가장 좋습니다
- 마지막 장면은 반드시 **행동 지시**("프로필 링크에서 확인하세요")
- 제목에 핵심 검색 키워드, 설명에 해시태그 3~5개
- 효능 보장·최저가 단정 등 과장 표현은 광고 규정 위반이 될 수 있으니 피하세요

---

## 9. 설정 요약 (`config.yaml`)

| 항목 | 설명 |
|---|---|
| `video.format` | `shorts`(세로) / `landscape`(가로) |
| `video.font_file` | 자막 폰트 (기본: 맑은 고딕 굵게) |
| `tts.speed` | 말 빠르기 (1.0 기본, 쇼츠는 1.05~1.15 추천) |
| `avatar.engine` | `sadtalker`(입 움직임) / `static`(사진 줌) |
| `music.volume` | 배경음악 크기 (0.1~0.3) |
| `youtube.default_privacy` | 기본 공개 설정 |

job 파일에서 `format`, `music`, `music_volume`, `avatar_layout`, `tts: {speed: 1.1}` 등을
영상별로 따로 지정할 수도 있습니다.

## 10. 문제 해결

| 증상 | 해결 |
|---|---|
| `ffmpeg` 를 찾을 수 없음 | `winget install Gyan.FFmpeg` 후 창 다시 열기 |
| 자막 글자가 깨짐 | `video.font_file` 경로에 한글 폰트가 있는지 확인 |
| 음성 설치 오류 | Python 3.10 사용, `python -m unidic download` 다시 실행 |
| SadTalker 너무 느림 | GPU 없으면 `avatar.engine: static` 사용 |
| 업로드 영상이 비공개로만 됨 | 6번의 API 심사 안내 참고 |
| 중간 파일 확인 | `python -m autotube --keep-work make ...` → `work/` 폴더 |
