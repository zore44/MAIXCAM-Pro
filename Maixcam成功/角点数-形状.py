from maix import image, camera, display, app, time
import numpy as np 
import cv2

kernel = np.ones((3,3), np.uint8) #创建核
cam = camera.Camera(320,224,fps=60) #初始化相机
disp = display.Display() #初始化显示屏

while not app.need_exit():
    #t = time.ticks_ms()

    img = cam.read() #从摄像机获取一帧图像
    img = img.lens_corr(strength=1.5) #从摄像机获取一帧图像
    img_raw = image.image2cv(img) #将图像转换为cv2格式

    img = cv2.cvtColor(img_raw, cv2.COLOR_BGR2GRAY) #转换为灰度模式
    img = cv2.bilateralFilter(img, 9, 75, 75) #双边滤波(去噪点)
    img = cv2.morphologyEx(img, cv2.MORPH_CLOSE, kernel) #闭运算(去噪点)
    #_, thresh = cv2.threshold(edged, 127, 255, cv2.THRESH_BINARY) #二值化
    edged = cv2.Canny(img, 200, 600) #Canny找边缘
    contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE) #findContours找角点
    for contour in contours:  #遍历找到的角点
        epsilon = 0.01 * cv2.arcLength(contour, True) #计算像素
        approx = cv2.approxPolyDP(contour, epsilon, True) #approxPolyDP逼近多边形
        if len(approx) >= 3:  #如果角点数>=3
            print("这是一个"+str(len(approx))+"边形") 
            cv2.drawContours(img_raw, [approx], 0, (0, 255, 0), 3) #drawContours画出轮廓
            for point in approx:   #遍历每个多边形角点
                x, y = point.ravel() #获取每个多边形角点坐标
                cv2.circle(img_raw,(x,y),5,(255,0,0),2) #circle画出多边形角点

    img_show = image.cv2image(img_raw) #将图像转换为maix格式
    disp.show(img_show) #使用屏幕显示该图像

    #print(f"time: {time.ticks_ms() - t}ms, fps: {1000 / (time.ticks_ms() - t)}")