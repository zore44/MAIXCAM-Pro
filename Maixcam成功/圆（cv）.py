from maix import camera, display, image, app
import cv2
import numpy as np

cam = camera.Camera(320, 240, image.Format.FMT_BGR888)   # 直接出 BGR
disp = display.Display()

while not app.need_exit():
    img = cam.read()
    frame = image.image2cv(img, ensure_bgr=True, copy=False)  # → numpy.ndarray

    # 灰度
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # 高斯模糊去噪
    blur = cv2.GaussianBlur(gray, (9, 9), 2)

    # ★ 霍夫圆检测（非传统 HoughCircles）
    circles = cv2.HoughCircles(
        blur,
        cv2.HOUGH_GRADIENT,
        dp=2,
        minDist=40,      # 圆心最小间距
        param1=50,       # Canny 高阈值
        param2=30,       # 累加器阈值（越小越敏感）
        minRadius=5,     # 圆最小半径
        maxRadius=80     # 圆最大半径
    )

    # 画圆
    if circles is not None:
        circles = np.uint16(np.around(circles))
        for (x, y, r) in circles[0, :]:
            cv2.circle(frame, (x, y), r, (0, 255, 0), 2)
            cv2.circle(frame, (x, y), 2, (0, 0, 255), 3)

    # numpy → maix.Image → 显示
    disp.show(image.cv2image(frame, bgr=True, copy=False))
