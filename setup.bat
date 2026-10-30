@echo off
chcp 65001 >nul
cd /d %~dp0
echo [1/4] 가상환경 만들기
py -3.10 -m venv venv || python -m venv venv
call venv\Scripts\activate
echo [2/4] 기본 패키지 설치
python -m pip install --upgrade pip
pip install -r requirements.txt
echo [3/4] 한국어 음성(MeloTTS) 설치
pip install git+https://github.com/myshell-ai/MeloTTS.git
python -m unidic download
echo [4/4] ffmpeg 확인
where ffmpeg || winget install --id Gyan.FFmpeg -e
echo 설치 완료! README 의 "YouTube API 설정" 을 진행하세요.
pause
