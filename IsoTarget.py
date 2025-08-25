# IsoTarget.py
# This version:
# - Swaps the behavior of "Skeletal Emphasis (Collins)" and "Low-Dose Boost".
# - Adds "RadFilter (Match Assist)" to aid matching difficult exposures.
# - Keeps Washburn Ichabod Balance, Jayhawk, Soft Tissue Enhance.
# - Uses cursor-anchored zoom (Ctrl+MouseWheel), AP-only rotation, dataset autoload,
#   splash and EULA, thumbnails to select the filter target (no target dropdown).

import os
import sys
import getpass
import datetime
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from PIL import Image, ImageTk, ImageEnhance, ImageFilter, ImageOps, ImageChops

# Pillow LANCZOS compatibility
try:
    from PIL.Image import Resampling as _Resample
    LANCZOS = _Resample.LANCZOS
except Exception:
    LANCZOS = getattr(Image, "LANCZOS", Image.BICUBIC)

APP_NAME  = "IsoTarget"
APP_TITLE = "IsoTarget :: Orthogonal DRR/KV Image Matcher"
DISPLAY_W, DISPLAY_H = 600, 400
THUMB_W, THUMB_H     = 300, 200


# ---------- resources ----------
def resource_path(rel_path: str) -> str:
    """Absolute path to bundled resource (works both in Python + PyInstaller)."""
    if hasattr(sys, "_MEIPASS"):
        base = sys._MEIPASS  # type: ignore[attr-defined]
    else:
        base = os.path.dirname(__file__)
    return os.path.join(base, rel_path)


def dataset_root() -> str:
    return os.path.join(os.path.expanduser("~"), "Desktop", "IsoFusionData")


def try_set_icon(win: tk.Misc):
    ico = resource_path("isotarget.ico")
    if os.path.exists(ico):
        try:
            win.iconbitmap(ico)
        except Exception:
            pass


# ---------- EULA ----------
EULA_TEXT = """ISO-TARGET EDUCATIONAL LICENSE AND USER AGREEMENT

IMPORTANT: PLEASE READ BEFORE USING THE SOFTWARE.

1) Authorized Users. IsoTarget is licensed only for current Washburn University Radiation Therapy students and authorized faculty/staff. Any other use is prohibited.

2) Educational / Non-Clinical Use Only. The Software is for instruction and training. It is not a medical device and must not be used for diagnosis, treatment planning, patient positioning, or clinical decision-making.

3) Privacy / PHI. Use only de-identified images. Do not import, store, or process PHI unless explicitly permitted and properly de-identified in accordance with policy and law.

4) No Redistribution. You may not share, sell, sublicense, publish, or distribute the Software or any portion thereof to any third party.

5) Ownership. The Software is licensed, not sold. All rights are reserved by the owner.

6) “AS IS” Warranty. The Software is provided “AS IS” and “AS AVAILABLE,” with no warranties of any kind, express or implied.

7) Limitation of Liability. To the maximum extent permitted by law, the developer, instructors, and Washburn University shall not be liable for any indirect, incidental, special, consequential, or exemplary damages, or for loss of data, profits, or goodwill, arising out of or related to the Software or this Agreement.

8) Termination. This Agreement terminates if you breach any term. Upon termination, you must cease use and delete all copies.

By selecting “I Agree” or using the Software, you acknowledge you have read, understood, and agree to be bound by this Agreement.
"""


def eula_file_path():
    root = os.path.join(os.path.expanduser("~"), ".isotarget")
    os.makedirs(root, exist_ok=True)
    return os.path.join(root, "EULA_ACCEPTED.txt")


def ensure_eula_acceptance(root: tk.Tk) -> bool:
    """Show EULA once and persist acceptance to a local file."""
    if os.path.exists(eula_file_path()):
        return True

    win = tk.Toplevel(root)
    try_set_icon(win)
    win.title("User Agreement — IsoTarget")
    win.geometry("800x650")
    win.configure(bg="#f5faff")
    win.transient(root)
    win.grab_set()
    win.update_idletasks()
    x = (win.winfo_screenwidth() // 2) - 400
    y = (win.winfo_screenheight() // 2) - 325
    win.geometry(f"800x650+{x}+{y}")

    head = tk.Frame(win, bg="#0b2942", height=60)
    head.pack(fill='x')
    head.pack_propagate(False)
    tk.Label(head, text="IsoTarget — Terms of Use", font=("Segoe UI", 18, "bold"),
             fg="white", bg="#0b2942").pack(pady=14)

    wrap = tk.Frame(win, bg="#f5faff")
    wrap.pack(fill='both', expand=True, padx=18, pady=18)
    pane = tk.Frame(wrap, bg="#ffffff", relief='ridge', bd=1)
    pane.pack(fill='both', expand=True)
    txt = scrolledtext.ScrolledText(
        pane, wrap=tk.WORD, font=("Segoe UI", 11),
        bg="#ffffff", fg="#0b2942", padx=16, pady=16, state='normal'
    )
    txt.pack(fill='both', expand=True, padx=8, pady=8)
    txt.insert("1.0", EULA_TEXT)
    txt.config(state='disabled')

    agree = tk.BooleanVar(False)
    cb = tk.Checkbutton(wrap, text="I have read and agree to the Terms of Use",
                        variable=agree, bg="#f5faff", font=("Segoe UI", 11))
    cb.pack(pady=(12, 6))
    btns = tk.Frame(wrap, bg="#f5faff")
    btns.pack()
    ok = tk.Button(btns, text="I Agree", width=16, state="disabled")
    cancel = tk.Button(btns, text="Decline", width=16)

    def on_ok():
        if agree.get():
            try:
                with open(eula_file_path(), "w", encoding="utf-8") as f:
                    f.write(f"Accepted by: {getpass.getuser()}\n")
                    f.write(f"Date: {datetime.datetime.now().isoformat()}\n")
                    f.write("Version: 1.0\n")
            except Exception:
                pass
            win.destroy()

    def on_cancel():
        if messagebox.askyesno("Decline", "Decline and exit IsoTarget?"):
            win.destroy()
            root.destroy()

    ok.config(command=on_ok)
    cancel.config(command=on_cancel)
    ok.pack(side='right', padx=6)
    cancel.pack(side='right', padx=6)

    def on_toggle(*_):
        ok.config(state="normal" if agree.get() else "disabled")

    agree.trace_add("write", on_toggle)
    root.wait_window(win)
    return os.path.exists(eula_file_path())


# ---------- Splash ----------
class SplashScreen(tk.Toplevel):
    def __init__(self, parent, duration_ms: int = 3000):
        super().__init__(parent)
        self.title(APP_NAME)
        self.configure(bg="#0d1117")
        self.overrideredirect(True)
        self.wm_attributes("-topmost", True)
        w, h = 720, 420
        self.geometry(f"{w}x{h}+{(self.winfo_screenwidth()-w)//2}+{(self.winfo_screenheight()-h)//2}")

        frame = tk.Frame(self, bg="#161b22", bd=2, relief=tk.RIDGE)
        frame.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.95, relheight=0.88)

        used_img = False
        try:
            img = Image.open(resource_path("splash.png")).resize((int(w*0.70), int(h*0.55)), LANCZOS)
            self._tk_img = ImageTk.PhotoImage(img)
            tk.Label(frame, image=self._tk_img, bg="#161b22").pack(pady=(22, 8))
            used_img = True
        except Exception:
            pass

        if not used_img:
            tk.Label(frame, text=APP_NAME, font=("Segoe UI", 40, "bold"),
                     fg="#58a6ff", bg="#161b22").pack(pady=(50, 20))

        tk.Label(frame, text="Developed by Sean Conrad RT(R)(T)",
                 font=("Segoe UI", 12), fg="#c9d1d9", bg="#161b22").pack()

        pb = ttk.Progressbar(frame, mode='indeterminate', length=int(w*0.6))
        pb.pack(pady=16)
        pb.start(12)
        self.after(duration_ms, lambda: (pb.stop(), self.destroy()))


# ---------- Main UI ----------
class OrthogonalMatchUI:
    def __init__(self, master: tk.Tk):
        self.master = master
        self.master.title(APP_TITLE)
        self.master.configure(bg="#f5faff")
        self.master.minsize(1400, 900)
        try_set_icon(self.master)

        # Center window
        self.master.update_idletasks()
        sw, sh = self.master.winfo_screenwidth(), self.master.winfo_screenheight()
        w, h = 1400, 900
        self.master.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

        self._init_state()
        self._build_layout()
        self._bind_keys()
        self._save_initial_state()
        self._save_state()
        self._update_match_overlay()

    # ----- state -----
    def _init_state(self):
        self.images = {'drr_ap': None, 'kv_ap': None, 'drr_lat': None, 'kv_lat': None}
        self.original_images = {k: None for k in self.images}
        self.kv_offsets = {'ap_x': 0, 'ap_y': 0, 'lat_x': 0, 'lat_y': 0}
        self.rotations = {'ap': 0, 'lat': 0}
        self.zoom_levels = {'ap': 1.0, 'lat': 1.0}
        self.pan_offsets = {'ap': (0, 0), 'lat': (0, 0)}  # view-level pan

        self.alpha = tk.DoubleVar(value=0.5)
        self.use_color_overlay = tk.BooleanVar(value=False)
        self.dataset_choice = tk.StringVar(value="Select Dataset")
        self.filter_var = tk.StringVar(value="Select Filter")
        self.adj_img_var = tk.StringVar(value="DRR AP")  # which image to adjust/filter

        self.history = []
        self.initial_state = None
        self.drag_start = None
        self.active_view = None
        self.tk_images = {}
        self.canvas = {}
        self.canvas_borders = {}
        self._ignore_rotation_callback = False

        self.adjustment_values = {
            'brightness': {'ap': 1.0, 'lat': 1.0},
            'contrast':   {'ap': 1.0, 'lat': 1.0},
            'sharpness':  {'ap': 1.0, 'lat': 1.0},
        }
        self.current_adjustment_image = 'drr_ap'

    # ----- layout -----
    def _build_layout(self):
        for i in range(6):
            self.master.grid_columnconfigure(i, weight=1)
        for i in range(9):
            self.master.grid_rowconfigure(i, weight=1)

        # Header
        header = tk.Frame(self.master, bg="#0b2942", height=60)
        header.grid(row=0, column=0, columnspan=6, sticky='ew')
        header.grid_propagate(False)
        tk.Label(header, text="IsoTarget", font=("Segoe UI", 22, "bold"),
                 fg="white", bg="#0b2942").pack(side='left', padx=18, pady=16)
        tk.Label(header, text="Orthogonal DRR/KV Image Matcher", font=("Segoe UI", 11),
                 fg="white", bg="#0b2942").pack(side='left', pady=16)

        # AP & LAT canvases
        for title, row, col, colspan in [('AP Match', 1, 0, 2), ('Lateral Match', 1, 2, 2)]:
            frame = tk.Frame(self.master, bg="#f5faff", highlightthickness=3, highlightbackground="black")
            frame.grid(row=row, column=col, columnspan=colspan, padx=8, pady=6, sticky='nsew')
            canvas = tk.Canvas(frame, bg='black', width=DISPLAY_W, height=DISPLAY_H)
            canvas.pack(fill='both', expand=True)
            tk.Label(self.master, text=title, bg="#f5faff", fg="#0b2942",
                     font=("Segoe UI", 10, "bold")).grid(row=row + 1, column=col, columnspan=colspan)
            self.canvas[title] = canvas
            self.canvas_borders[title] = frame
            view = 'ap' if 'AP' in title else 'lat'
            canvas.bind('<Button-1>',         lambda e, v=view: self._activate_drag(e, v))
            canvas.bind('<B1-Motion>',        lambda e, v=view: self._drag_kv(e, v))
            canvas.bind('<MouseWheel>',       lambda e, v=view: self._mouse_scroll(e, v))
            canvas.bind('<Control-MouseWheel>', lambda e, v=view: self._zoom(e, v))

        # Blend controls (left & right)
        def blend_row(colstart):
            fr = tk.Frame(self.master, bg="#f5faff")
            fr.grid(row=2, column=colstart, columnspan=2, sticky='ew', padx=8, pady=(0, 6))
            tk.Label(fr, text="Blend:", bg="#f5faff").pack(side='left')
            ttk.Scale(fr, from_=0, to=1, variable=self.alpha, orient='horizontal',
                      command=lambda _=None: self._update_match_overlay()).pack(side='left', fill='x', expand=True, padx=10)
            ttk.Checkbutton(fr, text="Color Overlay", variable=self.use_color_overlay,
                            command=self._update_match_overlay).pack(side='right', padx=6)
        blend_row(0)
        blend_row(2)

        # Thumbnails
        specs = [('DRR AP', 3, 0), ('KV AP', 3, 1), ('DRR LAT', 3, 2), ('KV LAT', 3, 3)]
        key_map = {'DRR AP': 'drr_ap', 'KV AP': 'kv_ap', 'DRR LAT': 'drr_lat', 'KV LAT': 'kv_lat'}
        for title, r, c in specs:
            outer = tk.Frame(self.master, bg="#f5faff")
            outer.grid(row=r, column=c, padx=6, pady=6, sticky='nsew')
            tk.Label(outer, text=title, bg="#f5faff", fg="#0b2942").pack()
            border = tk.Frame(outer, bg="#0b2942", bd=1, relief='solid')
            border.pack(fill='both', expand=True, padx=8, pady=(0, 8))
            canv = tk.Canvas(border, bg='black', width=THUMB_W, height=THUMB_H)
            canv.pack(fill='both', expand=True)
            self.canvas[title] = canv
            canv.bind('<Button-1>', lambda e, k=key_map[title], t=title: self._select_image_for_adjustment(k, t))

        # ---------- RIGHT PANEL ----------
        panel = tk.Frame(self.master, bg="#ffffff", bd=1, relief='ridge')
        panel.grid(row=1, column=4, rowspan=3, columnspan=2, sticky='nsew', padx=8, pady=6)
        self.master.grid_rowconfigure(1, weight=1)

        # Filters (Apply acts on the last clicked thumbnail / selected image)
        fl = tk.Frame(panel, bg="#ffffff")
        fl.pack(fill='x', padx=12, pady=(10, 8))
        tk.Label(fl, text="Filters:", bg="#ffffff", font=("Segoe UI", 11, "bold")).grid(row=0, column=0, sticky='w')
        filter_opts = [
            "Select Filter",
            "Washburn Ichabod Balance",
            "Low-Dose Boost",   # now uses *former Collins* effect
            "Skeletal Emphasis (Collins)",    # now uses *former Rizzler* effect
            "Local Contrast (Jayhawk)",
            "Soft Tissue Enhance",
            "RadFilter (Match Assist)"     # new
        ]
        self.filter_menu = ttk.OptionMenu(fl, self.filter_var, *filter_opts)
        self.filter_menu.grid(row=0, column=1, sticky='w', padx=(8, 8))
        ttk.Button(fl, text="Apply Filter", command=self._apply_selected_filter) \
            .grid(row=1, column=1, sticky='w', padx=(8, 8), pady=(6, 0))

        # Manual Adjustments
        adj = tk.Frame(panel, bg="#ffffff")
        adj.pack(fill='x', padx=12, pady=(8, 10))
        tk.Label(adj, text="Manual Adjustments", bg="#ffffff",
                 font=("Segoe UI", 10, "bold")).pack(anchor='w', pady=(0, 6))

        sel = tk.Frame(adj, bg="#ffffff")
        sel.pack(fill='x', pady=(0, 6))
        tk.Label(sel, text="Adjust:", bg="#ffffff").pack(side='left')
        ttk.OptionMenu(sel, self.adj_img_var, "DRR AP", "DRR AP", "KV AP", "DRR LAT", "KV LAT",
                       command=self._select_adjustment_image_from_menu) \
            .pack(side='left', padx=(8, 0))

        def slider(parent, label, key):
            row = tk.Frame(parent, bg="#ffffff")
            row.pack(fill='x', pady=5)
            tk.Label(row, text=f"{label}:", bg="#ffffff").pack(side='left')
            s = ttk.Scale(row, from_=0.1, to=3.0, value=1.0,
                          command=lambda v, k=key: self._adjust_image(k, float(v)))
            s.pack(side='left', fill='x', expand=True, padx=8)
            val = tk.Label(row, text="1.00", bg="#ffffff", fg="#4b5563")
            val.pack(side='left')
            return s, val

        self.brightness_scale, self.brightness_val = slider(adj, "Brightness", "brightness")
        self.contrast_scale,   self.contrast_val   = slider(adj, "Contrast",   "contrast")
        self.sharpness_scale,  self.sharpness_val  = slider(adj, "Sharpness",  "sharpness")

        ttk.Button(adj, text="Reset Adjustments", command=self._reset_adjustments) \
            .pack(anchor='e', pady=(6, 4))

        # Dataset menu (under Reset Adjustments)
        ds = tk.Frame(panel, bg="#ffffff")
        ds.pack(fill='x', padx=12, pady=(4, 10))
        tk.Label(ds, text="Dataset (autoload):", bg="#ffffff").grid(row=0, column=0, sticky='w')
        dataset_options = [
            "Select Dataset",
            "Abdomen", "AP C Spine", "Brain", "Breast AP KV 1", "Breast AP KV 2",
            "Breast Lateral Tangent", "Breast Tangent", "C-Spine G140", "C-Spine Orthogonal",
            "CW Sclav AP Lat", "CW Tangent", "H&N AP Lat", "H&N G45", "Head & Neck",
            "Head & Neck 2", "Head & Neck 3", "Knee AP-Lat", "Knee AP-Lat 2", "Knee G 330",
            "PAB", "Pelvis", "RT Breast AP-Lat", "RT Pelvis AP-LAT", "RT Pelvis PA", "Thorax",
            "Breast MV", "Breast MV 2", "Breast MV Med", "PAB MV", "Pelvis MV",
            "SCV MV", "SCV MV 2", "Thorax MV"
        ]
        ttk.OptionMenu(ds, self.dataset_choice, *dataset_options, command=self._load_dataset) \
            .grid(row=0, column=1, sticky='w', padx=(8, 0))

        # Help
        hb = tk.Frame(panel, bg="#ffffff")
        hb.pack(fill='x', padx=12, pady=(0, 8))
        ttk.Button(hb, text="Help", command=self._show_help).pack(anchor='e')

        # Quick Controls: Restore + compact Rotate AP + Zoom label
        qc = tk.Frame(panel, bg="#ffffff")
        qc.pack(fill='x', padx=12, pady=(6, 12))
        ttk.Button(qc, text="Restore to Default", command=self._reset_to_default) \
            .grid(row=0, column=0, sticky='ew', columnspan=2)
        rot = tk.Frame(qc, bg="#ffffff")
        rot.grid(row=1, column=0, columnspan=2, sticky='ew', pady=(8, 0))
        tk.Label(rot, text="Rotate AP:", bg="#ffffff").pack(side='left')
        self.rotation_scale = ttk.Scale(rot, from_=-180, to=180, orient='horizontal',
                                        command=self._rotate_active)
        self.rotation_scale.set(0)
        self.rotation_scale.pack(side='left', fill='x', expand=True, padx=8)
        self.rotation_label = tk.Label(rot, text="0°", bg="#ffffff", fg="#0b2942", width=5)
        self.rotation_label.pack(side='left')
        self.zoom_label = tk.Label(qc, text="Zoom: 100%", bg="#ffffff", fg="#4b5563")
        self.zoom_label.grid(row=2, column=0, columnspan=2, sticky='w', pady=(6, 0))

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        tk.Label(self.master, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor='w',
                 font=("Segoe UI", 9), bg="#0b2942", fg="white").grid(row=8, column=0, columnspan=6, sticky='ew')

    # ----- events -----
    def _bind_keys(self):
        self.master.bind('<Left>',  lambda e: self._nudge_kv(-1, 0))
        self.master.bind('<Right>', lambda e: self._nudge_kv(1, 0))
        self.master.bind('<Up>',    lambda e: self._nudge_kv(0, -1))
        self.master.bind('<Down>',  lambda e: self._nudge_kv(0, 1))
        self.master.bind('<Control-r>', lambda e: self._reset_to_default())
        self.master.bind('<Control-z>', lambda e: self._undo_last_action())
        self.master.focus_set()

    def _rotate_active(self, val):
        if self._ignore_rotation_callback or self.active_view != 'ap':
            return
        try:
            a = float(val)
            self.rotations['ap'] = a
            self.rotation_label.config(text=f"{a:.0f}°")
            self._save_state()
            self._update_match_overlay()
        except Exception as e:
            print("Rotation error:", e)

    def _activate_drag(self, event, view):
        self.active_view = view
        self.drag_start = (event.x, event.y)
        for name, frame in self.canvas_borders.items():
            frame.config(highlightbackground="yellow" if view in name.lower() else "black")
        self._ignore_rotation_callback = True
        if view == 'ap':
            self.rotation_scale.set(self.rotations['ap'])
            self.rotation_label.config(text=f"{self.rotations['ap']:.0f}°")
            self.status_var.set("AP view selected — rotation enabled (wheel or slider)")
        else:
            self.rotation_scale.set(0)
            self.rotation_label.config(text="0°")
            self.status_var.set("Lateral view selected — rotation disabled")
        self._ignore_rotation_callback = False

    def _drag_kv(self, event, view):
        if self.drag_start and self.images.get(f'kv_{view}'):
            dx = event.x - self.drag_start[0]
            dy = event.y - self.drag_start[1]
            self.drag_start = (event.x, event.y)
            if dx:
                self.kv_offsets[f'{view}_x'] += dx
            if dy:
                self.kv_offsets['ap_y'] += dy
                self.kv_offsets['lat_y'] += dy
            self._save_state()
            self._update_match_overlay()

    def _nudge_kv(self, dx, dy):
        if self.active_view:
            self.kv_offsets[f'{self.active_view}_x'] += dx
        if dy:
            self.kv_offsets['ap_y'] += dy
            self.kv_offsets['lat_y'] += dy
        self._save_state()
        self._update_match_overlay()

    def _zoom(self, event, view):
        """True zoom toward mouse cursor; pans adjusted so the cursor point stays fixed."""
        if not (self.images.get(f'drr_{view}') and self.images.get(f'kv_{view}')):
            return
        old = self.zoom_levels[view]
        step = 0.1 if event.delta > 0 else -0.1
        new = max(0.2, min(5.0, old + step))
        if new == old:
            return
        canvas = self.canvas['AP Match'] if view == 'ap' else self.canvas['Lateral Match']
        cx = canvas.canvasx(event.x)
        cy = canvas.canvasy(event.y)
        px, py = self.pan_offsets[view]
        px = px + cx * (1 - new / old)
        py = py + cy * (1 - new / old)
        self.pan_offsets[view] = (px, py)
        self.zoom_levels[view] = new
        self.zoom_label.config(text=f"Zoom: {int(new * 100)}%")
        self._save_state()
        self._update_match_overlay()

    def _mouse_scroll(self, event, view):
        if view == 'ap':
            delta = 1 if event.delta > 0 else -1
            self.rotations['ap'] = (self.rotations['ap'] + delta) % 360
            self._ignore_rotation_callback = True
            self.rotation_scale.set(self.rotations['ap'])
            self.rotation_label.config(text=f"{self.rotations['ap']:.0f}°")
            self._ignore_rotation_callback = False
            self._save_state()
            self._update_match_overlay()

    # ----- state mgmt -----
    def _save_initial_state(self):
        self.initial_state = {
            'kv_offsets': {'ap_x': 0, 'ap_y': 0, 'lat_x': 0, 'lat_y': 0},
            'rotations': {'ap': 0, 'lat': 0},
            'zoom_levels': {'ap': 1.0, 'lat': 1.0},
            'pan_offsets': {'ap': (0, 0), 'lat': (0, 0)},
            'adjustment_values': {
                'brightness': {'ap': 1.0, 'lat': 1.0},
                'contrast':   {'ap': 1.0, 'lat': 1.0},
                'sharpness':  {'ap': 1.0, 'lat': 1.0},
            },
            'alpha': 0.5,
            'use_color_overlay': False,
        }

    def _save_state(self):
        st = {
            'kv_offsets': self.kv_offsets.copy(),
            'rotations': self.rotations.copy(),
            'zoom_levels': self.zoom_levels.copy(),
            'pan_offsets': self.pan_offsets.copy(),
            'adjustment_values': {k: v.copy() for k, v in self.adjustment_values.items()},
            'alpha': self.alpha.get(),
            'use_color_overlay': self.use_color_overlay.get(),
        }
        self.history.append(st)
        if len(self.history) > 20:
            self.history.pop(0)

    def _reset_to_default(self):
        if not self.initial_state:
            self.status_var.set("No initial state to reset")
            return
        for k in self.images:
            if self.original_images[k] is not None:
                self.images[k] = self.original_images[k].copy()
        self.kv_offsets = self.initial_state['kv_offsets'].copy()
        self.rotations = self.initial_state['rotations'].copy()
        self.zoom_levels = self.initial_state['zoom_levels'].copy()
        self.pan_offsets = self.initial_state['pan_offsets'].copy()
        self.adjustment_values = {k: v.copy() for k, v in self.initial_state['adjustment_values'].items()}
        self.alpha.set(self.initial_state['alpha'])
        self.use_color_overlay.set(self.initial_state['use_color_overlay'])
        self._ignore_rotation_callback = True
        self.rotation_scale.set(0)
        self.rotation_label.config(text="0°")
        self._ignore_rotation_callback = False
        self.zoom_label.config(text="Zoom: 100%")
        self.brightness_scale.set(1.0); self.brightness_val.config(text="1.00")
        self.contrast_scale.set(1.0);   self.contrast_val.config(text="1.00")
        self.sharpness_scale.set(1.0);  self.sharpness_val.config(text="1.00")
        for t in ['DRR AP', 'KV AP', 'DRR LAT', 'KV LAT']:
            self.canvas[t].config(highlightbackground="black", highlightthickness=0)
        for f in self.canvas_borders.values():
            f.config(highlightbackground="black")
        self.active_view = None
        self.status_var.set("Restored to default")
        self._save_state()
        self._update_match_overlay()

    def _undo_last_action(self):
        if len(self.history) <= 1:
            self.status_var.set("Nothing to undo")
            return
        self.history.pop()
        prev = self.history[-1]
        self.kv_offsets = prev['kv_offsets']
        self.rotations = prev['rotations']
        self.zoom_levels = prev['zoom_levels']
        self.pan_offsets = prev['pan_offsets']
        self.adjustment_values = prev['adjustment_values']
        self.alpha.set(prev['alpha'])
        self.use_color_overlay.set(prev['use_color_overlay'])
        if self.active_view == 'ap':
            self._ignore_rotation_callback = True
            self.rotation_scale.set(self.rotations['ap'])
            self.rotation_label.config(text=f"{self.rotations['ap']:.0f}°")
            self._ignore_rotation_callback = False
        if self.current_adjustment_image:
            view = 'ap' if 'ap' in self.current_adjustment_image else 'lat'
            self.brightness_scale.set(self.adjustment_values['brightness'][view])
            self.contrast_scale.set(self.adjustment_values['contrast'][view])
            self.sharpness_scale.set(self.adjustment_values['sharpness'][view])
            self.brightness_val.config(text=f"{self.adjustment_values['brightness'][view]:.2f}")
            self.contrast_val.config(text=f"{self.adjustment_values['contrast'][view]:.2f}")
            self.sharpness_val.config(text=f"{self.adjustment_values['sharpness'][view]:.2f}")
        self.status_var.set("Undo successful")
        self._update_match_overlay()

    # ----- adjustments & filters -----
    def _select_image_for_adjustment(self, image_key, image_title):
        if not self.images.get(image_key):
            self.status_var.set(f"No image loaded for {image_title}")
            return
        self.current_adjustment_image = image_key
        title_map = {'drr_ap': 'DRR AP', 'kv_ap': 'KV AP', 'drr_lat': 'DRR LAT', 'kv_lat': 'KV LAT'}
        self.adj_img_var.set(title_map[image_key])
        view = 'ap' if 'ap' in image_key else 'lat'
        self.brightness_scale.set(self.adjustment_values['brightness'][view])
        self.contrast_scale.set(self.adjustment_values['contrast'][view])
        self.sharpness_scale.set(self.adjustment_values['sharpness'][view])
        self.brightness_val.config(text=f"{self.adjustment_values['brightness'][view]:.2f}")
        self.contrast_val.config(text=f"{self.adjustment_values['contrast'][view]:.2f}")
        self.sharpness_val.config(text=f"{self.adjustment_values['sharpness'][view]:.2f}")
        for t in ['DRR AP', 'KV AP', 'DRR LAT', 'KV LAT']:
            self.canvas[t].config(
                highlightbackground="yellow" if t == image_title else "black",
                highlightthickness=2 if t == image_title else 0
            )
        self.status_var.set(f"Selected {image_title} (filters & adjustments target)")

    def _select_adjustment_image_from_menu(self, img_name):
        key_map = {"DRR AP": "drr_ap", "KV AP": "kv_ap", "DRR LAT": "drr_lat", "KV LAT": "kv_lat"}
        self._select_image_for_adjustment(key_map[img_name], img_name)

    def _adjust_image(self, adj_type, value):
        if adj_type == 'brightness':
            self.brightness_val.config(text=f"{value:.2f}")
        elif adj_type == 'contrast':
            self.contrast_val.config(text=f"{value:.2f}")
        elif adj_type == 'sharpness':
            self.sharpness_val.config(text=f"{value:.2f}")

        view = 'ap' if 'ap' in self.current_adjustment_image else 'lat'
        self.adjustment_values[adj_type][view] = value

        original = self.original_images.get(self.current_adjustment_image)
        if original is None:
            return

        img = original.copy()
        img = ImageEnhance.Brightness(img).enhance(self.adjustment_values['brightness'][view])
        img = ImageEnhance.Contrast(img).enhance(self.adjustment_values['contrast'][view])
        img = ImageEnhance.Sharpness(img).enhance(self.adjustment_values['sharpness'][view])
        self.images[self.current_adjustment_image] = img
        self._save_state()
        self._update_match_overlay()
        self.status_var.set(f"Adjusted {adj_type} to {value:.2f}")

    def _reset_adjustments(self):
        view = 'ap' if 'ap' in self.current_adjustment_image else 'lat'
        self.adjustment_values['brightness'][view] = 1.0
        self.adjustment_values['contrast'][view] = 1.0
        self.adjustment_values['sharpness'][view] = 1.0
        self.brightness_scale.set(1.0); self.brightness_val.config(text="1.00")
        self.contrast_scale.set(1.0);   self.contrast_val.config(text="1.00")
        self.sharpness_scale.set(1.0);  self.sharpness_val.config(text="1.00")
        if self.original_images.get(self.current_adjustment_image) is not None:
            self.images[self.current_adjustment_image] = self.original_images[self.current_adjustment_image].copy()
        self._save_state()
        self._update_match_overlay()
        self.status_var.set(f"Reset adjustments for {self.adj_img_var.get()}")

    def _apply_selected_filter(self):
        name = self.filter_var.get()
        if name == "Select Filter":
            self.status_var.set("Please select a filter")
            return

        target_key = self.current_adjustment_image
        src = self.original_images.get(target_key)
        if src is None:
            self.status_var.set("Load a dataset and click a thumbnail to select an image first")
            return

        # NOTE: Collins and Rizzler behaviors are intentionally swapped here per request.
        funcs = {
            "Washburn Ichabod Balance": self._f_content_balance,
            "Low-Dose Boost":   self._f_collins_bone,       # swapped: Rizzler label uses former Collins effect
            "Skeletal Emphasis (Collins)":    self._f_rizzler_low_dose,   # swapped: Collins label uses former Rizzler effect
            "Local Contrast (Jayhawk)":   self._f_jayhawk_local_contrast,
            "Soft Tissue Enhance":        self._f_soft_tissue,
            "RadFilter (Match Assist)":   self._f_radfilter_match_assist,
        }

        try:
            out = funcs[name](src.copy())
            self.images[target_key] = out
            self._save_state()
            self._update_match_overlay()
            human = {"drr_ap":"DRR AP","kv_ap":"KV AP","drr_lat":"DRR LAT","kv_lat":"KV LAT"}[target_key]
            self.status_var.set(f"Applied {name} to {human}")
        except Exception as e:
            self.status_var.set(f"Filter error: {e}")
            messagebox.showerror("Filter Error", f"Could not apply {name}:\n{e}")

    # --- RadOnc-style filters ---
    def _f_content_balance(self, img):
        """Washburn (Ichabod) Balance: balanced visibility of bone + soft tissue."""
        g = img.convert('L')
        base = ImageOps.equalize(g)
        blur = g.filter(ImageFilter.GaussianBlur(radius=2))
        detail = ImageChops.subtract(g, blur)         # high-pass
        mix = ImageChops.add(base, detail)            # combine
        mix = ImageOps.autocontrast(mix, cutoff=1)
        mix = mix.filter(ImageFilter.UnsharpMask(radius=1.2, percent=120, threshold=3))
        return mix.convert('RGB')

    def _f_collins_bone(self, img):
        """Former Collins effect (now used for 'Low-Dose Boost (Rizzler)'): crisp bone edge emphasis."""
        g = img.convert('L')
        g = ImageOps.autocontrast(g, cutoff=2)
        high = g.filter(ImageFilter.UnsharpMask(radius=2.0, percent=170, threshold=3))
        high = ImageEnhance.Contrast(high).enhance(1.25)
        return high.convert('RGB')

    def _f_rizzler_low_dose(self, img):
        """Former Rizzler effect (now used for 'Bone Emphasis (Collins)'): low-dose denoise+sharpen."""
        g = img.convert('L')
        g = g.filter(ImageFilter.GaussianBlur(radius=1))
        g = ImageEnhance.Sharpness(g).enhance(1.15)
        g = ImageEnhance.Contrast(g).enhance(1.05)
        return g.convert('RGB')

    def _f_soft_tissue(self, img):
        """Soft Tissue Enhance: denoise + gentle midtone lift + moderate contrast."""
        g = img.convert('L')
        g = g.filter(ImageFilter.MedianFilter(size=3))
        gamma = 0.9
        g = g.point(lambda i: int(((i / 255.0) ** gamma) * 255))
        g = ImageEnhance.Contrast(g).enhance(1.08)
        g = g.filter(ImageFilter.SMOOTH_MORE)
        return g.convert('RGB')

    def _f_jayhawk_local_contrast(self, img):
        """Local Contrast (Jayhawk): equalize + strong unsharp for micro-contrast."""
        g = img.convert('L')
        g = ImageOps.equalize(g)
        g = g.filter(ImageFilter.UnsharpMask(radius=3, percent=180, threshold=2))
        g = ImageEnhance.Contrast(g).enhance(1.10)
        g = ImageEnhance.Sharpness(g).enhance(1.08)
        return g.convert('RGB')

    def _f_radfilter_match_assist(self, img):
        """
        RadFilter (Match Assist): multi-scale boost to help match tricky exposures.
        Idea: mild denoise -> midtone contrast stretch -> high-pass detail add -> gentle sharpen.
        """
        g = img.convert('L')
        # mild denoise
        g = g.filter(ImageFilter.MedianFilter(size=3))
        # midtone stretch
        g = ImageOps.autocontrast(g, cutoff=1)
        # multi-scale detail (approx. retinex-lite): high-pass at two scales
        blur1 = g.filter(ImageFilter.GaussianBlur(radius=2))
        blur2 = g.filter(ImageFilter.GaussianBlur(radius=6))
        hp1 = ImageChops.subtract(g, blur1)
        hp2 = ImageChops.subtract(g, blur2)
        mix = ImageChops.add(ImageChops.add(g, hp1), hp2)
        # gentle sharpen
        mix = mix.filter(ImageFilter.UnsharpMask(radius=1.2, percent=110, threshold=3))
        # slight contrast lift
        mix = ImageEnhance.Contrast(mix).enhance(1.06)
        return mix.convert('RGB')

    # ----- render path (correct pan/zoom) -----
    def _create_color_overlay(self, drr_img, kv_img):
        r = drr_img.convert("L")
        gb = kv_img.convert("L")
        return Image.merge("RGB", (r, gb, gb))

    def _update_match_overlay(self):
        for view in ['ap', 'lat']:
            drr = self.images.get(f'drr_{view}')
            kv  = self.images.get(f'kv_{view}')
            if not (drr and kv):
                continue

            z = self.zoom_levels[view]
            px, py = self.pan_offsets[view]
            sw, sh = int(DISPLAY_W * z), int(DISPLAY_H * z)
            drr_scaled = drr.resize((sw, sh), LANCZOS)
            kv_scaled  = kv.resize((sw, sh), LANCZOS)
            if view == 'ap' and self.rotations['ap'] != 0:
                kv_scaled = kv_scaled.rotate(self.rotations['ap'], expand=False)

            dx_rel = int(self.kv_offsets.get(f'{view}_x', 0))
            dy_rel = int(self.kv_offsets.get(f'{view}_y', 0))

            drr_view = Image.new("RGB", (DISPLAY_W, DISPLAY_H), (0, 0, 0))
            kv_view  = Image.new("RGB", (DISPLAY_W, DISPLAY_H), (0, 0, 0))
            drr_view.paste(drr_scaled, (-int(px), -int(py)))
            kv_view.paste(kv_scaled,  (dx_rel - int(px), dy_rel - int(py)))

            blended = (self._create_color_overlay(drr_view, kv_view)
                       if self.use_color_overlay.get()
                       else Image.blend(drr_view, kv_view, self.alpha.get()))

            key = 'AP Match' if view == 'ap' else 'Lateral Match'
            self.tk_images[key] = ImageTk.PhotoImage(blended)
            canv = self.canvas[key]
            canv.delete("all")
            canv.create_image(0, 0, anchor='nw', image=self.tk_images[key])

        # thumbnails
        for key in ['drr_ap', 'kv_ap', 'drr_lat', 'kv_lat']:
            img = self.images.get(key)
            if img:
                thumb = img.copy()
                thumb.thumbnail((THUMB_W, THUMB_H))
                self.tk_images[key] = ImageTk.PhotoImage(thumb)
                canv = self.canvas[key.upper().replace('_', ' ')]
                canv.delete("all")
                canv.create_image(0, 0, anchor='nw', image=self.tk_images[key])

    # ----- dataset IO -----
    def _load_dataset(self, selection):
        if selection == "Select Dataset":
            return
        dataset_dir = os.path.join(dataset_root(), selection)
        if not os.path.exists(dataset_dir):
            self.status_var.set(f"Dataset not found: {dataset_dir}")
            messagebox.showerror("Dataset Error", f"Dataset not found:\n{dataset_dir}")
            return

        file_map = {'drr_ap': '1', 'kv_ap': '2', 'drr_lat': '3', 'kv_lat': '4'}
        valid = {'.png', '.jpg', '.jpeg', '.tif', '.tiff', '.bmp'}

        self.images = {k: None for k in self.images}
        self.original_images = {k: None for k in self.original_images}
        loaded = 0
        names = os.listdir(dataset_dir)

        for key, prefix in file_map.items():
            path = None
            for fn in names:
                name, ext = os.path.splitext(fn.lower())
                if name.startswith(prefix) and ext in valid:
                    path = os.path.join(dataset_dir, fn)
                    break
            if path:
                try:
                    img = Image.open(path).convert("RGB")
                    self.images[key] = img
                    self.original_images[key] = img.copy()
                    loaded += 1
                except Exception as e:
                    print(f"Error loading {path}: {e}")

        if loaded > 0:
            self._reset_to_initial_values()
            self._save_initial_state()
            self.status_var.set(f"Loaded {loaded}/4 images from {selection}")
            self._update_match_overlay()
        else:
            self.status_var.set("No valid images found in dataset")
            messagebox.showerror("Dataset Error", "No valid images found in selected dataset.")

    def _reset_to_initial_values(self):
        self.kv_offsets = {'ap_x': 0, 'ap_y': 0, 'lat_x': 0, 'lat_y': 0}
        self.rotations = {'ap': 0, 'lat': 0}
        self.zoom_levels = {'ap': 1.0, 'lat': 1.0}
        self.pan_offsets = {'ap': (0, 0), 'lat': (0, 0)}
        self.adjustment_values = {
            'brightness': {'ap': 1.0, 'lat': 1.0},
            'contrast':   {'ap': 1.0, 'lat': 1.0},
            'sharpness':  {'ap': 1.0, 'lat': 1.0},
        }
        self.alpha.set(0.5)
        self.use_color_overlay.set(False)
        self._ignore_rotation_callback = True
        self.rotation_scale.set(0)
        self.rotation_label.config(text="0°")
        self._ignore_rotation_callback = False
        self.zoom_label.config(text="Zoom: 100%")
        for f in self.canvas_borders.values():
            f.config(highlightbackground="black")
        self.active_view = None

    # ----- help -----
    def _show_help(self):
        win = tk.Toplevel(self.master)
        try_set_icon(win)
        win.title("IsoTarget — Help & License")
        win.geometry("820x680")
        win.configure(bg="#f5faff")
        win.transient(self.master)
        win.grab_set()
        win.update_idletasks()
        x = (win.winfo_screenwidth() // 2) - 410
        y = (win.winfo_screenheight() // 2) - 340
        win.geometry(f"820x680+{x}+{y}")

        head = tk.Frame(win, bg="#0b2942", height=60)
        head.pack(fill='x')
        head.pack_propagate(False)
        tk.Label(head, text="IsoTarget Help", font=("Segoe UI", 18, "bold"),
                 fg='white', bg="#0b2942").pack(pady=14)

        body = tk.Frame(win, bg="#f5faff")
        body.pack(fill='both', expand=True, padx=16, pady=16)
        box = tk.Frame(body, bg="#ffffff", relief='ridge', bd=1)
        box.pack(fill='both', expand=True)
        txt = scrolledtext.ScrolledText(
            box, wrap=tk.WORD, font=("Segoe UI", 11),
            bg="#ffffff", fg="#0b2942", padx=18, pady=18, state='normal'
        )
        txt.pack(fill='both', expand=True, padx=8, pady=8)

        txt.insert("1.0", """IsoTarget — DRR/KV Image Matching Tool

CONTROLS
• Click AP or Lateral view to activate that pane.
• Click a thumbnail to SELECT the image for filters/adjustments.
• MouseWheel (AP active) — rotate AP KV.
• Ctrl + MouseWheel — zoom toward cursor (true zoom).
• Arrow Keys — nudge KV (fine positioning).
• Ctrl + Z — Undo;  Ctrl + R — Restore to Default.

RIGHT PANEL
• Filters — choose a RadOnc-style filter, click a thumbnail to select a target, then Apply.
  - Washburn Ichabod Balance: balanced bone & soft tissue (equalize + high-pass + unsharp).
  - Low-Dose Boost (now bone emphasis) strong bony edge clarity.
  - Skeletal Emphasis (Collins):   (now low-dose) light denoise + mild sharpen for noisy images.
  - Local Contrast (Jayhawk):  micro-contrast for fine landmarks.
  - Soft Tissue Enhance:       smooth + midtone lift.
  - RadFilter (Match Assist):  multi-scale boost for difficult exposures.
• Manual Adjustments — pick an image (Adjust:) and tune Brightness / Contrast / Sharpness.
• Dataset (autoload) — loads 1*, 2*, 3*, 4* images from ~/Desktop/IsoFusionData/<Dataset>.
• Restore to Default — resets images, transforms, and sliders.
• Rotate AP — compact slider (or use mouse wheel on AP).
""")
        txt.insert("end", "\nLICENSE (summary):\n\n" + EULA_TEXT)
        txt.config(state='disabled')
        ttk.Button(body, text="Close", command=win.destroy).pack(pady=10)


# ---------- entry ----------
def main():
    root = tk.Tk()
    try_set_icon(root)
    if not ensure_eula_acceptance(root):
        return
    splash = SplashScreen(root, duration_ms=3200)
    root.withdraw()
    root.after(3400, lambda: (root.deiconify(), OrthogonalMatchUI(root)))
    root.mainloop()


if __name__ == "__main__":
    main()
