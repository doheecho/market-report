@echo off
chcp 65001 >nul
echo =========================================================
echo SCM Risk GITHUB Auto Push Agent
echo =========================================================
cd /d "%~dp0"

echo [1/3] Staging changes - git add .
git add .

echo [2/3] Committing changes - git commit
git commit -m "Auto Refactor: Layout and split ratio 60:40 refinements"

echo [3/3] Pushing to GitHub - git push
git push origin main --force

echo =========================================================
echo Sync Completed! GitHub Pages will update in 30 seconds.
echo =========================================================
pause
