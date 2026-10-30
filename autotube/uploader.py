"""YouTube Data API v3 업로드 (OAuth 인증 1회 후 토큰 재사용)."""
import json
from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube.force-ssl"]


def get_service(ycfg):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    token = Path(ycfg["token"])
    creds = None
    if token.exists():
        creds = Credentials.from_authorized_user_file(str(token), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            secret = Path(ycfg["client_secret"])
            if not secret.exists():
                raise FileNotFoundError(
                    f"{secret} 가 없습니다. README 의 'YouTube API 설정' 을 따라 받아주세요.")
            flow = InstalledAppFlow.from_client_secrets_file(str(secret), SCOPES)
            creds = flow.run_local_server(port=0)
        token.parent.mkdir(parents=True, exist_ok=True)
        token.write_text(creds.to_json(), encoding="utf-8")
    return build("youtube", "v3", credentials=creds)


def upload(out_dir: Path, job, cfg):
    from googleapiclient.http import MediaFileUpload

    out_dir = Path(out_dir)
    done_file = out_dir / "upload.json"
    if done_file.exists():
        vid = json.loads(done_file.read_text(encoding="utf-8"))["id"]
        print(f"이미 업로드됨: https://youtu.be/{vid}")
        return vid

    ycfg = cfg["youtube"]
    yt = get_service(ycfg)
    privacy = job.get("privacy", ycfg["default_privacy"])
    status = {
        "privacyStatus": privacy,
        "selfDeclaredMadeForKids": False,
        "containsSyntheticMedia": bool(job.get("synthetic_media", ycfg["synthetic_media"])),
    }
    if job.get("publish_at"):  # 예약 공개는 private 상태에서만 가능
        status["privacyStatus"] = "private"
        status["publishAt"] = str(job["publish_at"])

    title = job["title"]
    if job.get("format", cfg["video"]["format"]) == "shorts" and "#shorts" not in title.lower():
        title = f"{title} #shorts"[:100]
    body = {
        "snippet": {
            "title": title[:100],
            "description": job.get("description", ""),
            "tags": job.get("tags", []),
            "categoryId": str(job.get("category_id", ycfg["category_id"])),
            "defaultLanguage": "ko",
            "defaultAudioLanguage": "ko",
        },
        "status": status,
    }
    media = MediaFileUpload(str(out_dir / "final.mp4"), chunksize=8 * 1024 * 1024,
                            resumable=True, mimetype="video/mp4")
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    resp = None
    while resp is None:
        st, resp = req.next_chunk()
        if st:
            print(f"  업로드 {int(st.progress() * 100)}%")
    vid = resp["id"]
    print(f"업로드 완료: https://youtu.be/{vid}")

    srt = out_dir / "subtitles.srt"
    if srt.exists() and job.get("upload_captions", True):
        try:
            yt.captions().insert(
                part="snippet",
                body={"snippet": {"videoId": vid, "language": "ko", "name": "한국어"}},
                media_body=MediaFileUpload(str(srt), mimetype="application/octet-stream"),
            ).execute()
        except Exception as e:  # 자막 업로드 실패해도 영상은 유지
            print(f"  ! 자막 업로드 실패: {e}")

    if job.get("thumbnail"):
        from .util import resolve
        thumb = resolve(job["thumbnail"], Path(job["_base"]))
        try:
            yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(thumb))).execute()
        except Exception as e:  # 채널 인증 전에는 썸네일 업로드가 막혀 있음
            print(f"  ! 썸네일 업로드 실패: {e}")

    done_file.write_text(json.dumps({"id": vid, "url": f"https://youtu.be/{vid}"}),
                         encoding="utf-8")
    return vid
