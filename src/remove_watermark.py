import os
import sys
import subprocess
from pathlib import Path
from PIL import Image, ImageFilter, ImageDraw

def has_opencv() -> bool:
    try:
        import cv2
        import numpy
        return True
    except ImportError:
        return False

def remove_watermark_inpaint(
    image: Image.Image,
    mask: Image.Image,
    method: str = "telea",
    radius: int = 5
) -> Image.Image:
    """
    對指定圖像與遮罩進行浮水印消除 (Inpainting)。
    image: PIL.Image (RGB 或 RGBA)
    mask: PIL.Image (單通道 'L'，白色 255 代表要抹除的水印，黑色 0 代表保留)
    method: 'telea' 或 'ns' (Navier-Stokes)
    radius: 邊界擴展半徑
    """
    orig_mode = image.mode
    if orig_mode != "RGB":
        base_img = image.convert("RGB")
    else:
        base_img = image

    # 確保 mask 尺寸與原圖一致
    if mask.size != base_img.size:
        mask = mask.resize(base_img.size, Image.NEAREST)
    if mask.mode != "L":
        mask = mask.convert("L")

    # 1. 優先嘗試調用 OpenCV Telea / Navier-Stokes
    if has_opencv():
        try:
            import cv2
            import numpy as np

            img_np = np.array(base_img)
            img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
            mask_np = np.array(mask)

            # 二值化遮罩確保邊界清晰
            _, mask_thresh = cv2.threshold(mask_np, 50, 255, cv2.THRESH_BINARY)

            # 稍微膨脹遮罩以完全覆蓋浮水印邊緣
            kernel = np.ones((3, 3), np.uint8)
            mask_dilated = cv2.dilate(mask_thresh, kernel, iterations=1)

            flag = cv2.INPAINT_TELEA if method == "telea" else cv2.INPAINT_NS
            res_bgr = cv2.inpaint(img_bgr, mask_dilated, inpaintRadius=max(1, radius), flags=flag)
            res_rgb = cv2.cvtColor(res_bgr, cv2.COLOR_BGR2RGB)
            result_img = Image.fromarray(res_rgb)
            if orig_mode == "RGBA" and "A" in image.getbands():
                result_img.putalpha(image.getchannel("A"))
            return result_img
        except Exception as e:
            print(f"[!] OpenCV inpaint 執行失敗，切換至 Pillow 備用方案: {e}")

    # 2. 兜底方案：純 Pillow 智慧周邊羽化模糊修補 (免 OpenCV 依賴)
    return _pillow_inpaint_fallback(base_img, mask, radius)

def _pillow_inpaint_fallback(img: Image.Image, mask: Image.Image, radius: int = 5) -> Image.Image:
    """
    純 Pillow 影像修補兜底演算法：
    以擴張遮罩、周邊取樣與多尺度邊緣羽化融合消除文字或半透明水印。
    """
    # 遮罩輕微模糊產生平滑過渡邊界
    blurred_mask = mask.filter(ImageFilter.GaussianBlur(radius=max(1, radius // 2)))
    
    # 產生多層次背景填補層
    fill_layer = img.filter(ImageFilter.GaussianBlur(radius=max(3, radius * 2)))
    fill_layer = fill_layer.filter(ImageFilter.MedianFilter(size=5))
    
    # 將填補層透過羽化遮罩與原圖混合
    result = Image.composite(fill_layer, img, blurred_mask)
    return result

def install_opencv(callback=None):
    """在背景安裝 opencv-python 與 numpy"""
    def _run():
        cmd = [sys.executable, "-m", "pip", "install", "opencv-python", "numpy", "--quiet"]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True)
            success = (res.returncode == 0) and has_opencv()
        except Exception:
            success = False
        if callback:
            callback(success)
    import threading
    t = threading.Thread(target=_run, daemon=True)
    t.start()
