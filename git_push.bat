@echo off
chcp 65001 >nul
echo =========================================================
echo 🌐 GITHUB 자동 동기화 에이전트 시작
echo =========================================================

:: Get script folder path safely
cd /d "%~dp0"

echo [1/4] 모든 수정된 코드 및 생성된 데이터(JSON) 스테이징 중...
git add .

echo [2/4] 자동 타임스탬프와 함께 로컬 커밋 생성 중...
git commit -m "Update SCM pipeline files and compiled views (%date% %time%)"

echo [3/4] 최신 깃허브 변경사항 원격 동기화(Pull & Rebase) 중...
git pull --rebase origin main

echo [4/4] 깃허브 원격 서버로 최종 Push 중...
git push origin main

echo =========================================================
echo ✨ 동기화 완료! GitHub Actions 분석기가 실행됩니다.
echo =========================================================
pause
