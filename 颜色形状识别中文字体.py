from maix import camera, display, image, app  
import math  
  
# 初始化摄像头和显示屏  
cam = camera.Camera(320, 240)  
disp = display.Display()  
  
# 加载中文字体  
image.load_font("sourcehansans", "/maixapp/share/font/SourceHanSansCN-Regular.otf", size=20)  
image.set_default_font("sourcehansans")  
  
# 定义颜色阈值 (LAB色彩空间)  
color_thresholds = {  
    "红色": [[0, 80, 40, 80, 10, 80]],  
    "绿色": [[0, 80, -120, -10, 0, 30]],   
    "蓝色": [[0, 80, 30, 100, -120, -60]]  
}  
  
def analyze_shape(blob):  
    """分析色块的形状"""  
    # 获取色块的宽高比  
    aspect_ratio = blob.w() / blob.h() if blob.h() > 0 else 1  
      
    # 获取色块的面积和周长比例来判断形状  
    area = blob.area()  
      
    # 简单的形状判断逻辑  
    if 0.8 <= aspect_ratio <= 1.2:  # 接近正方形  
        if area > 1000:  
            return "大圆形" if area / (blob.w() * blob.h()) > 0.7 else "正方形"  
        else:  
            return "小圆形" if area / (blob.w() * blob.h()) > 0.7 else "小正方形"  
    elif aspect_ratio > 1.5:  
        return "长方形"  
    else:  
        return "不规则形状"  
  
def detect_color_and_shape():  
    """检测颜色和形状"""  
    while not app.need_exit():  
        img = cam.read()  
          
        # 遍历每种颜色进行检测  
        for color_name, thresholds in color_thresholds.items():  
            blobs = img.find_blobs(thresholds, pixels_threshold=500, area_threshold=300)  
              
            for blob in blobs:  
                # 分析形状  
                shape = analyze_shape(blob)  
                  
                # 在色块周围画框  
                img.draw_rect(blob.x(), blob.y(), blob.w(), blob.h(), image.COLOR_GREEN, 2)  
                  
                # 显示中文标签  
                label = f"{color_name}{shape}"  
                img.draw_string(blob.x(), blob.y() - 25, label, image.COLOR_WHITE, scale=1)  
                  
                # 显示置信度信息  
                confidence_text = f"面积: {blob.area()}"  
                img.draw_string(blob.x(), blob.y() + blob.h() + 5, confidence_text, image.COLOR_YELLOW, scale=1)  
          
        # 显示帮助信息  
        img.draw_string(5, 5, "颜色形状识别", image.COLOR_WHITE, scale=1)  
        img.draw_string(5, 220, "支持: 红色、绿色、蓝色", image.COLOR_WHITE, scale=1)  
          
        disp.show(img)  
  
if __name__ == "__main__":  
    detect_color_and_shape()