import sys, shutil, subprocess
from pathlib import Path
from tkinter import Tk, filedialog, messagebox

SRC_DIR = Path(__file__).resolve().parent
ROOT_DIR = SRC_DIR.parent
BIN_DIR = ROOT_DIR / "bin"

def get_ai_bin():
    candidates = [
        BIN_DIR / "realesrgan-ncnn-vulkan.exe",
        ROOT_DIR / "realesrgan-ncnn-vulkan.exe",
        SRC_DIR / "realesrgan-ncnn-vulkan.exe"
    ]
    for c in candidates:
        if c.exists():
            return c
    system_bin = shutil.which("realesrgan-ncnn-vulkan")
    return Path(system_bin) if system_bin else None

def enhance_image(path: str, scale: int = 4):
    src = Path(path)
    dst = src.with_name(f"{src.stem}_enhanced{src.suffix}")

    # 1. AI 引擎優先
    bin_ai = get_ai_bin()
    if not bin_ai:
        try:
            from download_ai_engine import download_and_extract
            print("首次執行：檢測到尚未配置 AI 引擎，正在自動下載配置...")
            download_and_extract()
            bin_ai = get_ai_bin()
        except Exception:
            pass

    if bin_ai and bin_ai.exists():
        cmd = [str(bin_ai), "-i", str(src), "-o", str(dst), "-s", str(scale), "-n", "realesrgan-x4plus"]
        print(f"正在以 Real-ESRGAN 神經網路處理: {src.name} ...")
        subprocess.run(cmd, check=True)
        print(f"AI 修復完成: {dst}")
        return

    # 2. Pillow 降級
    try:
        from PIL import Image, ImageEnhance, ImageFilter
        with Image.open(src) as im:
            mode = im.mode
            img = im.resize((im.width * 2, im.height * 2), Image.Resampling.LANCZOS)
            img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
            img = ImageEnhance.Contrast(img).enhance(1.08)
            img = ImageEnhance.Color(img).enhance(1.05) if mode in ("RGB", "RGBA") else img
            img.save(dst, quality=95)
            print(f"Pillow 降級濾鏡修復完成: {dst}")
            return
    except ImportError:
        pass

    # 3. ffmpeg 兜底
    if shutil.which("ffmpeg"):
        vf = "scale=iw*2:ih*2:flags=lanczos,unsharp=5:5:1.0:5:5:0.0"
        subprocess.run(["ffmpeg", "-y", "-i", str(src), "-vf", vf, str(dst)], check=True)
        print(f"ffmpeg 降級修復完成: {dst}")
        return

    messagebox.showerror("錯誤", "無法找到可用修復引擎。請先啟動軟體下載 AI 引擎。")

if __name__ == "__main__":
    files = sys.argv[1:]
    if not files:
        from gui import EnhancerApp
        app = EnhancerApp()
        app.mainloop()
    else:
        for f in files:
            enhance_image(f)
