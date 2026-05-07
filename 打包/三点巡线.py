################################################################################
#三点法巡线
################################################################################
from maix import camera, display, image,time,app 
from maix.v1.machine import UART
import math
import struct
########################串口UART初始化################################
uart = UART("/dev/ttyS0", 115200)
time.sleep_ms(100) # wait uart ready
#uart.write(b'hello zpc')
################################摄像头初始化################################
cam = camera.Camera(320, 240)    #灰度化
disp = display.Display()
 
Threshold=[[0, 31, -2, 21, -30, 2]]                 #黑色路线阈值，可使用MaixCAM拍照，将照片放在OpenMv-IDE里去调阈值
 
 
#//这个ROI区域根据自己的实际情况去改变
 
ROIS=[(0,20,360,60,0.2),                            #上
        (0,90,360,60,0.4),                          #中
        (0,170,360,50,0.9)]                         #下
weight_sum = 0
for r in ROIS: weight_sum += r[4]                   #权重
 
 
line_rho=0                                          #偏移量
################################巡线################################
 
def car_run():
    global line_rho
    line_rho=0                                                                  
    line_blobs=[]                                                           #色块存放的列表
    centroid_sum = 0                                                        #权重
    for r in ROIS:
        blobs= img.find_blobs(Threshold, roi=r[0:4], merge=True,pixels_threshold=150)
        if blobs:
            for b in blobs:
                line_blobs.append(b)                                        #加入 line_blobs 列表
                centroid_sum += b.cx() * r[4]                               #计算centroid_sum，centroid_sum等于
                                                                            #每个区域的色块的中心点的x坐标值乘
 
                                                                            #本区域的权值
    line_rho = int(centroid_sum / weight_sum)                               #中间值公式
 
    #用于调试
    img.draw_string(0,30,' rho= '+str(line_rho),image.COLOR_WHITE)
 
    return line_blobs
 
 
#标记函数
def Mark(Line):
    for b in Line:
        img.draw_rect(b.x(),b.y(),b.w(),b.h(),color=image.COLOR_WHITE)
        img.draw_cross(b.cx(),b.cy(),image.Color.from_rgb(255, 255, 255), size=5, thickness=1)
 
 
################################发送数据################################
def Uart_Send(rho):
    # 文本模式发送，格式："值\n"
    data = f"{rho}\n".encode('utf-8')
    uart.write(data)
    print(data)
line_element=[]
while not app.need_exit():
    t = time.time_ms()
    img=cam.read()
 
    line_element=car_run()
 
    Mark(line_element)
 
    #数据发送
    Uart_Send(line_rho)
    
    #屏幕显示
    disp.show(img)
    #打印帧率
   # print("FPS= ",int(1000 / (time.time_ms() - t)))