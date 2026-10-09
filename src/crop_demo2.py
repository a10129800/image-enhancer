import os
import sys
from pathlib import Path
from PIL import Image
import numpy as np

def crop_app_window(src_path: Path, dst_path1: Path, dst_path2: Path = None):
    if not src_path.exists():
        print(f"[!] 找不到來源截圖: {src_path}")
        return False

    img = Image.open(src_path)
    rgb = img.convert("RGB")
    arr = np.array(rgb)
    h, w, _ = arr.shape

    # 尋找藍色按鈕 "🚀 開始 AI 畫質修復" (#2563eb: R~37, G~99, B~235)
    r = arr[:, :, 0]
    g = arr[:, :, 1]
    b = arr[:, :, 2]
    blue_mask = (r >= 20) & (r <= 55) & (g >= 80) & (g <= 125) & (b >= 200) & (b <= 255)

    blue_ys, blue_xs = np.where(blue_mask)
    if len(blue_xs) > 20:
        btn_right = int(np.percentile(blue_xs, 99))
        btn_bottom = int(np.percentile(blue_ys, 99))
        btn_top = int(np.percentile(blue_ys, 1))

        win_right = min(w, btn_right + 16)
        win_bottom = min(h, btn_bottom + 16)

        # 向上搜尋視窗上邊界 (VS Code 深色背景 #1e1e1e)
        win_top = 0
        test_x = max(0, min(w - 1, btn_right - 40))
        for y in range(btn_top - 50, 0, -1):
            p = arr[y, test_x]
            if p[0] < 55 and p[1] < 55 and p[2] < 55:
                win_top = y + 1
                break
        if win_top == 0:
            win_top = max(0, btn_top - 720)

        # 向左搜尋視窗左邊界 (VS Code 深色背景 #1e1e1e)
        win_left = 0
        mid_y = (win_top + win_bottom) // 2
        for x in range(btn_right - 100, 0, -1):
            p = arr[mid_y, x]
            if p[0] < 55 and p[1] < 55 and p[2] < 55:
                win_left = x + 1
                break
        if win_left == 0:
            win_left = max(0, btn_right - 860)

        cropped = img.crop((win_left, win_top, win_right, win_bottom))
    else:
        # 若未定位到藍色按鈕，直接使用原圖
        cropped = img

    dst_path1.parent.mkdir(parents=True, exist_ok=True)
    cropped.save(dst_path1)
    if dst_path2:
        dst_path2.parent.mkdir(parents=True, exist_ok=True)
        cropped.save(dst_path2)

    print(f"[+] Demo2.png 已成功更新！尺寸: {cropped.size} -> {dst_path1.name}")
    return True

if __name__ == "__main__":
    src = Path(r"C:\Users\mice\.gemini\antigravity-ide\brain\4a990e4f-7495-4a12-af4a-bf4993b67fb1\.user_uploaded\media_1791537731563.png")
    root_dir = Path(__file__).resolve().parent.parent
    import shutil
    shutil.copy2(str(src), str(root_dir / "assets" / "Demo2.png"))
    print("[+] Demo2.png 已直接複製更新完成！")
