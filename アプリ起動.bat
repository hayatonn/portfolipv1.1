@echo off
chcp 65001 > nul
echo ==========================================
echo   家族で見る資産管理ポートフォリオを起動中...
echo ==========================================
cd /d "%~dp0"
python -m streamlit run app.py
pause
