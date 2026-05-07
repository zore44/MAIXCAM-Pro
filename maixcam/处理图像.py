from maix import image, camera, display
import cv2

# --- 1. 初始化 ---
cam  = camera.Camera(320, 240, fps=60)
disp = display.Display()

# 创建一个形态学操作的核，4x4 大小
kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (4, 4))

while True:
    # a. 获取原始 MaixPy 图像
    img_a = cam.read()
    if not img_a:
        continue

    # b. 转换为 OpenCV 的“彩色原件” (img_raw)
    img_raw = image.image2cv(img_a, copy=False)

    # --- 在“复印件”上进行计算 ---
    # c. 创建“黑白复印件” (img) 用于处理
    img = cv2.cvtColor(img_raw, cv2.COLOR_BGR2GRAY)
    
    # d. 自适应二值化
    img = cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                cv2.THRESH_BINARY, 11, 2)
    
    # e. 闭运算，连接线条
    img = cv2.morphologyEx(img, cv2.MORPH_CLOSE, kernel)
    
    # f. Canny 边缘检测
    edged = cv2.Canny(img, 30, 160)
    img_show = image.cv2image(edged, copy=False)
    disp.show(img_show)
    # # g. 在边缘图上寻找轮廓
    # contours, _ = cv2.findContours(edged, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    # # --- 在“原件”上进行绘制 ---
    # # h. 遍历所有找到的轮廓
    # for contour in contours:
    #     # i. 对轮廓进行多边形逼近
    #     epsilon = 0.02 * cv2.arcLength(contour, True)
    #     approx = cv2.approxPolyDP(contour, epsilon, True)
        
    #     # j. 筛选出顶点数大于等于3的多边形
    #     if len(approx) == 4:  
    #         # k. 计算外接矩形
    #         x, y, w, h = cv2.boundingRect(approx)
            
    #         # l. 【核心修正】在“彩色原件” img_raw 上绘制蓝色的矩形！
    #         cv2.rectangle(img_raw, (x, y), (x + w, y + h), (255, 0, 0), 3)  
    
    # # m. 将绘制好矩形的“彩色原件”转换并显示
    # img_show = image.cv2image(img_raw, copy=False)
    # disp.show(img_show)
