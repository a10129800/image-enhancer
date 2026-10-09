import os
import sys
import time
import shutil
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = Path(__file__).resolve().parent
ASSETS_DIR = ROOT_DIR / "assets"
ASSETS_DIR.mkdir(exist_ok=True)

def find_uploaded_screenshot():
    # 若本地 assets 已有高品質預覽圖，直接沿用
    local_preview = ASSETS_DIR / "gui_preview.png"
    if local_preview.exists() and local_preview.stat().st_size > 50000:
        return local_preview
    return None

def capture_from_running_window():
    try:
        import ctypes
        from ctypes import wintypes
        from PIL import ImageGrab

        # 搜尋標題含 "AI 畫質修復" 的可見視窗
        user32 = ctypes.windll.user32
        target_hwnd = None

        def enum_windows_proc(hwnd, lparam):
            nonlocal target_hwnd
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    title = buff.value
                    if "AI 畫質修復" in title or "消除浮水印" in title:
                        target_hwnd = hwnd
                        return False
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        user32.EnumWindows(WNDENUMPROC(enum_windows_proc), 0)

        if target_hwnd:
            rect = wintypes.RECT()
            user32.GetWindowRect(target_hwnd, ctypes.byref(rect))
            bbox = (rect.left, rect.top, rect.right, rect.bottom)
            if (bbox[2] - bbox[0]) > 300 and (bbox[3] - bbox[1]) > 300:
                print(f"[+] 正在直接截取目前運行的軟體視窗 (HWND: {target_hwnd}, Rect: {bbox})...")
                img = ImageGrab.grab(bbox=bbox)
                return img
    except Exception as e:
        print(f"[-] 從運行視窗截圖略過: {e}")
    return None

def render_and_capture_new_window():
    try:
        from PIL import ImageGrab
        import ctypes
        from ctypes import wintypes

        if str(SRC_DIR) not in sys.path:
            sys.path.insert(0, str(SRC_DIR))
        from gui import EnhancerApp

        print("[*] 正在精準渲染原生軟體視窗並截取高畫質預覽圖...")
        app = EnhancerApp()
        app.update()
        time.sleep(0.4)
        app.update()

        try:
            hwnd = app.winfo_id()
            hwnd_root = ctypes.windll.user32.GetAncestor(hwnd, 2)
            rect = wintypes.RECT()
            ctypes.windll.user32.GetWindowRect(hwnd_root, ctypes.byref(rect))
            bbox = (rect.left, rect.top, rect.right, rect.bottom)
        except Exception:
            x = app.winfo_rootx()
            y = app.winfo_rooty()
            w = app.winfo_width()
            h = app.winfo_height()
            bbox = (x, y, x + w, y + h)

        img = ImageGrab.grab(bbox=bbox)
        app.destroy()
        return img
    except Exception as e:
        print(f"[-] 渲染軟體視窗截圖失敗: {e}")
        return None

def main():
    print("=" * 55)
    print("      📸 正在產生完整軟體介面預覽圖 (GUI Preview)")
    print("=" * 55)

    dst_gui_preview = ASSETS_DIR / "gui_preview.png"
    dst_demo2 = ASSETS_DIR / "Demo2.png"

    # 1. 優先使用已上傳的截圖
    uploaded = find_uploaded_screenshot()
    if uploaded:
        shutil.copy2(str(uploaded), str(dst_gui_preview))
        shutil.copy2(str(uploaded), str(dst_demo2))
        print(f"[🎉 成功] 已從來源更新截圖！檔案大小: {dst_gui_preview.stat().st_size} bytes")
        return True

    # 2. 嘗試從目前已開啟的視窗截圖
    img = capture_from_running_window()
    if img:
        img.save(str(dst_gui_preview))
        img.save(str(dst_demo2))
        print(f"[🎉 成功] 已截取當前軟體視窗！尺寸: {img.size}")
        return True

    # 3. 自動渲染原生介面視窗截圖
    img = render_and_capture_new_window()
    if img:
        img.save(str(dst_gui_preview))
        img.save(str(dst_demo2))
        print(f"[🎉 成功] 已自動渲染並截取完整介面！尺寸: {img.size}")
        return True

    print("[❌ 警告] 未能生成新截圖，保留現有檔案。")
    return False

if __name__ == "__main__":
    main()
