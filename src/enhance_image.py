import sys, shutil, subprocess
from pathlib import Path
from tkinter import messagebox

SRC_DIR = Path(__file__).resolve().parent
ROOT_DIR = SRC_DIR.parent
BIN_DIR = ROOT_DIR / "bin"

def get_ai_bin():
    bin_file = BIN_DIR / "realesrgan-ncnn-vulkan.exe"
    if bin_file.exists():
        return bin_file
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

    messagebox.showerror("錯誤", "無法找到或下載 AI 引擎 (realesrgan-ncnn-vulkan)。請檢查網路後重試。")

if __name__ == "__main__":
    files = sys.argv[1:]
    if not files:
        from gui import EnhancerApp
        app = EnhancerApp()
        app.mainloop()
    else:
        for f in files:
            enhance_image(f)
