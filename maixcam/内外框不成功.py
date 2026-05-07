from maix import camera, display, image  # 导入 Maix 平台摄像头、显示及图像处理模块
import cv2                              # 导入 OpenCV 计算机视觉库

# 实例化摄像头并设置分辨率（不同 Maix 设备可能需调整参数）
cam = camera.Camera(320, 240)

# 实例化显示对象（用于在开发板屏幕或外接显示设备输出图像）
disp = display.Display()

# 创建闭运算结构元素（3x3矩形核），用于形态学操作填充小空洞
kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))

while True:
    # 从摄像头捕获一帧图像
    img = cam.read()  
    # 将 Maix 图像格式转换为 OpenCV 可用的 numpy 数组格式
    img_raw = image.image2cv(img, copy=False)  

    # 颜色空间转换：从 BGR 彩色转为灰度图（单通道）
    img = cv2.cvtColor(img_raw, cv2.COLOR_BGR2GRAY)
    
    # 双边滤波：保留边缘的同时平滑图像（参数说明：
    # - 9：滤波核直径
    # - 10：颜色空间滤波器标准差
    # - 10：坐标空间滤波器标准差）
    #img = cv2.bilateralFilter(img, 9, 10, 10)
    
    # 形态学闭运算：先膨胀后腐蚀，用于填充前景物体内部的小孔洞
    img = cv2.morphologyEx(img, cv2.MORPH_CLOSE, kernel)
    
    # Canny 边缘检测（参数说明：
    # - 50：低阈值，用于边缘连接
    # - 150：高阈值，用于检测明显边缘）
    edged = cv2.Canny(img, 60, 150)
    
    # 将边缘检测结果转换回 Maix 图像格式并显示
    img_show = image.cv2image(edged, copy=False)  
    disp.show(img_show)
    
    # 轮廓检测（参数说明：
    # - cv2.RETR_TREE：检索所有轮廓并重建嵌套轮廓层次
    # - cv2.CHAIN_APPROX_SIMPLE：仅保留轮廓的端点）
    contours, _ = cv2.findContours(edged, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    # 遍历所有检测到的轮廓
    for contour in contours:
        # 计算轮廓周长并基于周长确定多边形逼近的精度（0.02为经验因子）
        epsilon = 0.02 * cv2.arcLength(contour, True)
        
        # 多边形逼近：用指定精度的多边形近似表示曲线轮廓
        approx = cv2.approxPolyDP(contour, epsilon, True)

        # 仅处理边数≥3的多边形（过滤噪声点）
        if len(approx) >= 3:
            # 在原始图像上绘制多边形轮廓（颜色：绿，线宽：2px）
            cv2.drawContours(img_raw, [approx], 0, (0, 255, 0), 2)
            
            # 遍历多边形的每个顶点
            for point in approx:
                # 提取顶点坐标
                x, y = point.ravel()
                # 在顶点位置绘制蓝色标记点（半径：5px，线宽：1px）
                cv2.circle(img_raw, (x, y), 5, (255, 0, 0), 1)

    # 注释掉的代码：若取消注释将显示带轮廓和顶点标记的原图
    # img_show = image.cv2image(img_raw, copy=False)  
    # disp.show(img_show)
