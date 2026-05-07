from maix import camera, display, image, app, touchscreen, time
import cv2
import numpy as np

cam = camera.Camera(320, 240)
disp = display.Display()
ts  = touchscreen.TouchScreen()

th1, th2 = 50, 150
kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))

while not app.need_exit():
    img  = cam.read()

    # 1. OpenCV 处理
    img_cv = image.image2cv(img, ensure_bgr=False, copy=True)
    gray   = cv2.cvtColor(img_cv, cv2.COLOR_RGB2GRAY)
    blur   = cv2.GaussianBlur(gray, (5, 5), 0)
    edge   = cv2.Canny(blur, th1, th2)
    closed = cv2.morphologyEx(edge, cv2.MORPH_CLOSE, kernel, 1)

    # 2. 找最大矩形
    cnts, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    out = img.copy()                       # 在副本上画框
    if cnts:
        largest = max(cnts, key=cv2.contourArea)
        peri    = 0.02 * cv2.arcLength(largest, True)
        approx  = cv2.approxPolyDP(largest, peri, True)
        if len(approx) == 4:
            pts = approx.reshape(-1, 2)
            for i in range(4):
                out.draw_line(int(pts[i][0]), int(pts[i][1]),
                              int(pts[(i+1)%4][0]), int(pts[(i+1)%4][1]),
                              image.COLOR_GREEN, 2)

    # 3. 转回 MaixPy Image
    canny_show = image.cv2image(edge,   bgr=False, copy=True)
    closed_show= image.cv2image(closed, bgr=False, copy=True)

    # 4. 文字提示
    canny_show.draw_string(5, 5, f"th1:{th1}", image.COLOR_RED, scale=1.5)
    closed_show.draw_string(5, 5, "closed", image.COLOR_GREEN, scale=1.2)

    # 5. 三图并排
    vis = image.Image(img.width()*3, img.height())
    vis.draw_image(0, 0, out)                # ← 这里换成画了框的 out
    vis.draw_image(img.width(), 0, canny_show)
    vis.draw_image(img.width()*2, 0, closed_show)
    disp.show(vis)

    # 6. 触屏调参
    x, y, p = ts.read()
    if p:
        th1 = max(10, min(240, th1 + (5 if y > 120 else -5)))
        time.sleep_ms(100)
