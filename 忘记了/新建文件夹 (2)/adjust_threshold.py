#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, gc, math
from maix import camera, display, image, nn, app, touchscreen, widget

# ---------- UI ---------- #
scr = display.Display()
ts  = touchscreen.TouchScreen()

# 六个通道按钮
btn_w, btn_h = 120, 60
btn_x, btn_y = 10, 40
btns = []
channels = ["Lmin","Lmax","amin","amax","bmin","bmax"]
for i in range(6):
    y = btn_y + i*(btn_h+5)
    btns.append((btn_x, y, btn_w, btn_h, channels[i]))

# 滑块
slider_x, slider_y = 10, 450
slider_w, slider_h = 300, 30
slider_val = 0        # 0-255

# 开关：二值化预览
switch_w, switch_h = 100, 50
switch_x, switch_y = scr.width()-switch_w-10, 100
switch_state = False

# OK 按钮
ok_w, ok_h = 100, 60
ok_x, ok_y = scr.width()-ok_w-10, scr.height()-ok_h-10

# ---------- 阈值 ---------- #
thr = [0,255, 0,255, 0,255]   # Lmin,Lmax,amin,amax,bmin,bmax
sel_idx = 0                   # 当前选中的通道索引

# ---------- 颜色转换 ---------- #
def rgb2lab(r,g,b):
    # 简化版：只做近似转换，满足调节即可
    def f(t):
        t = t/255.0
        if t > 0.04045:
            t = pow((t+0.055)/1.055, 2.4)
        else:
            t = t/12.92
        return t*100.0

    R = f(r)
    G = f(g)
    B = f(b)

    X = R*0.4124 + G*0.3576 + B*0.1805
    Y = R*0.2126 + G*0.7152 + B*0.0722
    Z = R*0.0193 + G*0.1192 + B*0.9505

    X /= 95.047
    Y /= 100.0
    Z /= 108.883

    def f2(t):
        if t > 0.008856:
            return pow(t, 1/3)
        else:
            return 7.787*t + 16/116

    fx = f2(X)
    fy = f2(Y)
    fz = f2(Z)

    L = 116*fy - 16
    a = 500*(fx - fy)
    b = 200*(fy - fz)

    return int(L), int(a), int(b)

# ---------- 保存阈值 ---------- #
def save_threshold():
    with open("/root/threshold.txt","w") as f:
        f.write(",".join(map(str, thr)))
    print("Threshold saved:", thr)

# ---------- 读取阈值 ---------- #
def load_threshold():
    global thr
    try:
        with open("/root/threshold.txt","r") as f:
            thr = list(map(int, f.read().strip().split(",")))
            print("Loaded threshold:", thr)
    except:
        pass
load_threshold()

# ---------- 主循环 ---------- #
while not app.need_exit():
    img = camera.capture()

    # 计算中心点 Lab
    cx, cy = img.width()//2, img.height()//2
    rgb = img.get_pixel(cx, cy)
    L,a,b = rgb2lab(rgb[0], rgb[1], rgb[2])

    # UI 绘制
    scr.draw_image(img, 0, 0)

    # 绘制按钮
    for i,(x,y,w,h,name) in enumerate(btns):
        color = (0,255,0) if i==sel_idx else (255,255,255)
        scr.draw_rect(x,y,w,h,color=color, thickness=2)
        scr.draw_string(x+5, y+20, name, color=color, scale=1.5)

    # 滑块
    scr.draw_rect(slider_x, slider_y, slider_w, slider_h, color=(100,100,100), thickness=1)
    pos = int(thr[sel_idx]/255.0*slider_w)
    scr.draw_rect(slider_x+pos-5, slider_y-5, 10, slider_h+10, color=(0,255,255), thickness=-1)

    # 实时值 & 阈值
    scr.draw_string(scr.width()//2-80, 10, f"LAB: {L},{a},{b}", color=(0,255,255), scale=2)
    scr.draw_string(scr.width()//2-80, 40, "Thr: "+",".join(map(str,thr)), color=(255,255,0), scale=1.8)

    # 开关
    scr.draw_rect(switch_x, switch_y, switch_w, switch_h, color=(0,255,0) if switch_state else (100,100,100), thickness=-1)
    scr.draw_string(switch_x+10, switch_y+15, "Bin", color=(0,0,0), scale=1.8)

    # OK
    scr.draw_rect(ok_x, ok_y, ok_w, ok_h, color=(0,255,0), thickness=-1)
    scr.draw_string(ok_x+25, ok_y+20, "OK", color=(0,0,0), scale=2)

    # 二值化预览
    if switch_state:
        mask = img.copy()
        mask.to_lab()
        mask.in_range((thr[0],thr[2],thr[4]), (thr[1],thr[3],thr[5]))
        scr.draw_image(mask, scr.width()-mask.width()//2-10, 200)

    scr.show()

    # ---------- 触摸事件 ---------- #
    x, y, pressed = ts.read()
    if pressed:
        # 按钮
        for i,(bx,by,bw,bh,_) in enumerate(btns):
            if bx<=x<=bx+bw and by<=y<=by+bh:
                sel_idx = i
                slider_val = thr[sel_idx]

        # 滑块
        if slider_x<=x<=slider_x+slider_w and slider_y<=y<=slider_y+slider_h:
            val = max(0, min(255, int((x-slider_x)/slider_w*255)))
            thr[sel_idx] = val

        # 开关
        if switch_x<=x<=switch_x+switch_w and switch_y<=y<=switch_y+switch_h:
            switch_state = not switch_state

        # OK
        if ok_x<=x<=ok_x+ok_w and ok_y<=y<=ok_y+ok_h:
            save_threshold()
            app.set_exit()

    gc.collect()
