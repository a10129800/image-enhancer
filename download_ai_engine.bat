@echo off
chcp 65001 >nul
echo 正在準備下載與設定 Real-ESRGAN-ncnn-vulkan AI 引擎...
python "%~dp0download_ai_engine.py"
pause
