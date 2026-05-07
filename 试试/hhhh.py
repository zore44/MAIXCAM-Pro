# ===================== HSV阈值调整工具 (OpenCV+MaixPy混合) =====================
from maix import image, camera, display, time, touchscreen, app
import cv2
import numpy as np

# ------------------ 配置与常量定义 ------------------
SCREEN_WIDTH, SCREEN_HEIGHT = 320, 240
CAMERA_RESOLUTION = (SCREEN_WIDTH, SCREEN_HEIGHT)

# HSV参数范围 (OpenCV标准格式)
PARAM_RANGES = {
    "H_min": (0, 179), "H_max": (0, 179),  # H: 0-179
    "S_min": (0, 255), "S_max": (0, 255),  # S: 0-255
    "V_min": (0, 255), "V_max": (0, 255)   # V: 0-255
}

class HSVThresholdTool:
    def __init__(self, disp=None):
        self.cam = camera.Camera(*CAMERA_RESOLUTION)
        self.disp = disp if disp is not None else display.Display()
        self.ts = touchscreen.TouchScreen()
        
        # HSV参数 (OpenCV标准格式)
        self.hsv_params = {
            "H_min": 35, "H_max": 85,    # 绿色范围 H: 35-85
            "S_min": 50, "S_max": 255,   # 饱和度: 50-255
            "V_min": 50, "V_max": 255    # 亮度: 50-255
        }
        
        self.in_binary_mode = False
        self.exit_flag = False
        self.selected_param = "H_min"  # 当前选中的参数
        
        # 界面布局
        self.preview_area = {"x": 0, "y": 0, "w": 200, "h": 150}
        self.control_area = {"x": 200, "y": 0, "w": 120, "h": 150}
        self.slider_area = {"x": 0, "y": 150, "w": 320, "h": 40}
        self.param_area = {"x": 0, "y": 190, "w": 320, "h": 50}
        
        self.buttons = {}
        self._init_ui()

    def _hsv_to_rgb_threshold(self, h_min, h_max, s_min, s_max, v_min, v_max):
        """将HSV阈值转换为RGB阈值范围"""
        try:
            # 采样HSV空间的关键点
            hsv_samples = [
                [h_min, s_min, v_min],
                [h_min, s_max, v_max], 
                [h_max, s_min, v_min],
                [h_max, s_max, v_max],
                [(h_min+h_max)//2, (s_min+s_max)//2, (v_min+v_max)//2]
            ]
            
            rgb_values = []
            for hsv in hsv_samples:
                hsv_img = np.uint8([[hsv]])
                rgb_img = cv2.cvtColor(hsv_img, cv2.COLOR_HSV2RGB)
                rgb_values.append(rgb_img[0][0])
            
            rgb_array = np.array(rgb_values)
            r_min, r_max = int(rgb_array[:, 0].min()), int(rgb_array[:, 0].max())
            g_min, g_max = int(rgb_array[:, 1].min()), int(rgb_array[:, 1].max())
            b_min, b_max = int(rgb_array[:, 2].min()), int(rgb_array[:, 2].max())
            
            # 适当扩展范围
            margin = 20
            r_min = max(0, r_min - margin)
            r_max = min(255, r_max + margin)
            g_min = max(0, g_min - margin)
            g_max = min(255, g_max + margin)
            b_min = max(0, b_min - margin)
            b_max = min(255, b_max + margin)
            
            return (r_min, r_max, g_min, g_max, b_min, b_max)
            
        except Exception as e:
            print(f"HSV转RGB失败: {e}")
            return (0, 100, 80, 255, 0, 100)

    def _get_green_rgb_threshold(self):
        """直接返回绿色的RGB阈值，避免转换错误"""
        # 经验值：绿色在RGB空间的典型范围
        return (0, 120, 50, 255, 0, 120)  # 绿色主导的RGB范围

    def _init_ui(self):
        """初始化UI界面"""
        # 创建控制按钮
        self.buttons["binary"] = {"x": 205, "y": 10, "w": 50, "h": 20, "text": "Binary"}
        self.buttons["exit"] = {"x": 260, "y": 10, "w": 50, "h": 20, "text": "Exit"}
        
        # 创建参数选择按钮 (一行6个)
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
        
        # 计算滑块位置 - 修正边界问题
        slider_width = 20
        usable_width = w - slider_width
        if max_val > min_val:
            slider_pos = int(x + (value - min_val) * usable_width / (max_val - min_val))
        else:
            slider_pos = x
        
        # 确保滑块不超出边界
        slider_pos = max(x, min(slider_pos, x + usable_width))
        
        # 绘制滑块
        img.draw_rect(slider_pos, y, slider_width, h, image.COLOR_RED, -1)
        
        # 绘制当前参数和值
        info_text = f"{self.selected_param}: {value} ({min_val}-{max_val})"
        img.draw_string(x, y - 15, info_text, image.COLOR_WHITE, scale=0.7)

    def _draw_button(self, img, btn_info, selected=False):
        """绘制按钮"""
        x, y, w, h = btn_info["x"], btn_info["y"], btn_info["w"], btn_info["h"]
        text = btn_info["text"]
        
        # 选中的参数按钮用红色边框
        color = image.COLOR_RED if selected else image.COLOR_WHITE
        img.draw_rect(x, y, w, h, color, 2)
        
        # 绘制文本
        img.draw_string(x + 2, y + 5, text, image.COLOR_WHITE, scale=0.5)

    def _is_point_in_rect(self, px, py, x, y, w, h):
        """检查点是否在矩形内"""
        return x <= px <= x + w and y <= py <= y + h

    def _handle_slider_touch(self, x, y):
        """处理主滑条触摸"""
        slider_x, slider_y, slider_w, slider_h = 10, self.slider_area["y"] + 5, 300, 30
        
        if self._is_point_in_rect(x, y, slider_x, slider_y, slider_w, slider_h):
            # 计算新值 - 修正边界问题
            min_val, max_val = PARAM_RANGES[self.selected_param]
            slider_width = 20
            usable_width = slider_w - slider_width
            
            # 计算相对位置，确保能到达0和1
            relative_pos = (x - slider_x) / usable_width
            relative_pos = max(0, min(1, relative_pos))
            
            new_value = int(min_val + relative_pos * (max_val - min_val))
            
            # 更新值
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
                    # 选择参数
                    self.selected_param = btn_name
                    print(f"选中参数: {self.selected_param}")
                return True
        return False

    def run(self):
        """运行阈值调整工具"""
        print("HSV阈值调整工具启动")
        print("- 点击参数按钮选择要调整的参数")
        print("- 拖动大滑条调整选中参数的值")
        print("- 点击Binary切换二值化显示")
        print("- 点击Exit退出")
        
        while not self.exit_flag:
            # 读取摄像头
            img = self.cam.read()
            
            # 处理二值化显示
            if self.in_binary_mode:
                # 裁剪预览区域
                crop = img.crop(self.preview_area["x"], self.preview_area["y"],
                               self.preview_area["w"], self.preview_area["h"])
                
                # 获取当前HSV参数
                h_min = self.hsv_params["H_min"]
                h_max = self.hsv_params["H_max"]
                s_min = self.hsv_params["S_min"]
                s_max = self.hsv_params["S_max"]
                v_min = self.hsv_params["V_min"]
                v_max = self.hsv_params["V_max"]
                
                # 方法1: 尝试直接使用HSV阈值
                try:
                    hsv_threshold = (h_min, h_max, s_min, s_max, v_min, v_max)
                    crop.binary([hsv_threshold])
                    print(f"直接使用HSV阈值成功: {hsv_threshold}")
                except Exception as e:
                    print(f"HSV阈值失败: {e}")
                    
                    # 方法2: 转换为RGB后使用
                    try:
                        rgb_threshold = self._hsv_to_rgb_threshold(h_min, h_max, s_min, s_max, v_min, v_max)
                        crop.binary([rgb_threshold])
                        print(f"使用转换RGB阈值成功: {rgb_threshold}")
                    except Exception as e:
                        print(f"转换RGB阈值失败: {e}")
                        
                        # 方法3: 使用默认绿色RGB阈值
                        try:
                            default_green = (0, 100, 80, 255, 0, 100)
                            crop.binary([default_green])
                            print(f"使用默认绿色阈值: {default_green}")
                        except Exception as e:
                            print(f"所有二值化方法都失败: {e}")
                
                # 替换预览区域
                img.draw_image(self.preview_area["x"], self.preview_area["y"], crop)
            
            # 绘制控制区域背景
            img.draw_rect(self.control_area["x"], self.control_area["y"],
                         self.control_area["w"], self.control_area["h"], 
                         image.COLOR_BLACK, -1)
            
            # 绘制滑条区域背景
            img.draw_rect(self.slider_area["x"], self.slider_area["y"],
                         self.slider_area["w"], self.slider_area["h"], 
                         image.COLOR_BLACK, -1)
            
            # 绘制参数区域背景
            img.draw_rect(self.param_area["x"], self.param_area["y"],
                         self.param_area["w"], self.param_area["h"], 
                         image.COLOR_BLACK, -1)
            
            # 绘制控制按钮
            self._draw_button(img, self.buttons["binary"])
            self._draw_button(img, self.buttons["exit"])
            
            # 绘制参数选择按钮
            param_names = ["H_min", "H_max", "S_min", "S_max", "V_min", "V_max"]
            for param in param_names:
                selected = (param == self.selected_param)
                self._draw_button(img, self.buttons[param], selected)
            
            # 绘制主滑条
            self._draw_main_slider(img)
            
            # 绘制分割线
            img.draw_rect(self.preview_area["w"], 0, 1, self.preview_area["h"], image.COLOR_WHITE, -1)
            img.draw_rect(0, self.preview_area["h"], SCREEN_WIDTH, 1, image.COLOR_WHITE, -1)
            img.draw_rect(0, self.param_area["y"], SCREEN_WIDTH, 1, image.COLOR_WHITE, -1)
            
            # 显示当前所有参数值
            y_offset = 40
            for param, value in self.hsv_params.items():
                color = image.COLOR_RED if param == self.selected_param else image.COLOR_WHITE
                img.draw_string(205, y_offset, f"{param}:{value}", color, scale=0.5)
                y_offset += 12
            
            # 处理触摸
            touch_x, touch_y, pressed = self.ts.read()
            if pressed:
                # 尝试坐标转换
                try:
                    adjusted_x, adjusted_y = image.resize_map_pos_reverse(
                        SCREEN_WIDTH, SCREEN_HEIGHT,
                        self.disp.width(), self.disp.height(),
                        image.Fit.FIT_CONTAIN, touch_x, touch_y
                    )
                    x, y = adjusted_x, adjusted_y
                except:
                    x, y = touch_x, touch_y
                
                # 处理按钮和滑条触摸
                if not self._handle_button_touch(x, y):
                    self._handle_slider_touch(x, y)
            
            # 显示图像
            self.disp.show(img)
            time.sleep_ms(30)
            
        # 返回最终HSV阈值 (OpenCV格式)
        return (self.hsv_params["H_min"], self.hsv_params["H_max"],
                self.hsv_params["S_min"], self.hsv_params["S_max"],
                self.hsv_params["V_min"], self.hsv_params["V_max"])

def get_hsv_threshold(disp=None):
    """获取HSV阈值的简单接口"""
    tool = HSVThresholdTool(disp)
    return tool.run()

def test_hsv_conversion():
    """测试HSV到RGB转换"""
    # 测试绿色HSV值
    green_hsv = np.uint8([[[60, 255, 255]]])  # 纯绿色
    green_rgb = cv2.cvtColor(green_hsv, cv2.COLOR_HSV2RGB)
    print(f"绿色HSV(60,255,255) -> RGB{green_rgb[0][0]}")
    
    # 测试你的HSV范围
    hsv_range = np.uint8([[[37, 50, 50]], [[81, 255, 255]]])
    rgb_range = cv2.cvtColor(hsv_range, cv2.COLOR_HSV2RGB)
    print(f"你的HSV范围:")
    print(f"  HSV(37,50,50) -> RGB{rgb_range[0][0]}")
    print(f"  HSV(81,255,255) -> RGB{rgb_range[1][0]}")

if __name__ == "__main__":
    # 先测试转换
    test_hsv_conversion()
    
    threshold = get_hsv_threshold()
    print(f"最终HSV阈值: {threshold}")








