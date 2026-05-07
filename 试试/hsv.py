# ===================== hsv.py =====================
# 导入必要的模块
from maix import image, camera, display, time, touchscreen, app
import math
import colorsys  # 用于颜色空间转换

# ------------------ 配置与常量定义（集中管理可配置项） ------------------
# 屏幕与摄像头参数
SCREEN_WIDTH, SCREEN_HEIGHT = 320, 240
CAMERA_RESOLUTION = (SCREEN_WIDTH, SCREEN_HEIGHT)

# HSV参数范围常量（避免硬编码，统一维护）
PARAM_RANGES = {
    "H_min": (0, 179),    # H通道范围 (0-179)
    "H_max": (0, 179),
    "S_min": (0, 255),    # S通道范围 (0-255)
    "S_max": (0, 255),
    "V_min": (0, 255),    # V通道范围 (0-255)
    "V_max": (0, 255)
}

# 其他常量
MIN_AREA = 100          # 色块最小有效面积
ADJUST_STEP = 5         # 参数调整步长 (HSV范围更大，调整步长也相应增加)
BUTTON_MARGIN_X = 4     # 按钮水平边距
BUTTON_MARGIN_Y = 4     # 按钮垂直边距


# ------------------ 颜色空间转换函数 ------------------
def hsv_to_rgb(h, s, v):
    """将HSV值转换为RGB值
    
    参数:
        h: 色调 (0-179)
        s: 饱和度 (0-255)
        v: 亮度 (0-255)
        
    返回:
        (r, g, b): RGB值 (0-255)
    """
    # 将HSV范围调整为colorsys模块期望的范围 (0-1)
    h = h / 179.0
    s = s / 255.0
    v = v / 255.0
    
    # 转换为RGB (0-1范围)
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    
    # 转换为0-255范围
    r = int(r * 255)
    g = int(g * 255)
    b = int(b * 255)
    
    return (r, g, b)

def hsv_to_rgb_threshold(h_min, h_max, s_min, s_max, v_min, v_max):
    """将HSV阈值范围转换为RGB阈值范围
    
    参数:
        h_min, h_max: H通道范围 (0-179)
        s_min, s_max: S通道范围 (0-255)
        v_min, v_max: V通道范围 (0-255)
        
    返回:
        (r_min, r_max, g_min, g_max, b_min, b_max): RGB阈值范围
    """
    # 转换HSV最小值到RGB
    r_min, g_min, b_min = hsv_to_rgb(h_min, s_min, v_min)
    
    # 转换HSV最大值到RGB
    r_max, g_max, b_max = hsv_to_rgb(h_max, s_max, v_max)
    
    # 确保最小值小于最大值
    if r_min > r_max:
        r_min, r_max = r_max, r_min
    if g_min > g_max:
        g_min, g_max = g_max, g_min
    if b_min > b_max:
        b_min, b_max = b_max, b_min
    
    return (r_min, r_max, g_min, g_max, b_min, b_max)

def try_convert_to_hsv(img):
    """尝试将图像转换为HSV颜色空间
    
    参数:
        img: 输入图像
        
    返回:
        转换后的图像或原始图像（如果转换失败）
    """
    try:
        # 尝试使用MaixPy的API将图像转换为HSV
        # 注意：这个函数可能不存在，取决于MaixPy的版本
        hsv_img = img.to_hsv()
        print("成功将图像转换为HSV颜色空间")
        return hsv_img
    except Exception as e:
        print(f"无法转换为HSV: {e}")
        return img  # 如果转换失败，返回原始图像

def manual_hsv_binary(img, h_min, h_max, s_min, s_max, v_min, v_max):
    """手动实现HSV二值化
    
    如果MaixPy不支持HSV二值化，我们可以尝试手动实现
    这个函数尝试创建一个新的二值化图像，基于HSV阈值
    
    参数:
        img: 输入图像
        h_min, h_max, s_min, s_max, v_min, v_max: HSV阈值
        
    返回:
        二值化后的图像
    """
    try:
        # 创建一个新的二值化图像
        binary_img = image.Image(img.width(), img.height(), image.GRAYSCALE)
        
        # 遍历图像的每个像素（注意：这可能非常慢）
        for x in range(img.width()):
            for y in range(img.height()):
                # 获取像素的RGB值
                r, g, b = img.get_pixel(x, y)
                
                # 将RGB转换为HSV（这是一个简化版本）
                # 实际上我们应该使用更准确的RGB到HSV转换
                # 但为了简单起见，我们使用这个近似方法
                max_val = max(r, g, b)
                min_val = min(r, g, b)
                delta = max_val - min_val
                
                # 计算H值 (0-179)
                h = 0
                if delta != 0:
                    if max_val == r:
                        h = 30 * ((g - b) / delta % 6)
                    elif max_val == g:
                        h = 30 * ((b - r) / delta + 2)
                    else:  # max_val == b
                        h = 30 * ((r - g) / delta + 4)
                
                # 计算S值 (0-255)
                s = 0 if max_val == 0 else int(delta * 255 / max_val)
                
                # V值就是max_val (0-255)
                v = max_val
                
                # 检查像素是否在HSV阈值范围内
                if (h_min <= h <= h_max and 
                    s_min <= s <= s_max and 
                    v_min <= v <= v_max):
                    binary_img.set_pixel(x, y, 255)  # 白色
                else:
                    binary_img.set_pixel(x, y, 0)    # 黑色
        
        return binary_img
    except Exception as e:
        print(f"手动HSV二值化失败: {e}")
        return img  # 如果失败，返回原始图像

# ------------------ 核心类定义（封装状态与方法） ------------------
class ColorThresholdConfig:
    def __init__(self, disp=None):
        # 初始化硬件
        self.cam = camera.Camera(*CAMERA_RESOLUTION)
        self.disp = disp if disp is not None else display.Display()
        self.ts = touchscreen.TouchScreen()

        # 状态变量
        self.hsv_params = {
            "H_min": 30, "H_max": 80,     # 默认绿色范围
            "S_min": 70, "S_max": 255,    # 中等到高饱和度
            "V_min": 50, "V_max": 255     # 中等到高亮度
        }
        self.in_binary_mode = False  # 二值化显示模式
        self.exit_flag = False       # 退出标志
        self.selected_param = None   # 当前选中参数
        self.ui_img = image.Image(SCREEN_WIDTH, SCREEN_HEIGHT)  # UI背景

        # 按钮位置存储（key: 按钮标签, value: [x, y, w, h]）
        self.buttons = {
            "exit": None,
            "binary": None,
            "params": {}  # 存储参数按钮: {label: pos}
        }

        # 初始化UI
        self._init_ui()

    def _init_ui(self):
        """初始化UI界面（绘制背景与按钮）"""
        # 绘制白色背景
        self.ui_img.draw_rect(0, 0, self.ui_img.width(), self.ui_img.height(), image.COLOR_WHITE)

        # 绘制退出按钮（右上角）
        exit_label = "< Exit"
        self.buttons["exit"] = self._draw_button(exit_label,
                                                x=SCREEN_WIDTH - self._get_button_width(exit_label),
                                                y=0)

        # 绘制二值化切换按钮（顶部中间）
        binary_label = "< Binary"
        btn_width = self._get_button_width(binary_label)
        self.buttons["binary"] = self._draw_button(binary_label,
                                                  x=(SCREEN_WIDTH - btn_width) // 2,
                                                  y=0)

        # 绘制参数调整按钮（左侧垂直排列）
        param_labels = ["<H_min", "<H_max", "<S_min", "<S_max", "<V_min", "<V_max"]
        y_offset = 0  # 垂直偏移量
        for label in param_labels:
            self.buttons["params"][label] = self._draw_button(label, x=0, y=y_offset)
            # 更新偏移量（下一个按钮在当前按钮下方）
            y_offset += self.buttons["params"][label][3]

    def _get_text_size(self, text):
        """获取文本尺寸（封装重复调用）"""
        return image.string_size(text)

    def _get_button_width(self, text):
        """计算按钮宽度（文本宽 + 2倍水平边距）"""
        text_w, _ = self._get_text_size(text)
        return 2 * BUTTON_MARGIN_X + text_w

    def _get_button_height(self, text):
        """计算按钮高度（文本高 + 2倍垂直边距）"""
        _, text_h = self._get_text_size(text)
        return 2 * BUTTON_MARGIN_Y + text_h

    def _draw_button(self, text, x, y):
        """绘制按钮并返回位置信息 [x, y, w, h]"""
        text_w, text_h = self._get_text_size(text)
        btn_w = self._get_button_width(text)
        btn_h = self._get_button_height(text)

        # 绘制按钮边框
        self.ui_img.draw_rect(x, y, btn_w, btn_h, image.COLOR_WHITE, 2)
        # 绘制按钮文本
        self.ui_img.draw_string(x + BUTTON_MARGIN_X, y + BUTTON_MARGIN_Y,
                               text, image.COLOR_WHITE)
        return [x, y, btn_w, btn_h]

    def _is_touch_in_button(self, x, y, btn_pos):
        """判断触摸点是否在按钮区域内"""
        btn_x, btn_y, btn_w, btn_h = btn_pos
        return (btn_x < x < btn_x + btn_w) and (btn_y < y < btn_y + btn_h)

    def _update_ui_status(self, img):
        """更新UI状态显示（参数值、模式状态）"""
        # 状态显示区域起始Y坐标（参数按钮下方）
        status_y = sum(btn[3] for btn in self.buttons["params"].values()) + 10

        # 绘制状态区域背景（白色覆盖）
        img.draw_rect(0, status_y, SCREEN_WIDTH, SCREEN_HEIGHT - status_y, image.COLOR_WHITE)

        # 显示HSV参数值（选中参数标红）
        for i, (param, value) in enumerate(self.hsv_params.items()):
            color = image.COLOR_RED if param == self.selected_param else image.COLOR_BLACK
            img.draw_string(10, status_y + i * 15, f"{param}: {value}", color)

        # 显示二值化模式状态
        mode_text = "Binary: ON" if self.in_binary_mode else "Binary: OFF"
        img.draw_string(SCREEN_WIDTH - 100, status_y, mode_text, image.COLOR_BLACK)

    def _handle_touch(self, x, y):
        """处理触摸事件（拆分逻辑，减少主循环复杂度）"""
        # 1. 检查是否点击退出按钮
        if self._is_touch_in_button(x, y, self.buttons["exit"]):
            self.exit_flag = True
            return

        # 2. 检查是否点击二值化切换按钮
        if self._is_touch_in_button(x, y, self.buttons["binary"]):
            self.in_binary_mode = not self.in_binary_mode
            print(f"二值化模式: {'开启' if self.in_binary_mode else '关闭'}")
            return

        # 3. 检查是否点击参数按钮（选中参数）
        for label, btn_pos in self.buttons["params"].items():
            if self._is_touch_in_button(x, y, btn_pos):
                self.selected_param = label[1:]  # 去掉前缀"<"
                print(f"选中参数: {self.selected_param}")
                return

        # 4. 右侧区域触摸（调整选中的参数）
        if x > SCREEN_WIDTH / 2 and self.selected_param:
            self._adjust_param(y)

    def _adjust_param(self, touch_y):
        """根据触摸Y坐标调整参数（上半部分增大，下半部分减小）"""
        param = self.selected_param
        min_val, max_val = PARAM_RANGES[param]

        # 上半屏触摸：增大参数；下半屏触摸：减小参数
        if touch_y < SCREEN_HEIGHT / 2:
            new_val = self.hsv_params[param] + ADJUST_STEP
        else:
            new_val = self.hsv_params[param] - ADJUST_STEP

        # 限制在有效范围内
        self.hsv_params[param] = max(min_val, min(new_val, max_val))
        print(f"{param} = {self.hsv_params[param]}")

    def run_threshold_adjust(self):
        """运行阈值调整模式（主交互逻辑）"""
        print("HSV阈值调整模式：")
        print(" - 点击< Binary切换二值化显示")
        print(" - 点击< Exit退出调整")
        print(" - 点击参数按钮选择参数，右侧触摸调整值")

        # 预计算二值化显示区域（固定不变，无需每次循环计算）
        max_btn_width = max(btn[2] for btn in self.buttons["params"].values())
        top_btn_height = max(self.buttons["exit"][3], self.buttons["binary"][3])
        binary_area = {
            "x": max_btn_width + 5,
            "y": top_btn_height + 5,
            "w": SCREEN_WIDTH - max_btn_width - 10,  # 左右各留5px边距
            "h": SCREEN_HEIGHT - top_btn_height - 10
        }

        while not self.exit_flag:
            # 读取摄像头图像
            img = self.cam.read()
            original_img = img.copy()  # 保存原始图像
            # 绘制UI背景
            img.draw_image(0, 0, self.ui_img)

            # 二值化模式处理
            current_threshold = (
                self.hsv_params["H_min"], self.hsv_params["H_max"],
                self.hsv_params["S_min"], self.hsv_params["S_max"],
                self.hsv_params["V_min"], self.hsv_params["V_max"]
            )
            if self.in_binary_mode:
                # 裁剪显示区域并二值化
                crop = original_img.crop(
                    binary_area["x"], binary_area["y"],
                    binary_area["w"], binary_area["h"]
                )
                # 获取HSV参数
                h_min = self.hsv_params["H_min"]
                h_max = self.hsv_params["H_max"]
                s_min = self.hsv_params["S_min"]
                s_max = self.hsv_params["S_max"]
                v_min = self.hsv_params["V_min"]
                v_max = self.hsv_params["V_max"]
                
                # 创建HSV阈值
                hsv_threshold = [(h_min, h_max, s_min, s_max, v_min, v_max)]
                print(f"HSV阈值: {hsv_threshold}")
                
                # 方法1: 将HSV阈值转换为RGB阈值
                r_min, r_max, g_min, g_max, b_min, b_max = hsv_to_rgb_threshold(h_min, h_max, s_min, s_max, v_min, v_max)
                rgb_threshold = [(r_min, r_max, g_min, g_max, b_min, b_max)]
                print(f"转换后的RGB阈值: {rgb_threshold}")
                
                # 尝试使用转换后的RGB阈值进行二值化
                try:
                    crop.binary(rgb_threshold)
                    print("使用转换后的RGB阈值成功")
                except Exception as e:
                    print(f"RGB阈值失败: {e}")
                    
                    # 方法2: 尝试直接使用HSV阈值
                    try:
                        crop.binary(hsv_threshold)
                        print("直接使用HSV阈值成功")
                    except Exception as e:
                        print(f"HSV阈值失败: {e}")
                        
                        # 方法3: 尝试手动实现HSV二值化
                        try:
                            print("尝试手动HSV二值化")
                            binary_crop = manual_hsv_binary(crop, h_min, h_max, s_min, s_max, v_min, v_max)
                            crop = binary_crop
                            print("手动HSV二值化成功")
                        except Exception as e:
                            print(f"手动HSV二值化失败: {e}")
                            # 最后尝试使用默认阈值
                            crop.binary([(30, 80, 50, 255, 50, 255)])
                            print("使用默认阈值")
                
                img.draw_image(binary_area["x"], binary_area["y"], crop)  # 绘制二值化图像
                # 绘制红色边框标记二值化区域
                img.draw_rect(binary_area["x"], binary_area["y"],
                             binary_area["w"], binary_area["h"],
                             image.COLOR_RED, 1)

            # 处理触摸事件
            touch_x, touch_y, pressed = self.ts.read()
            if pressed:
                # 转换触摸坐标到屏幕坐标系
                adjusted_x, adjusted_y = image.resize_map_pos_reverse(
                    SCREEN_WIDTH, SCREEN_HEIGHT,
                    self.disp.width(), self.disp.height(),
                    image.Fit.FIT_CONTAIN, touch_x, touch_y
                )
                self._handle_touch(adjusted_x, adjusted_y)

            # 更新UI状态显示
            self._update_ui_status(img)
            # 显示图像
            self.disp.show(img)

        return current_threshold

    def run_blob_detection(self, threshold):
        """运行色块检测模式（调整完成后）"""
        while not app.need_exit():
            img = self.cam.read()
            # 获取HSV阈值
            h_min, h_max, s_min, s_max, v_min, v_max = threshold
            
            # 创建HSV阈值
            hsv_threshold = [threshold]
            print(f"HSV阈值: {hsv_threshold}")
            
            # 将HSV阈值转换为RGB阈值
            r_min, r_max, g_min, g_max, b_min, b_max = hsv_to_rgb_threshold(h_min, h_max, s_min, s_max, v_min, v_max)
            rgb_threshold = [(r_min, r_max, g_min, g_max, b_min, b_max)]
            print(f"转换后的RGB阈值: {rgb_threshold}")
            
            # 尝试使用转换后的RGB阈值查找色块
            try:
                blobs = img.find_blobs(rgb_threshold, merge=True)
                print("使用转换后的RGB阈值查找色块成功")
            except Exception as e:
                print(f"RGB阈值查找色块失败: {e}")
                
                # 尝试直接使用HSV阈值
                try:
                    blobs = img.find_blobs(hsv_threshold, merge=True)
                    print("直接使用HSV阈值查找色块成功")
                except Exception as e:
                    print(f"HSV阈值查找色块失败: {e}")
                    # 最后尝试使用默认阈值
                    blobs = img.find_blobs([(30, 80, 50, 255, 50, 255)], merge=True)
                    print("使用默认阈值查找色块")

            # 绘制并打印有效色块（过滤小面积）
            for blob in blobs:
                if blob.area() < MIN_AREA:
                    continue
                # 绘制矩形和中心点
                img.draw_rect(blob[0], blob[1], blob[2], blob[3], image.COLOR_GREEN)
                img.draw_cross(blob[5], blob[6], image.COLOR_GREEN, size=3)
                print(f"色块中心: ({blob.cx()}, {blob.cy()}) 面积: {blob.area()}")

            self.disp.show(img)


# ------------------ 新增的极简接口 ------------------

def get_hsv_threshold(disp=None):
    cfg = ColorThresholdConfig(disp=disp)
    return cfg.run_threshold_adjust()

# 为了兼容性，保留原来的函数名
def get_lab_threshold(disp=None):
    """兼容旧版本的函数名，实际上返回HSV阈值"""
    return get_hsv_threshold(disp)


# ------------------ 你自己的 main 示例 ------------------
if __name__ == "__main__":
    # 1) 只拿阈值
    th = get_hsv_threshold()  # 或者使用 get_lab_threshold() 保持兼容性
    print("拿到最终HSV阈值：", th)

    # 2) 如果想继续跑色块检测，可以再建一个对象
    # cfg = ColorThresholdConfig()
    # cfg.run_blob_detection(th)
