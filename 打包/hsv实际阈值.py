from maix import camera, display, image
import time

cam = camera.Camera(320, 240)
disp = display.Display()

# 参数配置
area_threshold = 1000
pixels_threshold = 1000
thresholds = [[0, 80, 40, 80, 10, 80]]  # 红色阈值

# 阈值参数文本
threshold_text = f"HSV阈值: H({thresholds[0][0]}-{thresholds[0][1]}), S({thresholds[0][2]}-{thresholds[0][3]}), V({thresholds[0][4]}-{thresholds[0][5]})"

def get_color_type(h, s, v):
    """根据HSV值判断颜色类型"""
    if (h < 10 or h > 170) and s > 50:  # 红色
        return "Red"
    elif 35 < h < 85 and s > 50:  # 绿色
        return "Green"
    elif 85 < h < 135 and s > 50:  # 蓝色
        return "Blue"
    else:
        return "Other"

try:
    while True:
        img = cam.read()
        
        blobs = img.find_blobs(thresholds, 
                              area_threshold=area_threshold, 
                              pixels_threshold=pixels_threshold,
                              merge=True)
        
        # 在图像顶部显示阈值参数
        img.draw_rect(0, 0, 320, 20, color=image.COLOR_BLACK, thickness=-1)  # 黑色背景
        img.draw_string(10, 5, threshold_text, color=image.COLOR_WHITE, scale=0.6)
        
        for b in blobs:
            # 绘制边界框
            corners = b.corners()
            for i in range(4):
                img.draw_line(corners[i][0], corners[i][1],
                             corners[(i + 1) % 4][0], corners[(i + 1) % 4][1],
                             image.COLOR_RED, thickness=2)
            
            # 获取像素值的兼容性写法
            pixel_value = img.get_pixel(b.cx(), b.cy())
            
            # 处理不同返回值格式
            if isinstance(pixel_value, (list, tuple)) and len(pixel_value) >= 3:
                h, s, v = pixel_value[0], pixel_value[1], pixel_value[2]
            else:
                # 如果是灰度值，转换为HSV
                gray_value = pixel_value
                h, s, v = 0, 0, gray_value  # 灰度图只有亮度信息
            
            # 显示颜色信息
            color_type = get_color_type(h, s, v)
            color_info = f"{color_type} H:{h} S:{s} V:{v}"
            
            # 绘制信息背景
            img.draw_rect(b.cx() - 40, b.cy() - 40, 80, 30, color=image.COLOR_BLACK, thickness=-1)
            img.draw_string(b.cx() - 40, b.cy() - 30, 
                           color_info,
                           color=image.COLOR_WHITE,
                           scale=0.8)
            
            # 绘制中心点标记
            img.draw_cross(b.cx(), b.cy(), color=image.COLOR_RED, thickness=2)
        
        disp.show(img)

except KeyboardInterrupt:
    pass
finally:
    cam.close()
    disp.close()
    print("资源已释放")