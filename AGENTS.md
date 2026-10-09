# 專案開發規範與歷史實踐指南 (AGENTS.md)

本專案為 **圖片/照片 AI 畫質修復 & 消除浮水印工具 (Real-ESRGAN GUI)**。

---

## 核心工程鐵律與避坑記憶

### 1. GitHub 預覽圖片與 Camo 快取處理 (Cache Busting)
- **原因**：GitHub README 透過 `camo.githubusercontent.com` 快取圖片，若覆蓋原圖片檔名（如舊的 `Demo2.png`），線上網頁通常數小時內不會更新，瀏覽器也會強烈快取。
- **作法**：更新介面展示圖時，必須**變更檔案名稱**（如 `assets/gui_preview.png`）並同步更新 `README.md`，強制 GitHub CDN 與瀏覽器立即刷新。

### 2. 介面預覽圖 (GUI Preview) 的生成原則
- **嚴禁脆弱的像素閥值自動裁切**：先前的色塊裁切演算法因誤判日誌框，導致視窗頂部分頁、清單與參數區被截斷。
- **三級保障機制**（詳見 `src/capture_gui.py`）：
  1. 優先使用使用者上傳的完整原生截圖（不二次裁切）。
  2. 若無，使用 Windows API 擷取目前正在運行的軟體視窗邊界。
  3. 若皆無，背景喚醒 Tkinter 介面並以 `ImageGrab` 截取原生全視窗像素。

### 3. 發布與推送流程
- 專案根目錄維持極簡乾淨，僅保留使用者入口：
  - `run_enhance.bat`（腳本啟動器）
  - `圖片畫質提高工具.exe`（原生無黑視窗 C# 啟動器）
- 開發者一鍵推送工具：
  - `git_push.bat` -> 自動觸發 `git_push.py`，完成目錄整理、截圖校驗、內部腳本隔離、Commit 與 Push。
- 內部維護與打包發布工具：
  - 統一收納至 `scripts/`（如 `create_release.bat`、`build_launcher.bat`），避免根目錄雜亂。
