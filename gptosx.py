#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Snow Leopard-ish Desktop Simulator (Tkinter, 600x400, single file)
Features:
- Boot screen with spinner animation
- Login screen
- Desktop with gradient wallpaper
- Menu bar with  menu (About, Restart, Shut Down, Log Out)
- Dock with hover magnification + bounce on launch
- Draggable, layered, in-desktop windows with traffic-light controls
- Apps: Finder (mock), Safari (preview), Notes (editable)
No external assets; everything drawn on Canvas inside 600x400.
"""

import tkinter as tk
from tkinter import scrolledtext, messagebox
import math
import time

# ---------------------------- Config ----------------------------
WIDTH, HEIGHT = 600, 400
MENUBAR_H = 22
DOCK_H = 58
WORK_X = 8
WORK_Y = MENUBAR_H + 6
WORK_W = WIDTH - 16
WORK_H = HEIGHT - MENUBAR_H - DOCK_H - 14

BG_WALLPAPER_TOP = "#a9c9ff"
BG_WALLPAPER_BOT = "#7ca9ff"
MENUBAR_BG = "#ececec"
MENUPOP_BG = "#f8f8f8"
TITLEBAR_BG = "#e7e7e7"
WIN_BG = "#ffffff"
DESKTOP_LABEL = "#ffffff"

# ---------------------------- Utility ----------------------------
def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v

def lerp_color(c1, c2, t):
    def hex_to_rgb(h): return (int(h[1:3],16), int(h[3:5],16), int(h[5:7],16))
    def rgb_to_hex(r,g,b): return f"#{r:02x}{g:02x}{b:02x}"
    r1,g1,b1 = hex_to_rgb(c1); r2,g2,b2 = hex_to_rgb(c2)
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    return rgb_to_hex(r,g,b)

# ---------------------------- Window Class ----------------------------
class DesktopWindow:
    _counter = 0
    def __init__(self, osapp, title, x, y, w, h, builder):
        DesktopWindow._counter += 1
        self.id = DesktopWindow._counter
        self.os = osapp
        self.cv = osapp.canvas
        self.title = title
        self.x, self.y, self.w, self.h = x, y, w, h
        self.builder = builder
        self.drag_off = (0, 0)
        self.zoomed = False
        self.hidden = False
        self.tag = f"win-{self.id}"

        # Shadow (subtle)
        self.shadow = self.cv.create_rectangle(self.x+3, self.y+5, self.x+self.w+3, self.y+self.h+5,
                                               fill="#000000", outline="", stipple="gray50", tags=(self.tag,))
        # Frame + titlebar
        self.body = self.cv.create_rectangle(self.x, self.y, self.x+self.w, self.y+self.h,
                                             fill=WIN_BG, outline="#c9c9c9", width=1, tags=(self.tag,))
        self.titlebar = self.cv.create_rectangle(self.x, self.y, self.x+self.w, self.y+24,
                                                 fill=TITLEBAR_BG, outline="#d0d0d0", tags=(self.tag,"titlebar-"+self.tag))
        self.title_text = self.cv.create_text(self.x+ self.w//2, self.y+12, text=self.title,
                                              font=("Helvetica", 10, "bold"), fill="#333", tags=(self.tag,"titlebar-"+self.tag))

        # Traffic-lights
        r = 6; cx = self.x + 14; cy = self.y + 12
        self.btn_close = self.cv.create_oval(cx-r, cy-r, cx+r, cy+r, fill="#ff5f57", outline="#d44a43",
                                             tags=(self.tag,"btn-close-"+self.tag))
        self.btn_min   = self.cv.create_oval(cx+16-r, cy-r, cx+16+r, cy+r, fill="#febc2e", outline="#ca9724",
                                             tags=(self.tag,"btn-min-"+self.tag))
        self.btn_zoom  = self.cv.create_oval(cx+32-r, cy-r, cx+32+r, cy+r, fill="#28c840", outline="#1f9e33",
                                             tags=(self.tag,"btn-zoom-"+self.tag))

        # Content area (embed a Frame)
        self.content = tk.Frame(self.cv, bg=WIN_BG)
        self.content_id = self.cv.create_window(self.x+1, self.y+25, window=self.content,
                                                anchor="nw", width=self.w-2, height=self.h-26, tags=(self.tag,))

        # Build app UI
        self.builder(self.content, self)

        # Bindings
        self.cv.tag_bind(self.tag, "<Button-1>", self._focus)
        self.cv.tag_bind("titlebar-"+self.tag, "<Button-1>", self._start_drag)
        self.cv.tag_bind("titlebar-"+self.tag, "<B1-Motion>", self._on_drag)
        self.cv.tag_bind("btn-close-"+self.tag, "<Button-1>", lambda e: self.close())
        self.cv.tag_bind("btn-min-"+self.tag,   "<Button-1>", lambda e: self.minimize())
        self.cv.tag_bind("btn-zoom-"+self.tag,  "<Button-1>", lambda e: self.toggle_zoom())

        self.focus()

    # ----- Window ops -----
    def bbox(self): return (self.x, self.y, self.x+self.w, self.y+self.h)

    def _start_drag(self, e):
        self.focus()
        self.drag_off = (e.x - self.x, e.y - self.y)

    def _on_drag(self, e):
        nx = e.x - self.drag_off[0]
        ny = e.y - self.drag_off[1]
        # Clamp to workspace
        nx = clamp(nx, WORK_X, WORK_X + WORK_W - self.w)
        ny = clamp(ny, WORK_Y, WORK_Y + WORK_H - self.h)
        self._move_to(nx, ny)

    def _move_to(self, nx, ny):
        dx, dy = nx - self.x, ny - self.y
        if dx == 0 and dy == 0: return
        for item in (self.shadow, self.body, self.titlebar, self.title_text,
                     self.btn_close, self.btn_min, self.btn_zoom, self.content_id):
            self.cv.move(item, dx, dy)
        self.x, self.y = nx, ny

    def resize_to(self, w, h):
        self.w, self.h = w, h
        # Update shapes
        self.cv.coords(self.shadow, self.x+3, self.y+5, self.x+self.w+3, self.y+self.h+5)
        self.cv.coords(self.body,   self.x, self.y, self.x+self.w, self.y+self.h)
        self.cv.coords(self.titlebar, self.x, self.y, self.x+self.w, self.y+24)
        self.cv.coords(self.title_text, self.x+self.w//2, self.y+12)
        # Traffic lights
        cx = self.x + 14; cy = self.y + 12; r = 6
        self.cv.coords(self.btn_close, cx-r, cy-r, cx+r, cy+r)
        self.cv.coords(self.btn_min,   cx+16-r, cy-r, cx+16+r, cy+r)
        self.cv.coords(self.btn_zoom,  cx+32-r, cy-r, cx+32+r, cy+r)
        # Content
        self.cv.coords(self.content_id, self.x+1, self.y+25)
        self.cv.itemconfigure(self.content_id, width=self.w-2, height=self.h-26)

    def focus(self, *_):
        # Raise to top
        self.cv.tag_raise(self.tag)
        # Inform menubar
        self.os.set_active_app(self.title)

    def close(self):
        self.os.unregister_window(self)
        for item in (self.shadow, self.body, self.titlebar, self.title_text,
                     self.btn_close, self.btn_min, self.btn_zoom, self.content_id):
            self.cv.delete(item)
        try:
            self.content.destroy()
        except Exception:
            pass

    def minimize(self):
        if self.hidden: return
        self.hidden = True
        for item in (self.shadow, self.body, self.titlebar, self.title_text,
                     self.btn_close, self.btn_min, self.btn_zoom, self.content_id):
            self.cv.itemconfigure(item, state="hidden")
        self.os.notify_minimized(self)

    def restore(self):
        if not self.hidden: return
        self.hidden = False
        for item in (self.shadow, self.body, self.titlebar, self.title_text,
                     self.btn_close, self.btn_min, self.btn_zoom, self.content_id):
            self.cv.itemconfigure(item, state="normal")
        self.focus()

    def toggle_zoom(self):
        if not self.zoomed:
            self._pre_zoom = (self.x, self.y, self.w, self.h)
            self._move_to(WORK_X+4, WORK_Y+4)
            self.resize_to(WORK_W-8, WORK_H-8)
            self.zoomed = True
        else:
            x,y,w,h = self._pre_zoom
            self._move_to(x,y); self.resize_to(w,h)
            self.zoomed = False

# ---------------------------- OS App ----------------------------
class SnowLeopardOS:
    def __init__(self, root):
        self.root = root
        self.root.title("macOS Snow Leopard — Simulator")
        self.root.geometry(f"{WIDTH}x{HEIGHT}")
        self.root.resizable(False, False)
        self.state = "boot"
        self.windows = []
        self.active_app = "Finder"
        self._dock_anim = {}
        self._hover_timer = None

        # Main canvas (all UI inside)
        self.canvas = tk.Canvas(self.root, width=WIDTH, height=HEIGHT, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self._boot_screen()

    # ----- State handling -----
    def _clear(self):
        self.canvas.delete("all")

    # ----- Boot Screen -----
    def _boot_screen(self):
        self.state = "boot"
        self._clear()
        self.canvas.configure(bg="#dcdcdc")
        cx, cy = WIDTH//2, HEIGHT//2 - 10
        # Apple-ish blob
        self.canvas.create_oval(cx-30, cy-40, cx+30, cy+40, fill="#9e9e9e", outline="")
        self.canvas.create_oval(cx+8, cy-18, cx+38, cy+18, fill="#dcdcdc", outline="")
        self.canvas.create_oval(cx-8, cy-62, cx+8, cy-42, fill="#9e9e9e", outline="")

        # Spinner
        self._spinner_lines = []
        for i in range(12):
            a = math.radians(i*30)
            x0 = cx + 18*math.cos(a); y0 = cy+80 + 18*math.sin(a)
            x1 = cx + 26*math.cos(a); y1 = cy+80 + 26*math.sin(a)
            ln = self.canvas.create_line(x0,y0,x1,y1, width=3, fill="#b0b0b0")
            self._spinner_lines.append(ln)
        self._spin_angle = 0
        self._animate_spinner()
        # Proceed to login
        self.root.after(4200, self._login_screen)

    def _animate_spinner(self):
        if self.state != "boot": return
        self._spin_angle = (self._spin_angle + 30) % 360
        for i, ln in enumerate(self._spinner_lines):
            c = int(180 + 75 * math.sin(math.radians(i*30 + self._spin_angle)))
            self.canvas.itemconfigure(ln, fill=f"#{c:02x}{c:02x}{c:02x}")
        self.root.after(90, self._animate_spinner)

    # ----- Login Screen -----
    def _login_screen(self):
        self.state = "login"
        self._clear()
        self._draw_wallpaper()

        # Frosted panel
        panel = self.canvas.create_rectangle(WIDTH//2-120, HEIGHT//2-60, WIDTH//2+120, HEIGHT//2+60,
                                             fill="#f0f0f0", outline="#d0d0d0")
        self.canvas.create_text(WIDTH//2, HEIGHT//2-35, text="Welcome to Snow Leopard",
                                font=("Helvetica", 12, "bold"))
        # Entries using embedded windows
        self.user = tk.Entry(self.root, justify="center")
        self.passw = tk.Entry(self.root, justify="center", show="•")
        self.user.insert(0, "catuser")
        self.passw.insert(0, "••••••")
        self.user_id = self.canvas.create_window(WIDTH//2, HEIGHT//2-5, window=self.user)
        self.pass_id = self.canvas.create_window(WIDTH//2, HEIGHT//2+25, window=self.passw)
        btn = tk.Button(self.root, text="Login", command=self._desktop)
        self.login_btn = self.canvas.create_window(WIDTH//2, HEIGHT//2+55, window=btn)
        self.user.bind("<Return>", lambda e: self._desktop())
        self.passw.bind("<Return>", lambda e: self._desktop())

    # ----- Desktop -----
    def _desktop(self):
        self.state = "desktop"
        self._clear()
        self._draw_wallpaper()
        self._draw_menubar()
        self._draw_dock()
        self._draw_desktop_icons()
        self._tick_clock()
        # Launch Finder on start (classic feel)
        self.launch_app("Finder")

    # Wallpaper gradient
    def _draw_wallpaper(self):
        steps = 40
        for i in range(steps):
            t = i/(steps-1)
            color = lerp_color(BG_WALLPAPER_TOP, BG_WALLPAPER_BOT, t)
            self.canvas.create_rectangle(0, int(i*HEIGHT/steps), WIDTH, int((i+1)*HEIGHT/steps),
                                         outline="", fill=color)

    # Menubar
    def _draw_menubar(self):
        self.canvas.create_rectangle(0,0,WIDTH,MENUBAR_H, fill=MENUBAR_BG, outline="#d8d8d8")
        # Apple menu trigger
        self._apple_text = self.canvas.create_text(10, MENUBAR_H//2, text="",
                                                   font=("Helvetica", 12, "bold"), anchor="w")
        self.canvas.tag_bind(self._apple_text, "<Button-1>", self._toggle_apple_menu)
        # App name
        self._app_label = self.canvas.create_text(28, MENUBAR_H//2, text=self.active_app,
                                                  font=("Helvetica", 10, "bold"), anchor="w")
        # Right clock
        self._clock_label = self.canvas.create_text(WIDTH-6, MENUBAR_H//2,
                                                    text=time.strftime("%a %H:%M"),
                                                    font=("Helvetica", 9), anchor="e")

        # Hidden Apple popup
        self._menu_frame = tk.Frame(self.root, bg=MENUPOP_BG, bd=1, relief="solid")
        def add_item(text, cmd=None):
            b = tk.Button(self._menu_frame, text=text, relief="flat", anchor="w",
                          bg=MENUPOP_BG, activebackground="#ececec", command=lambda: (self._hide_apple(), cmd and cmd()))
            b.pack(fill="x", padx=6, pady=2)
        add_item("About This Mac", self._about)
        add_item("—")
        add_item("Restart…", self._restart)
        add_item("Shut Down…", self._shutdown)
        add_item("Log Out catuser…", self._logout)
        self._menu_shown = False

    def _toggle_apple_menu(self, *_):
        if self._menu_shown:
            self._hide_apple()
        else:
            self._show_apple()

    def _show_apple(self):
        if self._menu_shown: return
        self._menu_shown = True
        self._menu_frame.place(x=4, y=MENUBAR_H+2, width=170)

    def _hide_apple(self):
        if not self._menu_shown: return
        self._menu_shown = False
        self._menu_frame.place_forget()

    def _about(self):
        messagebox.showinfo("About This Mac",
                            "Snow Leopard (sim)\nTkinter 600×400 desktop\n© 2025 CatGPT R1")

    def _restart(self):
        # simple reset to boot
        self._clear()
        self._boot_screen()

    def _shutdown(self):
        self.root.destroy()

    def _logout(self):
        self._login_screen()

    def set_active_app(self, name):
        self.active_app = name
        self.canvas.itemconfigure(self._app_label, text=name)

    def _tick_clock(self):
        if self.state != "desktop": return
        self.canvas.itemconfigure(self._clock_label, text=time.strftime("%a %H:%M"))
        self.root.after(1000, self._tick_clock)

    # Dock
    def _draw_dock(self):
        y0 = HEIGHT - DOCK_H
        self.canvas.create_rectangle(0, y0, WIDTH, HEIGHT, fill="#f4f4f4", outline="#d8d8d8")
        # App icons (emoji for simplicity)
        self.dock_icons = [
            {"name":"Finder", "emoji":"🗂", "cx":220, "cy":y0+30, "size":22},
            {"name":"Safari", "emoji":"🧭", "cx":270, "cy":y0+30, "size":22},
            {"name":"Notes",  "emoji":"📝", "cx":320, "cy":y0+30, "size":22},
        ]
        self._dock_items = []
        for icon in self.dock_icons:
            t_id = self.canvas.create_text(icon["cx"], icon["cy"], text=icon["emoji"],
                                           font=("Helvetica", icon["size"]))
            self._dock_items.append(t_id)
            icon["text_id"] = t_id
            # click binding
            self.canvas.tag_bind(t_id, "<Button-1>", lambda e, n=icon["name"]: self._dock_click(n))
        # Hover magnification
        self.canvas.bind("<Motion>", self._dock_hover)
        self.canvas.bind("<Leave>", lambda e: self._dock_reset())

    def _dock_hover(self, e):
        y0 = HEIGHT - DOCK_H
        if e.y < y0 or e.y > HEIGHT:  # only when over dock
            self._dock_reset(); return
        for icon in self.dock_icons:
            d = math.hypot(e.x - icon["cx"], e.y - icon["cy"])
            # Smooth bell-ish curve, radius ~ 80px
            scale = 1.0 + 0.9 * max(0.0, 1.0 - (d/80.0)**2)
            new_size = int(22 * scale)
            self.canvas.itemconfigure(icon["text_id"], font=("Helvetica", new_size))
            # lift slightly when larger
            self.canvas.coords(icon["text_id"], icon["cx"], (HEIGHT-DOCK_H)+30 - (new_size-22)*0.25)

    def _dock_reset(self):
        for icon in self.dock_icons:
            self.canvas.itemconfigure(icon["text_id"], font=("Helvetica", 22))
            self.canvas.coords(icon["text_id"], icon["cx"], (HEIGHT-DOCK_H)+30)

    def _dock_click(self, name):
        self.launch_app(name)
        # Bounce animation
        icon = next((i for i in self.dock_icons if i["name"]==name), None)
        if icon:
            self._bounce_icon(icon, phase=0)

    def _bounce_icon(self, icon, phase=0):
        # Simple up-down bounce
        tid = icon["text_id"]
        base_y = (HEIGHT-DOCK_H)+30
        offset = int(10 * math.sin(phase/2))
        self.canvas.coords(tid, icon["cx"], base_y - offset)
        if phase < 18:
            self.root.after(25, lambda: self._bounce_icon(icon, phase+1))
        else:
            self.canvas.coords(tid, icon["cx"], base_y)

    def notify_minimized(self, win):
        # Add a subtle dot under the app icon (not persistent; just a cue)
        icon = next((i for i in self.dock_icons if i["name"]==win.title), None)
        if not icon: return
        r = 3
        cx, cy = icon["cx"], HEIGHT - 8
        dot = self.canvas.create_oval(cx-r, cy-r, cx+r, cy+r, fill="#3aa3ff", outline="")
        self.root.after(700, lambda: self.canvas.delete(dot))

    # Desktop icons
    def _draw_desktop_icons(self):
        # (x,y) inside workspace
        items = [("Safari", "🧭", 60, WORK_Y+70, self.app_safari),
                 ("Finder", "🗂",  130, WORK_Y+70, self.app_finder),
                 ("Notes",  "📝",  200, WORK_Y+70, self.app_notes)]
        self.desktop_icons = []
        for name, emoji, x, y, fn in items:
            rect = self.canvas.create_rectangle(x-22, y-24, x+22, y+20, fill="#f0f0f0", outline="#a0a0a0")
            txt  = self.canvas.create_text(x, y-2, text=emoji, font=("Helvetica", 18))
            lbl  = self.canvas.create_text(x, y+30, text=name, font=("Helvetica", 9), fill=DESKTOP_LABEL)
            self.canvas.tag_bind(rect, "<Double-1>", lambda e, n=name: self.launch_app(n))
            self.canvas.tag_bind(txt,  "<Double-1>", lambda e, n=name: self.launch_app(n))
            self.canvas.tag_bind(lbl,  "<Double-1>", lambda e, n=name: self.launch_app(n))
            self.desktop_icons += [rect, txt, lbl]

    # ----- Window registry -----
    def register_window(self, win):
        self.windows.append(win)

    def unregister_window(self, win):
        if win in self.windows:
            self.windows.remove(win)

    def get_window(self, title):
        for w in self.windows:
            if w.title == title:
                return w
        return None

    # ----- App launchers -----
    def launch_app(self, name):
        # Restore if minimized / already exists
        existing = self.get_window(name)
        if existing:
            existing.restore(); existing.focus(); return

        # Build new
        if name == "Finder":
            builder = self.app_finder
            x,y,w,h = WORK_X+16, WORK_Y+12, 300, 210
        elif name == "Safari":
            builder = self.app_safari
            x,y,w,h = WORK_X+40, WORK_Y+24, 340, 230
        elif name == "Notes":
            builder = self.app_notes
            x,y,w,h = WORK_X+60, WORK_Y+36, 320, 200
        else:
            return
        win = DesktopWindow(self, name, x,y,w,h, builder)
        self.register_window(win)

    # ----- App UIs -----
    def app_finder(self, frame, win):
        frame.configure(bg="#fbfbfb")
        sidebar = tk.Listbox(frame, height=10)
        for f in ["Favorites", "—", "AirDrop", "Applications", "Desktop", "Documents",
                  "Downloads", "Movies", "Music", "Pictures"]:
            sidebar.insert("end", f)
        sidebar.place(x=6, y=6, width=110, height=win.h-40)
        # Main area
        header = tk.Label(frame, text="Finder — Your Files", bg="#fbfbfb", anchor="w")
        header.place(x=122, y=6, width=win.w-140, height=24)
        area = tk.Listbox(frame)
        for item in ["Applications", "Documents", "Downloads", "Pictures", "Music"]:
            area.insert("end", f"📁 {item}")
        area.place(x=122, y=34, width=win.w-140, height=win.h-70)

    def app_safari(self, frame, win):
        frame.configure(bg="#ffffff")
        url = tk.Entry(frame, relief="sunken")
        url.insert(0, "https://www.apple.com/mac-osx/snow-leopard/")
        url.place(x=6, y=6, width=win.w-90, height=22)
        go = tk.Button(frame, text="Go", command=lambda: self._safari_load(url.get(), out))
        go.place(x=win.w-78, y=5, width=70, height=24)
        out = scrolledtext.ScrolledText(frame, wrap="word")
        out.place(x=6, y=34, width=win.w-12, height=win.h-66)
        out.insert("end",
                   "Safari Preview (offline)\n\n"
                   "This is a lightweight, text-only preview pane.\n"
                   "Network fetches are not performed in this demo.\n\n"
                   "Tip: Click the green button to zoom the window; "
                   "yellow to minimize to the dock; red to close.\n")

    def _safari_load(self, url, out):
        out.delete("1.0", "end")
        out.insert("end", f"Loading (simulated): {url}\n\n")
        out.insert("end",
                   "macOS Snow Leopard (2009): performance, polish, and subtlety.\n"
                   "This simulator mimics the spirit — not the full functionality — of Safari.\n")

    def app_notes(self, frame, win):
        frame.configure(bg="#fffef8")
        lbl = tk.Label(frame, text="Notes", anchor="w", bg="#fffef8")
        lbl.place(x=6, y=6, width=win.w-12, height=20)
        txt = scrolledtext.ScrolledText(frame, wrap="word", bg="#fffef8")
        txt.place(x=6, y=28, width=win.w-12, height=win.h-54)
        txt.insert("end", "Welcome back to Snow Leopard.\n\nType your notes here… 🐾")

# ---------------------------- Run ----------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = SnowLeopardOS(root)
    root.mainloop()
