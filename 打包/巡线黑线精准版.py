from maix import touchscreen, camera, display, image, time, app,uart
from maix.image import Image
import math

# 屏幕参数
_image_width  = 320
_image_height = 240
_btn_width  = _image_width//6
_btn_height = _image_height//6

# 识别区域参数（改为只识别中心区域）
_center_width = _image_width // 2  # 中心区域宽度
_center_height = _image_height // 3  # 中心区域高度
_center_x = (_image_width - _center_width) // 2
_center_y = (_image_height - _center_height) // 2

# 界面控制变量
_btn_id_pixel   = -1
_btn_id_binary  = -1
_to_show_binary = False
_to_get_pixel   = False

#串口初始化
devices = uart.list_devices()
serial = uart.UART(devices[0],115200)
received_data = ""
last_send_time = time.time_s()
send_interval = 0.1  # 发送间隔0.1秒

class GUI:
    def __init__(self) -> None:
        self.background = None
        self.items      = list()
        self.callbacks  = list()
        self.labels     = list()
        self._ts   = touchscreen.TouchScreen()
        self._disp = display.Display()
        self._last_pressed = 0

    def createButton(self, x : int, y:int, width : int, height : int) -> int:
        item_id = len(self.items)
        self.items.append([x, y, width, height])
        self.callbacks.append(None)
        self.labels.append(None)
        return item_id

    def setItemCallback(self, item_id : int, cb ) -> None:
        if item_id < len(self.items):
            self.callbacks[item_id] = cb

    def setItemLabel(self, item_id : int, label : str) -> None:
        if item_id < len(self.items):
            self.labels[item_id] = label

    def get_touch(self) -> tuple:
        if self.background is None:
            return (0,0)
            
        x, y = self.touch_x, self.touch_y
        # 坐标映射回原图
        x = x if x >= 0 else 0
        y = y if y >= 0 else 0
        return (x, y)

    def run(self, background : Image) -> None:
        self.background = background
        self.touch_x, self.touch_y, pressed = self._ts.read()
        
        # 检测按键输入
        if self._last_pressed != pressed:
            self._last_pressed = pressed
            for id in range(len(self.items)):
                if self._is_in_item(id, self.touch_x, self.touch_y):
                    if self.callbacks[id] is not None:
                        self.callbacks[id](id, pressed)
                    break

        # 更新界面元素
        for id in range(len(self.items)):
            label_size = image.string_size(self.labels[id])
            label_x = max(self.items[id][0], self.items[id][0] + (self.items[id][2] - label_size.width())//2)
            label_y = max(self.items[id][1], self.items[id][1] + (self.items[id][3] - label_size.height())//2)

            self.background.draw_rect(self.items[id][0], self.items[id][1], self.items[id][2], self.items[id][3], image.COLOR_RED, 2)
            if self.labels[id] is not None:
                self.background.draw_string(label_x, label_y, self.labels[id], image.COLOR_WHITE)

        # 绘制识别区域
        self.background.draw_rect(_center_x, _center_y, _center_width, _center_height, image.COLOR_BLUE, 2)
                
        self._disp.show(self.background)

    def _is_in_item(self, item_id : int, x : int, y : int) -> bool:
        if item_id >= len(self.items) or self.background is None:
            return False
            
        item = self.items[item_id]
        if x > item[0] and x < (item[0]+item[2]) and y > item[1] and y < (item[1]+item[3]):
            return True
        return False
#读取串口数据
def read_serial_data():
    global received_data
    try:
        data = serial.read()
        if data and len(data) > 0:
            received_data += data.decode('utf-8',error = 'ignore')
            messages = received_data.split('\n')
            if len(messages) > 1:
                for msg in messages[:-1]:
                    print(f"收到数据: {msg}")
                received_data = messages[-1]
    except Exception as e:
        print(f"串口读取错误: {e}")

#pid控制
def pid_control(error,last_error,integral,kp,ki,kd):
    x = kp * error
    add += error
    y = ki * add
    z = kd * (error - last_error)
    output = x + y + z
    last_error = error
    return output, last_error, x
#角度
def theta_change(theta):
    if theta > 90:
        theta = theta - 180
        return theta
    else: 
        return theta

def rgb_to_lab(rgb):
    '''RGB到LAB颜色空间转换'''
    M = [
        [0.412453, 0.357580, 0.180423],
        [0.212671, 0.715160, 0.072169],
        [0.019334, 0.119193, 0.950227]
    ]
    
    r, g, b = [c / 255.0 for c in rgb]
    
    r = r / 12.92 if r <= 0.04045 else ((r + 0.055) / 1.055) ** 2.4
    g = g / 12.92 if g <= 0.04045 else ((g + 0.055) / 1.055) ** 2.4
    b = b / 12.92 if b <= 0.04045 else ((b + 0.055) / 1.055) ** 2.4
    
    X = M[0][0] * r + M[0][1] * g + M[0][2] * b
    Y = M[1][0] * r + M[1][1] * g + M[1][2] * b
    Z = M[2][0] * r + M[2][1] * g + M[2][2] * b
    
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
    '''保存阈值到配置文件'''
    if len(threshold) < 6:
        return 

    app.set_app_config_kv('demo_find_line', 'lmin', str(threshold[0]), False)
    app.set_app_config_kv('demo_find_line', 'lmax', str(threshold[1]), False)
    app.set_app_config_kv('demo_find_line', 'amin', str(threshold[2]), False)
    app.set_app_config_kv('demo_find_line', 'amax', str(threshold[3]), False)
    app.set_app_config_kv('demo_find_line', 'bmin', str(threshold[4]), False)
    app.set_app_config_kv('demo_find_line', 'bmax', str(threshold[5]), True)

def get_configured_threshold():
    '''从配置文件加载阈值'''
    threshold = [0, 35, -10, 10, -10, 10]  # 更适合黑色的默认阈值
    
    for key in ['lmin', 'lmax', 'amin', 'amax', 'bmin', 'bmax']:
        value_str = app.get_app_config_kv('demo_find_line', key, '', False)
        if value_str:
            idx = ['lmin', 'lmax', 'amin', 'amax', 'bmin', 'bmax'].index(key)
            threshold[idx] = int(value_str)
            
    return threshold

def find_center_line(lines, center_x, center_y, width, height):
    '''找到最接近中心区域的线'''
    if not lines:
        return None
        
    center_point = (center_x + width//2, center_y + height//2)
    closest_line = None
    min_distance = float('inf')
    
    for line in lines:
        # 计算线段中心点
        line_center = ((line.x1() + line.x2()) // 2, (line.y1() + line.y2()) // 2)
        # 计算到中心区域的距离
        distance = math.sqrt((line_center[0] - center_point[0])**2 + (line_center[1] - center_point[1])**2)
        
        if distance < min_distance:
            min_distance = distance
            closest_line = line
            
    return closest_line

def btn_pressed(btn_id, state):
    '''按钮回调函数'''
    global _to_show_binary, _to_get_pixel, _btn_id_binary, _btn_id_pixel
    if state == 0:  # 只响应触摸抬起
        return 

    if btn_id == _btn_id_binary:
        _to_show_binary = not _to_show_binary
        if _to_get_pixel:
            _to_get_pixel = False
    elif btn_id == _btn_id_pixel:
        _to_get_pixel = not _to_get_pixel

def main():
    global _to_show_binary, _to_get_pixel, _btn_id_binary, _btn_id_pixel

    print("初始化相机...")
    cam = camera.Camera(_image_width, _image_height) 
    
    print("初始化GUI...")
    gui = GUI()

    _btn_id_pixel = gui.createButton(0, _image_height-_btn_height, _btn_width, _btn_height)
    gui.setItemLabel(_btn_id_pixel, '取阈值')
    gui.setItemCallback(_btn_id_pixel, btn_pressed)

    _btn_id_binary = gui.createButton(_image_width-_btn_width, _image_height-_btn_height, _btn_width, _btn_height)
    gui.setItemLabel(_btn_id_binary, '二值化')
    gui.setItemCallback(_btn_id_binary, btn_pressed)

    last_x, last_y = -1, -1
    threshold = get_configured_threshold()
    print("初始阈值:", threshold)
    
    while not app.need_exit():
        # 1. 读取图像
        img = cam.read()
        if img is None:
            continue
            
        # 2. 图像预处理（简化以提高性能）
        img = img.gaussian(1)  # 轻度高斯模糊
        
        #初始化控制输出
        output = 0
        #检测线状态
        line_detected = 1 if lines and len(lines) > 0 else 0
        #线条底部
        bottom_x,bottom_y = get_bottom_endpoint(line,_image_height)
        # 计算误差
        error_x = bottom_x - mid
        theta = theta_change(line.theta())
        #pid控制
        output_bottom,last_error_bottom,x_bottom = pid_control(error_x,last_error_bottom,x_bottom,0.6,0,0.17)
        output_theta,last_error_theta,x_theta = pid_control(theta,last_error_theta,x_theta,0.52, 0, 0.15)
        output = output_bottom + output_theta
        output = max(-127, min(127, output))
        output = int(output)
        print(f"检测到线条 - 底部误差: {error_x}, 角度: {theta}, 输出: {output}")
        

        try:
            if line_detected:
                # 映射到0-255范围，128表示中心
                send_value = 128 + output
                send_value = max(0, min(255, send_value))
                
                # 构建文本消息并使用GBK编码
                message = f"{send_value}\n"  # 格式: D:值\n
                message_bytes = message.encode('gbk')
                uart.write(message_bytes)
                print(f"发送: {message.strip()} (检测到线条, 控制值: {output})")
            else:
                # 发送未检测到线条的消息
                message = "NO\n"  # 格式: N:0\n
                message_bytes = message.encode('gbk')
                uart.write(message_bytes)
                print("未检测到线条")
        except Exception as e:
            print(f"串口发送错误: {e}")
        # 3. 提取中心区域进行处理
        center_img = img.copy().crop(_center_x, _center_y, _center_width, _center_height)
        
        # 4. 二值化处理
        if _to_show_binary:
            processed_img = center_img.binary([threshold], invert=False)
        else:
            processed_img = center_img
        
        # 5. 阈值采样
        if _to_get_pixel:
            x, y = gui.get_touch()
            # 将坐标映射到中心区域
            x_center = x - _center_x
            y_center = y - _center_y
            
            if (0 <= x_center < _center_width and 0 <= y_center < _center_height 
                and (last_x != x or last_y != y)):
                last_x, last_y = x, y
                rgb = processed_img.get_pixel(x_center, y_center, True)
                lab = rgb_to_lab(rgb)
                
                if len(lab) >= 3:
                    # 调整阈值以更好地识别黑色
                    threshold[0] = max(0, min(lab[0] - 15, 30))  # L值下限
                    threshold[1] = min(100, max(lab[0] + 15, 40))  # L值上限
                    threshold[2] = max(-128, min(lab[1] - 10, 0))  # a值下限
                    threshold[3] = min(127, max(lab[1] + 10, 10))  # a值上限
                    threshold[4] = max(-128, min(lab[2] - 10, 0))  # b值下限
                    threshold[5] = min(127, max(lab[2] + 10, 10))  # b值上限
                    
                    print("更新阈值:", threshold)
                    set_configured_threshold(threshold)
                    
            # 在原图上绘制十字线
            img.draw_cross(x, y, image.COLOR_YELLOW, 8, 2)
        
        # 6. 线性回归寻迹（优化参数以提高性能）
        lines = processed_img.get_regression(
            [threshold],
            area_threshold=100,
            pixels_threshold=100,
            robust=True,
            x_stride=2,  # 增加步长以提高性能
            y_stride=2   # 增加步长以提高性能
        )
        
        # 7. 找到最接近中心的线
        center_line = find_center_line(lines, _center_x, _center_y, _center_width, _center_height)
        
        # 8. 在原图上绘制识别结果
        if center_line:
            # 将中心区域的坐标映射回原图
            x1 = center_line.x1() + _center_x
            y1 = center_line.y1() + _center_y
            x2 = center_line.x2() + _center_x
            y2 = center_line.y2() + _center_y
            
            img.draw_line(x1, y1, x2, y2, image.COLOR_GREEN, 3)
            
            # 计算线条角度和距离信息
            theta = center_line.theta()
            magnitude = center_line.magnitude()
            img.draw_string(0, 0, f"角度: {theta:.1f}°", image.COLOR_WHITE)
            img.draw_string(0, 20, f"强度: {magnitude:.1f}", image.COLOR_WHITE)
        
        # 9. 更新显示
        gui.run(img)

if __name__ == '__main__':
    main()