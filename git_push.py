import subprocess, os, sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
os.chdir(DIR)

REPO_URL = "https://github.com/a10129800/image-enhancer.git"

def run_cmd(cmd):
    print(f"[*] 執行: {cmd}")
    res = subprocess.run(cmd, shell=True)
    return res.returncode == 0

def main():
    print("=" * 55)
    print("      🚀 圖片/照片 AI 畫質修復工具 - GitHub 推送程序")
    print("=" * 55)
    print()

    # 1. 檢查 Git
    res = subprocess.run("git --version", shell=True, capture_output=True)
    if res.returncode != 0:
        print("[❌ 錯誤] 系統未安裝 Git，請先至 https://git-scm.com/ 安裝。")
        input("\n按 Enter 鍵退出...")
        return

    # 2. 初始化 Git 倉庫
    if not (DIR / ".git").exists():
        print("[1/4] 初始化本機 Git 倉庫...")
        run_cmd("git init")
        run_cmd("git branch -M main")
    else:
        print("[1/4] 本機 Git 倉庫已就緒。")

    # 3. 綁定 GitHub 遠端倉庫
    check_remote = subprocess.run("git remote get-url origin", shell=True, capture_output=True, text=True)
    if check_remote.returncode != 0:
        print(f"[2/4] 正在綁定遠端倉庫: {REPO_URL}")
        run_cmd(f"git remote add origin {REPO_URL}")
    else:
        current_url = check_remote.stdout.strip()
        print(f"[2/4] 目前綁定倉庫: {current_url}")
        if "a10129800/image-enhancer" not in current_url:
            run_cmd(f"git remote set-url origin {REPO_URL}")

    # 4. 暫存檔案 (.gitignore 會自動排除大模型)
    print("\n[3/4] 暫存檔案變更...")
    run_cmd("git add .")

    # 5. Commit
    print("\n[4/4] 建立 Commit 與推送...")
    subprocess.run('git commit -m "feat: 圖片/照片 AI 畫質修復工具 (Real-ESRGAN GUI)"', shell=True)

    # 6. 推送至 main 分支
    print("\n正在推送到 GitHub main 分支...")
    push_res = subprocess.run("git push -u origin main", shell=True)

    if push_res.returncode != 0:
        print("\n[⚠️ 提示] 初次推送若遇到遠端 README 衝突，正在嘗試自動同步合併...")
        run_cmd("git pull origin main --rebase")
        push_res = subprocess.run("git push -u origin main", shell=True)

    print()
    if push_res.returncode == 0:
        print("=" * 55)
        print("  🎉 恭喜！專案已成功推送至 GitHub！")
        print(f"  🔗 倉庫網址: https://github.com/a10129800/image-enhancer")
        print("=" * 55)
    else:
        print("[❌ 提示] 推送失敗，請確認您已在瀏覽器登入 GitHub 並且擁有寫入權限。")

    print()
    input("請按 Enter 鍵結束...")

if __name__ == "__main__":
    main()
