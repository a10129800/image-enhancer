import os, sys, zipfile, shutil, urllib.request, subprocess
from pathlib import Path

TARGET_DIR = Path(__file__).resolve().parent

# 提供官方來源與多組鏡像加速節點
URLS = [
    "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-windows.zip",
    "https://mirror.ghproxy.com/https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-windows.zip",
    "https://ghproxy.net/https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-windows.zip"
]

def download_file_pure_python(url: str, dst: Path, progress_cb=None):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*"
    })
    with urllib.request.urlopen(req, timeout=30) as resp, open(dst, 'wb') as f:
        total = int(resp.headers.get('content-length', 0))
        downloaded = 0
        chunk_size = 128 * 1024
        while True:
            chunk = resp.read(chunk_size)
            if not chunk:
                break
            f.write(chunk)
            downloaded += len(chunk)
            if progress_cb and total > 0:
                progress_cb(downloaded, total)
    return dst.exists() and dst.stat().st_size > 10 * 1024 * 1024

def download_and_extract(progress_cb=None):
    zip_path = TARGET_DIR / "realesrgan_temp.zip"
    success = False
    last_err = None

    # 清理殘留半成品
    if zip_path.exists():
        try:
            zip_path.unlink()
        except Exception:
            pass

    for url in URLS:
        try:
            print(f"嘗試下載: {url}")
            if download_file_pure_python(url, zip_path, progress_cb):
                success = True
                break
        except Exception as e:
            last_err = e
            print(f"下載失敗 ({url}): {e}")

    if not success:
        if zip_path.exists():
            zip_path.unlink()
        raise RuntimeError(f"下載逾時或連線失敗，請檢查網路。\n錯誤: {last_err}")

    # 解壓縮並重整目錄結構
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for member in zip_ref.namelist():
                filename = Path(member).name
                if not filename:
                    continue
                if "models/" in member or "models\\" in member:
                    target = TARGET_DIR / "models" / filename
                    target.parent.mkdir(parents=True, exist_ok=True)
                else:
                    target = TARGET_DIR / filename
                with zip_ref.open(member) as src, open(target, 'wb') as dst:
                    shutil.copyfileobj(src, dst)
    finally:
        if zip_path.exists():
            zip_path.unlink()

    exe_file = TARGET_DIR / "realesrgan-ncnn-vulkan.exe"
    if not exe_file.exists():
        raise FileNotFoundError("未檢測到解壓縮後的 realesrgan-ncnn-vulkan.exe")

    return True

if __name__ == "__main__":
    try:
        download_and_extract()
    except Exception as e:
        print(f"❌ 錯誤: {e}")
