import json
import time
import threading
import sys
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import pyautogui
from pynput import keyboard, mouse


class AutoClickerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Api Auto Clicker")
        app_width = 640
        app_height = 800
        
        screen_width = self.root.winfo_screenwidth()
        x = 10
        
        y = 10 
        
        self.root.geometry(f"{app_width}x{app_height}+{x}+{y}")
        # ---------------------------

        self.root.resizable(True, True)

        
        # ================= STATE =================
        self.running = False
        self.stop_event = threading.Event()

        self.is_recording = False
        self.is_playing_macro = False
        self.macro_events = []
        self._mouse_listener = None
        self._last_event_time = None

        self.overlay = None
        self.overlay_running = False
        self.always_on_top_var = tk.BooleanVar(value=False)
        self.show_overlay_var = tk.BooleanVar(value=True)


        # ================= VARIABLES =================
        # Delay per click (NEW)
        self.delay_hour = tk.StringVar(value="0")
        self.delay_min = tk.StringVar(value="0")
        self.delay_sec = tk.StringVar(value="1")
        self.delay_ms = tk.StringVar(value="0")

        self.button_var = tk.StringVar(value="left")

        self.target_var = tk.StringVar(value="current")
        self.x_var = tk.StringVar(value="0")
        self.y_var = tk.StringVar(value="0")

        # Stop timer
        self.stop_hour = tk.StringVar(value="0")
        self.stop_min = tk.StringVar(value="0")
        self.stop_sec = tk.StringVar(value="0")
        self.stop_ms = tk.StringVar(value="0")

        self.max_clicks_var = tk.StringVar(value="0")
        # ================= HOTKEY =================
        self.hotkey_start = tk.StringVar(value="F6")
        self.hotkey_stop = tk.StringVar(value="F7")

        self.modifier_start = tk.StringVar(value="None")
        self.modifier_stop = tk.StringVar(value="None")

        self.hotkey_pick = tk.StringVar(value="F8")
        self.modifier_pick = tk.StringVar(value="None")

        self.hotkey_record = tk.StringVar(value="F9")
        self.hotkey_play = tk.StringVar(value="F10")

        self.modifier_record = tk.StringVar(value="None")
        self.modifier_play = tk.StringVar(value="None")

        self._last_hotkey_config = {}
        self.hotkey_visible = tk.BooleanVar(value=False)

        self.hotkey_listener = None

        # Status
        self.status_var = tk.StringVar(value="Status: STOPPED")
        self.indicator_var = tk.StringVar(value="AUTOCLICK: OFF")
        self.remaining_time_var = tk.StringVar(value="Remaining time: --")
        self.remaining_click_var = tk.StringVar(value="Remaining clicks: --")
        self.macro_info_var = tk.StringVar(value="Macro: 0 events")
        self.macro_use_limits_var = tk.BooleanVar(value=True)

        pyautogui.FAILSAFE = True

        self._build_ui()
        # Auto apply hotkey khi thay đổi
        for var in [
            self.modifier_start, self.hotkey_start,
            self.modifier_stop, self.hotkey_stop,
            self.modifier_pick, self.hotkey_pick,
            self.modifier_record, self.hotkey_record,
            self.modifier_play, self.hotkey_play
        ]:
            var.trace_add("write", lambda *args: self._apply_hotkeys())

        self._apply_hotkeys()

        # Lưu giá trị hợp lệ ban đầu
        number_vars = [
            self.delay_hour, self.delay_min, self.delay_sec, self.delay_ms,
            self.stop_hour, self.stop_min, self.stop_sec, self.stop_ms,
            self.max_clicks_var
        ]

        for var in number_vars:
            var._last_valid = str(var.get())

            def callback(*args, v=var):
                value = str(v.get())
                if value.isdigit() or value == "":
                    v._last_valid = value
                else:
                    self.root.after(0, lambda: v.set(v._last_valid))

            var.trace_add("write", callback)
        
        self.root.update()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)



    # ================= OVERLAY =================
    def _show_overlay(self, text, color):
        if not self.show_overlay_var.get():
            return
        if self.overlay:
            return
        self.overlay = tk.Toplevel(self.root)
        self.overlay.overrideredirect(True)
        self.overlay.attributes("-topmost", True)
        self.overlay.attributes("-alpha", 0.85)

        label = tk.Label(self.overlay, text=text, fg="white",
                         bg=color, font=("Segoe UI", 10, "bold"),
                         padx=10, pady=4)
        label.pack()

        self.overlay_running = True
        self._update_overlay_position()

    def _update_overlay_position(self):
        if not self.overlay_running or not self.overlay:
            return
        x, y = pyautogui.position()
        self.overlay.geometry(f"+{x+15}+{y+15}")
        self.root.after(50, self._update_overlay_position)

    def _hide_overlay(self):
        self.overlay_running = False
        if self.overlay:
            self.overlay.destroy()
            self.overlay = None

    # ================= UI =================
    def _build_ui(self):
        pad = {"padx": 10, "pady": 6}

        ttk.Label(self.root, text="Api Auto Clicker",font=("Segoe UI", 16, "bold")).pack(pady=10)
        container = ttk.Frame(self.root)
        container.pack(fill="both", expand=True)

        canvas = tk.Canvas(container, highlightthickness=0, borderwidth=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)

        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        window_id = canvas.create_window((0, 0), window=scrollable_frame)

        def on_canvas_configure(event):
            canvas_width = event.width
            canvas.itemconfig(window_id, width=canvas_width)
            canvas.coords(window_id, canvas_width // 2, 0)

        canvas.bind("<Configure>", on_canvas_configure)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        center_wrapper = ttk.Frame(scrollable_frame)
        center_wrapper.pack(expand=True)

        frame = ttk.Frame(center_wrapper)
        frame.pack(padx=20, fill="x")




        vcmd = (self.root.register(self._validate_number), "%P")

        # ================= Delay =================
        box = ttk.LabelFrame(frame, text="Delay Per Click")
        box.pack(fill="x", expand=True, **pad)


        labels = ["Hour", "Min", "Sec", "Ms"]
        vars_ = [self.delay_hour, self.delay_min,
                self.delay_sec, self.delay_ms]

        for i in range(4):
            ttk.Label(box, text=labels[i], width=6).grid(row=0, column=i*2, padx=5)
            ttk.Entry(box, width=6,
                    textvariable=vars_[i],
                    validate="key",
                    validatecommand=vcmd).grid(row=0, column=i*2+1, padx=5)

        # ================= Stop =================
        box = ttk.LabelFrame(frame, text="Stop After")
        box.pack(fill="x", expand=True, **pad)


        labels = ["Hour", "Min", "Sec", "Ms"]
        vars_ = [self.stop_hour, self.stop_min,
                self.stop_sec, self.stop_ms]

        for i in range(4):
            ttk.Label(box, text=labels[i], width=6).grid(row=0, column=i*2, padx=5)
            ttk.Entry(box, width=6,
                    textvariable=vars_[i],
                    validate="key",
                    validatecommand=vcmd).grid(row=0, column=i*2+1, padx=5)

        ttk.Label(box, text="Max clicks/loops:", width=15).grid(row=1, column=0, padx=5, pady=5)
        ttk.Entry(box, width=8,
                textvariable=self.max_clicks_var,
                validate="key",
                validatecommand=vcmd).grid(row=1, column=1, padx=5)

        # ================= Mouse =================
        box = ttk.LabelFrame(frame, text="Mouse Button")
        box.pack(fill="x", expand=True, **pad)


        for i, b in enumerate(("left", "right", "middle")):
            ttk.Radiobutton(box, text=b.capitalize(),
                            value=b,
                            variable=self.button_var)\
                .grid(row=0, column=i, padx=10)

        # ================= Position =================
        box = ttk.LabelFrame(frame, text="Target Position")
        box.pack(fill="x", expand=True, **pad)


        ttk.Radiobutton(box, text="Current mouse",
                        value="current",
                        variable=self.target_var)\
            .grid(row=0, column=0, sticky="w", padx=5)

        ttk.Radiobutton(box, text="Fixed XY",
                        value="fixed",
                        variable=self.target_var)\
            .grid(row=1, column=0, sticky="w", padx=5)

        ttk.Label(box, text="X").grid(row=1, column=1)
        ttk.Entry(box, width=6,
                textvariable=self.x_var,
                validate="key",
                validatecommand=vcmd)\
            .grid(row=1, column=2)

        ttk.Label(box, text="Y").grid(row=1, column=3)
        ttk.Entry(box, width=6,
                textvariable=self.y_var,
                validate="key",
                validatecommand=vcmd)\
            .grid(row=1, column=4)


        # ================= Window (Options) =================
        box = ttk.LabelFrame(frame, text="Options")
        box.pack(fill="x", expand=True, **pad)

        check_opts = {
            "anchor": "w",
            "padx": 5,
            "highlightthickness": 0,
            "bd": 0,
            "font": ("Segoe UI", 9) 
        }

        # Checkbox 1: Always on top
        self.cb_always_top = tk.Checkbutton(
            box,
            text="Always on top",
            variable=self.always_on_top_var,
            command=self._toggle_always_on_top,
            **check_opts
        )
        self.cb_always_top.grid(row=0, column=0, sticky="w", padx=5, pady=2)

        # Checkbox 2: Apply limits to Macro
        self.cb_macro_limit = tk.Checkbutton(
            box,
            text="Apply limits to Macro (time & loops)",
            variable=self.macro_use_limits_var,
            **check_opts
        )
        self.cb_macro_limit.grid(row=1, column=0, sticky="w", padx=5, pady=2)

        # Checkbox 3: Show on-screen text overlay
        self.cb_overlay = tk.Checkbutton(
            box,
            text="Show on-screen text overlay",
            variable=self.show_overlay_var,
            command=self._on_toggle_overlay,
            **check_opts
        )
        self.cb_overlay.grid(row=2, column=0, sticky="w", padx=5, pady=2)

        # ================= Hotkey (Collapsible) =================
        self.hotkey_section = ttk.Frame(frame)
        self.hotkey_section.pack(fill="x", **pad)

        # Nút toggle
        self.hotkey_toggle_btn = ttk.Button(
            self.hotkey_section,
            text="▶ Hotkey Settings",
            command=self._toggle_hotkey_section
        )
        self.hotkey_toggle_btn.pack(fill="x")

        # Box chính nằm TRONG hotkey_section
        self.hotkey_box = ttk.LabelFrame(self.hotkey_section, text="Hotkey Settings")

        labels = ["Start", "Stop", "Pick Pos", "Record/Stop Record", "Play"]

        vars_mod = [
            self.modifier_start,
            self.modifier_stop,
            self.modifier_pick,
            self.modifier_record,
            self.modifier_play
        ]

        vars_key = [
            self.hotkey_start,
            self.hotkey_stop,
            self.hotkey_pick,
            self.hotkey_record,
            self.hotkey_play
        ]

        # Tăng width=18 và thêm sticky="w" (căn trái)
        ttk.Label(self.hotkey_box, text="Action", width=18).grid(row=0, column=0, sticky="w", padx=5)
        ttk.Label(self.hotkey_box, text="Modifier", width=10).grid(row=0, column=1, padx=5)
        ttk.Label(self.hotkey_box, text="Key", width=6).grid(row=0, column=2, padx=5)

        for i, text in enumerate(labels):
            # Tăng width=18 và thêm sticky="w"
            ttk.Label(self.hotkey_box, text=text, width=18)\
                .grid(row=i+1, column=0, sticky="w", padx=5, pady=4)

            ttk.Combobox(
                self.hotkey_box,
                textvariable=vars_mod[i],
                values=["None", "Ctrl", "Alt", "Shift"],
                width=8,
                state="readonly"
            ).grid(row=i+1, column=1, padx=5)

            ttk.Combobox(
                self.hotkey_box,
                textvariable=vars_key[i],
                values=[f"F{x}" for x in range(1, 13)],
                width=6,
                state="readonly"
            ).grid(row=i+1, column=2, padx=5)
            
       # ================= Macro =================
        box = ttk.LabelFrame(frame, text="Macro")
        box.pack(fill="x", expand=True, **pad)

        # Hàng 0
        self.btn_record = ttk.Button(box, text="Record/Stop Record", command=self.toggle_record)
        self.btn_record.grid(row=0, column=0, padx=6, pady=4, sticky="ew")

        self.btn_play = ttk.Button(box, text="Play", command=self.play_macro)
        self.btn_play.grid(row=0, column=1, padx=6, pady=4, sticky="ew")

        # Hàng 1
        self.btn_save = ttk.Button(box, text="Save", command=self.save_macro)
        self.btn_save.grid(row=1, column=0, padx=6, pady=4, sticky="ew")

        self.btn_load = ttk.Button(box, text="Load", command=self.load_macro)
        self.btn_load.grid(row=1, column=1, padx=6, pady=4, sticky="ew")

        # Nhãn hiển thị số lượng (Gộp 2 hàng bằng rowspan=2 để căn giữa)
        ttk.Label(box, textvariable=self.macro_info_var)\
            .grid(row=0, column=2, rowspan=2, padx=15)
        # ================= Controls =================
        control = ttk.Frame(frame)
        control.pack(fill="x", pady=10)

        ttk.Button(control, text="▶ START",
                command=self.start)\
            .pack(side="left", expand=True, fill="x", padx=6)

        ttk.Button(control, text="⛔ STOP",
                command=self.stop)\
            .pack(side="left", expand=True, fill="x", padx=6)

        # ================= Status =================
        ttk.Label(frame, textvariable=self.indicator_var,
                font=("Segoe UI", 10, "bold")).pack()

        ttk.Label(frame, textvariable=self.status_var).pack()
        ttk.Label(frame, textvariable=self.remaining_time_var).pack()
        ttk.Label(frame, textvariable=self.remaining_click_var).pack()


    # ================= LOGIC =================



    def _get_interval(self):
        return (
            int(self.delay_hour.get() or 0) * 3600 +
            int(self.delay_min.get() or 0) * 60 +
            int(self.delay_sec.get() or 0) +
            (int(self.delay_ms.get() or 0) / 1000)
        )



    def _set_fixed(self, x, y):
        self.target_var.set("fixed")
        self.x_var.set(int(x))
        self.y_var.set(int(y))



    def _click_loop(self):
        interval = self._get_interval()
        if interval <= 0:
            interval = 0.01

        clicks = 0

        total_stop_time = (
            int(self.stop_hour.get() or 0) * 3600 +
            int(self.stop_min.get() or 0) * 60 +
            int(self.stop_sec.get() or 0) +
            (int(self.stop_ms.get() or 0) / 1000)
        )

        start_time = time.perf_counter()

        while not self.stop_event.is_set():
            elapsed = time.perf_counter() - start_time

            # CẬP NHẬT THỜI GIAN CÒN LẠI (MỚI SỬA)
            if total_stop_time > 0:
                remaining_time = total_stop_time - elapsed
                if remaining_time <= 0:
                    break
                # Update UI cho thời gian
                self.remaining_time_var.set(f"Remaining time: {remaining_time:.1f}s")

            max_clicks = int(self.max_clicks_var.get() or 0)

            if max_clicks > 0 and clicks >= max_clicks:
                break

            if self.target_var.get() == "current":
                x, y = pyautogui.position()
            else:
                x = int(self.x_var.get() or 0)
                y = int(self.y_var.get() or 0)

            pyautogui.click(x, y, button=self.button_var.get())
            clicks += 1
            
            # UPDATE remaining clicks
            if max_clicks > 0:
                remaining = max_clicks - clicks
                self.remaining_click_var.set(
                    f"Remaining clicks: {max(0, remaining)}"
                )

            time.sleep(interval)

        self.stop()


    def _toggle_hotkey_section(self):
        if self.hotkey_visible.get() == False:
            self.hotkey_box.pack(fill="x", padx=10, pady=6)
            self.hotkey_toggle_btn.config(text="▼ Hotkey Settings")
            self.hotkey_visible.set(True)
        else:
            self.hotkey_box.pack_forget()
            self.hotkey_toggle_btn.config(text="▶ Hotkey Settings")
            self.hotkey_visible.set(False)



    def start(self):
        if self.running or self.is_playing_macro:
            return

        self.running = True
        self.stop_event.clear()
        self.indicator_var.set("AUTOCLICK: ON")

        # CẬP NHẬT REMAINING CLICKS
        max_clicks = int(self.max_clicks_var.get() or 0)
        if max_clicks > 0:
            self.remaining_click_var.set(f"Remaining clicks: {max_clicks}")
        else:
            self.remaining_click_var.set("Remaining clicks: ∞")

        # CẬP NHẬT REMAINING TIME (MỚI THÊM)
        total_stop_time = (
            int(self.stop_hour.get() or 0) * 3600 +
            int(self.stop_min.get() or 0) * 60 +
            int(self.stop_sec.get() or 0) +
            (int(self.stop_ms.get() or 0) / 1000)
        )
        if total_stop_time > 0:
            self.remaining_time_var.set(f"Remaining time: {total_stop_time:.1f}s")
        else:
            self.remaining_time_var.set("Remaining time: ∞")

        self._show_overlay("🟢 AUTO CLICK", "#27ae60")
        threading.Thread(target=self._click_loop, daemon=True).start()


    def stop(self):
        self.running = False
        self.stop_event.set()
        self.indicator_var.set("AUTOCLICK: OFF")
        self._hide_overlay()
        self.remaining_click_var.set("Remaining clicks: --")
        self.remaining_time_var.set("Remaining time: --")

        if self.is_recording:
            self.stop_record()
        if self.is_playing_macro:
            self.stop_macro()


    def _set_macro_ui_state(self, playing: bool):
        state = "disabled" if playing else "normal"

        # Disable tất cả trừ stop macro
        self.btn_record.config(state=state)
        self.btn_play.config(state=state)
        self.btn_save.config(state=state)
        self.btn_load.config(state=state)




    def _toggle_always_on_top(self):
        self.root.attributes("-topmost", self.always_on_top_var.get())

    def _on_toggle_overlay(self):
        if not self.show_overlay_var.get():
            self._hide_overlay()
        else:
            if self.running:
                self._show_overlay("🟢 AUTO CLICK", "#27ae60")
            elif self.is_recording:
                self._show_overlay("🔴 RECORDING", "#c0392b")
            elif self.is_playing_macro:
                self._show_overlay("🟣 PLAY MACRO", "#8e44ad")
        
    def _format_hotkey(self, modifier, key):
        key = key.lower()
        if modifier == "None":
            return f"<{key}>"
        return f"<{modifier.lower()}>+<{key}>"
    
    def _validate_number(self, new_value):
        if new_value == "":
            return True
        return new_value.isdigit()

    def _on_invalid_number(self, var):
        var.set(var._last_valid)

    def _apply_hotkeys(self):
        if getattr(self, '_is_restoring_hotkeys', False):
            return
        
        if self.hotkey_listener:
            self.hotkey_listener.stop()

        all_hotkeys = {
            "start": self._format_hotkey(self.modifier_start.get(),
                                        self.hotkey_start.get()),
            "stop": self._format_hotkey(self.modifier_stop.get(),
                                        self.hotkey_stop.get()),
            "pick": self._format_hotkey(self.modifier_pick.get(),
                                        self.hotkey_pick.get()),
            "record": self._format_hotkey(self.modifier_record.get(),
                                        self.hotkey_record.get()),
            "play": self._format_hotkey(self.modifier_play.get(),
                                        self.hotkey_play.get()),
        }

        used = set()

        for name, hk in all_hotkeys.items():
            if hk in used:
                messagebox.showerror(
                    "Hotkey Error",
                    f"Hotkey {hk} is already in use!"
                )

                # QUAY LẠI HOTKEY CŨ
                self._restore_last_hotkeys()
                return

            used.add(hk)

        # Lưu config hợp lệ
        self._last_hotkey_config = {
            "modifier_start": self.modifier_start.get(),
            "hotkey_start": self.hotkey_start.get(),
            "modifier_stop": self.modifier_stop.get(),
            "hotkey_stop": self.hotkey_stop.get(),
            "modifier_pick": self.modifier_pick.get(),
            "hotkey_pick": self.hotkey_pick.get(),
            "modifier_record": self.modifier_record.get(),
            "hotkey_record": self.hotkey_record.get(),
            "modifier_play": self.modifier_play.get(),
            "hotkey_play": self.hotkey_play.get(),
        }

        hotkey_map = {
            all_hotkeys["start"]: self.start,
            all_hotkeys["stop"]: self._handle_stop_hotkey,
            all_hotkeys["pick"]: lambda: self._set_fixed(*pyautogui.position()),
            all_hotkeys["record"]: self._handle_record_hotkey,
            all_hotkeys["play"]: self.play_macro,
        }


        self.hotkey_listener = keyboard.GlobalHotKeys(hotkey_map)
        self.hotkey_listener.start()

    def _restore_last_hotkeys(self):
        if not self._last_hotkey_config:
            return
        
        self._is_restoring_hotkeys = True

        self.modifier_start.set(self._last_hotkey_config["modifier_start"])
        self.hotkey_start.set(self._last_hotkey_config["hotkey_start"])

        self.modifier_stop.set(self._last_hotkey_config["modifier_stop"])
        self.hotkey_stop.set(self._last_hotkey_config["hotkey_stop"])

        self.modifier_pick.set(self._last_hotkey_config["modifier_pick"])
        self.hotkey_pick.set(self._last_hotkey_config["hotkey_pick"])

        self.modifier_record.set(self._last_hotkey_config["modifier_record"])
        self.hotkey_record.set(self._last_hotkey_config["hotkey_record"])

        self.modifier_play.set(self._last_hotkey_config["modifier_play"])
        self.hotkey_play.set(self._last_hotkey_config["hotkey_play"])

        self._is_restoring_hotkeys = False

        self._apply_hotkeys()

    # ===== Macro giữ nguyên =====
    def toggle_record(self):
        if self.is_recording:
            self._set_macro_ui_state(True)
            self.stop_record()
            return

        self.macro_events.clear()
        self.is_recording = True
        self._last_event_time = time.perf_counter()
        self._show_overlay("🔴 RECORDING", "#c0392b")

        def on_click(x, y, button, pressed):
            # NẾU KHÔNG CÒN GHI NỮA -> KILL LUỒNG LẮNG NGHE CHUỘT
            if not self.is_recording:
                return False 
            
            # Nếu chỉ di chuột hoặc thả chuột ra -> Bỏ qua
            if not pressed:
                return
            
            now = time.perf_counter()
            self.macro_events.append({
                "delay": now - self._last_event_time,
                "x": x,
                "y": y,
                "button": button.name
            })
            self._last_event_time = now
            self.macro_info_var.set(f"Macro: {len(self.macro_events)} events")

        self._mouse_listener = mouse.Listener(on_click=on_click)
        self._mouse_listener.start()

    def stop_record(self):
        self.is_recording = False
        self._set_macro_ui_state(False)
        if self._mouse_listener:
            self._mouse_listener.stop()
            self._mouse_listener = None
        self._hide_overlay()

    def play_macro(self):
        if not self.macro_events:
            return

        self.is_playing_macro = True
        self._set_macro_ui_state(True)
        self._show_overlay("🟣 PLAY MACRO", "#8e44ad")

        def worker():
            loops = 0  # Theo dõi số vòng lặp thay vì số click
            start_time = time.perf_counter()

            total_stop_time = (
                int(self.stop_hour.get() or 0) * 3600 +
                int(self.stop_min.get() or 0) * 60 +
                int(self.stop_sec.get() or 0) +
                (int(self.stop_ms.get() or 0) / 1000)
            )

            max_loops = int(self.max_clicks_var.get() or 0)

            while self.is_playing_macro:
                
                # Kiểm tra giới hạn số LOOP trước khi bắt đầu 1 vòng mới
                if self.macro_use_limits_var.get():
                    if max_loops > 0 and loops >= max_loops:
                        self.stop_macro()
                        break

                for ev in self.macro_events:
                    if not self.is_playing_macro:
                        break

                    # Kiểm tra thời gian Stop Time liên tục ngay cả khi đang trong 1 vòng lặp
                    if self.macro_use_limits_var.get():
                        elapsed = time.perf_counter() - start_time
                        if total_stop_time > 0 and elapsed >= total_stop_time:
                            self.stop_macro()
                            break

                    time.sleep(ev["delay"])
                    pyautogui.click(ev["x"], ev["y"], button=ev["button"])

                loops += 1  # Kết thúc 1 vòng lặp toàn bộ macro thì +1

                # Nếu không bật Limit thì mặc định chỉ chạy 1 lần rồi nghỉ
                if not self.macro_use_limits_var.get():
                    break

            self.stop_macro()

        threading.Thread(target=worker, daemon=True).start()

    def stop_macro(self):
        self.is_playing_macro = False
        self._hide_overlay()
        self._set_macro_ui_state(False)

    def _handle_stop_hotkey(self):
        if self.running:
            self.stop()

        if self.is_recording:
            self.stop_record()

        if self.is_playing_macro:
            self.stop_macro()

    def _handle_record_hotkey(self):

        # Nếu đang play thì không cho record
        if self.is_playing_macro:
            return

        # Nếu đang record → stop
        if self.is_recording:
            self.stop_record()
            return

        # Nếu đã có macro → hỏi ghi đè
        if self.macro_events:
            confirm = messagebox.askyesno(
                "Overwrite Macro",
                "The existing macro will be overwritten.\nDo you want to continue?"
            )
            if not confirm:
                return

        # Clear và bắt đầu record mới
        self.macro_events.clear()
        self.macro_info_var.set("Macro: 0 events")
        self.toggle_record()

    def save_macro(self):
        if not self.macro_events:
            return
        path = filedialog.asksaveasfilename(defaultextension=".json")
        if path:
            with open(path, "w") as f:
                json.dump(self.macro_events, f, indent=2)

    def load_macro(self):
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if path:
            with open(path) as f:
                self.macro_events = json.load(f)
            self.macro_info_var.set(f"Macro: {len(self.macro_events)} events")


    def on_close(self):
        self.stop()
        self.stop_macro()
        if self.is_recording:
            self.stop_record()
        self.root.destroy()


def main():
    root = tk.Tk()
    root.iconbitmap(resource_path("AccuracyUp.ico"))
    AutoClickerApp(root)
    root.mainloop()


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)



if __name__ == "__main__":
    main()
