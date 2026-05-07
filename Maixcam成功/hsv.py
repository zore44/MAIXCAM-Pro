# ===================== MaixCam Pro 脱机HSV阈值调整工具 =====================
from maix import image, camera, display, time, touchscreen, app
import cv2
import numpy as np

# ------------------ 配置与常量定义 ------------------
SCREEN_WIDTH, SCREEN_HEIGHT = 320, 240
CAMERA_RESOLUTION = (SCREEN_WIDTH, SCREEN_HEIGHT)

# HSV参数范围 (OpenCV标准格式: H=0-179, S=0-255, V=0-255)
PARAM_RANGES = {
    "H_min": (0, 179), "H_max": (0, 179),
    "S_min": (0, 255), "S_max": (0, 255), 
    "V_min": (0, 255), "V_max": (0, 255)
}

class MaixCamProThresholdTool:
    def __init__(self, disp=None):
        # 初始化硬件 - 使用BGR888格式便于OpenCV处理
        self.cam = camera.Camera(*CAMERA_RESOLUTION, format=image.Format.FMT_BGR888)
        self.disp = disp if disp is not None else display.Display()
        self.ts = touchscreen.TouchScreen()
        
        # HSV参数 (默认绿色范围)
        self.hsv_params = {
            "H_min": 35, "H_max": 77,    # 绿色色调范围
            "S_min": 43, "S_max": 255,   # 饱和度范围
            "V_min": 46, "V_max": 255    # 亮度范围
        }
        
        self.in_binary_mode = False
        self.exit_flag = False
        self.selected_param = "H_min"
        
        # 界面布局
        self.preview_area = {"x": 0, "y": 0, "w": 200, "h": 150}
        self.control_area = {"x": 200, "y": 0, "w": 120, "h": 150}
        self.slider_area = {"x": 0, "y": 150, "w": 320, "h": 40}
        self.param_area = {"x": 0, "y": 190, "w": 320, "h": 50}
        
        self.buttons = {}
        self._init_ui()

    def _opencv_hsv_threshold(self, img_np, h_min, h_max, s_min, s_max, v_min, v_max):
        """使用OpenCV进行HSV阈值处理"""
        try:
            # 转换为HSV颜色空间
            hsv = cv2.cvtColor(img_np, cv2.COLOR_BGR2HSV)
            
            # 创建HSV范围
            lower_bound = np.array([h_min, s_min, v_min])
            upper_bound = np.array([h_max, s_max, v_max])
            
            # 创建掩码
            mask = cv2.inRange(hsv, lower_bound, upper_bound)
            
            # 中值滤波去噪
            mask = cv2.medianBlur(mask, 5)
            
            # 转换为3通道便于显示
            mask_bgr = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
            
            return mask_bgr
            
        except Exception as e:
            print(f"OpenCV HSV处理失败: {e}")
            return img_np

    def _find_contours_and_draw(self, img_np, mask):
        """查找轮廓并绘制边界框"""
        try:
            # 转换掩码为灰度
            if len(mask.shape) == 3:
                mask_gray = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
            else:
                mask_gray = mask
            
            # 查找轮廓
            contours, _ = cv2.findContours(mask_gray, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            blob_count = 0
            for contour in contours:
                area = cv2.contourArea(contour)
                if area < 500:  # 过滤小面积
                    continue
                    
                # 绘制边界框
                x, y, w, h = cv2.boundingRect(contour)
                cv2.rectangle(img_np, (x, y), (x + w, y + h), (0, 255, 0), 2)
                
                # 绘制中心点
                cx, cy = x + w // 2, y + h // 2
                cv2.circle(img_np, (cx, cy), 3, (0, 0, 255), -1)
                
                blob_count += 1
            
            return blob_count
            
        except Exception as e:
            print(f"轮廓检测失败: {e}")
            return 0

    def _init_ui(self):
        """初始化UI界面"""
        # 控制按钮
        self.buttons["binary"] = {"x": 205, "y": 10, "w": 50, "h": 20, "text": "Binary"}
        self.buttons["exit"] = {"x": 260, "y": 10, "w": 50, "h": 20, "text": "Exit"}
        
        # 参数选择按钮
        param_names = ["H_min", "H_max", "S_min", "S_max", "V_min", "V_max"]
        btn_w, btn_h = 48, 25
        start_x = 10
        for i, param in enumerate(param_names):
            x = start_x + i * (btn_w + 3)
            y = self.param_area["y"] + 15
            self.buttons[param] = {"x": x, "y": y, "w": btn_w, "h": btn_h, "text": param}

    def _draw_main_slider(self, img):
        """绘制主滑条"""
        x, y, w, h = 10, self.slider_area["y"] + 5, 300, 30
        min_val, max_val = PARAM_RANGES[self.selected_param]
        value = self.hsv_params[self.selected_param]
        
        # 绘制滑条背景
        img.draw_rect(x, y, w, h, image.COLOR_WHITE, 2)
        img.draw_rect(x+2, y+2, w-4, h-4, image.COLOR_BLACK, -1)
        
        # 计算滑块位置
        slider_width = 20
        usable_width = w - slider_width
        if max_val > min_val:
            slider_pos = int(x + (value - min_val) * usable_width / (max_val - min_val))
        else:
            slider_pos = x
        
        slider_pos = max(x, min(slider_pos, x + usable_width))
        
        # 绘制滑块
        img.draw_rect(slider_pos, y, slider_width, h, image.COLOR_RED, -1)
        
        # 显示参数信息
        info_text = f"{self.selected_param}: {value} ({min_val}-{max_val})"
        img.draw_string(x, y - 15, info_text, image.COLOR_WHITE, scale=0.7)

    def _draw_button(self, img, btn_info, selected=False):
        """绘制按钮"""
        x, y, w, h = btn_info["x"], btn_info["y"], btn_info["w"], btn_info["h"]
        text = btn_info["text"]
        
        color = image.COLOR_RED if selected else image.COLOR_WHITE
        img.draw_rect(x, y, w, h, color, 2)
        img.draw_string(x + 2, y + 5, text, image.COLOR_WHITE, scale=0.5)

    def _is_point_in_rect(self, px, py, x, y, w, h):
        """检查点是否在矩形内"""
        return x <= px <= x + w and y <= py <= y + h

    def _handle_slider_touch(self, x, y):
        """处理滑条触摸"""
        slider_x, slider_y, slider_w, slider_h = 10, self.slider_area["y"] + 5, 300, 30
        
        if self._is_point_in_rect(x, y, slider_x, slider_y, slider_w, slider_h):
            min_val, max_val = PARAM_RANGES[self.selected_param]
            slider_width = 20
            usable_width = slider_w - slider_width
            
            relative_pos = (x - slider_x) / usable_width
            relative_pos = max(0, min(1, relative_pos))
            
            new_value = int(min_val + relative_pos * (max_val - min_val))
            self.hsv_params[self.selected_param] = new_value
            print(f"{self.selected_param} = {new_value}")
            return True
        return False

    def _handle_button_touch(self, x, y):
        """处理按钮触摸"""
        for btn_name, btn_info in self.buttons.items():
            bx, by, bw, bh = btn_info["x"], btn_info["y"], btn_info["w"], btn_info["h"]
            
            if self._is_point_in_rect(x, y, bx, by, bw, bh):
                if btn_name == "binary":
                    self.in_binary_mode = not self.in_binary_mode
                    print(f"二值化模式: {'开启' if self.in_binary_mode else '关闭'}")
                elif btn_name == "exit":
                    self.exit_flag = True
                    print("退出程序")
                elif btn_name in self.hsv_params:
                    self.selected_param = btn_name
                    print(f"选中参数: {self.selected_param}")
                return True
        return False

    def run(self):
        """运行阈值调整工具"""
        print("MaixCam Pro HSV阈值调整工具启动")
        print("- 点击参数按钮选择要调整的参数")
        print("- 拖动滑条调整参数值")
        print("- 点击Binary切换二值化显示")
        print("- 点击Exit退出")
        
        while not self.exit_flag:
            # 读取摄像头 (BGR888格式)
            img = self.cam.read()
            
            # 转换为numpy数组供OpenCV处理
            img_np = image.image2cv(img, ensure_bgr=True, copy=True)
            
            # 获取当前HSV参数
            h_min = self.hsv_params["H_min"]
            h_max = self.hsv_params["H_max"]
            s_min = self.hsv_params["S_min"]
            s_max = self.hsv_params["S_max"]
            v_min = self.hsv_params["V_min"]
            v_max = self.hsv_params["V_max"]
            
            # 处理二值化显示
            if self.in_binary_mode:
                # 裁剪预览区域
                crop_np = img_np[self.preview_area["y"]:self.preview_area["y"]+self.preview_area["h"],
                                self.preview_area["x"]:self.preview_area["x"]+self.preview_area["w"]]
                
                # 使用OpenCV进行HSV阈值处理
                binary_crop = self._opencv_hsv_threshold(crop_np, h_min, h_max, s_min, s_max, v_min, v_max)
                
                # 将处理后的图像放回原图
                img_np[self.preview_area["y"]:self.preview_area["y"]+self.preview_area["h"],
                       self.preview_area["x"]:self.preview_area["x"]+self.preview_area["w"]] = binary_crop
                
                print(f"HSV参数: H({h_min}-{h_max}) S({s_min}-{s_max}) V({v_min}-{v_max})")
            else:
                # 非二值化模式：查找并绘制轮廓
                hsv = cv2.cvtColor(img_np, cv2.COLOR_BGR2HSV)
                lower_bound = np.array([h_min, s_min, v_min])
                upper_bound = np.array([h_max, s_max, v_max])
                mask = cv2.inRange(hsv, lower_bound, upper_bound)
                mask = cv2.medianBlur(mask, 5)
                
                blob_count = self._find_contours_and_draw(img_np, mask)
                if blob_count > 0:
                    print(f"检测到 {blob_count} 个目标")
            
            # 转换回MaixPy图像格式
            img_show = image.cv2image(img_np, bgr=True)
            
            # 绘制UI元素
            # 绘制控制区域背景
            img_show.draw_rect(self.control_area["x"], self.control_area["y"],
                              self.control_area["w"], self.control_area["h"], 
                              image.COLOR_BLACK, -1)
            
            # 绘制滑条和参数区域背景
            img_show.draw_rect(self.slider_area["x"], self.slider_area["y"],
                              self.slider_area["w"], self.slider_area["h"], 
                              image.COLOR_BLACK, -1)
            img_show.draw_rect(self.param_area["x"], self.param_area["y"],
                              self.param_area["w"], self.param_area["h"], 
                              image.COLOR_BLACK, -1)
            
            # 绘制按钮
            self._draw_button(img_show, self.buttons["binary"])
            self._draw_button(img_show, self.buttons["exit"])
            
            # 绘制参数选择按钮
            param_names = ["H_min", "H_max", "S_min", "S_max", "V_min", "V_max"]
            for param in param_names:
                selected = (param == self.selected_param)
                self._draw_button(img_show, self.buttons[param], selected)
            
            # 绘制主滑条
            self._draw_main_slider(img_show)
            
            # 绘制分割线
            img_show.draw_rect(self.preview_area["w"], 0, 1, self.preview_area["h"], image.COLOR_WHITE, -1)
            img_show.draw_rect(0, self.preview_area["h"], SCREEN_WIDTH, 1, image.COLOR_WHITE, -1)
            img_show.draw_rect(0, self.param_area["y"], SCREEN_WIDTH, 1, image.COLOR_WHITE, -1)
            
            # 显示当前参数值
            y_offset = 40
            for param, value in self.hsv_params.items():
                color = image.COLOR_RED if param == self.selected_param else image.COLOR_WHITE
                img_show.draw_string(205, y_offset, f"{param}:{value}", color, scale=0.5)
                y_offset += 12
            
            # 处理触摸
            touch_x, touch_y, pressed = self.ts.read()
            if pressed:
                try:
                    adjusted_x, adjusted_y = image.resize_map_pos_reverse(
                        SCREEN_WIDTH, SCREEN_HEIGHT,
                        self.disp.width(), self.disp.height(),
                        image.Fit.FIT_CONTAIN, touch_x, touch_y
                    )
                    x, y = adjusted_x, adjusted_y
                except:
                    x, y = touch_x, touch_y
                
                if not self._handle_button_touch(x, y):
                    self._handle_slider_touch(x, y)
            
            # 显示图像
            self.disp.show(img_show)
            time.sleep_ms(30)
        
        # 返回最终HSV阈值
        return (self.hsv_params["H_min"], self.hsv_params["H_max"],
                self.hsv_params["S_min"], self.hsv_params["S_max"],
                self.hsv_params["V_min"], self.hsv_params["V_max"])

def get_hsv_threshold(disp=None):
    """获取HSV阈值的简单接口"""
    tool = MaixCamProThresholdTool(disp)
    return tool.run()

def test_threshold_detection(threshold):
    """测试阈值检测效果"""
    print(f"测试HSV阈值: {threshold}")
    
    cam = camera.Camera(320, 240, format=image.Format.FMT_BGR888)
    disp = display.Display()
    
    h_min, h_max, s_min, s_max, v_min, v_max = threshold
    
    while not app.need_exit():
        img = cam.read()
        img_np = image.image2cv(img, ensure_bgr=True, copy=True)
        
        # HSV阈值处理
        hsv = cv2.cvtColor(img_np, cv2.COLOR_BGR2HSV)
        lower_bound = np.array([h_min, s_min, v_min])
        upper_bound = np.array([h_max, s_max, v_max])
        mask = cv2.inRange(hsv, lower_bound, upper_bound)
        mask = cv2.medianBlur(mask, 5)
        
        # 查找轮廓
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        blob_count = 0
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 500:
                continue
                
            x, y, w, h = cv2.boundingRect(contour)
            cv2.rectangle(img_np, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cx, cy = x + w // 2, y + h // 2
            cv2.circle(img_np, (cx, cy), 3, (0, 0, 255), -1)
            blob_count += 1
        
        if blob_count > 0:
            print(f"检测到 {blob_count} 个目标")
        
        img_show = image.cv2image(img_np, bgr=True)
        disp.show(img_show)

if __name__ == "__main__":
    # 调整阈值
    threshold = get_hsv_threshold()
    print(f"最终HSV阈值: {threshold}")
    
    # 测试检测效果
    test_threshold_detection(threshold)