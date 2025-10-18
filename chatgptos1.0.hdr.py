#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🐱 CATOS XP VM v3.7 — [C] Samsoft Simulations (Stable Build)
------------------------------------------------------------
XP-era *styled* simulated desktop (600×400) with:
  - VirtualBox-like HUD (VM state + optional CPU/RAM stats)
  - CMD emulator
  - Notepad
  - Control Panel
  - Real Internet Browser via pywebview (with safe fallbacks)
  
Design goals:
  • Single-file, cross-platform (Windows/macOS/Linux)
  • Graceful fallbacks when optional deps are missing
  • Avoids menu/grab deadlocks, thread issues with pywebview
  • No Microsoft assets included; UI styling only.

Optional dependencies:
  pip install pywebview pillow psutil

License: You indicated GPL-3.0-or-later; feel free to apply that here as well.
© 2025 FlamesCo / Samsoft Simulations
"""

import sys
import os
import datetime
import threading
import webbrowser

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# ---- Optional deps (safe fallbacks) -----------------------------------------
try:
    import webview as _webview
    _WEBVIEW_OK = True
except Exception:
    _webview = None
    _WEBVIEW_OK = False

try:
    from PIL import Image, ImageDraw, ImageTk
    _PIL_OK = True
except Exception:
    Image = ImageDraw = ImageTk = None
    _PIL_OK = False

try:
    import psutil
    _PSUTIL_OK = True
except Exception:
    psutil = None
    _PSUTIL_OK = False

# ---- Constants & theme ------------------------------------------------------
APP_TITLE = "[C] Samsoft Simulations — CATOS XP VM v3.7"
WIN_W, WIN_H = 600, 400

XP_BLUE = "#0b5394"     # desktop background
TASKBAR_BLUE = "#245ca6" # taskbar
HUD_BG = "#222222"       # HUD (VirtualBox-like) bar
HUD_FG = "#f2f2f2"
WIN_BG = "#ece9d8"       # control panel background
TXT_MONO = ("Consolas" if sys.platform.startswith("win") else "Courier New", 10)
TXT_UI = ("Segoe UI" if sys.platform.startswith("win") else "TkDefaultFont", 9)

# ---- VM state ---------------------------------------------------------------
_VM_PAUSED = False
_WEBVIEW_STARTED = False   # pywebview can only be started once per process

def is_paused():
    return _VM_PAUSED

def guard_not_paused():
    if is_paused():
        messagebox.showinfo("VM Paused", "Resume the VM from the HUD to continue.")
        return True
    return False

# ---- Root window ------------------------------------------------------------
root = tk.Tk()
root.title(APP_TITLE)
root.geometry(f"{WIN_W}x{WIN_H}")
root.configure(bg=XP_BLUE)

def on_exit():
    if messagebox.askokcancel("Exit CATOS", "Power off the VM?"):
        try:
            root.destroy()
        except Exception:
            os._exit(0)

root.protocol("WM_DELETE_WINDOW", on_exit)

# ---- Splash (optional, uses Pillow if present) ------------------------------
def show_splash():
    splash = tk.Toplevel(root)
    splash.overrideredirect(True)
    splash.geometry(f"{WIN_W}x{WIN_H}+{root.winfo_x()}+{root.winfo_y()}")

    if _PIL_OK:
        img = Image.new("RGB", (WIN_W, WIN_H), "black")
        d = ImageDraw.Draw(img)
        text = "Starting CATOS XP..."
        # Simple center-ish placement
        d.text((WIN_W//2 - 80, WIN_H//2 - 10), text, fill="lime")
        tkimg = ImageTk.PhotoImage(img)
        lbl = tk.Label(splash, image=tkimg, bg="black")
        lbl.image = tkimg
        lbl.pack(fill="both", expand=True)
    else:
        lbl = tk.Label(splash, text="Starting CATOS XP...", bg="black", fg="lime", font=TXT_MONO)
        lbl.pack(fill="both", expand=True)

    def close():
        try:
            splash.destroy()
        except Exception:
            pass
    splash.after(900, close)

# Uncomment to show splash on launch
# show_splash()

# ---- HUD (VirtualBox-like top bar) -----------------------------------------
hud = tk.Frame(root, bg=HUD_BG, height=26)
hud.pack(side="top", fill="x")

hud_left = tk.Frame(hud, bg=HUD_BG)
hud_left.pack(side="left", padx=8)

hud_center = tk.Frame(hud, bg=HUD_BG)
hud_center.pack(side="left", expand=True)

hud_right = tk.Frame(hud, bg=HUD_BG)
hud_right.pack(side="right", padx=8)

hud_title = tk.Label(hud_left, text="CATOS XP VM — Running", bg=HUD_BG, fg=HUD_FG, font=TXT_UI)
hud_title.pack(side="left")

# HUD Buttons: Power, Reset, Pause (no destructive operations by default)
def vm_power_off():
    on_exit()

def vm_reset():
    if messagebox.askyesno("Reset", "Soft reset the VM UI? (apps will close)"):
        for w in root.winfo_children():
            # Keep HUD and taskbar
            if w not in (hud, taskbar):
                try: w.destroy()
                except Exception: pass
        build_desktop()

def vm_toggle_pause():
    global _VM_PAUSED
    _VM_PAUSED = not _VM_PAUSED
    state = "Paused" if _VM_PAUSED else "Running"
    hud_title.config(text=f"CATOS XP VM — {state}")
    # Simple visual dim when paused
    try:
        root.attributes("-alpha", 0.85 if _VM_PAUSED else 1.0)
    except Exception:
        pass

btn_style = dict(bg="#444444", fg=HUD_FG, relief="flat", font=TXT_UI)
tk.Button(hud_right, text="Pause/Resume", command=vm_toggle_pause, **btn_style).pack(side="right", padx=4)
tk.Button(hud_right, text="Reset", command=vm_reset, **btn_style).pack(side="right", padx=4)
tk.Button(hud_right, text="Power Off", command=vm_power_off, **btn_style).pack(side="right", padx=4)

# HUD metrics (optional psutil)
hud_metrics = tk.Label(hud_center, text="", bg=HUD_BG, fg="#cfcfcf", font=TXT_UI)
hud_metrics.pack()

if _PSUTIL_OK:
    # Prime cpu_percent to avoid first 0.0
    psutil.cpu_percent(interval=None)

def update_hud():
    if _PSUTIL_OK:
        try:
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory().percent
            hud_metrics.config(text=f"CPU {cpu:.0f}%  •  RAM {mem:.0f}%")
        except Exception:
            hud_metrics.config(text="")
    else:
        hud_metrics.config(text="")  # hide if not available
    root.after(1000, update_hud)

update_hud()

# ---- Taskbar (bottom) -------------------------------------------------------
taskbar = tk.Frame(root, bg=TASKBAR_BLUE, height=28)
taskbar.pack(side="bottom", fill="x")

clock_label = tk.Label(taskbar, bg=TASKBAR_BLUE, fg="white", font=TXT_UI)

def update_clock():
    clock_label.config(text=datetime.datetime.now().strftime("%I:%M:%S %p"))
    root.after(1000, update_clock)

clock_label.pack(side="right", padx=10)
update_clock()

# ---- Apps -------------------------------------------------------------------
def open_cmd():
    if guard_not_paused(): return
    win = tk.Toplevel(root)
    win.title("Command Prompt — [C] Samsoft")
    win.geometry("540x320")
    win.configure(bg="black")

    text = tk.Text(win, bg="black", fg="lime", insertbackground="white", font=TXT_MONO, undo=False)
    text.pack(fill="both", expand=True)

    banner = (
        "Microsoft Windows XP [Version 5.1.2600]\n"
        "(C) Samsoft Simulations 2025. All rights reserved.\n\n"
        "C:\\Samsoft> "
    )
    text.insert("end", banner)
    text.mark_set("insert", "end")

    def write_out(s):
        text.insert("end", s)
        text.see("end")

    def handle_cmd(event):
        # Read last input line after the prompt
        line = text.get("end-2l linestart", "end-1c").replace("C:\\Samsoft> ", "").strip()
        low = line.lower()

        if low in ("dir", "ls"):
            out = (
                "\nVolume in drive C is SAMSOFT_DRIVE\n"
                "Directory of C:\\Samsoft\n\n"
                "CMD.EXE\nNOTEPAD.EXE\nBROWSER.EXE\nCONTROL.EXE\n"
            )
        elif low.startswith("echo "):
            out = "\n" + line[5:] + "\n"
        elif low == "help":
            out = (
                "\nCommands: DIR, ECHO, CLS, HELP, EXIT, DATE, TIME, VER, START <APP>\n"
                "Apps: NOTEPAD, BROWSER, CONTROL\n"
            )
        elif low == "cls":
            text.delete("1.0", "end")
            out = "C:\\Samsoft> "
            write_out(out)
            return "break"
        elif low == "exit":
            win.destroy()
            return "break"
        elif low == "date":
            out = f"\n{datetime.date.today().isoformat()}\n"
        elif low == "time":
            out = f"\n{datetime.datetime.now().strftime('%H:%M:%S')}\n"
        elif low == "ver":
            out = "\nCATOS XP VM v3.7 (Samsoft Simulations)\n"
        elif low.startswith("start "):
            target = low.split(" ", 1)[1].strip()
            if target == "notepad":
                open_notepad(); out = "\nLaunched Notepad.\n"
            elif target == "browser":
                open_browser(); out = "\nLaunched Browser.\n"
            elif target in ("control", "control.exe", "control panel"):
                open_control_panel(); out = "\nLaunched Control Panel.\n"
            else:
                out = f"\nUnknown app: {target}\n"
        else:
            out = f"\n'{line}' is not recognized as an internal command.\n"

        write_out(out + "\nC:\\Samsoft> ")
        return "break"

    text.bind("<Return>", handle_cmd)
    text.focus()

def open_notepad():
    if guard_not_paused(): return
    pad = tk.Toplevel(root)
    pad.title("Notepad — [C] Samsoft")
    pad.geometry("520x340")

    txt = tk.Text(pad, wrap="word", bg="white", fg="black")
    txt.pack(fill="both", expand=True)

    def save_file():
        p = filedialog.asksaveasfilename(
            defaultextension=".txt", filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if p:
            with open(p, "w", encoding="utf-8") as f:
                f.write(txt.get("1.0", "end-1c"))

    def open_file():
        p = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
        if p:
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                txt.delete("1.0", "end")
                txt.insert("1.0", f.read())

    m = tk.Menu(pad)
    f = tk.Menu(m, tearoff=0)
    f.add_command(label="Open", command=open_file)
    f.add_command(label="Save", command=save_file)
    f.add_separator()
    f.add_command(label="Exit", command=pad.destroy)
    m.add_cascade(label="File", menu=f)
    pad.config(menu=m)

def _start_webview():
    """
    Start pywebview exactly once in a background thread. Subsequent calls
    will try to bring the window to front. If pywebview fails to init,
    we fall back to default browser.
    """
    global _WEBVIEW_STARTED
    try:
        _webview.create_window("CATOS Browser — [C] Samsoft", "https://duckduckgo.com",
                               width=WIN_W, height=WIN_H, confirm_close=True)
        _WEBVIEW_STARTED = True
        _webview.start()
    except Exception:
        _WEBVIEW_STARTED = False
        webbrowser.open("https://duckduckgo.com")

def open_browser():
    if guard_not_paused(): return
    if _WEBVIEW_OK and not _WEBVIEW_STARTED:
        threading.Thread(target=_start_webview, daemon=True).start()
    elif _WEBVIEW_OK and _WEBVIEW_STARTED:
        try:
            # Bring existing webview to front if possible
            if _webview.windows:
                try:
                    _webview.windows[0].bring_to_front()
                except Exception:
                    pass
            else:
                webbrowser.open("https://duckduckgo.com")
        except Exception:
            webbrowser.open("https://duckduckgo.com")
    else:
        webbrowser.open("https://duckduckgo.com")

def open_control_panel():
    if guard_not_paused(): return
    win = tk.Toplevel(root)
    win.title("Control Panel — [C] Samsoft")
    win.geometry("420x220")
    win.configure(bg=WIN_BG)

    tk.Label(win, text="[C] Samsoft Control Center",
             font=("Segoe UI" if sys.platform.startswith("win") else "TkDefaultFont", 12, "bold"),
             bg=WIN_BG).pack(pady=10)

    info = [
        "CATOS XP VM v3.7",
        "FlamesCo BSD-like Kernel Emulation (UI only)",
        f"Virtual Machine: {'Paused' if _VM_PAUSED else 'Running'}",
        f"Browser: {'pywebview' if _WEBVIEW_OK else 'system web browser'}",
        "Status: Stable Build",
    ]
    if _PSUTIL_OK:
        try:
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory().percent
            info.append(f"System: CPU {cpu:.0f}% • RAM {mem:.0f}%")
        except Exception:
            pass

    tk.Label(win, text="\n".join(info), bg=WIN_BG, justify="left", font=TXT_MONO).pack(padx=12)

# ---- Start Menu -------------------------------------------------------------
menu = tk.Menu(root, tearoff=0, bg="white", fg="black")
menu.add_command(label="Command Prompt 🖥️", command=open_cmd)
menu.add_command(label="Notepad 📝", command=open_notepad)
menu.add_command(label="Browser 🌐", command=open_browser)
menu.add_command(label="Control Panel ⚙️", command=open_control_panel)
menu.add_separator()
menu.add_command(label="About CATOS…", command=lambda: messagebox.showinfo(
    "About",
    "CATOS XP VM v3.7 — XP-style desktop simulator.\n"
    "This project mimics UI only; no Microsoft assets included."
))
menu.add_command(label="Exit CATOS", command=on_exit)

def show_menu(event=None):
    # Works both from click and programmatic open; avoids grab deadlock
    try:
        if event:
            menu.tk_popup(event.x_root, event.y_root)
        else:
            x = start_btn.winfo_rootx()
            y = start_btn.winfo_rooty() - menu.winfo_reqheight()
            menu.tk_popup(x, y)
    finally:
        try:
            menu.grab_release()
        except Exception:
            pass

start_btn = tk.Button(taskbar, text="Start", bg=XP_BLUE, fg="white",
                      relief="flat", font=("Segoe UI" if sys.platform.startswith("win") else "TkDefaultFont", 9, "bold"),
                      command=lambda: show_menu(None))
start_btn.pack(side="left", padx=6, pady=2)

# Right-click anywhere on desktop to open menu as well
root.bind("<Button-3>", show_menu)

# ---- Desktop icons ----------------------------------------------------------
desktop = tk.Frame(root, bg=XP_BLUE)
desktop.pack(fill="both", expand=True)

ICON_SPEC = [
    ("My Computer", "💻", open_control_panel),
    ("Internet", "🌐", open_browser),
    ("Command Prompt", "🖥️", open_cmd),
    ("Notepad", "📝", open_notepad),
]

def build_desktop():
    # Clear desktop frame
    for w in desktop.winfo_children():
        w.destroy()
    # Layout icons in a simple column
    for i, (label, emoji, fn) in enumerate(ICON_SPEC):
        b = tk.Button(
            desktop, text=f"{emoji}\n{label}", fg="white", bg=XP_BLUE,
            relief="flat", font=TXT_UI, command=fn, activebackground=XP_BLUE, activeforeground="white",
            cursor="hand2"
        )
        b.grid(row=i, column=0, padx=20, pady=10, sticky="w")

build_desktop()

# ---- Run --------------------------------------------------------------------
if __name__ == "__main__":
    root.mainloop()
