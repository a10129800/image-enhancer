import os, sys, shutil, subprocess, threading, time
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk, ImageDraw

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

# 匯入浮水印消除模組
try:
    from remove_watermark import remove_watermark_inpaint, has_opencv, install_opencv
except ImportError:
    from src.remove_watermark import remove_watermark_inpaint, has_opencv, install_opencv

class EnhancerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("圖片/照片 AI 畫質修復 & 消除浮水印工具")
        self.geometry("860x780")
        self.minsize(760, 680)
        self.configure(bg="#f4f5f7")

        # --- AI 放大分頁狀態 ---
        self.selected_files = []
        self.is_processing = False
        self.is_cancelled = False
        self.current_proc = None
        self.current_dst = None

        # --- 浮水印分頁狀態 ---
        self.wm_orig_image = None       # PIL Image 原圖
        self.wm_current_image = None    # PIL Image (修復後或原圖)
        self.wm_mask = None             # PIL Image (L 通道，與原圖同尺寸)
        self.wm_file_path = None        # 原圖路徑
        self.wm_mask_history = []       # 撤銷歷史
        self.wm_brush_size = 25         # 筆刷半徑 (px)
        self.wm_base_scale = 1.0        # 適應畫布的基準縮放
        self.wm_zoom_level = 1.0        # 額外放大倍率 (1.0 = 100%, 最大 8.0)
        self.wm_pan_x = 0.0             # 平移 X 偏移
        self.wm_pan_y = 0.0             # 平移 Y 偏移
        self.wm_canvas_offset = (0, 0)  # 居中偏移 (dx, dy)
        self.wm_effective_scale = 1.0   # 最終縮放比例
        self.wm_canvas_img_ref = None   # 防止被 GC 回收
        self.wm_last_pos = None
        self.wm_pan_start = None        # 滑鼠右鍵平移拖曳起點

        self._organize_workspace()
        self._setup_icon()
        self._setup_style()
        self._build_ui()
        self._check_engine_status()
        self._check_opencv_status()
        self._log("系統初始化完成，準備就緒。")

    def _setup_icon(self):
        ico_path = ROOT_DIR / "assets" / "app.ico"
        png_path = ROOT_DIR / "assets" / "app_icon.png"
        icon_source = Path(r"C:\Users\mice\.gemini\antigravity-ide\brain\c76d24df-8eaa-44b9-90c0-75c423faeaad\app_icon_1791528717867.jpg")

        if not ico_path.exists() and icon_source.exists():
            try:
                img = Image.open(icon_source)
                ico_path.parent.mkdir(exist_ok=True)
                img.save(ico_path, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
                img.save(png_path)
            except Exception:
                pass

        if ico_path.exists():
            try:
                self.iconbitmap(str(ico_path))
            except Exception:
                pass

        # 自動生成帶有精美圖示的本機 Windows 捷徑 (.lnk)
        lnk_path = ROOT_DIR / "圖片畫質提高工具.lnk"
        bat_target = ROOT_DIR / "run_enhance.bat"
        if not lnk_path.exists() and ico_path.exists() and bat_target.exists():
            try:
                vbs_code = f'Set ws=CreateObject("WScript.Shell"):Set l=ws.CreateShortcut("{lnk_path}"):l.TargetPath="{bat_target}":l.WorkingDirectory="{ROOT_DIR}":l.IconLocation="{ico_path},0":l.Save'
                vbs_temp = ROOT_DIR / "create_lnk.vbs"
                vbs_temp.write_text(vbs_code, encoding="utf-8")
                subprocess.run(["cscript", "//nologo", str(vbs_temp)], capture_output=True)
                if vbs_temp.exists():
                    vbs_temp.unlink()
            except Exception:
                pass

    def _organize_workspace(self):
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

        assets_dir = ROOT_DIR / "assets"
        assets_dir.mkdir(exist_ok=True)
        for img_name in ["DEMO.png", "Demo2.png"]:
            p = ROOT_DIR / img_name
            if p.exists() and not (assets_dir / img_name).exists():
                shutil.move(str(p), str(assets_dir / img_name))

    def _setup_style(self):
        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.style.configure(".", font=("Microsoft JhengHei UI", 10))
        self.style.configure("Header.TLabel", font=("Microsoft JhengHei UI", 14, "bold"), background="#f4f5f7")
        self.style.configure("Status.TLabel", font=("Microsoft JhengHei UI", 9), foreground="#555", background="#f4f5f7")
        self.style.configure("TNotebook.Tab", font=("Microsoft JhengHei UI", 10, "bold"), padding=[16, 6])

    def _build_ui(self):
        # 頂部全域標籤
        top_frame = tk.Frame(self, bg="#f4f5f7", padx=16, pady=8)
        top_frame.pack(fill=tk.X)
        ttk.Label(top_frame, text="✨ 圖片/照片 AI 畫質修復 & 消除浮水印工具", style="Header.TLabel").pack(anchor="w")

        # 分頁選單 Notebook
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 8))

        # 分頁 1: 🚀 AI 畫質修復
        self.tab_enhance = tk.Frame(self.notebook, bg="#f4f5f7")
        self.notebook.add(self.tab_enhance, text=" 🚀 AI 畫質修復 (4x 超解析度) ")
        self._build_enhance_tab()

        # 分頁 2: 🧼 塗抹消除浮水印
        self.tab_watermark = tk.Frame(self.notebook, bg="#f4f5f7")
        self.notebook.add(self.tab_watermark, text=" 🧼 塗抹消除浮水印 (Inpainting) ")
        self._build_watermark_tab()

    # =========================================================================
    # 分頁 1：AI 畫質修復
    # =========================================================================
    def _build_enhance_tab(self):
        parent = self.tab_enhance

        self.lbl_engine = ttk.Label(parent, text="引擎狀態檢測中...", style="Status.TLabel")
        self.lbl_engine.pack(anchor="w", padx=12, pady=(6, 2))

        # 檔案選取清單
        file_frame = tk.LabelFrame(parent, text=" 待修復圖片清單 ", font=("Microsoft JhengHei UI", 10, "bold"), bg="#f4f5f7", padx=12, pady=6)
        file_frame.pack(fill=tk.BOTH, expand=False, padx=12, pady=4)
        file_frame.config(height=130)

        btn_row = tk.Frame(file_frame, bg="#f4f5f7")
        btn_row.pack(fill=tk.X, pady=(0, 4))
        ttk.Button(btn_row, text="➕ 選擇圖片 (可多選)", command=self._pick_files).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_row, text="🗑️ 清空清單", command=self._clear_files).pack(side=tk.LEFT)

        list_container = tk.Frame(file_frame, bg="#f4f5f7")
        list_container.pack(fill=tk.BOTH, expand=True)

        list_scroll = ttk.Scrollbar(list_container)
        self.listbox = tk.Listbox(
            list_container, yscrollcommand=list_scroll.set,
            font=("Microsoft JhengHei UI", 10), selectmode=tk.EXTENDED, height=3,
            bg="#ffffff", fg="#111827", selectbackground="#2563eb", selectforeground="#ffffff"
        )
        list_scroll.config(command=self.listbox.yview)
        list_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 參數設定
        opt_frame = tk.LabelFrame(parent, text=" 修復參數設定 ", font=("Microsoft JhengHei UI", 10, "bold"), bg="#f4f5f7", padx=12, pady=6)
        opt_frame.pack(fill=tk.X, padx=12, pady=4)

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

        # 進度條
        stat_box = tk.Frame(parent, bg="#f4f5f7", padx=12, pady=4)
        stat_box.pack(fill=tk.X)
        self.progress = ttk.Progressbar(stat_box, mode="determinate")
        self.progress.pack(fill=tk.X, pady=(0, 2))
        self.lbl_progress = ttk.Label(stat_box, text="準備就緒", style="Status.TLabel")
        self.lbl_progress.pack(anchor="w")

        # 歷程日誌框
        log_frame = tk.LabelFrame(parent, text=" 📜 執行歷程與處理記錄 ", font=("Microsoft JhengHei UI", 10, "bold"), bg="#f4f5f7", padx=10, pady=6)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=4)

        log_scroll = ttk.Scrollbar(log_frame)
        self.txt_log = tk.Text(
            log_frame, yscrollcommand=log_scroll.set,
            font=("Microsoft JhengHei UI", 10),
            bg="#ffffff", fg="#111827", insertbackground="#111827",
            spacing1=2, spacing2=1, spacing3=2, padx=10, pady=6,
            relief=tk.SOLID, bd=1, wrap=tk.WORD, height=6
        )
        self.txt_log.tag_config("time", foreground="#6b7280")
        self.txt_log.tag_config("success", foreground="#15803d", font=("Microsoft JhengHei UI", 10, "bold"))
        self.txt_log.tag_config("info", foreground="#1d4ed8")
        self.txt_log.tag_config("warn", foreground="#b91c1c", font=("Microsoft JhengHei UI", 10, "bold"))

        log_scroll.config(command=self.txt_log.yview)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.txt_log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 底部按鈕
        bot_frame = tk.Frame(parent, bg="#f4f5f7", padx=12, pady=8)
        bot_frame.pack(fill=tk.X)

        self.btn_dl_engine = ttk.Button(bot_frame, text="⬇️ 下載/更新 AI 引擎", command=self._download_engine)
        self.btn_dl_engine.pack(side=tk.LEFT)

        self.btn_start = tk.Button(
            bot_frame, text="🚀 開始 AI 畫質修復", font=("Microsoft JhengHei UI", 10, "bold"),
            bg="#2563eb", fg="white", activebackground="#1d4ed8", activeforeground="white",
            padx=14, pady=6, relief=tk.FLAT, cursor="hand2", command=self._start_enhance
        )
        self.btn_start.pack(side=tk.RIGHT, padx=(6, 0))

        self.btn_cancel = tk.Button(
            bot_frame, text="⏹️ 取消修復", font=("Microsoft JhengHei UI", 10, "bold"),
            bg="#9ca3af", fg="white", activebackground="#dc2626", activeforeground="white",
            padx=12, pady=6, relief=tk.FLAT, cursor="arrow", command=self._cancel_enhance, state=tk.DISABLED
        )
        self.btn_cancel.pack(side=tk.RIGHT, padx=(6, 0))

        self.btn_open_folder = ttk.Button(bot_frame, text="📁 開啟所在資料夾", command=self._open_output_dir)
        self.btn_open_folder.pack(side=tk.RIGHT, padx=6)

    # =========================================================================
    # 分頁 2：塗抹消除浮水印 (Inpainting)
    # =========================================================================
    def _build_watermark_tab(self):
        parent = self.tab_watermark

        # 頂部控制面板
        tool_frame = tk.LabelFrame(parent, text=" 塗抹工具列 ", font=("Microsoft JhengHei UI", 10, "bold"), bg="#f4f5f7", padx=10, pady=6)
        tool_frame.pack(fill=tk.X, padx=12, pady=(6, 4))

        row1 = tk.Frame(tool_frame, bg="#f4f5f7")
        row1.pack(fill=tk.X, pady=2)

        ttk.Button(row1, text="📂 開啟圖片", command=self._wm_pick_image).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(row1, text="筆刷粗細：", background="#f4f5f7").pack(side=tk.LEFT)
        self.wm_slider = ttk.Scale(row1, from_=5, to=80, value=25, orient=tk.HORIZONTAL, command=self._wm_update_brush_size)
        self.wm_slider.pack(side=tk.LEFT, padx=(0, 4), fill=tk.X)
        self.lbl_brush_size = ttk.Label(row1, text="25px", width=5, background="#f4f5f7")
        self.lbl_brush_size.pack(side=tk.LEFT, padx=(0, 8))

        # 縮放控制群組
        zoom_box = tk.Frame(row1, bg="#f4f5f7")
        zoom_box.pack(side=tk.LEFT, padx=(4, 10))
        ttk.Label(zoom_box, text="🔍 視角：", background="#f4f5f7").pack(side=tk.LEFT)
        ttk.Button(zoom_box, text="➕ 放大", width=6, command=self._wm_zoom_in).pack(side=tk.LEFT, padx=1)
        ttk.Button(zoom_box, text="➖ 縮小", width=6, command=self._wm_zoom_out).pack(side=tk.LEFT, padx=1)
        ttk.Button(zoom_box, text="🔄 重置", width=6, command=self._wm_zoom_reset).pack(side=tk.LEFT, padx=1)
        self.lbl_zoom = ttk.Label(zoom_box, text="100%", width=5, font=("Microsoft JhengHei UI", 9, "bold"), background="#f4f5f7")
        self.lbl_zoom.pack(side=tk.LEFT, padx=2)

        ttk.Label(row1, text="修補模式：", background="#f4f5f7").pack(side=tk.LEFT)
        self.wm_method_var = tk.StringVar(value="Telea (推薦-邊緣細緻)")
        cmb_wm = ttk.Combobox(row1, textvariable=self.wm_method_var, values=["Telea (推薦-邊緣細緻)", "Navier-Stokes (流體平滑)"], width=18, state="readonly")
        cmb_wm.current(0)
        cmb_wm.pack(side=tk.LEFT, padx=(0, 8))

        ttk.Button(row1, text="↩️ 復原 (Undo)", command=self._wm_undo).pack(side=tk.LEFT, padx=2)
        ttk.Button(row1, text="🗑️ 清除標記", command=self._wm_clear_mask).pack(side=tk.LEFT, padx=2)

        # 動作按鈕列
        row2 = tk.Frame(tool_frame, bg="#f4f5f7")
        row2.pack(fill=tk.X, pady=(6, 2))

        self.btn_wm_run = tk.Button(
            row2, text="✨ 立即消除水印", font=("Microsoft JhengHei UI", 10, "bold"),
            bg="#0284c7", fg="white", activebackground="#0369a1", activeforeground="white",
            padx=14, pady=5, relief=tk.FLAT, cursor="hand2", command=self._wm_apply_inpaint
        )
        self.btn_wm_run.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_wm_save = ttk.Button(row2, text="💾 另存消除後圖片", command=self._wm_save_image, state=tk.DISABLED)
        self.btn_wm_save.pack(side=tk.LEFT, padx=4)

        self.btn_wm_send = tk.Button(
            row2, text="🚀 傳送至 AI 放大修復", font=("Microsoft JhengHei UI", 10, "bold"),
            bg="#16a34a", fg="white", activebackground="#15803d", activeforeground="white",
            padx=12, pady=5, relief=tk.FLAT, cursor="hand2", command=self._wm_send_to_enhancer, state=tk.DISABLED
        )
        self.btn_wm_send.pack(side=tk.LEFT, padx=4)

        self.lbl_wm_info = ttk.Label(row2, text="💡 提示：滾輪可縮放視角(最高800%)，按住右鍵拖動畫布，左鍵塗抹浮水印", style="Status.TLabel")
        self.lbl_wm_info.pack(side=tk.RIGHT, padx=4)

        # 中央互動式畫布
        canvas_frame = tk.Frame(parent, bg="#e2e8f0", bd=1, relief=tk.SOLID)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=4)

        self.wm_canvas = tk.Canvas(canvas_frame, bg="#1e293b", cursor="crosshair", highlightthickness=0)
        self.wm_canvas.pack(fill=tk.BOTH, expand=True)

        self.wm_canvas.bind("<Configure>", lambda e: self._wm_render_canvas())
        self.wm_canvas.bind("<Button-1>", self._wm_on_mouse_down)
        self.wm_canvas.bind("<B1-Motion>", self._wm_on_mouse_drag)
        self.wm_canvas.bind("<ButtonRelease-1>", self._wm_on_mouse_up)
        # 滑鼠滾輪縮放
        self.wm_canvas.bind("<MouseWheel>", self._wm_on_mouse_wheel)
        # 滑鼠右鍵或中鍵平移拖曳 (Pan)
        self.wm_canvas.bind("<Button-3>", self._wm_on_pan_down)
        self.wm_canvas.bind("<B3-Motion>", self._wm_on_pan_drag)
        self.wm_canvas.bind("<ButtonRelease-3>", self._wm_on_pan_up)
        self.wm_canvas.bind("<Button-2>", self._wm_on_pan_down)
        self.wm_canvas.bind("<B2-Motion>", self._wm_on_pan_drag)
        self.wm_canvas.bind("<ButtonRelease-2>", self._wm_on_pan_up)
        # 移動時顯示筆刷大小光標
        self.wm_canvas.bind("<Motion>", self._wm_on_mouse_move)
        self.wm_canvas.bind("<Leave>", lambda e: self.wm_canvas.delete("brush_cursor"))

        # 底部引擎與狀態提示列
        wm_status_frame = tk.Frame(parent, bg="#f4f5f7", padx=12, pady=4)
        wm_status_frame.pack(fill=tk.X)
        self.lbl_wm_engine = ttk.Label(wm_status_frame, text="檢測消除模組中...", style="Status.TLabel")
        self.lbl_wm_engine.pack(side=tk.LEFT)

        self.btn_install_cv = ttk.Button(wm_status_frame, text="⚡ 一鍵安裝高品質 OpenCV 引擎", command=self._wm_install_opencv)

    # -------------------------------------------------------------------------
    # 浮水印分頁邏輯
    # -------------------------------------------------------------------------
    def _check_opencv_status(self):
        if has_opencv():
            self.lbl_wm_engine.config(text="🟢 OpenCV 電影級 Inpainting 引擎已就緒（高品質無損修補）", foreground="#16a34a")
            self.btn_install_cv.pack_forget()
        else:
            self.lbl_wm_engine.config(text="🟡 目前使用 Pillow 智慧羽化修補模式（建議安裝 OpenCV 引擎可獲完美效果）", foreground="#d97706")
            self.btn_install_cv.pack(side=tk.RIGHT)

    def _wm_install_opencv(self):
        self.lbl_wm_engine.config(text="⏳ 正在背景安裝 opencv-python 與 numpy，請稍候...", foreground="#2563eb")
        self.btn_install_cv.config(state=tk.DISABLED)

        def done_cb(success):
            self.after(0, lambda: [
                self._check_opencv_status(),
                messagebox.showinfo("安裝結果", "🎉 OpenCV 消除引擎安裝成功！現已支援高品質修補。" if success else "安裝失敗，請確認網路或手動執行 pip install opencv-python")
            ])
        install_opencv(callback=done_cb)

    def _wm_update_brush_size(self, val):
        self.wm_brush_size = int(float(val))
        self.lbl_brush_size.config(text=f"{self.wm_brush_size}px")

    def _wm_pick_image(self):
        f = filedialog.askopenfilename(
            title="選擇要移除水印的圖片",
            filetypes=[("圖片檔案", "*.jpg *.jpeg *.png *.webp *.bmp *.tif")]
        )
        if not f:
            return

        try:
            self.wm_file_path = Path(f)
            self.wm_orig_image = Image.open(f).convert("RGB")
            self.wm_current_image = self.wm_orig_image.copy()
            self.wm_mask = Image.new("L", self.wm_orig_image.size, 0)
            self.wm_mask_history.clear()
            self.wm_mask_history.append(self.wm_mask.copy())

            # 重設視角縮放與平移
            self.wm_zoom_level = 1.0
            self.wm_pan_x = 0.0
            self.wm_pan_y = 0.0
            self.lbl_zoom.config(text="100%")

            self.btn_wm_save.config(state=tk.DISABLED)
            self.btn_wm_send.config(state=tk.DISABLED)
            self._wm_render_canvas()
            self.lbl_wm_info.config(text=f"已載入: {self.wm_file_path.name} ({self.wm_orig_image.width}x{self.wm_orig_image.height})，滾輪可放大局部、右鍵拖曳平移、左鍵塗抹")
        except Exception as e:
            messagebox.showerror("讀取失敗", f"無法開啟圖片：\n{e}")

    def _wm_render_canvas(self):
        if not self.wm_current_image:
            self.wm_canvas.delete("all")
            self.wm_canvas.create_text(
                self.wm_canvas.winfo_width() // 2 or 300,
                self.wm_canvas.winfo_height() // 2 or 200,
                text="🖼️ 請點擊上方『📂 開啟圖片』載入圖片\n以滑鼠滾輪放大/縮小視角，右鍵拖曳平移，左鍵塗抹浮水印",
                fill="#94a3b8", font=("Microsoft JhengHei UI", 12), justify=tk.CENTER
            )
            return

        cw = self.wm_canvas.winfo_width()
        ch = self.wm_canvas.winfo_height()
        if cw < 50 or ch < 50:
            return

        iw, ih = self.wm_orig_image.size
        base_scale = min(cw / iw, ch / ih, 1.0)
        self.wm_base_scale = base_scale
        eff_scale = base_scale * self.wm_zoom_level
        self.wm_effective_scale = eff_scale

        dw = int(iw * eff_scale)
        dh = int(ih * eff_scale)

        dx = (cw - dw) // 2 + int(self.wm_pan_x)
        dy = (ch - dh) // 2 + int(self.wm_pan_y)
        self.wm_canvas_offset = (dx, dy)

        # 視窗可見區域
        vx0 = max(0, dx)
        vy0 = max(0, dy)
        vx1 = min(cw, dx + dw)
        vy1 = min(ch, dy + dh)

        preview = self.wm_current_image.copy()
        if self.wm_mask and self.wm_mask.getbbox():
            red_overlay = Image.new("RGB", self.wm_orig_image.size, (239, 68, 68))
            alpha_mask = self.wm_mask.point(lambda p: int(p * 0.55))
            preview.paste(red_overlay, (0, 0), alpha_mask)

        self.wm_canvas.delete("all")

        if vx1 > vx0 and vy1 > vy0:
            cx0 = max(0.0, min(float(iw), (vx0 - dx) / eff_scale))
            cy0 = max(0.0, min(float(ih), (vy0 - dy) / eff_scale))
            cx1 = max(0.0, min(float(iw), (vx1 - dx) / eff_scale))
            cy1 = max(0.0, min(float(ih), (vy1 - dy) / eff_scale))

            crop_box = (int(cx0), int(cy0), max(int(cx0) + 1, int(cx1)), max(int(cy0) + 1, int(cy1)))
            cropped = preview.crop(crop_box)
            resized = cropped.resize((vx1 - vx0, vy1 - vy0), Image.BILINEAR)

            self.wm_canvas_img_ref = ImageTk.PhotoImage(resized)
            self.wm_canvas.create_image(vx0, vy0, anchor=tk.NW, image=self.wm_canvas_img_ref)

    # --- 縮放與平移控制 ---
    def _wm_zoom_in(self):
        cw = self.wm_canvas.winfo_width() // 2 or 300
        ch = self.wm_canvas.winfo_height() // 2 or 200
        self._wm_zoom_at(cw, ch, 1.3)

    def _wm_zoom_out(self):
        cw = self.wm_canvas.winfo_width() // 2 or 300
        ch = self.wm_canvas.winfo_height() // 2 or 200
        self._wm_zoom_at(cw, ch, 0.77)

    def _wm_zoom_reset(self):
        self.wm_zoom_level = 1.0
        self.wm_pan_x = 0.0
        self.wm_pan_y = 0.0
        self.lbl_zoom.config(text="100%")
        self._wm_render_canvas()

    def _wm_on_mouse_wheel(self, event):
        if not self.wm_orig_image:
            return
        factor = 1.25 if event.delta > 0 else 0.8
        self._wm_zoom_at(event.x, event.y, factor)

    def _wm_zoom_at(self, cx, cy, factor):
        if not self.wm_orig_image:
            return
        old_zoom = self.wm_zoom_level
        new_zoom = max(1.0, min(8.0, old_zoom * factor))
        if abs(new_zoom - old_zoom) < 0.01:
            return

        cw = self.wm_canvas.winfo_width()
        ch = self.wm_canvas.winfo_height()
        iw, ih = self.wm_orig_image.size
        base_scale = getattr(self, "wm_base_scale", 1.0)

        old_eff = base_scale * old_zoom
        new_eff = base_scale * new_zoom
        old_dx, old_dy = self.wm_canvas_offset

        # 找出游標在原圖的對應點
        img_x = (cx - old_dx) / old_eff if old_eff > 0 else 0
        img_y = (cy - old_dy) / old_eff if old_eff > 0 else 0

        self.wm_zoom_level = new_zoom

        if new_zoom <= 1.0:
            self.wm_pan_x = 0.0
            self.wm_pan_y = 0.0
        else:
            new_dw = int(iw * new_eff)
            new_dh = int(ih * new_eff)
            new_dx = cx - img_x * new_eff
            new_dy = cy - img_y * new_eff
            self.wm_pan_x = new_dx - (cw - new_dw) // 2
            self.wm_pan_y = new_dy - (ch - new_dh) // 2

        self.lbl_zoom.config(text=f"{int(self.wm_zoom_level * 100)}%")
        self._wm_render_canvas()

    def _wm_on_pan_down(self, event):
        self.wm_pan_start = (event.x, event.y)
        self.wm_canvas.config(cursor="fleur")

    def _wm_on_pan_drag(self, event):
        if not self.wm_orig_image or not self.wm_pan_start:
            return
        dx = event.x - self.wm_pan_start[0]
        dy = event.y - self.wm_pan_start[1]
        self.wm_pan_x += dx
        self.wm_pan_y += dy
        self.wm_pan_start = (event.x, event.y)
        self._wm_render_canvas()

    def _wm_on_pan_up(self, event):
        self.wm_pan_start = None
        self.wm_canvas.config(cursor="crosshair")

    def _wm_on_mouse_move(self, event):
        if not self.wm_orig_image:
            return
        self.wm_canvas.delete("brush_cursor")
        br = self.wm_brush_size
        self.wm_canvas.create_oval(
            event.x - br, event.y - br, event.x + br, event.y + br,
            outline="#ffffff", width=2, tags="brush_cursor"
        )
        self.wm_canvas.create_oval(
            event.x - br, event.y - br, event.x + br, event.y + br,
            outline="#ef4444", width=1, dash=(3, 3), tags="brush_cursor"
        )

    def _canvas_to_img_coords(self, cx, cy):
        dx, dy = self.wm_canvas_offset
        eff_scale = getattr(self, "wm_effective_scale", 1.0)
        if eff_scale <= 0:
            return 0, 0
        ix = int((cx - dx) / eff_scale)
        iy = int((cy - dy) / eff_scale)
        return max(0, min(self.wm_orig_image.width - 1, ix)), max(0, min(self.wm_orig_image.height - 1, iy))

    def _wm_on_mouse_down(self, event):
        if not self.wm_orig_image:
            return
        self.wm_last_pos = (event.x, event.y)
        self._wm_paint_at(event.x, event.y)

    def _wm_on_mouse_drag(self, event):
        if not self.wm_orig_image:
            return
        if self.wm_last_pos:
            self._wm_paint_line(self.wm_last_pos[0], self.wm_last_pos[1], event.x, event.y)
        else:
            self._wm_paint_at(event.x, event.y)
        self.wm_last_pos = (event.x, event.y)

    def _wm_on_mouse_up(self, event):
        self.wm_last_pos = None
        if self.wm_mask:
            if len(self.wm_mask_history) > 12:
                self.wm_mask_history.pop(0)
            self.wm_mask_history.append(self.wm_mask.copy())
            self._wm_render_canvas()

    def _wm_paint_at(self, cx, cy):
        ix, iy = self._canvas_to_img_coords(cx, cy)
        eff_scale = getattr(self, "wm_effective_scale", 1.0)
        r = max(1, int(self.wm_brush_size / eff_scale))
        draw = ImageDraw.Draw(self.wm_mask)
        draw.ellipse([ix - r, iy - r, ix + r, iy + r], fill=255)
        br = self.wm_brush_size
        self.wm_canvas.create_oval(cx - br, cy - br, cx + br, cy + br, fill="#ef4444", outline="", tags="temp_stroke")

    def _wm_paint_line(self, x1, y1, x2, y2):
        ix1, iy1 = self._canvas_to_img_coords(x1, y1)
        ix2, iy2 = self._canvas_to_img_coords(x2, y2)
        eff_scale = getattr(self, "wm_effective_scale", 1.0)
        r = max(1, int(self.wm_brush_size / eff_scale))
        draw = ImageDraw.Draw(self.wm_mask)
        draw.line([ix1, iy1, ix2, iy2], fill=255, width=r * 2)
        draw.ellipse([ix2 - r, iy2 - r, ix2 + r, iy2 + r], fill=255)
        self.wm_canvas.create_line(x1, y1, x2, y2, fill="#ef4444", width=self.wm_brush_size * 2, capstyle=tk.ROUND, tags="temp_stroke")

    def _wm_undo(self):
        if len(self.wm_mask_history) > 1:
            self.wm_mask_history.pop()
            self.wm_mask = self.wm_mask_history[-1].copy()
            self._wm_render_canvas()
            self.lbl_wm_info.config(text="已復原上一步筆刷標記。")
        elif len(self.wm_mask_history) == 1:
            self._wm_clear_mask()

    def _wm_clear_mask(self):
        if not self.wm_orig_image:
            return
        self.wm_mask = Image.new("L", self.wm_orig_image.size, 0)
        self.wm_mask_history = [self.wm_mask.copy()]
        self.wm_current_image = self.wm_orig_image.copy()
        self._wm_render_canvas()
        self.lbl_wm_info.config(text="已清除所有塗抹標記。")

    def _wm_apply_inpaint(self):
        if not self.wm_current_image or not self.wm_mask:
            messagebox.showwarning("提示", "請先載入圖片！")
            return
        if not self.wm_mask.getbbox():
            messagebox.showwarning("提醒", "請先用滑鼠在圖片上塗抹欲消除的浮水印或瑕疵！")
            return

        method = "telea" if "Telea" in self.wm_method_var.get() else "ns"
        self.lbl_wm_info.config(text="⏳ 正在進行智慧消除修補運算中，請稍候...")
        self.btn_wm_run.config(state=tk.DISABLED, bg="#9ca3af")

        def worker():
            try:
                res_img = remove_watermark_inpaint(
                    image=self.wm_orig_image,
                    mask=self.wm_mask,
                    method=method,
                    radius=5
                )
                def on_success():
                    self.wm_current_image = res_img
                    # 消除完成後自動清除遮罩
                    self.wm_mask = Image.new("L", self.wm_orig_image.size, 0)
                    self.wm_mask_history = [self.wm_mask.copy()]
                    self._wm_render_canvas()
                    self.btn_wm_run.config(state=tk.NORMAL, bg="#0284c7")
                    self.btn_wm_save.config(state=tk.NORMAL)
                    self.btn_wm_send.config(state=tk.NORMAL)
                    self.lbl_wm_info.config(text="🎉 浮水印消除完成！可另存圖片或一鍵傳送至 AI 畫質放大。")
                self.after(0, on_success)
            except Exception as e:
                def on_error(err=e):
                    self.btn_wm_run.config(state=tk.NORMAL, bg="#0284c7")
                    self.lbl_wm_info.config(text=f"❌ 消除修復失敗: {err}")
                    messagebox.showerror("修復錯誤", f"消除浮水印時發生錯誤：\n{err}")
                self.after(0, on_error)

        threading.Thread(target=worker, daemon=True).start()

    def _wm_save_image(self):
        if not self.wm_current_image:
            return
        default_name = f"{self.wm_file_path.stem}_clean{self.wm_file_path.suffix}" if self.wm_file_path else "cleaned.png"
        f = filedialog.asksaveasfilename(
            title="另存修復後圖片",
            initialfile=default_name,
            filetypes=[("PNG 圖片", "*.png"), ("JPG 圖片", "*.jpg"), ("所有檔案", "*.*")]
        )
        if f:
            try:
                self.wm_current_image.save(f)
                messagebox.showinfo("成功", f"圖片已儲存至：\n{f}")
            except Exception as e:
                messagebox.showerror("儲存失敗", f"無法儲存檔案：\n{e}")

    def _wm_send_to_enhancer(self):
        """將去水印後的成品，一鍵送至 Tab 1 (AI 畫質放大)"""
        if not self.wm_current_image or not self.wm_file_path:
            return
        temp_dir = ROOT_DIR / "samples"
        temp_dir.mkdir(exist_ok=True)
        out_path = temp_dir / f"{self.wm_file_path.stem}_cleaned.png"
        try:
            self.wm_current_image.save(out_path)
            str_path = str(out_path.resolve())
            if str_path not in self.selected_files:
                self.selected_files.append(str_path)
                self.listbox.insert(tk.END, str_path)
            # 切換至 Tab 1
            self.notebook.select(0)
            self._log(f"📥 已將消除浮水印成果載入至 AI 放大清單: {out_path.name}")
            self.lbl_progress.config(text=f"已成功載入去水印圖片，可直接點擊『開始 AI 畫質修復』進行 4x 放大！")
        except Exception as e:
            messagebox.showerror("傳送失敗", f"無法傳送圖片：\n{e}")

    # =========================================================================
    # 分頁 1 相關功能 (日誌/引擎/批次修復/取消)
    # =========================================================================
    def _log(self, text: str):
        now_str = time.strftime("%H:%M:%S")
        self.txt_log.insert(tk.END, f"[{now_str}] ", "time")
        tag = None
        if "✅" in text:
            tag = "success"
        elif "⏳" in text or "🚀" in text or "📥" in text:
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

        if self.current_proc:
            try:
                pid = self.current_proc.pid
                subprocess.run(f"taskkill /F /T /PID {pid}", shell=True, capture_output=True)
                self.current_proc.kill()
            except Exception:
                pass

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
