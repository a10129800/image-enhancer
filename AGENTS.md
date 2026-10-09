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

### 3. 發布與極簡根目錄原則 (Root Directory Hygiene)
- **根目錄零 Python 散落**：專案根目錄維持 **0 個 `.py` 檔案**。
- **使用者與開發者入口嚴格精簡**（根目錄僅保留這 3 個）：
  - `圖片畫質提高工具.exe`（原生無黑視窗 C# 啟動器，主入口）
  - `run_enhance.bat`（命令列備用啟動器）
  - `git_push.bat`（開發者一鍵整理與推送器）
- **維護與打包工具全數收納**：
  - 統一收納至 `scripts/`（如 `git_push.py`、`create_release.bat/py`、`build_launcher.bat`）。
  - `scripts/` 預設加入 `.gitignore` 隔離，不公開至 GitHub。
- **核心原始碼純粹收納**：
  - 應用邏輯 100% 收納於 `src/`。

### 4. Git 遠端倉庫隔離與 Untrack 機制 (二進位檔與個人工作區)
- **永久隔離名單**：
  - `*.code-workspace`（個人 IDE 配置）
  - `*.exe` / `圖片畫質提高工具.exe`（本機編譯二進位檔，發布走 Release，不進 Git）
  - `scripts/`（內部建置維護腳本）
- **避坑記憶**：
  - 若檔案**已被 Git 追蹤過**，僅修改 `.gitignore` 無法生效，Git 仍會持續追蹤變更！
  - 必須透過 `git rm --cached -f` 強制從 Git 索引剔除（本機檔案完好保留），再 Commit & Push 才能自遠端刪除。
  - `scripts/git_push.py` 在推送流程中已內建自動剔除檢查，確保遠端倉庫永遠純淨。

### 5. Windows 批次檔編碼與引號避坑 (Unicode 安全)
- **原因**：Windows `cmd.exe` 在解析 UTF-8 的批次檔時，遇到中文字元或包含括號 `()` 的註解/訊息時，極易發生語法截斷或誤判為命令區塊（例如 `'道具.code-workspace' is not recognized`）。
- **作法**：
  - 根目錄的 `.bat` 只保留最純粹的 1~2 行 ASCII 轉發指令（如 `python "%~dp0scripts\git_push.py"`）。
  - 所有涉及中文檔名、Git 命令處理、檔案搬移的邏輯，**一律交由 Python 以 List 傳參（CreateProcessW 原生 Unicode API）執行**，徹底杜絕 Windows cmd 的編碼崩潰。

### 6. IDE 視覺降噪規範 (Visual Noise Reduction)
- **痛點**：VS Code 側邊欄預設會顯示 `__pycache__`、`dist`、`.git` 等編譯快取與暫存資料夾，造成嚴重視覺雜亂感。
- **作法**：
  - 專案透過 `.vscode/settings.json` 與 `*.code-workspace` 的 `files.exclude` 統一配置全域過濾。
  - 自動屏蔽 `**/__pycache__`、`dist`、`**/*.pyc`、`**/.git`，確保開發者側邊欄永遠保持清爽乾淨、層次分明。

### 7. 拒絕過度工程 (Ponytail 實踐準則)
- **死碼與廢棄腳本即刻清除**：一旦有新演算法取代（如 `capture_gui.py` 取代 `crop_demo2.py`），舊程式碼連同引用必須立刻清理，禁止保留「未來可能有用」的冗餘代碼。
- **拒絕無意義的冗餘降級**：身為 AI 工具，AI 引擎缺失時應引導自動下載或彈出明確指引，嚴禁疊加無關痛癢的手寫傳統濾鏡兜底（如手工插值加銳化），保持主核心邏輯簡潔專注。
