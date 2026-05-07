from maix import image, camera, display
import cv2
import numpy as np
# --- 1. 初始化 (保持不变) ---
cam  = camera.Camera(320, 240, fps=60)
disp = display.Display()
kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (4, 4))

while True:
    # a. b. c. d. e. f. (图像获取和预处理部分，保持不变)
    img_a = cam.read()
    if not img_a:
        continue
    img_raw = image.image2cv(img_a, copy=False)
    img = cv2.cvtColor(img_raw, cv2.COLOR_BGR2GRAY)
    img = cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                cv2.THRESH_BINARY, 11, 2)
    img = cv2.morphologyEx(img, cv2.MORPH_CLOSE, kernel)
    edged = cv2.Canny(img, 30, 160)
  
 

    
    # g. 在边缘图上寻找轮廓 (保持不变)
    contours, _ = cv2.findContours(edged, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    # =================================================================
    # --- 【核心修改部分】 ---
    # =================================================================
    
    # 【新增】初始化“擂主”变量
    biggest_contour = None # 用于存储面积最大的轮廓
    max_area = 0           # 用于存储最大面积的值

    # h. 遍历所有找到的轮廓，进行“打擂”
    for contour in contours:
        # i. 对轮廓进行多边形逼近 (保持不变)
        epsilon = 0.005 * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)
        
        # j. 筛选出四边形 (保持不变)
        if len(approx) == 4:
            # 【新增】计算当前四边形的面积
            current_area = cv2.contourArea(approx)
            
            # 【新增】“打擂”逻辑：如果当前面积比记录的最大面积还大
            if current_area > max_area:
                # 它就成为新的擂主！
                max_area = current_area
                biggest_contour = approx

    # 【修改】在循环结束后，才对唯一的“擂主”进行绘制
    # k. 检查擂主是否存在
    if biggest_contour is not None:
        # l. 计算擂主的外接矩形（改为旋转矩形）
        rect = cv2.minAreaRect(biggest_contour)  # 获取最小外接旋转矩形
        box = cv2.boxPoints(rect)  # 将旋转矩形转换为四个顶点坐标
        box = np.int0(box)  # 转换为整数坐标
        
        # m. 在“彩色原件” img_raw 上绘制旋转矩形
        cv2.drawContours(img_raw, [box], 0, (255, 0, 0), 3)  # 绘制旋转矩形
    
    # n. 将绘制好矩形的“彩色原件”转换并显示
    img_show = image.cv2image(img_raw, copy=False)
    disp.show(img_show)
