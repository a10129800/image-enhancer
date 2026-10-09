import os
import subprocess
from pathlib import Path

def main():
    root_dir = Path(__file__).resolve().parent.parent
    os.chdir(root_dir)

    print("=" * 55)
    print("      🔨 正在編譯原生圖示啟動器 (圖片畫質提高工具.exe)")
    print("=" * 55)

    launcher_cs = root_dir / "src" / "launcher.cs"
    icon_path = root_dir / "assets" / "app.ico"
    output_exe = root_dir / "圖片畫質提高工具.exe"

    if not launcher_cs.exists():
        print(f"[❌ 錯誤] 找不到原始碼: {launcher_cs}")
        return False

    sys_root = Path(os.environ.get("SystemRoot", r"C:\Windows"))
    csc_candidates = [
        sys_root / "Microsoft.NET" / "Framework64" / "v4.0.30319" / "csc.exe",
        sys_root / "Microsoft.NET" / "Framework" / "v4.0.30319" / "csc.exe",
    ]

    csc_path = next((c for c in csc_candidates if c.exists()), None)
    if not csc_path:
        print("[❌ 錯誤] 找不到 Windows 內建 C# 編譯器 (csc.exe)！")
        return False

    print(f"[*] 使用編譯器: {csc_path}")
    print(f"[*] 圖示檔案: {icon_path.name if icon_path.exists() else '無'}")

    args = [
        str(csc_path),
        "/nologo",
        "/target:winexe",
        "/r:System.Windows.Forms.dll",
    ]
    if icon_path.exists():
        args.append(f"/win32icon:{icon_path}")
    args.append(f"/out:{output_exe}")
    args.append(str(launcher_cs))

    cmd_str = " ".join(f'"{a}"' if " " in a or ":" in a and not a.startswith("/") else a for a in args)
    # 執行編譯
    res = subprocess.run(cmd_str, shell=True)
    if res.returncode == 0 and output_exe.exists():
        size_kb = output_exe.stat().st_size / 1024
        print()
        print("=" * 55)
        print(f"  🎉 編譯成功！已在根目錄產生：{output_exe.name}")
        print(f"  📦 檔案大小: {size_kb:.1f} KB (已內嵌相機鏡頭圖示，無黑視窗)")
        print("=" * 55)
        return True
    else:
        print("[❌ 失敗] 編譯啟動器失敗。")
        return False

if __name__ == "__main__":
    main()
