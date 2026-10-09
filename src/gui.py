import os, sys, shutil, subprocess, threading, time
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# 解決 Windows 高解析度螢幕 (DPI 縮放 125%/150%) 導致介面與字體模糊發虛的問題
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

SRC_DIR = Path(__file__).resolve().parent
ROOT_DIR = SRC_DIR.parent
BIN_DIR = ROOT_DIR / "bin"

class EnhancerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("圖片/照片 AI 畫質修復工具 (Real-ESRGAN)")
        self.geometry("760x720")
        self.minsize(660, 620)
        self.configure(bg="#f4f5f7")

        self.selected_files = []
        self.is_processing = False
        self.is_cancelled = False
        self.current_proc = None

        self._organize_workspace()
        self._setup_style()
        self._build_ui()
        self._check_engine_status()
        self._log("系統初始化完成，準備就緒。")

    def _organize_workspace(self):
        # 1. 整理二進位執行檔與模型到 bin/
        BIN_DIR.mkdir(parents=True, exist_ok=True)
        for bin_file in ["realesrgan-ncnn-vulkan.exe", "vcomp140.dll", "vcomp140d.dll"]:
            p = ROOT_DIR / bin_file
            if p.exists():
                target = BIN_DIR / bin_file
                if not target.exists():
                    shutil.move(str(p), str(target))
                else:
                    p.unlink()

        models_root = ROOT_DIR / "models"
        if models_root.exists() and models_root != (BIN_DIR / "models"):
            target_models = BIN_DIR / "models"
            target_models.mkdir(parents=True, exist_ok=True)
            for m in models_root.iterdir():
                dest = target_models / m.name
                if not dest.exists():
                    shutil.move(str(m), str(dest))
            try:
                shutil.rmtree(str(models_root))
            except Exception:
                pass

        # 2. 整理展示截圖至 assets/
        assets_dir = ROOT_DIR / "assets"
        assets_dir.mkdir(exist_ok=True)
        uploaded_demo2 = Path(r"C:\Users\mice\.gemini\antigravity-ide\brain\c76d24df-8eaa-44b9-90c0-75c423faeaad\.user_uploaded\media_1791528421190.png")
        if uploaded_demo2.exists():
            shutil.copy2(str(uploaded_demo2), str(assets_dir / "Demo2.png"))
            try:
                shutil.copy2(str(uploaded_demo2), str(ROOT_DIR / "Demo2.png"))
            except Exception:
                pass

        for img_name in ["DEMO.png", "Demo2.png"]:
            p = ROOT_DIR / img_name
            if p.exists() and not (assets_dir / img_name).exists():
                shutil.move(str(p), str(assets_dir / img_name))

        # 3. 整理範例至 samples/
        samples_dir = ROOT_DIR / "samples"
        samples_dir.mkdir(exist_ok=True)
        for sample_name in ["input.jpg", "input2.jpg", "onepiece_demo.mp4"]:
            p = ROOT_DIR / sample_name
            if p.exists():
                shutil.move(str(p), str(samples_dir / sample_name))

        # 4. 整理文檔至 docs/
        docs_dir = ROOT_DIR / "docs"
        docs_dir.mkdir(exist_ok=True)
        win_readme = ROOT_DIR / "README_windows.md"
        if win_readme.exists():
            shutil.move(str(win_readme), str(docs_dir / "realesrgan_upstream_readme.md"))

    def _setup_style(self):
        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.style.configure(".", font=("Microsoft JhengHei UI", 10))
        self.style.configure("Header.TLabel", font=("Microsoft JhengHei UI", 14, "bold"), background="#f4f5f7")
        self.style.configure("Status.TLabel", font=("Microsoft JhengHei UI", 9), foreground="#555", background="#f4f5f7")
        self.style.configure("Accent.TButton", font=("Microsoft JhengHei UI", 10, "bold"))

    def _build_ui(self):
        # 1. 頂部標題區
        top_frame = tk.Frame(self, bg="#f4f5f7", padx=16, pady=10)
        top_frame.pack(fill=tk.X)
        ttk.Label(top_frame, text="✨ 圖片/照片 AI 畫質修復工具", style="Header.TLabel").pack(anchor="w")
        self.lbl_engine = ttk.Label(top_frame, text="引擎狀態檢測中...", style="Status.TLabel")
        self.lbl_engine.pack(anchor="w", pady=(2, 0))

        # 2. 檔案選取區
        file_frame = tk.LabelFrame(self, text=" 待修復圖片清單 ", font=("Microsoft JhengHei UI", 10, "bold"), bg="#f4f5f7", padx=12, pady=6)
        file_frame.pack(fill=tk.BOTH, expand=False, padx=16, pady=4)
        file_frame.config(height=140)

        btn_row = tk.Frame(file_frame, bg="#f4f5f7")
        btn_row.pack(fill=tk.X, pady=(0, 4))
        ttk.Button(btn_row, text="➕ 選擇圖片 (可多選)", command=self._pick_files).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_row, text="🗑️ 清空清單", command=self._clear_files).pack(side=tk.LEFT)

        list_container = tk.Frame(file_frame, bg="#f4f5f7")
        list_container.pack(fill=tk.BOTH, expand=True)

        list_scroll = ttk.Scrollbar(list_container)
        self.listbox = tk.Listbox(
            list_container, yscrollcommand=list_scroll.set,
            font=("Microsoft JhengHei UI", 10), selectmode=tk.EXTENDED, height=4,
            bg="#ffffff", fg="#111827", selectbackground="#2563eb", selectforeground="#ffffff"
        )
        list_scroll.config(command=self.listbox.yview)
        list_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 3. 設定區
        opt_frame = tk.LabelFrame(self, text=" 修復參數設定 ", font=("Microsoft JhengHei UI", 10, "bold"), bg="#f4f5f7", padx=12, pady=6)
        opt_frame.pack(fill=tk.X, padx=16, pady=4)

        row1 = tk.Frame(opt_frame, bg="#f4f5f7")
        row1.pack(fill=tk.X, pady=2)

        ttk.Label(row1, text="AI 模型：", background="#f4f5f7").pack(side=tk.LEFT)
        self.model_var = tk.StringVar(value="realesrgan-x4plus")
        models = [
            ("realesrgan-x4plus (通用照片/真實圖片)", "realesrgan-x4plus"),
            ("realesrgan-x4plus-anime (動漫/插畫特化)", "realesrgan-x4plus-anime"),
            ("realesr-animevideov3 (快速二次元模式)", "realesr-animevideov3")
        ]
        self.cmb_model = ttk.Combobox(row1, textvariable=self.model_var, values=[m[0] for m in models], width=36, state="readonly")
        self.cmb_model.current(0)
        self.cmb_model.pack(side=tk.LEFT, padx=(0, 16))
        self.model_map = {m[0]: m[1] for m in models}

        ttk.Label(row1, text="放大倍率：", background="#f4f5f7").pack(side=tk.LEFT)
        self.scale_var = tk.StringVar(value="4")
        cmb_scale = ttk.Combobox(row1, textvariable=self.scale_var, values=["2", "4"], width=4, state="readonly")
        cmb_scale.pack(side=tk.LEFT)

        # 4. 進度條區
        stat_box = tk.Frame(self, bg="#f4f5f7", padx=16, pady=4)
        stat_box.pack(fill=tk.X)
        self.progress = ttk.Progressbar(stat_box, mode="determinate")
        self.progress.pack(fill=tk.X, pady=(0, 2))
        self.lbl_progress = ttk.Label(stat_box, text="準備就緒", style="Status.TLabel")
        self.lbl_progress.pack(anchor="w")

        # 5. [新增] 執行歷程與處理記錄框框 (紅圈處)
        log_frame = tk.LabelFrame(self, text=" 📜 執行歷程與處理記錄 ", font=("Microsoft JhengHei UI", 10, "bold"), bg="#f4f5f7", padx=10, pady=6)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=4)

        log_scroll = ttk.Scrollbar(log_frame)
        self.txt_log = tk.Text(
            log_frame, yscrollcommand=log_scroll.set,
            font=("Microsoft JhengHei UI", 10),
            bg="#ffffff", fg="#111827", insertbackground="#111827",
            spacing1=3, spacing2=2, spacing3=3, padx=10, pady=6,
            relief=tk.SOLID, bd=1, wrap=tk.WORD, height=8
        )
        # 設定彩色標籤樣式，使文字層次分明
        self.txt_log.tag_config("time", foreground="#6b7280")
        self.txt_log.tag_config("success", foreground="#15803d", font=("Microsoft JhengHei UI", 10, "bold"))
        self.txt_log.tag_config("info", foreground="#1d4ed8")
        self.txt_log.tag_config("warn", foreground="#b91c1c", font=("Microsoft JhengHei UI", 10, "bold"))

        log_scroll.config(command=self.txt_log.yview)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.txt_log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 6. 底部操作按鈕區
        bot_frame = tk.Frame(self, bg="#f4f5f7", padx=16, pady=10)
        bot_frame.pack(fill=tk.X)

        self.btn_dl_engine = ttk.Button(bot_frame, text="⬇️ 下載/更新 AI 引擎", command=self._download_engine)
        self.btn_dl_engine.pack(side=tk.LEFT)

        # 開始修復按鈕
        self.btn_start = tk.Button(
            bot_frame, text="🚀 開始 AI 畫質修復", font=("Microsoft JhengHei UI", 10, "bold"),
            bg="#2563eb", fg="white", activebackground="#1d4ed8", activeforeground="white",
            padx=14, pady=6, relief=tk.FLAT, cursor="hand2", command=self._start_enhance
        )
        self.btn_start.pack(side=tk.RIGHT, padx=(6, 0))

        # [新增] 取消進度按鈕
        self.btn_cancel = tk.Button(
            bot_frame, text="⏹️ 取消修復", font=("Microsoft JhengHei UI", 10, "bold"),
            bg="#9ca3af", fg="white", activebackground="#dc2626", activeforeground="white",
            padx=12, pady=6, relief=tk.FLAT, cursor="arrow", command=self._cancel_enhance, state=tk.DISABLED
        )
        self.btn_cancel.pack(side=tk.RIGHT, padx=(6, 0))

        # 開啟資料夾按鈕
        self.btn_open_folder = ttk.Button(bot_frame, text="📁 開啟所在資料夾", command=self._open_output_dir)
        self.btn_open_folder.pack(side=tk.RIGHT, padx=6)

    def _log(self, text: str):
        now_str = time.strftime("%H:%M:%S")
        self.txt_log.insert(tk.END, f"[{now_str}] ", "time")

        tag = None
        if "✅" in text:
            tag = "success"
        elif "⏳" in text or "🚀" in text:
            tag = "info"
        elif "❌" in text or "⚠️" in text or "⏹️" in text:
            tag = "warn"

        if tag:
            self.txt_log.insert(tk.END, f"{text}\n", tag)
        else:
            self.txt_log.insert(tk.END, f"{text}\n")

        self.txt_log.see(tk.END)

    def _get_ai_bin(self):
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

    def _check_engine_status(self):
        ai_bin = self._get_ai_bin()
        if ai_bin:
            self.lbl_engine.config(text=f"🟢 AI 引擎已就緒：{ai_bin.name}", foreground="#16a34a")
            self.btn_dl_engine.config(text="✅ AI 引擎已安裝")
            self._log(f"AI 引擎就緒: {ai_bin}")
        else:
            self.lbl_engine.config(text="🟡 尚未檢測到 Real-ESRGAN-ncnn-vulkan（可點擊左下方按鈕一鍵下載）", foreground="#d97706")
            self._log("未檢測到本機 AI 引擎，需要時可點擊左下角下載。")

    def _pick_files(self):
        files = filedialog.askopenfilenames(
            title="選擇圖片",
            filetypes=[("圖片檔案", "*.jpg *.jpeg *.png *.webp *.bmp *.tif")]
        )
        added_count = 0
        for f in files:
            p = str(Path(f).resolve())
            if p not in self.selected_files:
                self.selected_files.append(p)
                self.listbox.insert(tk.END, p)
                added_count += 1
        if added_count > 0:
            self._log(f"選取加入 {added_count} 張圖片，目前清單共 {len(self.selected_files)} 張。")
            self.lbl_progress.config(text=f"已選取 {len(self.selected_files)} 張圖片")

    def _clear_files(self):
        if self.is_processing:
            return
        self.selected_files.clear()
        self.listbox.delete(0, tk.END)
        self.lbl_progress.config(text="已清空清單")
        self._log("已清空待修復圖片清單。")

    def _download_engine(self):
        if self.is_processing:
            return
        if self._get_ai_bin():
            messagebox.showinfo("提示", "Real-ESRGAN AI 引擎已經就緒，無需重複下載！")
            return

        self.is_processing = True
        self.is_cancelled = False
        self.lbl_progress.config(text="正在連接伺服器下載 Real-ESRGAN AI 引擎 (約 25MB)...")
        self.progress.config(mode="determinate", value=0, maximum=100)
        self._log("開始下載 Real-ESRGAN AI 引擎...")

        def progress_callback(current, total):
            pct = int((current / total) * 100) if total > 0 else 0
            mb_cur = current / (1024 * 1024)
            mb_tot = total / (1024 * 1024)
            self.after(0, lambda: [
                self.progress.config(value=pct),
                self.lbl_progress.config(text=f"下載進度: {pct}% ({mb_cur:.1f}MB / {mb_tot:.1f}MB) ...")
            ])

        def worker():
            try:
                from download_ai_engine import download_and_extract
                download_and_extract(progress_cb=progress_callback)
                ai_bin = self._get_ai_bin()
                if not ai_bin:
                    raise FileNotFoundError("下載完成但未能定位到執行檔 realesrgan-ncnn-vulkan.exe")
                self.after(0, lambda: [
                    self._check_engine_status(),
                    self.progress.config(value=100),
                    self.lbl_progress.config(text="✅ AI 引擎已成功安裝並就緒！"),
                    self._log("✅ Real-ESRGAN AI 引擎下載安裝成功！"),
                    messagebox.showinfo("成功", f"Real-ESRGAN AI 引擎已成功安裝！\n路徑: {ai_bin}")
                ])
            except Exception as e:
                self.after(0, lambda err=e: [
                    self._check_engine_status(),
                    self.progress.config(value=0),
                    self.lbl_progress.config(text=f"❌ 下載失敗: {err}"),
                    self._log(f"❌ 下載引擎失敗: {err}"),
                    messagebox.showerror("下載失敗", f"無法下載或解壓 AI 引擎：\n{err}\n\n請檢查網路連線或防毒軟體設定。")
                ])
            finally:
                self.is_processing = False

        threading.Thread(target=worker, daemon=True).start()

    def _start_enhance(self):
        if self.is_processing:
            return
        if not self.selected_files:
            messagebox.showwarning("提醒", "請先選擇至少一張圖片！")
            return

        ai_bin = self._get_ai_bin()
        if not ai_bin:
            if messagebox.askyesno("提示", "尚未安裝 Real-ESRGAN AI 引擎，是否立即自動下載？"):
                self._download_engine()
            return

        self.is_processing = True
        self.is_cancelled = False
        self.current_proc = None
        self.current_dst = None

        # 按鈕狀態切換
        self.btn_start.config(state=tk.DISABLED, bg="#9ca3af", cursor="arrow")
        self.btn_cancel.config(state=tk.NORMAL, bg="#ef4444", cursor="hand2")

        total = len(self.selected_files)
        self.progress.config(mode="determinate", maximum=total, value=0)

        model_name = self.model_map.get(self.cmb_model.get(), "realesrgan-x4plus")
        scale = self.scale_var.get()

        self._log(f"🚀 開始批次 AI 畫質修復：共 {total} 張圖片 (模型: {model_name}, 放大: {scale}x)")

        def worker():
            success_count = 0
            for idx, file_path in enumerate(self.selected_files, start=1):
                if self.is_cancelled:
                    break

                src = Path(file_path)
                dst = src.with_name(f"{src.stem}_enhanced_{model_name}{src.suffix}")
                self.current_dst = dst

                self.after(0, lambda i=idx, s=src: [
                    self.lbl_progress.config(text=f"正在放大 ({i}/{total}): {s.name} ..."),
                    self._log(f"⏳ ({i}/{total}) 開始放大處理: {s.name} ...")
                ])

                try:
                    cmd = [str(ai_bin), "-i", str(src), "-o", str(dst), "-s", str(scale), "-n", model_name]
                    models_dir = ai_bin.parent / "models"
                    if models_dir.exists():
                        cmd += ["-m", str(models_dir)]

                    si = subprocess.STARTUPINFO()
                    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

                    self.current_proc = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        bufsize=1,
                        universal_newlines=True,
                        startupinfo=si,
                        creationflags=creationflags
                    )

                    # 即時讀取單張圖片內部放大百分比 (例如 25.00%, 50.00%)
                    if self.current_proc.stdout:
                        for line in iter(self.current_proc.stdout.readline, ''):
                            if self.is_cancelled:
                                break
                            txt = line.strip()
                            if "%" in txt:
                                self.after(0, lambda i=idx, s=src, p=txt: [
                                    self.lbl_progress.config(text=f"正在放大 ({i}/{total}): {s.name} [{p}]")
                                ])

                    self.current_proc.wait()

                    if self.is_cancelled:
                        self.after(0, lambda s=src: self._log(f"⏹️ 已即時中斷放大: {s.name}"))
                        break

                    if self.current_proc.returncode == 0:
                        success_count += 1
                        self.after(0, lambda i=idx, d=dst: self._log(f"✅ ({i}/{total}) 完成！輸出: {d.name}"))
                    else:
                        self.after(0, lambda s=src: self._log(f"⚠️ 處理失敗: {s.name} (結束碼 {self.current_proc.returncode})"))
                except Exception as e:
                    self.after(0, lambda s=src, err=e: self._log(f"❌ 處理異常 {s.name}: {err}"))

                self.after(0, lambda i=idx: self.progress.config(value=i))

            # 結束或被取消後的處理
            def finish_ui():
                self.current_proc = None
                self.btn_start.config(state=tk.NORMAL, bg="#2563eb", cursor="hand2")
                self.btn_cancel.config(state=tk.DISABLED, bg="#9ca3af", cursor="arrow")

                if self.is_cancelled:
                    self.lbl_progress.config(text=f"⏹️ 已取消作業（已完成 {success_count}/{total} 張）")
                    self._log(f"⏹️ 使用者已手動取消修復作業（已完成 {success_count}/{total} 張）。")
                    messagebox.showinfo("已取消", f"修復作業已在中途取消！\n已完成: {success_count}/{total} 張圖片。")
                else:
                    self.lbl_progress.config(text=f"🎉 全部 {total} 張圖片修復完成！")
                    self._log(f"🎉 全部 {total} 張圖片修復完成！")
                    messagebox.showinfo("完成", f"已成功修復 {total} 張圖片！")

                self.is_processing = False

            self.after(0, finish_ui)

        threading.Thread(target=worker, daemon=True).start()

    def _cancel_enhance(self):
        if not self.is_processing or self.is_cancelled:
            return
        self.is_cancelled = True
        self._log("⚠️ 收到取消指令！正在立即強制中斷運算中之程序...")
        self.lbl_progress.config(text="⏹️ 正在立即中止運算...")

        # 0 秒強制殺死 Windows 行程樹 (taskkill /F /T)
        if self.current_proc:
            try:
                pid = self.current_proc.pid
                subprocess.run(f"taskkill /F /T /PID {pid}", shell=True, capture_output=True)
                self.current_proc.kill()
            except Exception:
                pass

        # 自動清理放大到一半的未完成半成品檔案
        if self.current_dst:
            try:
                time.sleep(0.2)
                p = Path(self.current_dst)
                if p.exists():
                    p.unlink()
                    self._log(f"🗑️ 已自動清理放大到一半的半成品檔案: {p.name}")
            except Exception:
                pass

    def _open_output_dir(self):
        target = Path(self.selected_files[0]).parent if self.selected_files else ROOT_DIR
        self._log(f"開啟輸出資料夾: {target}")
        os.startfile(str(target))

if __name__ == "__main__":
    app = EnhancerApp()
    app.mainloop()
