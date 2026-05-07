from maix import image, camera, display, uart, time, app
import math

# 初始化摄像头和显示屏
cam = camera.Camera(320, 240)
disp = display.Display()

# 黑色检测阈值 (LAB颜色空间)
black_thresholds = [[9,45,-15,18,-20,19], [16,46,3,33,3,33], [14,44,-16,25,-13,36], [0,33,-15,16,-19,13]]
black_threshold = [[0, 30, -20, 20, -20, 20]]  # 黑色阈值 (巡线用)
red_threshold = [[9, 38, 9, 55, -2, 31]]  #红
# 设置检测参数
area_threshold = 300      # 面积阈值，过滤小色块
pixels_threshold = 300    # 像素阈值，过滤小色块

# 巡线ROI区域配置 (x, y, w, h, weight)
line_roi_configs = [  
    {"roi": (0, 60, 320, 30), "weight": 0.1},   # 上部区域  
    {"roi": (0, 120, 320, 40), "weight": 0.3},  # 中部区域    
    {"roi": (0, 180, 320, 40), "weight": 0.6}   # 下部区域  
]  

# 十字路口检测ROI配置  
crossroad_roi_configs = {  
    "horizontal": (40, 120, 240, 60),    # 横向检测区域  
    "left": (0, 120, 80, 80),           # 左侧检测区域  
    "right": (240, 120, 80, 80)         # 右侧检测区域  
}  

#串口初始化
device = "/dev/ttyS0"
serial = uart.UART(device, 115200)

# 全局变量  
line_angle = 0  
is_crossroad = False  
frame_count = 0  
last_time = time.time()  

class LineTracker:  
    def __init__(self):  
        self.weight_sum = sum(config["weight"] for config in line_roi_configs)  
        self.center_x = 160  # 图像中心点  
        self.max_deviation = 160  # 最大偏移量  
          
    def detect_line(self, img):  
        """三点法巡线检测"""  
        global line_angle  
          
        line_blobs = []  
        weighted_centroid = 0  
          
        # 遍历每个ROI区域  
        for config in line_roi_configs:  
            roi = config["roi"]  
            weight = config["weight"]  
              
            # 在ROI区域内查找黑色色块  
            blobs = img.find_blobs(  
                red_threshold,  
                roi=roi,  
                pixels_threshold=100,  
                area_threshold=50,  
                merge=True  
            )  
              
            if blobs:  
                # 选择最大的色块  
                max_blob = max(blobs, key=lambda b: b.pixels())  
                line_blobs.append(max_blob)  
                weighted_centroid += max_blob.cx() * weight  
                  
                # 绘制检测到的色块  
                self._draw_blob(img, max_blob)  
          
        # 计算巡线角度  
        if weighted_centroid > 0:  
            line_position = weighted_centroid / self.weight_sum  
            deviation = (line_position - self.center_x) / self.max_deviation  
            line_angle = max(-90, min(90, deviation * 90))  
        else:  
            line_angle = 0  
              
        return line_blobs  
      
    def _draw_blob(self, img, blob):  
        """绘制色块边框"""  
        x, y, w, h = blob.rect()  
        img.draw_rect(x, y, w, h, image.COLOR_GREEN, 2)  
        img.draw_cross(blob.cx(), blob.cy(), image.COLOR_RED, 5)  

class CrossroadDetector:  
    def __init__(self):  
        self.detection_thresholds = {  
            "horizontal": {"pixels": 1500, "area": 1500, "min_width": 180, "min_height": 30},  
            "side": {"pixels": 800, "area": 800, "min_pixels": 1000}  
        }  
      
    def detect_crossroad(self, img):  
        """十字路口检测"""  
        global is_crossroad  
          
        # 检测横向区域  
        horizontal_blobs = img.find_blobs(  
            red_threshold,  
            roi=crossroad_roi_configs["horizontal"],  
            pixels_threshold=self.detection_thresholds["horizontal"]["pixels"],  
            area_threshold=self.detection_thresholds["horizontal"]["area"]  
        )  
          
        # 检测左侧区域  
        left_blobs = img.find_blobs(  
            red_threshold,  
            roi=crossroad_roi_configs["left"],  
            pixels_threshold=self.detection_thresholds["side"]["pixels"],  
            area_threshold=self.detection_thresholds["side"]["area"]  
        )  
          
        # 检测右侧区域  
        right_blobs = img.find_blobs(  
            red_threshold,  
            roi=crossroad_roi_configs["right"],  
            pixels_threshold=self.detection_thresholds["side"]["pixels"],  
            area_threshold=self.detection_thresholds["side"]["area"]  
        )  
          
        # 绘制检测区域  
        self._draw_roi_boxes(img)  
          
        # 十字路口判断逻辑  
        crossroad_detected = False  
          
        if horizontal_blobs and left_blobs and right_blobs:  
            max_horizontal = max(horizontal_blobs, key=lambda b: b.pixels())  
            max_left = max(left_blobs, key=lambda b: b.pixels())  
            max_right = max(right_blobs, key=lambda b: b.pixels())  
              
            # 检查横向色块尺寸  
            h_width = max_horizontal.w()  
            h_height = max_horizontal.h()  
              
            # 检查左右色块大小  
            left_pixels = max_left.pixels()  
            right_pixels = max_right.pixels()  
              
            if (h_width > self.detection_thresholds["horizontal"]["min_width"] and  
                h_height > self.detection_thresholds["horizontal"]["min_height"] and  
                left_pixels > self.detection_thresholds["side"]["min_pixels"] and  
                right_pixels > self.detection_thresholds["side"]["min_pixels"]):  
                  
                crossroad_detected = True  
                self._draw_blob(img, max_horizontal)  
          
        is_crossroad = crossroad_detected  
        return crossroad_detected  
      
    def _draw_roi_boxes(self, img):  
        """绘制ROI检测区域"""  
        for roi in crossroad_roi_configs.values():  
            x, y, w, h = roi  
            img.draw_rect(x, y, w, h, image.COLOR_RED, 1)  
      
    def _draw_blob(self, img, blob):  
        """绘制检测到的色块"""  
        x, y, w, h = blob.rect()  
        img.draw_rect(x, y, w, h, image.COLOR_BLUE, 2)  

class Visualizer:  
    def __init__(self):  
        self.center_x = 160  
        self.center_y = 180  
        self.indicator_length = 80  
      
    def draw_status(self, img, line_blobs):  
        """绘制状态信息和角度指示器"""  
        # 绘制角度指示器  
        angle_rad = math.radians(line_angle)  
        end_x = int(self.center_x + self.indicator_length * math.sin(angle_rad))  
        end_y = int(self.center_y - self.indicator_length * math.cos(angle_rad))  
          
        img.draw_line(self.center_x, self.center_y, end_x, end_y,   
                     image.COLOR_RED, 3)  
          
        # 显示角度信息  
        angle_text = f"Angle: {line_angle:.1f}°"  
        img.draw_string(10, 10, angle_text, image.COLOR_RED)  
          
        # 显示十字路口状态  
        cross_text = "Cross: YES" if is_crossroad else "Cross: NO"  
        img.draw_string(10, 30, cross_text, image.COLOR_RED)  
          
        # 显示帧率  
        self._update_fps(img)  
      
    def _update_fps(self, img):  
        """更新并显示帧率"""  
        global frame_count, last_time  
          
        current_time = time.time()  
        frame_count += 1  
          
        if current_time - last_time >= 1.0:  
            fps = frame_count / (current_time - last_time)  
            frame_count = 0  
            last_time = current_time  
              
            fps_text = f"FPS: {fps:.1f}"  
            img.draw_string(10, 50, fps_text, image.COLOR_BLUE)  

class UartCommunicator:  
    def __init__(self, uart_instance):  
        self.uart = uart_instance  
        self.last_send_time = time.time()  
        self.send_interval = 0.1  # 发送间隔  
      
    def send_data(self, angle):  
        """发送数据到串口"""  
        current_time = time.time()  
          
        if current_time - self.last_send_time < self.send_interval:  
            return  
          
        if is_crossroad:  
            # 十字路口检测到时发送特殊标识  
            data = b'S\r\n'  
            self.uart.write(data)  
            print("Crossroad Detected: Sent 'S'")  
        else:  
            # 正常巡线发送角度数据  
            angle_int = int(angle)  
            data = f"{angle_int}\r\n".encode()  
            self.uart.write(data)  
            print(f"Sending angle: {angle_int}")  
          
        self.last_send_time = current_time  

def is_valid_block(blob):  
    """验证检测到的色块是否有效"""  
    # 过滤过大的色块 (可能是误检)  
    if blob.area() > 3000:  
        return False  
    # 过滤过大的宽高  
    if blob.w() > 55 or blob.h() > 55:  
        return False  
    return True  

# 创建处理器实例  
line_tracker = LineTracker()  
crossroad_detector = CrossroadDetector()  
visualizer = Visualizer()  
uart_comm = UartCommunicator(serial)  

# 主循环  
def main():  
    print("黑色巡线和十字路口识别系统启动")  
      
    while not app.need_exit():  
        try:  
            # 获取图像  
            img = cam.read()  
              
            # 十字路口检测  
            crossroad_detector.detect_crossroad(img)  
              
            # 巡线检测  
            line_blobs = line_tracker.detect_line(img)  
              
            # 黑色小块检测  
            black_blobs = None  
            for threshold in black_thresholds:  
                black_blobs = img.find_blobs([threshold],   
                                           area_threshold=area_threshold,   
                                           pixels_threshold=pixels_threshold)  

                # 计算有效色块数量  
                valid_count = 0  
                for blob in black_blobs:  
                    if is_valid_block(blob):  
                        valid_count += 1  

                # 如果找到足够的有效色块，使用此阈值  
                if valid_count >= 1:  
                    break  

            # 绘制检测结果  
            valid_blobs = []  
            if black_blobs:  
                for blob in black_blobs:  
                    if is_valid_block(blob):  
                        valid_blobs.append(blob)  
                        # 绘制边界框  
                        img.draw_rect(blob.x(), blob.y(), blob.w(), blob.h(),   
                                     image.COLOR_GREEN, 2)  

                        # 绘制中心点  
                        img.draw_circle(blob.cx(), blob.cy(), 3, image.COLOR_RED, -1)  

                        # 显示信息  
                        info = f"X:{blob.cx()}, Y:{blob.cy()}, Area:{blob.area()}"  
                        img.draw_string(blob.x(), blob.y() - 10, info,   
                                       image.COLOR_WHITE, scale=1)  

                        # 输出检测结果到串口  
                        print(f"黑色小块检测: 中心坐标({blob.cx()}, {blob.cy()}), 面积:{blob.area()}")  

            # 检测是否有6个以上有效黑色小块  
            if len(valid_blobs) >= 6:  
                # 发送字符 'T' 到串口  
                serial.write(b'T\r\n')  
                print("检测到6个以上黑色小块，发送T")  

            # 可视化显示  
            visualizer.draw_status(img, line_blobs)  
              
            # 串口数据发送  
            uart_comm.send_data(line_angle)  
              
            # 显示图像  
            disp.show(img)  
              
        except Exception as e:  
            print(f"处理错误: {e}")  
            time.sleep_ms(10)  

if __name__ == "__main__":  
    main()