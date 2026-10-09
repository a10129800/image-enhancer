import os, sys, shutil, subprocess, threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

DIR = Path(__file__).resolve().parent

class EnhancerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("圖片/照片 AI 畫質修復工具 (Real-ESRGAN)")
        self.geometry("680x560")
        self.minsize(550, 450)
        self.configure(bg="#f4f5f7")

        self.selected_files = []
        self.is_processing = False

        self._setup_style()
        self._build_ui()
        self._check_engine_status()

    def _setup_style(self):
        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.style.configure(".", font=("Microsoft JhengHei UI", 10))
        self.style.configure("Header.TLabel", font=("Microsoft JhengHei UI", 14, "bold"), background="#f4f5f7")
        self.style.configure("Status.TLabel", font=("Microsoft JhengHei UI", 9), foreground="#555", background="#f4f5f7")
        self.style.configure("Accent.TButton", font=("Microsoft JhengHei UI", 10, "bold"))

    def _build_ui(self):
        # 頂部標題區
        top_frame = tk.Frame(self, bg="#f4f5f7", padx=16, pady=12)
        top_frame.pack(fill=tk.X)
        ttk.Label(top_frame, text="✨ 圖片/照片 AI 畫質修復工具", style="Header.TLabel").pack(anchor="w")
        self.lbl_engine = ttk.Label(top_frame, text="引擎狀態檢測中...", style="Status.TLabel")
        self.lbl_engine.pack(anchor="w", pady=(2, 0))

        # 檔案選取區
        file_frame = tk.LabelFrame(self, text=" 待修復圖片清單 ", font=("Microsoft JhengHei UI", 10, "bold"), bg="#f4f5f7", padx=12, pady=8)
        file_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=4)

        btn_row = tk.Frame(file_frame, bg="#f4f5f7")
        btn_row.pack(fill=tk.X, pady=(0, 6))
        ttk.Button(btn_row, text="➕ 選擇圖片 (可多選)", command=self._pick_files).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_row, text="🗑️ 清空清單", command=self._clear_files).pack(side=tk.LEFT)

        # 圖片清單列表
        list_scroll = ttk.Scrollbar(file_frame)
        self.listbox = tk.Listbox(file_frame, yscrollcommand=list_scroll.set, font=("Consolas", 9), selectmode=tk.EXTENDED)
        list_scroll.config(command=self.listbox.yview)
        list_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 設定區
        opt_frame = tk.LabelFrame(self, text=" 修復參數設定 ", font=("Microsoft JhengHei UI", 10, "bold"), bg="#f4f5f7", padx=12, pady=8)
        opt_frame.pack(fill=tk.X, padx=16, pady=6)

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

        # 進度條與狀態日誌
        stat_box = tk.Frame(self, bg="#f4f5f7", padx=16, pady=4)
        stat_box.pack(fill=tk.X)
        self.progress = ttk.Progressbar(stat_box, mode="determinate")
        self.progress.pack(fill=tk.X, pady=(0, 4))
        self.lbl_progress = ttk.Label(stat_box, text="準備就緒", style="Status.TLabel")
        self.lbl_progress.pack(anchor="w")

        # 底部操作區
        bot_frame = tk.Frame(self, bg="#f4f5f7", padx=16, pady=10)
        bot_frame.pack(fill=tk.X)
        self.btn_start = tk.Button(
            bot_frame, text="🚀 開始 AI 畫質修復", font=("Microsoft JhengHei UI", 11, "bold"),
            bg="#2563eb", fg="white", activebackground="#1d4ed8", activeforeground="white",
            padx=16, pady=6, relief=tk.FLAT, cursor="hand2", command=self._start_enhance
        )
        self.btn_start.pack(side=tk.RIGHT, padx=(6, 0))

        self.btn_open_folder = ttk.Button(bot_frame, text="📁 開啟所在資料夾", command=self._open_output_dir)
        self.btn_open_folder.pack(side=tk.RIGHT, padx=6)

        self.btn_dl_engine = ttk.Button(bot_frame, text="⬇️ 下載/更新 AI 引擎", command=self._download_engine)
        self.btn_dl_engine.pack(side=tk.LEFT)

    def _get_ai_bin(self):
        local_bin = DIR / "realesrgan-ncnn-vulkan.exe"
        if local_bin.exists():
            return local_bin
        system_bin = shutil.which("realesrgan-ncnn-vulkan")
        return Path(system_bin) if system_bin else None

    def _check_engine_status(self):
        ai_bin = self._get_ai_bin()
        if ai_bin:
            self.lbl_engine.config(text=f"🟢 AI 引擎已就緒：{ai_bin.name}", foreground="#16a34a")
            self.btn_dl_engine.config(text="✅ AI 引擎已安裝")
        else:
            self.lbl_engine.config(text="🟡 尚未檢測到 Real-ESRGAN-ncnn-vulkan（可點擊左下方按鈕一鍵下載）", foreground="#d97706")

    def _pick_files(self):
        files = filedialog.askopenfilenames(
            title="選擇圖片",
            filetypes=[("圖片檔案", "*.jpg *.jpeg *.png *.webp *.bmp *.tif")]
        )
        for f in files:
            p = str(Path(f).resolve())
            if p not in self.selected_files:
                self.selected_files.append(p)
                self.listbox.insert(tk.END, p)
        self.lbl_progress.config(text=f"已選取 {len(self.selected_files)} 張圖片")

    def _clear_files(self):
        if self.is_processing:
            return
        self.selected_files.clear()
        self.listbox.delete(0, tk.END)
        self.lbl_progress.config(text="已清空清單")

    def _download_engine(self):
        if self.is_processing:
            return
        if self._get_ai_bin():
            messagebox.showinfo("提示", "Real-ESRGAN AI 引擎已經就緒，無需重複下載！")
            return

        self.is_processing = True
        self.lbl_progress.config(text="正在連接伺服器下載 Real-ESRGAN AI 引擎 (約 25MB)...")
        self.progress.config(mode="determinate", value=0, maximum=100)

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
                    messagebox.showinfo("成功", f"Real-ESRGAN AI 引擎已成功安裝！\n路徑: {ai_bin}")
                ])
            except Exception as e:
                self.after(0, lambda err=e: [
                    self._check_engine_status(),
                    self.progress.config(value=0),
                    self.lbl_progress.config(text=f"❌ 下載失敗: {err}"),
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
        self.btn_start.config(state=tk.DISABLED, bg="#9ca3af")
        total = len(self.selected_files)
        self.progress.config(mode="determinate", maximum=total, value=0)

        model_name = self.model_map.get(self.cmb_model.get(), "realesrgan-x4plus")
        scale = self.scale_var.get()

        def worker():
            for idx, file_path in enumerate(self.selected_files, start=1):
                src = Path(file_path)
                dst = src.with_name(f"{src.stem}_enhanced_{model_name}{src.suffix}")
                self.after(0, lambda i=idx, s=src: self.lbl_progress.config(text=f"正在修復 ({i}/{total}): {s.name} ..."))
                try:
                    cmd = [str(ai_bin), "-i", str(src), "-o", str(dst), "-s", str(scale), "-n", model_name]
                    # Windows 下隱藏命令提示字元黑視窗
                    si = subprocess.STARTUPINFO()
                    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    subprocess.run(cmd, startupinfo=si, check=True)
                except Exception as e:
                    print(f"處理失敗 {src.name}: {e}")
                self.after(0, lambda i=idx: self.progress.config(value=i))

            self.after(0, lambda: [
                self.lbl_progress.config(text=f"🎉 全部 {total} 張圖片修復完成！"),
                self.btn_start.config(state=tk.NORMAL, bg="#2563eb"),
                messagebox.showinfo("完成", f"已成功修復 {total} 張圖片！")
            ])
            self.is_processing = False

        threading.Thread(target=worker, daemon=True).start()

    def _open_output_dir(self):
        target = Path(self.selected_files[0]).parent if self.selected_files else DIR
        os.startfile(str(target))

if __name__ == "__main__":
    app = EnhancerApp()
    app.mainloop()
