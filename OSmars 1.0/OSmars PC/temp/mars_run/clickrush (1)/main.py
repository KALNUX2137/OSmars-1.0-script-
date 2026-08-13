#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OSmars Click Rush — prosta mini-gra (tkinter, bez dodatkowych bibliotek)."""
import random
import time
import tkinter as tk
from tkinter import font as tkfont


class ClickRush:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🪐 OSmars Click Rush")
        self.root.geometry("480x360")
        self.root.configure(bg="#0b0b12")
        self.root.resizable(False, False)

        self.score = 0
        self.time_left = 20.0
        self.running = False
        self.target = None
        self._tick_job = None

        title_font = tkfont.Font(family="Segoe UI", size=18, weight="bold")
        ui_font = tkfont.Font(family="Segoe UI", size=12)

        self.lbl_title = tk.Label(
            self.root, text="Click Rush", fg="#a78bfa", bg="#0b0b12", font=title_font
        )
        self.lbl_title.pack(pady=(16, 4))

        self.lbl_info = tk.Label(
            self.root,
            text="Klikaj fioletowe cele! Masz 20 sekund.",
            fg="#c4b5fd",
            bg="#0b0b12",
            font=ui_font,
        )
        self.lbl_info.pack()

        self.hud = tk.Label(
            self.root, text="Score: 0   |   Time: 20.0",
            fg="#e9d5ff", bg="#0b0b12", font=ui_font
        )
        self.hud.pack(pady=6)

        self.canvas = tk.Canvas(
            self.root, width=440, height=220,
            bg="#14141f", highlightthickness=1, highlightbackground="#4c1d95"
        )
        self.canvas.pack(pady=8)

        self.btn = tk.Button(
            self.root, text="▶ Start", command=self.start,
            bg="#7c3aed", fg="white", activebackground="#6d28d9",
            relief="flat", padx=16, pady=6, font=ui_font
        )
        self.btn.pack(pady=8)

        self.root.protocol("WM_DELETE_WINDOW", self.root.destroy)

    def start(self):
        if self.running:
            return
        self.score = 0
        self.time_left = 20.0
        self.running = True
        self.btn.config(state="disabled", text="Gra…")
        self.canvas.delete("all")
        self.spawn_target()
        self.tick()

    def tick(self):
        if not self.running:
            return
        self.time_left -= 0.1
        if self.time_left <= 0:
            self.time_left = 0
            self.finish()
            return
        self.hud.config(text=f"Score: {self.score}   |   Time: {self.time_left:.1f}")
        self._tick_job = self.root.after(100, self.tick)

    def spawn_target(self):
        self.canvas.delete("target")
        r = 18
        x = random.randint(r + 4, 440 - r - 4)
        y = random.randint(r + 4, 220 - r - 4)
        self.target = self.canvas.create_oval(
            x - r, y - r, x + r, y + r,
            fill="#8b5cf6", outline="#c4b5fd", width=2, tags="target"
        )
        self.canvas.tag_bind("target", "<Button-1>", self.on_hit)

    def on_hit(self, _event=None):
        if not self.running:
            return
        self.score += 1
        self.hud.config(text=f"Score: {self.score}   |   Time: {self.time_left:.1f}")
        self.spawn_target()

    def finish(self):
        self.running = False
        self.canvas.delete("all")
        self.canvas.create_text(
            220, 100, text=f"Koniec!\nScore: {self.score}",
            fill="#e9d5ff", font=("Segoe UI", 20, "bold"), justify="center"
        )
        self.btn.config(state="normal", text="▶ Jeszcze raz")
        self.hud.config(text=f"Score: {self.score}   |   Time: 0.0")

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    ClickRush().run()
