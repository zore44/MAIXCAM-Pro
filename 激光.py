#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# MaixCAM-Pro : 摄像头 -> OpenCV -> 显示

from maix import camera, display, image,app
import cv2
import numpy as np

# ---------------- 摄像头/显示 ----------------
cam = camera.Camera(320, 240, fps=90)   # 分辨率、帧率随意
disp = display.Display()

# ---------------- 激光检测函数（纯 OpenCV） ----------------
def detect_red_laser(frame_bgr):
    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
    # 红色激光在 HSV 的两个区间
    mask1 = cv2.inRange(hsv, (0,  50, 170), (10, 255, 255))
    mask2 = cv2.inRange(hsv, (170,50, 170), (180,255, 255))
    mask = cv2.bitwise_or(mask1, mask2)
    # 开运算去噪
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3,3))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, 1)
    # 找最大轮廓
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL,
                               cv2.CHAIN_APPROX_SIMPLE)
    if cnts:
        c = max(cnts, key=cv2.contourArea)
        if cv2.contourArea(c) > 3:          # 过滤噪点
            M = cv2.moments(c)
            cx, cy = int(M['m10']/M['m00']), int(M['m01']/M['m00'])
            cv2.drawMarker(frame_bgr, (cx, cy), (0,255,0),
                           markerType=cv2.MARKER_CROSS, thickness=2)
    return frame_bgr

# ---------------- 主循环 ----------------
while not app.need_exit():
    img = cam.read()                    # Maix 原生 image 对象
    if not img:
        continue

    # ① 摄像头 -> OpenCV (numpy.ndarray, BGR)
    img_bgr = image.image2cv(img, ensure_bgr=True, copy=True)

    # ② 任意 OpenCV 处理
    img_bgr = detect_red_laser(img_bgr)

    # ③ OpenCV -> Maix 图像 -> 显示
    img2 = image.cv2image(img_bgr, bgr=True, copy=True)
    disp.show(img2)
