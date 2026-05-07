from maix import image, camera, display, app, uart, time # MaixPy 核心库
import cv2          # OpenCV 视觉库
import numpy as np  # NumPy 数值计算库

cam = camera.Camera(320, 240, fps=80)
disp = display.Display()


while not app.need_exit():
    img = cam.read()
    img_cv = image.image2cv(img, ensure_bgr=True, copy=True)
    gray   = cv2.cvtColor(img_cv, cv2.COLOR_RGB2GRAY)
    blur   = cv2.GaussianBlur(gray, (5,5), 0)
    # kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    # closing = cv2.morphologyEx(blur, cv2.MORPH_CLOSE, kernel)
    edge   = cv2.Canny(blur, 50, 150)
        # Shi-Tomasi 角点检测
    #corners = cv2.goodFeaturesToTrack(blur, maxCorners=50, qualityLevel=0.1, minDistance=10)
    
    # 将角点绘制到图像上
    # if corners is not None:
    #     corners = np.int0(corners)
    #     for i in corners:
    #         x, y = i.ravel()
    #         cv2.circle(img_cv, (x, y), 3, (0, 0, 255), -1)  # 红色圆点标记角点
    # img_show = image.cv2image(img_cv, copy=False)
    # disp.show(img_show)
    
    # #cnts,_ = cv2.findContours(edge, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)#轮廓
    img_show = image.cv2image(edge, copy=False)
    disp.show(img_show)
    fps = time.fps()            
    print(f"time: {1000/fps:.02f}ms, fps: {fps:.02f}")
    
    
    
    
    
    
    # contours, _ = cv2.findContours(edge, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE) #findContours找角点
    # for contour in contours:  #遍历找到的角点
    #     epsilon = 0.01 * cv2.arcLength(contour, True) #计算像素
    #     approx = cv2.approxPolyDP(contour, epsilon, True) #approxPolyDP逼近多边形
    #     if len(approx) >= 3:  #如果角点数>=3
    #         print("这是一个"+str(len(approx))+"边形") 
    #         cv2.drawContours(img_cv, [approx], 0, (0, 255, 0), 3) #drawContours画出轮廓
    #         for point in approx:   #遍历每个多边形角点
    #             x, y = point.ravel() #获取每个多边形角点坐标
    #             cv2.circle(img_cv,(x,y),5,(255,0,0),2) #circle画出多边形角点
    # img_show = image.cv2image(img_cv,bgr=True,copy=True) #将图像转换为maix格式
    # disp.show(img_show) #使用屏幕显示该图像





    
 



