"""명령어:
  python -m autotube make  jobs/example.yaml        영상만 만들기
  python -m autotube run   jobs/example.yaml        만들고 바로 업로드
  python -m autotube upload jobs/x.yaml output/폴더  만든 영상 업로드
  python -m autotube watch                          inbox 폴더 감시 → 자동 제작/업로드
  python -m autotube auth                           유튜브 로그인(최초 1회)
  python -m autotube write --product "..."          (선택) 로컬 AI로 대본 job 생성
"""
import argparse
import shutil
import time
import traceback
from datetime import datetime
from pathlib import Path

from .config import load_config, load_job


def cmd_make(a, cfg):
    from .compose import make_video
    return make_video(load_job(a.job), cfg)


def cmd_run(a, cfg):
    from .compose import make_video
    from .uploader import upload
    job = load_job(a.job)
    upload(make_video(job, cfg), job, cfg)


def cmd_upload(a, cfg):
    from .uploader import upload
    upload(Path(a.out_dir), load_job(a.job), cfg)


def cmd_auth(a, cfg):
    from .uploader import get_service
    get_service(cfg["youtube"])
    print("유튜브 인증 완료")


def cmd_watch(a, cfg):
    from .compose import make_video
    from .uploader import upload
    inbox = Path(cfg["watch"]["inbox"])
    done, failed = inbox.parent / "done", inbox.parent / "failed"
    for d in (inbox, done, failed):
        d.mkdir(parents=True, exist_ok=True)
    do_upload = cfg["watch"]["upload"] and not a.no_upload
    print(f"감시 중: {inbox.resolve()}  (업로드: {'켜짐' if do_upload else '꺼짐'}, Ctrl+C 종료)")
    while True:
        for f in sorted(inbox.glob("*.y*ml")):
            print(f"\n=== {f.name} ===")
            try:
                job = load_job(f)
                out = make_video(job, cfg)
                if do_upload:
                    upload(out, job, cfg)
                shutil.move(str(f), done / f.name)
            except Exception:
                err = traceback.format_exc()
                print(err)
                stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                shutil.move(str(f), failed / f.name)
                (failed / f"{f.stem}_{stamp}.log").write_text(err, encoding="utf-8")
        if a.once:
            break
        time.sleep(cfg["watch"]["interval"])


def cmd_write(a, cfg):
    from .writer import write_job
    text = write_job(a.product, a.image or [], cfg, a.avatar)
    out = Path(a.out or Path(cfg["watch"]["inbox"]) /
               f"{datetime.now():%Y%m%d_%H%M%S}.yaml")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(text)
    print(f"저장: {out}  (내용 확인/수정 후 make 또는 watch 로 제작)")


def main():
    p = argparse.ArgumentParser(prog="autotube", description="로컬 영상 제작 + 유튜브 자동 업로드")
    p.add_argument("-c", "--config", default="config.yaml")
    p.add_argument("--keep-work", action="store_true", help="중간 파일(work 폴더) 남기기")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("make", help="영상 만들기")
    s.add_argument("job")
    s.set_defaults(fn=cmd_make)
    s = sub.add_parser("run", help="만들고 업로드")
    s.add_argument("job")
    s.set_defaults(fn=cmd_run)
    s = sub.add_parser("upload", help="이미 만든 영상 업로드")
    s.add_argument("job")
    s.add_argument("out_dir")
    s.set_defaults(fn=cmd_upload)
    s = sub.add_parser("auth", help="유튜브 로그인")
    s.set_defaults(fn=cmd_auth)
    s = sub.add_parser("watch", help="inbox 폴더 자동 처리")
    s.add_argument("--once", action="store_true", help="한 번만 처리하고 종료(작업 스케줄러용)")
    s.add_argument("--no-upload", action="store_true")
    s.set_defaults(fn=cmd_watch)
    s = sub.add_parser("write", help="로컬 AI(Ollama)로 판매 대본 job 생성")
    s.add_argument("--product", required=True, help="상품 정보(이름, 특징, 가격, 후기 등)")
    s.add_argument("--image", action="append", help="상품 이미지 (여러 번 지정 가능)")
    s.add_argument("--avatar", help="인물 사진")
    s.add_argument("--out", help="저장할 yaml 경로 (기본: inbox)")
    s.set_defaults(fn=cmd_write)

    a = p.parse_args()
    cfg = load_config(a.config)
    cfg["keep_work"] = a.keep_work
    a.fn(a, cfg)


if __name__ == "__main__":
    main()
