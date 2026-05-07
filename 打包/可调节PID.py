from maix import camera, image, time, app, touchscreen, display, uart
import math

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

    def run(self, background : image) -> None:  # 修改这里：将Image改为image
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

# PID控制参数
Kp_angle = 0.5    # 角度比例系数
Ki_angle = 0.0    # 角度积分系数（新增）
Kd_angle = 0.1    # 角度微分系数（新增）

Kp_offset = 0.3   # 偏移比例系数
Ki_offset = 0.0   # 偏移积分系数（新增）
Kd_offset = 0.05  # 偏移微分系数（新增）

max_steering = 128 # 最大转向角度范围调整为-128到128

# PID控制器状态变量
last_angle_error = 0.0     # 上次角度误差
angle_integral = 0.0       # 角度误差积分
last_offset_error = 0.0    # 上次偏移误差
offset_integral = 0.0      # 偏移误差积分
last_time = time.time()    # 上次计算时间

# 黑色阈值 (更精确的纯黑线阈值设置)
BLACK_THRESHOLD = (0, 20, -10, 10, -10, 10)

# 图像中心（用于计算偏移）
img_center_x = _image_width // 2

# PID参数调整按钮ID
_btn_id_kp_up = -1
_btn_id_kp_down = -1
_btn_id_ki_up = -1
_btn_id_ki_down = -1
_btn_id_kd_up = -1
_btn_id_kd_down = -1

# 当前调整的PID参数组（0=角度，1=偏移）
_current_pid_group = 0

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
    threshold = [0, 100, -128, 127, -128, 127] #默认阈值

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

def save_pid_params():
    '''
    保存PID参数到配置文件
    '''
    app.set_app_config_kv('demo_find_line', 'kp_angle', str(Kp_angle), False)
    app.set_app_config_kv('demo_find_line', 'ki_angle', str(Ki_angle), False)
    app.set_app_config_kv('demo_find_line', 'kd_angle', str(Kd_angle), False)
    app.set_app_config_kv('demo_find_line', 'kp_offset', str(Kp_offset), False)
    app.set_app_config_kv('demo_find_line', 'ki_offset', str(Ki_offset), False)
    app.set_app_config_kv('demo_find_line', 'kd_offset', str(Kd_offset), True)

def load_pid_params():
    '''
    从配置文件加载PID参数
    '''
    global Kp_angle, Ki_angle, Kd_angle, Kp_offset, Ki_offset, Kd_offset
    
    value_str = app.get_app_config_kv('demo_find_line', 'kp_angle', '', False)
    if len(value_str) > 0:
        Kp_angle = float(value_str)
        
    value_str = app.get_app_config_kv('demo_find_line', 'ki_angle', '', False)
    if len(value_str) > 0:
        Ki_angle = float(value_str)
        
    value_str = app.get_app_config_kv('demo_find_line', 'kd_angle', '', False)
    if len(value_str) > 0:
        Kd_angle = float(value_str)
        
    value_str = app.get_app_config_kv('demo_find_line', 'kp_offset', '', False)
    if len(value_str) > 0:
        Kp_offset = float(value_str)
        
    value_str = app.get_app_config_kv('demo_find_line', 'ki_offset', '', False)
    if len(value_str) > 0:
        Ki_offset = float(value_str)
        
    value_str = app.get_app_config_kv('demo_find_line', 'kd_offset', '', False)
    if len(value_str) > 0:
        Kd_offset = float(value_str)

def btn_pressed(btn_id, state):
    '''
    界面上按键的装填改变回调函数
    '''
    global _to_show_binary, _to_get_pixel, _btn_id_binary, _btn_id_pixel
    global Kp_angle, Ki_angle, Kd_angle, Kp_offset, Ki_offset, Kd_offset
    global _current_pid_group
    
    if state == 0: #只响应触摸抬起的动作
        return 

    if btn_id == _btn_id_binary:
        _to_show_binary = not _to_show_binary
        if _to_get_pixel:
            _to_get_pixel = False
    elif btn_id == _btn_id_pixel:
        _to_get_pixel = not _to_get_pixel
    elif btn_id == _btn_id_kp_up:
        if _current_pid_group == 0:  # 角度PID
            Kp_angle += 0.05
            Kp_angle = round(Kp_angle, 2)
        else:  # 偏移PID
            Kp_offset += 0.05
            Kp_offset = round(Kp_offset, 2)
        save_pid_params()
    elif btn_id == _btn_id_kp_down:
        if _current_pid_group == 0:  # 角度PID
            Kp_angle = max(0, Kp_angle - 0.05)
            Kp_angle = round(Kp_angle, 2)
        else:  # 偏移PID
            Kp_offset = max(0, Kp_offset - 0.05)
            Kp_offset = round(Kp_offset, 2)
        save_pid_params()
    elif btn_id == _btn_id_ki_up:
        if _current_pid_group == 0:  # 角度PID
            Ki_angle += 0.01
            Ki_angle = round(Ki_angle, 2)
        else:  # 偏移PID
            Ki_offset += 0.01
            Ki_offset = round(Ki_offset, 2)
        save_pid_params()
    elif btn_id == _btn_id_ki_down:
        if _current_pid_group == 0:  # 角度PID
            Ki_angle = max(0, Ki_angle - 0.01)
            Ki_angle = round(Ki_angle, 2)
        else:  # 偏移PID
            Ki_offset = max(0, Ki_offset - 0.01)
            Ki_offset = round(Ki_offset, 2)
        save_pid_params()
    elif btn_id == _btn_id_kd_up:
        if _current_pid_group == 0:  # 角度PID
            Kd_angle += 0.01
            Kd_angle = round(Kd_angle, 2)
        else:  # 偏移PID
            Kd_offset += 0.01
            Kd_offset = round(Kd_offset, 2)
        save_pid_params()
    elif btn_id == _btn_id_kd_down:
        if _current_pid_group == 0:  # 角度PID
            Kd_angle = max(0, Kd_angle - 0.01)
            Kd_angle = round(Kd_angle, 2)
        else:  # 偏移PID
            Kd_offset = max(0, Kd_offset - 0.01)
            Kd_offset = round(Kd_offset, 2)
        save_pid_params()
    elif btn_id == _btn_id_pid_group:
        # 切换PID参数组
        _current_pid_group = 1 - _current_pid_group

def calculate_steering_angle(lines):
    """计算转向角度（使用完整PID控制）"""
    global last_angle_error, angle_integral, last_offset_error, offset_integral, last_time
    
    if not lines:
        return None, False
    
    line = lines[0]  # 只处理第一条检测到的直线
    
    # 获取直线参数
    theta = line.theta()
    
    # 角度转换（使0°表示水平线，90°表示垂直线）
    if theta > 90:
        theta = 270 - theta
    else:
        theta = 90 - theta
    
    # 计算直线中心点（原图坐标）
    line_center_x = (line.x1() + line.x2()) / 2
    
    # 计算直线中心与图像中心的偏移
    offset = line_center_x - img_center_x
    
    # 显示直线信息
    info = f"θ: {theta:.1f}°, 偏移: {offset:.1f}"
    
    # 计算时间间隔（秒）
    current_time = time.time()
    dt = current_time - last_time
    last_time = current_time
    
    # 计算角度误差
    angle_error = theta - 90  # 目标是垂直向上的直线（90°）
    
    # 计算偏移误差
    offset_error = offset
    
    # 角度PID控制
    angle_integral += angle_error * dt
    angle_derivative = (angle_error - last_angle_error) / dt if dt > 0 else 0
    steering_from_angle = (Kp_angle * angle_error) + (Ki_angle * angle_integral) + (Kd_angle * angle_derivative)
    
    # 偏移PID控制
    offset_integral += offset_error * dt
    offset_derivative = (offset_error - last_offset_error) / dt if dt > 0 else 0
    steering_from_offset = (Kp_offset * offset_error) + (Ki_offset * offset_integral) + (Kd_offset * offset_derivative)
    
    # 保存当前误差用于下次计算
    last_angle_error = angle_error
    last_offset_error = offset_error
    
    # 综合角度和偏移计算最终转向角
    steering_angle = steering_from_angle + steering_from_offset
    
    # 限制最大转向角在-128到128之间
    steering_angle = max(-max_steering, min(max_steering, steering_angle))
    
    return steering_angle, True

def main():
    global _to_show_binary, _to_get_pixel, _btn_id_binary, _btn_id_pixel
    global _btn_id_kp_up, _btn_id_kp_down, _btn_id_ki_up, _btn_id_ki_down, _btn_id_kd_up, _btn_id_kd_down, _btn_id_pid_group
    
    print(app.get_app_config_path())
    cam = camera.Camera(_image_width, _image_height) 
    gui = GUI()

    _btn_id_pixel = gui.createButton(0, _image_height-_btn_height, _btn_width, _btn_height)
    gui.setItemLabel(_btn_id_pixel, '取阈值')
    gui.setItemCallback(_btn_id_pixel, btn_pressed)

    _btn_id_binary = gui.createButton(_image_width-_btn_width, _image_height-_btn_height, _btn_width, _btn_height)
    gui.setItemLabel(_btn_id_binary, '二值化')
    gui.setItemCallback(_btn_id_binary, btn_pressed)
    
    # 创建PID调整按钮
    btn_y = _image_height - _btn_height * 3
    btn_width = _btn_width * 2
    
    _btn_id_kp_up = gui.createButton(_image_width//2 - btn_width, btn_y, btn_width//2, _btn_height)
    gui.setItemLabel(_btn_id_kp_up, "+Kp")
    gui.setItemCallback(_btn_id_kp_up, btn_pressed)
    
    _btn_id_kp_down = gui.createButton(_image_width//2, btn_y, btn_width//2, _btn_height)
    gui.setItemLabel(_btn_id_kp_down, "-Kp")
    gui.setItemCallback(_btn_id_kp_down, btn_pressed)
    
    _btn_id_ki_up = gui.createButton(_image_width//2 - btn_width, btn_y + _btn_height, btn_width//2, _btn_height)
    gui.setItemLabel(_btn_id_ki_up, "+Ki")
    gui.setItemCallback(_btn_id_ki_up, btn_pressed)
    
    _btn_id_ki_down = gui.createButton(_image_width//2, btn_y + _btn_height, btn_width//2, _btn_height)
    gui.setItemLabel(_btn_id_ki_down, "-Ki")
    gui.setItemCallback(_btn_id_ki_down, btn_pressed)
    
    _btn_id_kd_up = gui.createButton(_image_width//2 - btn_width, btn_y + _btn_height*2, btn_width//2, _btn_height)
    gui.setItemLabel(_btn_id_kd_up, "+Kd")
    gui.setItemCallback(_btn_id_kd_up, btn_pressed)
    
    _btn_id_kd_down = gui.createButton(_image_width//2, btn_y + _btn_height*2, btn_width//2, _btn_height)
    gui.setItemLabel(_btn_id_kd_down, "-Kd")
    gui.setItemCallback(_btn_id_kd_down, btn_pressed)
    
    _btn_id_pid_group = gui.createButton(_image_width//2 - btn_width//2, _image_height - _btn_height, btn_width, _btn_height)
    gui.setItemLabel(_btn_id_pid_group, "角度PID")
    gui.setItemCallback(_btn_id_pid_group, btn_pressed)

    last_x = -1
    last_y = -1
    threshold = get_configured_threshold()
    load_pid_params()  # 加载PID参数
    print(threshold)
    
    # 串口初始化
    devices = uart.list_devices()
    serial = uart.UART(devices[0], 115200)
    
    # 串口变量
    receive_data = None
    last_send_time = time.time()
    send_interval = 0.1

    while not app.need_exit():
        # 1. 读取图像
        img = cam.read()
        
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
                    print(threshold)
                    set_configured_threshold(threshold)
            img.draw_cross(x, y, image.COLOR_YELLOW, 8, 2)
        
        # 3. 二值化显示选项
        if _to_show_binary:
            img = img.binary([BLACK_THRESHOLD], invert=False)
            # 增加图像增强处理
            img.open(1)  # 开运算去除小噪点
            img.gaussian(1)  # 高斯模糊平滑边缘
        
        # 4. 线性回归寻迹画线（使用黑色阈值）
        area_threshold = 100
        lines = img.get_regression([BLACK_THRESHOLD], area_threshold=area_threshold, pixels_threshold=area_threshold)
        
        # 初始化转向角
        steering_angle = 0
        has_line = False
        
        # 处理检测到的直线
        for line in lines:
            # 绘制直线
            img.draw_line(line.x1(), line.y1(), line.x2(), line.y2(), image.COLOR_GREEN, 2)
            has_line = True
            break  # 只处理第一条检测到的直线
        
        # 5. 计算转向角并通过串口发送
        steering_angle, has_line = calculate_steering_angle(lines)
        
        if has_line and (time.time() - last_send_time > send_interval):
            receive_data = steering_angle
            try:
                # 发送转向角数据（范围-128到128）
                # 转为字符串并保留1位小数，加换行符分隔
                data_str = f"{receive_data:.1f}\n"  
                serial.write(bytes(data_str.encode('utf-8')))
                print(f"转向角：{receive_data:.1f}°")
                last_send_time = time.time()
            except Exception as e:
                print(f"发送错误：{e}")
        
        # 6. 显示转向角信息
        if has_line:
            # 显示转向角
            img.draw_string(0, 30, f"转向角: {steering_angle:.1f}°", image.COLOR_RED)
        else:
            # 未检测到直线时的处理
            img.draw_string(0, 20, "未检测到直线!", image.COLOR_RED)
            # 发送无检测信号（用-128表示）
            try:
                serial.write(bytes("-128.0\n".encode('utf-8')))
                last_send_time = time.time()
            except Exception as e:
                print(f"发送错误：{e}")
        
        # 7. 显示当前PID参数
        pid_label = f"角度PID: Kp={Kp_angle}, Ki={Ki_angle}, Kd={Kd_angle}"
        if _current_pid_group == 1:
            pid_label = f"偏移PID: Kp={Kp_offset}, Ki={Ki_offset}, Kd={Kd_offset}"
        img.draw_string(0, 50, pid_label, image.COLOR_YELLOW)
        
        # 8. 更新显示    
        gui.run(img)

if __name__ == '__main__':
    main()