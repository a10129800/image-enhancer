# GUI 預覽截圖生成與 GitHub 快取擊破規範 (GUI Preview & Caching Rule)

## 1. GitHub README 圖片快取擊破 (Cache Busting)
- **問題根源**：GitHub 針對 README 中的圖片會經由 Camo CDN 代理 (`camo.githubusercontent.com`) 進行強制快取，且瀏覽器也會快取同名圖片數小時至數天。若更新截圖時直接覆蓋原檔名（如 `Demo2.png`），線上網頁極高機率持續顯示舊的殘缺或過期圖片。
- **鐵律**：
  1. 當更新重要展示圖或修復預覽圖時，**必須變更檔名**（如改為 `gui_preview.png` 或附加版本號），並同步更新 `README.md` 的參照路徑。
  2. 變更 URL 會強制 GitHub Camo 與使用者瀏覽器立即重新抓取，保證 100% 即時呈現最新畫面。

## 2. 軟體介面預覽圖 (GUI Preview) 生成與裁切準則
- **禁止脆弱的自動裁切**：
  - 嚴禁使用顏色閾值或粗暴像素搜尋進行自動裁切，極易因元件色差或深色底色導致視窗上半部（標題列、分頁標籤、參數區塊）被腰斬。
- **標準三級保障流程**：
  1. **第一優先（使用者原生截圖）**：若有使用者提供的視窗截圖，優先完整採用，不做任何毀滅性二次裁切。
  2. **第二優先（擷取執行中視窗）**：使用 Windows API (`user32.EnumWindows` + `GetWindowRect`) 抓取正在運行的視窗 HWND 完整邊界（包含原生標題列、控制按鈕與所有元件）。
  3. **第三優先（無痕自動渲染）**：若無現成截圖或運行中視窗，由後台啟動 GUI 實例，等候元件渲染完成後以 `PIL.ImageGrab` 依精確座標截取 1:1 原生高清圖。

## 3. 一鍵自動化推送工作流 (Git Push Workflow)
- 推送腳本 (`git_push.py` / `git_push.bat`) 應具備自動化閉環：
  - 自動整理目錄架構 (`bin/`, `assets/`, `docs/`, `samples/`)。
  - 自動調用 `src/capture_gui.py` 驗證並生成完整的預覽圖。
  - 自動隔離內部輔助工具（`git rm --cached` 排除打包與內部發行腳本）。
  - 自動暫存、清晰撰寫 Commit 訊息並推送至遠端主分支。
