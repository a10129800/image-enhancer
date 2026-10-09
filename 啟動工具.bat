@echo off
chcp 65001 >nul
cd /d "%~dp0"

:: 1. 自動整理目錄結構（無損遷移）
if exist "bin" (
    if not exist "core" ren "bin" "core"
)
if exist "dist" (
    if not exist "release" ren "dist" "release"
)
if exist "samples" (
    if not exist "assets\samples" move /y "samples" "assets\" >nul 2>&1
)
if exist "docs" (
    if not exist "assets\docs" move /y "docs" "assets\" >nul 2>&1
)

:: 2. 清理根目錄舊啟動檔案與執行檔
if exist "run_enhance.bat" del /f /q "run_enhance.bat" >nul 2>&1
if exist "git_push.bat" del /f /q "git_push.bat" >nul 2>&1
if exist "*.exe" del /f /q "*.exe" >nul 2>&1

:: 3. 隱藏開發輔助與工作區設定檔（使檔案總管視覺保持極簡乾淨）
if exist "*.code-workspace" attrib +h "*.code-workspace" >nul 2>&1
if exist "AGENTS.md" attrib +h "AGENTS.md" >nul 2>&1
if exist "LICENSE" attrib +h "LICENSE" >nul 2>&1
if exist "requirements.txt" attrib +h "requirements.txt" >nul 2>&1

:: 4. 啟動主程式
python src\gui.py
if %errorlevel% neq 0 (
    echo.
    echo [提示] 啟動異常，請確認已安裝 Python 3.8+ 且包含在系統 PATH 中。
    pause
)
