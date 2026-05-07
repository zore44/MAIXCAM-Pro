from maix import image, camera, display, app, time
import cv2
import numpy as np

cam = camera.Camera(320, 240, fps=80)
disp = display.Display()

STEP = 8   # 每隔 8 像素画一个红点

while not app.need_exit():
    img = cam.read()

    # 1. 灰度 → 高斯 → Canny
    img_cv = image.image2cv(img, ensure_bgr=True, copy=True)
    gray = cv2.cvtColor(img_cv, cv2.COLOR_RGB2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edge = cv2.Canny(blur, 50, 150)

    # 2. 把边缘图转 3 通道，背景黑，边缘白
    edge_rgb = cv2.cvtColor(edge, cv2.COLOR_GRAY2BGR)

    # 3. 取所有白色像素坐标
    ys, xs = np.where(edge == 255)
    points = list(zip(xs, ys))

    # 4. 每隔 STEP 个点画一个红点
    for i in range(0, len(points), STEP):
        x, y = points[i]
        cv2.circle(edge_rgb, (x, y), 1, (0, 0, 255), -1)

    # 5. 显示
    img_show = image.cv2image(edge_rgb, bgr=True, copy=False)
    disp.show(img_show)

    fps = time.fps()
    print(f"time: {1000/fps:.02f}ms, fps: {fps:.02f}")
