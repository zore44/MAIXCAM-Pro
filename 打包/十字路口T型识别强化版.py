from maix import camera, image, time, app, touchscreen, display
import math
from collections import Counter
import serial  # 导入串口库

# 日志级别设置
LOG_LEVEL_DEBUG = 1
LOG_LEVEL_INFO = 2
LOG_LEVEL_WARNING = 3
LOG_LEVEL_ERROR = 4
LOG_LEVEL = LOG_LEVEL_INFO  # 设置默认日志级别为INFO，只显示重要信息

def log(level, message):
    if level >= LOG_LEVEL:
        print(message)

class AppState:
    def __init__(self):
        self.intersection_history = []
        self.last_stable_type = "无"
        self.stable_count = 0
        self.last_sent_time = 0  # 记录上次发送时间(毫秒)
        self.send_interval = 100  # 发送间隔(毫秒)

class GUI:
    def __init__(self) -> None:
        self.background = None
        self.items      = list()
        self.callbacks  = list()
        self.labels     = list()

        self.touch_x = 0
        self.touch_y = 0

        image.load_font("sourcehansans", "/maixapp/share/font/SourceHanSansCN-Regular.otf")
        image.set_default_font("sourcehansans")

        self._ts   = touchscreen.TouchScreen()
        self._disp = display.Display()
        self._last_pressed = 0

    def _is_in_item(self, item_id : int, x : int, y : int) -> bool:
        if item_id >= len(self.items) or self.background == None:
            return False
        
        item_pos = self.items[item_id]
        item_disp_pos = image.resize_map_pos(self.background.width(), self.background.height(), self._disp.width(), self._disp.height(), image.Fit.FIT_CONTAIN, item_pos[0], item_pos[1], item_pos[2], item_pos[3])
        
        if x > item_disp_pos[0] and x < (item_disp_pos[0]+item_disp_pos[2]) and y > item_disp_pos[1] and y < (item_disp_pos[1]+item_disp_pos[3]):
            return True
        else:
            return False

    def createButton(self, x : int, y:int, width : int, height : int) -> int:
        '''
        创建一个按钮组件，参数为按钮的位置坐标
        '''
        item_id = len(self.items)
        self.items.append([x, y, width, height])
        self.callbacks.append(None)
        self.labels.append(None)
        return item_id

    def setItemCallback(self, item_id : int, cb ) -> None:
        '''
        设置界面组件的回调函数，比如按钮按下时所自动调用的函数
        该回调函数原型如下:
        callback(item_id : int) -> None
        '''
        if item_id >= len(self.items):
            return
        self.callbacks[item_id] = cb

    def setItemLabel(self, item_id : int, label : str) -> None:
        '''
        设置界面组件中所显示信息
        '''
        if item_id >= len(self.items):
            return
        self.labels[item_id] = label

    def get_touch(self) -> tuple:
        '''
        返回最近时间触摸动作的位置
        '''
        if self.background == None:
            return (0,0)
            
        x, y = image.resize_map_pos_reverse(self.background.width(), self.background.height(), self._disp.width(), self._disp.height(), image.Fit.FIT_CONTAIN, self.touch_x, self.touch_y)
        x = x if x >= 0 else 0
        y = y if y >= 0 else 0
        return (x, y)

    # 修改了这里的类型提示，使用 image.Image
    def run(self, background : image.Image) -> None:
        self.background = background
        self.touch_x, self.touch_y, pressed = self._ts.read()
        # 检测按键输入
        if self._last_pressed != pressed:
            self._last_pressed = pressed

            for id in range(len(self.items)):
                if self._is_in_item(id, self.touch_x, self.touch_y):
                    if self.callbacks[id] != None:
                        self.callbacks[id](id, pressed)
                    break

        # 更新界面元素
        for id in range(len(self.items)):
            label_size = image.string_size(self.labels[id])
            label_x = (self.items[id][0] + (self.items[id][2] - label_size.width())//2) if self.items[id][2] > label_size.width() else self.items[id][0]
            label_y = (self.items[id][1] + (self.items[id][3] - label_size.height())//2) if self.items[id][3] > label_size.height() else self.items[id][1]

            self.background.draw_rect(self.items[id][0], self.items[id][1], self.items[id][2], self.items[id][3], image.COLOR_RED, 2)
            if self.labels[id] != None:
                self.background.draw_string(label_x, label_y, self.labels[id], image.COLOR_WHITE)

        self._disp.show(self.background)

#屏幕宽度和高度
_image_width  = 320
_image_height = 240
_btn_width  = _image_width//6
_btn_height = _image_height//6

_btn_id_pixel   = -1
_btn_id_binary  = -1
_to_show_binary = False
_to_get_pixel   = False

# 路口检测相关变量
_intersection_type = "无"  # 当前检测到的路口类型
_red_threshold = [(28, 48, 32, 70, -23, 33)]  # 巡线检测阈值
_red_area_threshold = 20  # 阈值调整
app_state = AppState()  # 新增状态管理对象

# 路口检测参数
# 下方区域增强参数
BOTTOM_REGION_WEIGHT = 2.0  # 提高下方区域权重
BOTTOM_REGION_EXPAND = 1.5  # 扩大下方区域

# 上方区域增强参数
TOP_REGION_WEIGHT = 1.8     # 提高上方区域权重
TOP_REGION_EXPAND = 1.4     # 扩大上方区域

# 距离检测参数
DISTANCE_MULTIPLIER = 1.3   # 距离计算乘数
MIN_LINE_MAGNITUDE = 800    # 提高最小线条强度阈值

# 多级检测参数
FAR_REGION_HEIGHT = _image_height // 8  # 远距离检测区域高度
FAR_REGION_THRESHOLD = 200              # 提高远距离检测阈值

# 自定义颜色常量
def create_color(r, g, b):
    """创建MaixPy兼容的颜色对象"""
    return image.Color(r, g, b)

COLOR_MAGENTA = create_color(255, 0, 255)
CYAN_COLOR = create_color(0, 255, 255)

def rgb_to_lab(rgb):
    '''
    实现RGB值到LAB值的转换
    '''
    # RGB到XYZ的转换矩阵
    M = [
        [0.412453, 0.357580, 0.180423],
        [0.212671, 0.715160, 0.072169],
        [0.019334, 0.119193, 0.950227]
    ]
    
    # 归一化RGB值
    r, g, b = rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0
    
    # 线性化RGB值
    r = r / 12.92 if r <= 0.04045 else ((r + 0.055) / 1.055) ** 2.4
    g = g / 12.92 if g <= 0.04045 else ((g + 0.055) / 1.055) ** 2.4
    b = b / 12.92 if b <= 0.04045 else ((b + 0.055) / 1.055) ** 2.4
    
    # 计算XYZ值
    X = M[0][0] * r + M[0][1] * g + M[0][2] * b
    Y = M[1][0] * r + M[1][1] * g + M[1][2] * b
    Z = M[2][0] * r + M[2][1] * g + M[2][2] * b
    
    # XYZ到LAB的转换
    X /= 0.95047
    Y /= 1.0
    Z /= 1.08883
    
    def f(t):
        return t ** (1/3) if t > 0.008856 else 7.787 * t + 16/116
    
    L = 116 * f(Y) - 16
    a = 500 * (f(X) - f(Y))
    b = 200 * (f(Y) - f(Z))
    
    return [L, a, b]

def set_configured_threshold(threshold):
    '''
    阈值参数信息存入配置文件
    '''
    if len(threshold) < 6:
        return 

    app.set_app_config_kv('demo_find_line', 'lmin', str(threshold[0]), False)
    app.set_app_config_kv('demo_find_line', 'lmax', str(threshold[1]), False)
    app.set_app_config_kv('demo_find_line', 'amin', str(threshold[2]), False)
    app.set_app_config_kv('demo_find_line', 'amax', str(threshold[3]), False)
    app.set_app_config_kv('demo_find_line', 'bmin', str(threshold[4]), False)
    app.set_app_config_kv('demo_find_line', 'bmax', str(threshold[5]), True)

def get_configured_threshold():
    '''
    获取所存储配置文件中的阈值参数
    '''
    # 使用指定的默认阈值
    threshold = [28, 48, 32, 70, -23, 33]
    
    # 尝试从配置文件加载
    value_str = app.get_app_config_kv('demo_find_line', 'lmin','', False)
    if len(value_str) > 0:
        threshold[0] = int(value_str)
    value_str = app.get_app_config_kv('demo_find_line', 'lmax','', False)
    if len(value_str) > 0:
        threshold[1] = int(value_str)
    value_str = app.get_app_config_kv('demo_find_line', 'amin','', False)
    if len(value_str) > 0:
        threshold[2] = int(value_str)
    value_str = app.get_app_config_kv('demo_find_line', 'amax','', False)
    if len(value_str) > 0:
        threshold[3] = int(value_str)
    value_str = app.get_app_config_kv('demo_find_line', 'bmin','', False)
    if len(value_str) > 0:
        threshold[4] = int(value_str)
    value_str = app.get_app_config_kv('demo_find_line', 'bmax','', False)
    if len(value_str) > 0:
        threshold[5] = int(value_str)
    return threshold

# 检测图像指定区域是否存在红色色块
def detect_red_in_area(img, x, y, width, height, weight=1.0, is_top_region=False):
    roi = img.copy().crop(x, y, width, height)
    blobs = roi.find_blobs(_red_threshold, pixels_threshold=_red_area_threshold, area_threshold=_red_area_threshold)
    
    # 计算区域内红色像素占比
    if len(blobs) > 0:
        total_red_pixels = sum(blob.pixels() for blob in blobs)
        roi_area = width * height
        red_ratio = total_red_pixels / roi_area
        
        # 应用权重（上方和下方区域权重更高）
        weighted_ratio = red_ratio * weight
        
        # 打印区域检测详情
        region_type = "顶部" if is_top_region else "普通"
        log(LOG_LEVEL_DEBUG, f"{region_type}区域({x},{y},{width},{height}): 红色像素比={red_ratio:.2f}, 加权比={weighted_ratio:.2f}")
        
        # 加权后超过阈值视为检测到
        return weighted_ratio > 0.1
    return False

# 检测远距离红线
def detect_far_red(img):
    far_region = (0, 0, img.width(), FAR_REGION_HEIGHT)
    roi = img.copy().crop(far_region[0], far_region[1], far_region[2], far_region[3])
    blobs = roi.find_blobs(_red_threshold, pixels_threshold=FAR_REGION_THRESHOLD, area_threshold=FAR_REGION_THRESHOLD)
    
    if len(blobs) > 0:
        largest_blob = max(blobs, key=lambda b: b.pixels())
        # 计算距离（这里使用简化算法，实际应用中可能需要更复杂的计算）
        distance = img.height() - (far_region[1] + largest_blob.cy())
        return True, distance, largest_blob
    return False, 0, None

# 计算线条距离（从图像底部到线条的垂直距离）
def calculate_line_distance(img_height, line, is_top_line=False):
    # 获取线条的两个端点
    x1, y1 = line.x1(), line.y1()
    x2, y2 = line.x2(), line.y2()
    
    # 计算线条在图像底部的投影点
    if y2 != y1:  # 避免除零错误
        k = (x2 - x1) / (y2 - y1)
        # 计算线条与图像底部(y=img_height)的交点x值
        x_bottom = int(x1 + k * (img_height - y1))
        # 确保x在图像范围内
        x_bottom = max(0, min(img_height-1, x_bottom))
        
        return img_height - max(y1, y2)  # 返回线条底部到图像底部的距离
    return 0

# 改进的区域检测逻辑（只保留上下左右四个方向）
def detect_intersection(img):
    global _intersection_type
    
    # 区域尺寸动态适应图像大小
    base_region_w, base_region_h = img.width()//4, img.height()//6
    
    # 只保留上下左右四个检测区域
    regions = {
        'top':    (img.width()//2-int(base_region_w*TOP_REGION_EXPAND//2), 
                  0, 
                  int(base_region_w*TOP_REGION_EXPAND), 
                  int(base_region_h*TOP_REGION_EXPAND)),
        'bottom': (img.width()//2-int(base_region_w*BOTTOM_REGION_EXPAND//2), 
                  img.height()-int(base_region_h*BOTTOM_REGION_EXPAND), 
                  int(base_region_w*BOTTOM_REGION_EXPAND), 
                  int(base_region_h*BOTTOM_REGION_EXPAND)),
        'left':   (0, img.height()//2-base_region_h//2, base_region_w, base_region_h),
        'right':  (img.width()-base_region_w, img.height()//2-base_region_h//2, base_region_w, base_region_h)
    }

    # 加权检测（上方和下方区域权重更高）
    red_counts = {}
    top_line_detected = False
    
    for name, (x, y, w, h) in regions.items():
        is_top_region = name in ['top']
        weight = TOP_REGION_WEIGHT if is_top_region else BOTTOM_REGION_WEIGHT if name == 'bottom' else 1.0
        
        red_counts[name] = detect_red_in_area(img, x, y, w, h, weight, is_top_region)
        
        # 在图像上绘制检测区域
        color = image.COLOR_GREEN if red_counts[name] else image.COLOR_RED
        img.draw_rect(x, y, w, h, color=color, thickness=2)
        # 绘制区域名称
        img.draw_string(x, y, name, color=image.COLOR_WHITE, scale=0.8)
        
        # 记录顶部区域是否检测到红线
        if is_top_region and red_counts[name]:
            top_line_detected = True
    
    # 检测远距离红线
    far_detected, far_distance, far_blob = detect_far_red(img)
    if far_detected:
        log(LOG_LEVEL_DEBUG, f"远距离检测: 距离={far_distance}, 像素数={far_blob.pixels()}")
        # 在图像上标记远距离检测到的红线
        x, y = far_blob.cx(), far_blob.cy()
        img.draw_circle(x, y, 10, COLOR_MAGENTA, 2)
        img.draw_string(x-15, y-15, "远", color=COLOR_MAGENTA, scale=0.8)
    
    # 打印各区域检测结果用于调试
    log(LOG_LEVEL_DEBUG, f"区域检测结果: 上={red_counts['top']}, 下={red_counts['bottom']}, 左={red_counts['left']}, 右={red_counts['right']}")
    
    # 动态判断逻辑
    main_lines = sum(red_counts[k] for k in ['top','bottom','left','right'])
    
    # 十字路口检测逻辑：上下左右四个方向都检测到红线
    is_crossroad = (red_counts['top'] and red_counts['bottom'] and 
                   red_counts['left'] and red_counts['right'])
    
    # T型路口检测逻辑：下左右三个方向检测到红线
    is_t_junction = (red_counts['bottom'] and red_counts['left'] and red_counts['right'])
    
    # L型路口检测逻辑：相邻两个方向检测到红线
    is_l_junction = (
        (red_counts['top'] and red_counts['left']) or
        (red_counts['top'] and red_counts['right']) or
        (red_counts['bottom'] and red_counts['left']) or
        (red_counts['bottom'] and red_counts['right'])
    )
    
    # 改进的路口类型判断
    if is_crossroad:
        _intersection_type = "十字路口"
    elif is_t_junction:
        _intersection_type = "T型路口"
    elif is_l_junction:
        _intersection_type = "L型路口"
    elif main_lines == 3:
        # 其他三个方向的组合，标记为复杂路口
        _intersection_type = "复杂路口"
    elif main_lines == 2:
        if red_counts['top'] and red_counts['bottom']:
            _intersection_type = "垂直线"
        elif red_counts['left'] and red_counts['right']:
            _intersection_type = "水平线"
        else:
            _intersection_type = "L型路口（可能）"
    elif main_lines == 1:
        if red_counts['top']:
            _intersection_type = "上方线"
        elif red_counts['bottom']:
            _intersection_type = "下方线"
        elif red_counts['left']:
            _intersection_type = "左侧线"
        elif red_counts['right']:
            _intersection_type = "右侧线"
    else:
        _intersection_type = "无"
    
    return _intersection_type, red_counts, top_line_detected, far_detected

# 改进的时序滤波（防抖动）
def get_stable_intersection(current_type):
    global app_state
    
    app_state.intersection_history.append(current_type)
    if len(app_state.intersection_history) > 10:  # 增加历史记录长度
        app_state.intersection_history.pop(0)
    
    # 统计最近结果
    counter = Counter(app_state.intersection_history)
    most_common = counter.most_common(1)
    
    # 针对不同类型设置不同的确认阈值
    if current_type in ["十字路口", "T型路口"]:
        required_count = 6  # 复杂路口需要更多确认
    else:
        required_count = 4  # 其他类型较低要求
    
    if most_common[0][1] >= required_count:
        if most_common[0][0] != app_state.last_stable_type:
            app_state.stable_count += 1
            if app_state.stable_count >= 2:  # 连续2周期确认
                app_state.last_stable_type = most_common[0][0]
                app_state.stable_count = 0
        return app_state.last_stable_type
    
    # 显示置信度信息
    confidence = most_common[0][1] / len(app_state.intersection_history) * 100
    return f"{most_common[0][0]} ({confidence:.0f}%)"

def btn_pressed(btn_id, state):
    '''
    界面上按键的状态改变回调函数
    '''
    global _to_show_binary, _to_get_pixel, _btn_id_binary, _btn_id_pixel
    if state == 0: #只响应触摸抬起的动作
        return 

    if btn_id == _btn_id_binary:
        _to_show_binary = not _to_show_binary
        if _to_get_pixel:
            _to_get_pixel = False
    elif btn_id == _btn_id_pixel:
        _to_get_pixel = not _to_get_pixel

# 串口发送函数
def send_intersection_type(ser, intersection_type):
    if ser.is_open:
        try:
            if intersection_type == "十字路口":
                ser.write(b'S')  # 发送'S'表示十字路口
                log(LOG_LEVEL_INFO, "串口发送: S (十字路口)")
            elif intersection_type == "T型路口":
                ser.write(b'T')  # 发送'T'表示T型路口
                log(LOG_LEVEL_INFO, "串口发送: T (T型路口)")
            else:
                ser.write(b'N')  # 发送'N'表示其他情况
                log(LOG_LEVEL_INFO, "串口发送: N (其他)")
        except Exception as e:
            log(LOG_LEVEL_ERROR, f"串口发送错误: {e}")

def main():
    global _to_show_binary, _to_get_pixel, _btn_id_binary, _btn_id_pixel, _intersection_type

    log(LOG_LEVEL_INFO, app.get_app_config_path())
    cam = camera.Camera(_image_width, _image_height) 
    gui = GUI()

    _btn_id_pixel = gui.createButton(0, _image_height-_btn_height, _btn_width, _btn_height)
    gui.setItemLabel(_btn_id_pixel, '取阈值')
    gui.setItemCallback(_btn_id_pixel, btn_pressed)

    _btn_id_binary = gui.createButton(_image_width-_btn_width, _image_height-_btn_height, _btn_width, _btn_height)
    gui.setItemLabel(_btn_id_binary, '二值化')
    gui.setItemCallback(_btn_id_binary, btn_pressed)

    last_x = -1
    last_y = -1
    threshold = get_configured_threshold()
    log(LOG_LEVEL_INFO, f"当前阈值: {threshold}")
    
    # 初始化串口
    try:
        ser = serial.Serial(
            port="/dev/ttyS1",  # 根据实际情况修改串口号
            baudrate=115200,    # 波特率
            timeout=0.1         # 超时时间
        )
        log(LOG_LEVEL_INFO, "串口初始化成功")
    except Exception as e:
        log(LOG_LEVEL_ERROR, f"串口初始化失败: {e}")
        ser = None
    
    last_sent_type = None  # 记录上次发送的路口类型
    
    while not app.need_exit():
        # 获取当前时间（使用MaixPy平台支持的time.ticks_s()，并转换为毫秒）
        current_time = time.ticks_s() * 1000
        
        # 1. 读取图像
        img = cam.read()
        if _to_show_binary:
            img = img.binary([threshold], False)
        
        # 2. 图像取阈值
        if _to_get_pixel:
            x,y = gui.get_touch()
            if last_x != x or last_y != y:
                last_x = x
                last_y = y

                rgb = img.get_pixel(x, y, True)
                lab = rgb_to_lab(rgb)
                if len(lab) >= 3:
                    threshold[0] = math.floor(lab[0]) - 30
                    threshold[0] = threshold[0] if threshold[0] >= 0 else 0

                    threshold[1] = math.ceil(lab[0]) + 30
                    threshold[1] = threshold[1] if threshold[1] <= 100 else 100
                    
                    threshold[2] = math.floor(lab[1]) - 10
                    threshold[2] = threshold[2] if threshold[2] >= -128 else -128

                    threshold[3] = math.ceil(lab[1]) + 10
                    threshold[3] = threshold[3] if threshold[3] <= 127 else 127

                    threshold[4] = math.floor(lab[2]) - 10
                    threshold[4] = threshold[4] if threshold[4] >= -128 else -128

                    threshold[5] = math.ceil(lab[2]) + 10
                    threshold[5] = threshold[5] if threshold[5] <= 127 else 127
                    log(LOG_LEVEL_INFO, f"更新阈值: {threshold}")
                    set_configured_threshold(threshold)
            img.draw_cross(x, y, image.COLOR_YELLOW, 8, 2)
        
        # 3. 检测路口
        current_intersection, red_counts, top_line_detected, far_detected = detect_intersection(img)  # 获取路口类型和检测结果
        stable_intersection = get_stable_intersection(current_intersection)
        
        # 4. 线性回归寻迹画线并计算距离
        area_threshold = 100
        lines = img.get_regression([threshold], area_threshold=area_threshold, pixels_threshold=area_threshold)
        max_distance = 0
        strongest_line = None
        
        for line in lines:
            if line.magnitude() > MIN_LINE_MAGNITUDE:  # 过滤弱线条
                # 计算线条距离
                distance = calculate_line_distance(img.height(), line)
                
                # 记录最强线条及其距离
                if line.magnitude() > (strongest_line.magnitude() if strongest_line else 0):
                    strongest_line = line
                    max_distance = distance
                
                # 绘制线条
                img.draw_line(line.x1(), line.y1(), line.x2(), line.y2(), image.COLOR_GREEN, 2)
                
                # 显示线条信息
                img.draw_string(0, 0, f"强度:{line.magnitude()} 角度:{line.theta()} 距离:{distance:.1f}", color=image.COLOR_WHITE)
        
        # 5. 显示检测结果
        img.draw_string(0, 20, f"路口类型: {stable_intersection}", color=image.COLOR_WHITE, scale=1)
        img.draw_string(0, 45, f"原始检测: {current_intersection}", color=image.COLOR_YELLOW, scale=0.8)
        
        # 显示区域检测统计
        region_stats = f"主区域: {sum(1 for k in ['top','bottom','left','right'] if red_counts[k])}/4"
        img.draw_string(0, 70, region_stats, color=CYAN_COLOR, scale=0.8)
        
        # 显示顶部红线检测信息
        if top_line_detected:
            img.draw_string(0, 95, "顶部红线: 已检测", color=CYAN_COLOR, scale=0.8)
        
        # 显示远距离检测信息
        if far_detected:
            img.draw_string(0, 115, "远距离检测: 已检测", color=COLOR_MAGENTA, scale=0.8)
        
        # 显示检测到的最远线条距离
        if strongest_line:
            distance_info = f"最远红线距离: {max_distance:.1f}px"
            img.draw_string(0, 135 if far_detected else 115, distance_info, color=image.COLOR_WHITE, scale=0.8)
        
        # 6. 连续发送路口类型（添加时间间隔控制）
        if current_time - app_state.last_sent_time > app_state.send_interval:
            # 无论类型是否变化，都发送数据
            send_intersection_type(ser, stable_intersection)
            last_sent_type = stable_intersection
            app_state.last_sent_time = current_time
        
        # 7. 更新显示    
        gui.run(img)
    
    # 程序结束时关闭串口
    if ser and ser.is_open:
        ser.close()
        log(LOG_LEVEL_INFO, "串口已关闭")

if __name__ == '__main__':
    main()