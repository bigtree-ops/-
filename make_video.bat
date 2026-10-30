@echo off
chcp 65001 >nul
cd /d %~dp0
call venv\Scripts\activate
REM 사용법: job 파일(.yaml)을 이 파일 위에 끌어다 놓으면 영상만 만듭니다
python -m autotube make "%~1"
pause
