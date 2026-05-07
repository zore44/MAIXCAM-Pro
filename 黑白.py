from maix import image, camera, display, app, uart, time # MaixPy 核心库
import cv2          # OpenCV 视觉库
import numpy as np  # NumPy 数值计算库
from struct import pack # 用于将数据打包成二进制格式进行串口通信
# 面积过滤器：只处理面积在这个范围内的轮廓
MIN_AREA = 200
MAX_AREA = 800


cam = camera.Camera(320, 240, fps=80)
disp = display.Display()


while not app.need_exit():
    img = cam.read()
    img_raw = image.image2cv(img, copy=True)                
    gray = cv2.cvtColor(img_raw, cv2.COLOR_BGR2GRAY)
                # b. 预处理：自适应二值化。能很好地适应光照不均的情况。
    bin_img = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C ,
                                                cv2.THRESH_BINARY, 11, 2)
    # 构造腐蚀核（3x3 矩形）
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
    eroded = cv2.erode(bin_img, kernel, iterations=2)
    dilated = cv2.dilate(eroded, kernel, iterations=1)  # 恢复主干厚度
 

    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)


    for contour in contours:
                    # f. 过滤：面积太小或太大的轮廓直接跳过
        area = cv2.contourArea(contour)
        if not (MIN_AREA <= area <= MAX_AREA):
            continue                   
                    # g. 过滤：完全贴边的轮廓可能是干扰，跳过
        x, y, w, h = cv2.boundingRect(contour)
        margin = 1
        if x < margin or y < margin or x + w > img_raw.shape[1] - margin or y + h > img_raw.shape[0] - margin:
            continue
    # 1. 把 dilated（单通道）转成 OpenCV 三通道
    dilated_bgr = cv2.cvtColor(dilated, cv2.COLOR_GRAY2BGR)

# 2. 画轮廓（绿色线宽 2）
    cv2.drawContours(dilated_bgr, contours, -1, (0, 255, 0), 2)

#3. 再转回 Maix 的 Image 对象并显示
    img_show = image.cv2image(dilated_bgr, copy=False)
    disp.show(img_show)


           

                