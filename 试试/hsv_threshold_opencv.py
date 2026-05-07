# ===================== HSV阈值调整工具 (基于OpenCV) =====================
from maix import image, camera, display, time, touchscreen, app
import cv2
import numpy as np

# ------------------ 配置与常量定义 ------------------
SCREEN_WIDTH, SCREEN_HEIGHT = 320, 240
CAMERA_RESOLUTION = (SCREEN_WIDTH, SCREEN_HEIGHT)

# HSV参数范围
PARAM_RANGES = {
    "H_min": (0, 179), "H_max": (0, 179),
    "S_min": (0, 255), "S_max": (0, 255), 
    "V_min": (0, 255), "V_max": (0, 255)
}

ADJUST_STEP = 5
BUTTON_MARGIN_X = 4
BUTTON_MARGIN_Y = 4

class HSVThresholdTool:
    def __init__(self, disp=None):
        self.cam = camera.Camera(*CAMERA_RESOLUTION)
        self.disp = disp if disp is not None else display.Display()
        self.ts = touchscreen.TouchScreen()
        
        # HSV参数 (OpenCV格式: H:0-179, S:0-255, V:0-255)
        self.hsv_params = {
            "H_min": 35, "H_max": 85,   # 绿色范围
            "S_min": 50, "S_max": 255,
            "V_min": 50, "V_max": 255
        }
        
        self.in_binary_mode = False
        self.exit_flag = False
        self.selected_param = None
        self.ui_img = image.Image(SCREEN_WIDTH, SCREEN_HEIGHT)
        
        self.buttons = {"exit": None, "binary": None, "params": {}}
        self._init_ui()

    def _init_ui(self):
        """初始化UI界面"""
        self.ui_img.draw_rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, image.COLOR_BLACK, -1)
        
        # 退出按钮
        exit_label = "< Exit"
        self.buttons["exit"] = self._draw_button(exit_label, 
                                                SCREEN_WIDTH - self._get_button_width(exit_label), 0)
        
        # 二值化按钮
        binary_label = "< Binary"
        btn_width = self._get_button_width(binary_label)
        self.buttons["binary"] = self._draw_button(binary_label, 
                                                  (SCREEN_WIDTH - btn_width) // 2, 0)
        
        # 参数按钮
        param_labels = ["<H_min", "<H_max", "<S_min", "<S_max", "<V_min", "<V_max"]
        y_offset = 30
        for label in param_labels:
            self.buttons["params"][label] = self._draw_button(label, 0, y_offset)
            y_offset += self.buttons["params"][label][3]

    def _get_text_size(self, text):
        return image.string_size(text)

    def _get_button_width(self, text):
        text_w, _ = self._get_text_size(text)
        return 2 * BUTTON_MARGIN_X + text_w

    def _get_button_height(self, text):
        _, text_h = self._get_text_size(text)
        return 2 * BUTTON_MARGIN_Y + text_h

    def _draw_button(self, text, x, y):
        """绘制按钮"""
        btn_w = self._get_button_width(text)
        btn_h = self._get_button_height(text)
        
        self.ui_img.draw_rect(x, y, btn_w, btn_h, image.COLOR_WHITE, 2)
        self.ui_img.draw_string(x + BUTTON_MARGIN_X, y + BUTTON_MARGIN_Y, 
                               text, image.COLOR_WHITE)
        return [x, y, btn_w, btn_h]

    def _is_touch_in_button(self, x, y, btn_pos):
        """检查触摸是否在按钮内"""
        btn_x, btn_y, btn_w, btn_h = btn_pos
        return (btn_x < x < btn_x + btn_w) and (btn_y < y < btn_y + btn_h)

    def _opencv_hsv_binary(self, img_array, h_min, h_max, s_min, s_max, v_min, v_max):
        """使用OpenCV进行HSV二值化"""
        try:
            # 转换为HSV
            hsv = cv2.cvtColor(img_array, cv2.COLOR_RGB2HSV)
            
            # 创建掩码
            lower_hsv = np.array([h_min, s_min, v_min])
            upper_hsv = np.array([h_max, s_max, v_max])
            mask = cv2.inRange(hsv, lower_hsv, upper_hsv)
            
            # 转换为RGB格式的二值图像
            binary_rgb = cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB)
            return binary_rgb
            
        except Exception as e:
            print(f"OpenCV HSV二值化失败: {e}")
            return img_array

    def _maix_to_opencv(self, maix_img):
        """将MaixPy图像转换为OpenCV格式"""
        try:
            # 获取图像数据
            width = maix_img.width()
            height = maix_img.height()
            
            # 创建numpy数组
            img_array = np.zeros((height, width, 3), dtype=np.uint8)
            
            # 逐像素复制 (这可能比较慢，但确保兼容性)
            for y in range(height):
                for x in range(width):
                    pixel = maix_img.get_pixel(x, y)
                    if isinstance(pixel, (list, tuple)) and len(pixel) >= 3:
                        img_array[y, x] = [pixel[0], pixel[1], pixel[2]]
                    else:
                        # 处理整数格式像素
                        r = (pixel >> 16) & 0xFF
                        g = (pixel >> 8) & 0xFF  
                        b = pixel & 0xFF
                        img_array[y, x] = [r, g, b]
            
            return img_array
            
        except Exception as e:
            print(f"图像转换失败: {e}")
            return None

    def _opencv_to_maix(self, cv_img, target_img):
        """将OpenCV图像转换回MaixPy格式"""
        try:
            height, width = cv_img.shape[:2]
            for y in range(height):
                for x in range(width):
                    if len(cv_img.shape) == 3:
                        r, g, b = cv_img[y, x]
                        target_img.set_pixel(x, y, [int(r), int(g), int(b)])
                    else:
                        # 灰度图
                        val = cv_img[y, x]
                        target_img.set_pixel(x, y, [int(val), int(val), int(val)])
        except Exception as e:
            print(f"图像转换回MaixPy失败: {e}")

    def _handle_touch(self, x, y):
        """处理触摸事件"""
        # 退出按钮
        if self._is_touch_in_button(x, y, self.buttons["exit"]):
            self.exit_flag = True
            return
            
        # 二值化按钮
        if self._is_touch_in_button(x, y, self.buttons["binary"]):
            self.in_binary_mode = not self.in_binary_mode
            print(f"二值化模式: {'开启' if self.in_binary_mode else '关闭'}")
            return
            
        # 参数按钮
        for label, btn_pos in self.buttons["params"].items():
            if self._is_touch_in_button(x, y, btn_pos):
                self.selected_param = label[1:]  # 去掉"<"前缀
                print(f"选中参数: {self.selected_param}")
                return
                
        # 右侧区域调整参数
        if x > SCREEN_WIDTH / 2 and self.selected_param:
            self._adjust_param(y)

    def _adjust_param(self, touch_y):
        """调整参数值"""
        param = self.selected_param
        min_val, max_val = PARAM_RANGES[param]
        
        # 上半屏增大，下半屏减小
        if touch_y < SCREEN_HEIGHT / 2:
            new_val = self.hsv_params[param] + ADJUST_STEP
        else:
            new_val = self.hsv_params[param] - ADJUST_STEP
            
        self.hsv_params[param] = max(min_val, min(new_val, max_val))
        print(f"{param} = {self.hsv_params[param]}")

    def _update_ui_status(self, img):
        """更新状态显示"""
        status_y = 200
        
        # 清除状态区域
        img.draw_rect(0, status_y, SCREEN_WIDTH, SCREEN_HEIGHT - status_y, 
                     image.COLOR_BLACK, -1)
        
        # 显示参数值
        for i, (param, value) in enumerate(self.hsv_params.items()):
            color = image.COLOR_RED if param == self.selected_param else image.COLOR_WHITE
            img.draw_string(10, status_y + i * 15, f"{param}: {value}", color)
            
        # 显示模式状态
        mode_text = "Binary: ON" if self.in_binary_mode else "Binary: OFF"
        img.draw_string(SCREEN_WIDTH - 100, status_y, mode_text, image.COLOR_WHITE)

    def run(self):
        """运行阈值调整工具"""
        print("HSV阈值调整工具启动")
        print("- 点击参数按钮选择要调整的参数")
        print("- 在右侧区域触摸调整数值")
        print("- 点击Binary切换二值化显示")
        
        # 计算二值化显示区域
        binary_area = {
            "x": 120, "y": 30,
            "w": SCREEN_WIDTH - 130, "h": 160
        }
        
        while not self.exit_flag:
            # 读取摄像头
            img = self.cam.read()
            original_img = img.copy()
            
            # 绘制UI
            img.draw_image(0, 0, self.ui_img)
            
            # 二值化模式
            if self.in_binary_mode:
                # 裁剪区域
                crop = original_img.crop(binary_area["x"], binary_area["y"],
                                       binary_area["w"], binary_area["h"])
                
                # 转换为OpenCV格式并进行HSV二值化
                cv_img = self._maix_to_opencv(crop)
                if cv_img is not None:
                    binary_cv = self._opencv_hsv_binary(cv_img,
                        self.hsv_params["H_min"], self.hsv_params["H_max"],
                        self.hsv_params["S_min"], self.hsv_params["S_max"], 
                        self.hsv_params["V_min"], self.hsv_params["V_max"])
                    
                    # 转换回MaixPy格式
                    binary_maix = image.Image(binary_area["w"], binary_area["h"])
                    self._opencv_to_maix(binary_cv, binary_maix)
                    
                    # 显示二值化结果
                    img.draw_image(binary_area["x"], binary_area["y"], binary_maix)
                
                # 绘制红色边框
                img.draw_rect(binary_area["x"], binary_area["y"],
                             binary_area["w"], binary_area["h"], 
                             image.COLOR_RED, 1)
            
            # 处理触摸
            touch_x, touch_y, pressed = self.ts.read()
            if pressed:
                self._handle_touch(touch_x, touch_y)
            
            # 更新状态显示
            self._update_ui_status(img)
            
            # 显示图像
            self.disp.show(img)
            
        # 返回最终阈值
        return (self.hsv_params["H_min"], self.hsv_params["H_max"],
                self.hsv_params["S_min"], self.hsv_params["S_max"],
                self.hsv_params["V_min"], self.hsv_params["V_max"])

def get_hsv_threshold(disp=None):
    """获取HSV阈值的简单接口"""
    tool = HSVThresholdTool(disp)
    return tool.run()

if __name__ == "__main__":
    threshold = get_hsv_threshold()
    print(f"最终HSV阈值: {threshold}")