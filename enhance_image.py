import sys, shutil, subprocess
from pathlib import Path
from tkinter import Tk, filedialog, messagebox

DIR = Path(__file__).resolve().parent

def get_ai_bin():
    local_bin = DIR / "realesrgan-ncnn-vulkan.exe"
    if local_bin.exists():
        return local_bin
    system_bin = shutil.which("realesrgan-ncnn-vulkan")
    if system_bin:
        return Path(system_bin)
    return None

def enhance_image(path: str, scale: int = 4):
    src = Path(path)
    dst = src.with_name(f"{src.stem}_enhanced{src.suffix}")

    # 1. AI 引擎優先 (自動檢查本地或環境變數)
    bin_ai = get_ai_bin()
    if not bin_ai:
        try:
            from download_ai_engine import download_and_extract
            print("首次執行：檢測到尚未內建 AI 引擎，正在自動下載配置...")
            download_and_extract()
            bin_ai = get_ai_bin()
        except Exception:
            pass

    if bin_ai and bin_ai.exists():
        # -s 4: 預設放大 4 倍, -n realesrgan-x4plus
        cmd = [str(bin_ai), "-i", str(src), "-o", str(dst), "-s", str(scale), "-n", "realesrgan-x4plus"]
        print(f"正在以 Real-ESRGAN 神經網路處理: {src.name} ...")
        subprocess.run(cmd, check=True)
        print(f"AI 修復完成: {dst}")
        return

    # 2. Pillow 濾鏡降級備用
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

    messagebox.showerror("錯誤", "無法找到可用修復引擎。請先執行 download_ai_engine.bat 下載 AI 模組。")

if __name__ == "__main__":
    files = sys.argv[1:]
    if not files:
        from gui import EnhancerApp
        app = EnhancerApp()
        app.mainloop()
    else:
        for f in files:
            enhance_image(f)

