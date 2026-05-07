#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from maix import camera, display, image, app

# ---------- 读取阈值 ---------- #
def load_threshold():
    try:
        with open("/root/threshold.txt", "r") as f:
            thr = list(map(int, f.read().strip().split(",")))
            print("Loaded threshold:", thr)
            return thr
    except:
        print("No threshold file found, using default.")
        return [0, 255, 0, 255, 0, 255]

thr = load_threshold()
Lmin, Lmax, amin, amax, bmin, bmax = thr

# ---------- 主循环 ---------- #
while not app.need_exit():
    img = camera.capture()

    # 转换为 Lab 并二值化
    lab = img.copy()
    lab.to_lab()
    mask = lab.in_range((Lmin, amin, bmin), (Lmax, amax, bmax))

    # 显示原图 + 二值化结果
    scr = display.Display()
    scr.draw_image(img, 0, 0)
    scr.draw_image(mask, img.width(), 0)
    scr.show()
