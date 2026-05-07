from maix import image,camera,display
import cv2


cam  = camera.Camera(320,240,fps=60)
disp = display.Display()



kernel  = cv2.getStructuringElement(cv2.MORPH_RECT, (4, 4))
while True:
    img=cam.read()
    img_raw=image.image2cv(img,copy=False)#转cv
    img=cv2.cvtColor(img_raw,cv2.COLOR_BGR2GRAY)#灰度
    img = cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                                cv2.THRESH_BINARY, 11, 2)
    #img=cv2.bilateralFilter(img,10,9,10)#双边滤波
   
    img =cv2.morphologyEx(img,cv2.MORPH_CLOSE,kernel)#闭运算（先膨胀后腐蚀）
    edged = cv2.Canny(img, 30, 160)#轮廓
    img_show=image.cv2image(edged ,copy=False)
    disp.show(img_show)