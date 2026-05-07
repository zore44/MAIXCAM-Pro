#########################                maixcam巡线         ####################

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

# 黑色阈值 (更精确的纯黑线阈值设置)
BLACK_THRESHOLD = (0, 20, -10, 10, -10, 10)

# PID控制参数
Kp_angle = 0.5    # 角度比例系数
Kp_offset = 0.3   # 偏移比例系数
max_steering = 128 # 最大转向角度范围调整为-128到128

# 图像中心（用于计算偏移）
img_center_x = _image_width // 2

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

def btn_pressed(btn_id, state):
    '''
    界面上按键的装填改变回调函数
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

def calculate_steering_angle(lines):
    """计算转向角度"""
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
    
    # 计算转向角（比例控制）
    angle_error = theta - 90  # 目标是垂直向上的直线（90°）
    steering_from_angle = Kp_angle * angle_error
    steering_from_offset = Kp_offset * offset
    
    # 综合角度和偏移计算最终转向角
    steering_angle = steering_from_angle + steering_from_offset
    
    # 限制最大转向角在-128到128之间
    steering_angle = max(-max_steering, min(max_steering, steering_angle))
    
    return steering_angle, True

def main():
    global _to_show_binary, _to_get_pixel, _btn_id_binary, _btn_id_pixel

    print(app.get_app_config_path())
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
        
        # 7. 更新显示    
        gui.run(img)

if __name__ == '__main__':
    main()
































#########################           407vet6巡线maixcam                        ###################


    #include "stm32f4xx.h"
#include "sys.h"
#include <math.h>
#include <string.h>
#include <stdlib.h>

// 定义PID控制参数结构体
typedef struct {
    float Kp;           // 比例系数
    float Ki;           // 积分系数
    float Kd;           // 微分系数
    float error;        // 当前误差
    float prevError;    // 上一次误差
    float integral;     // 积分项
    float derivative;   // 微分项
    float output;       // 输出值
    float maxOutput;    // 最大输出值
    float minOutput;    // 最小输出值
    float integralLimit;// 积分限幅
    float outputFilter; // 输出滤波系数
    float lastOutput;   // 上一次输出值
} PID_Controller;

// 电机速度相关变量
int Left_Speed = 0;
int Right_Speed = 0;
int Base_Speed = 250;          // 基础速度
int Max_Base_Speed = 300;      // 最大基础速度
int Min_Base_Speed = 150;      // 最小基础速度

// 电机死区补偿
int Motor_Deadband = 30;       // 电机死区补偿值

// 串口通信相关变量
uint8_t Serial_RxData;
uint8_t Serial_RxFlag;
uint8_t buffer[9];             // 陀螺仪数据缓存区
uint8_t RxData_Cnt;            // 接收数据计数
int Yaw;                       // 陀螺仪Yaw角数据
char str[30] = "";
uint8_t com_data;
uint8_t RxBuffer1[4] = {0};
uint8_t RxCounter1 = 0;

// 巡线专用变量
float Line_Steering = 0.0f;    // 从串口接收的转向角(-128~128)
uint8_t Line_Data_Valid = 0;   // 有效巡线数据标志
char Line_RxBuffer[10] = {0};  // 巡线数据接收缓冲区
uint8_t Line_RxIndex = 0;      // 巡线数据接收索引
float Line_Kp = 1.2f;          // 巡线转向比例系数

// 辅助变量
uint16_t cnttt, cnttt1, cnttt2;
double distance;
int Left_Speed_cnt = 0;
extern uint8_t main_mode, mode2, mode1, flag_z;

// 陀螺仪辅助相关变量
float Target_Angle = 0.0f;         // 目标角度（直线行走）
uint8_t Use_Gyro_Assist = 1;       // 启用陀螺仪辅助
float Gyro_Assist_Weight = 0.3f;   // 陀螺仪辅助权重（降低权重，优先巡线数据）
float Gyro_Offset = 0.0f;          // 陀螺仪偏移量

// PID控制器实例
PID_Controller gyroPID;            // 陀螺仪PID

// 全局变量定义
int x = 0;                         // 全局变量x

// PID初始化函数
void PID_Init(PID_Controller *pid, float Kp, float Ki, float Kd, 
             float minOutput, float maxOutput, float integralLimit, float outputFilter) {
    pid->Kp = Kp;
    pid->Ki = Ki;
    pid->Kd = Kd;
    pid->minOutput = minOutput;
    pid->maxOutput = maxOutput;
    pid->integralLimit = integralLimit;
    pid->outputFilter = outputFilter;
    pid->error = 0;
    pid->prevError = 0;
    pid->integral = 0;
    pid->derivative = 0;
    pid->output = 0;
    pid->lastOutput = 0;
}

// 角度归一化（-180°~180°）
float Normalize_Angle(float angle) {
    while (angle > 180.0f) angle -= 360.0f;
    while (angle < -180.0f) angle += 360.0f;
    return angle;
}

// PID计算函数
float PID_Compute(PID_Controller *pid, float setpoint, float measurement, float dt) {
    pid->error = setpoint - measurement;
    
    // 积分项计算与限幅
    pid->integral += pid->error * dt;
    if (pid->integral > pid->integralLimit) pid->integral = pid->integralLimit;
    if (pid->integral < -pid->integralLimit) pid->integral = -pid->integralLimit;
    
    // 微分项计算
    pid->derivative = (pid->error - pid->prevError) / dt;
    
    // 计算输出并滤波
    pid->output = pid->Kp * pid->error + pid->Ki * pid->integral + pid->Kd * pid->derivative;
    if (pid->outputFilter > 0 && pid->outputFilter < 1) {
        pid->output = pid->outputFilter * pid->output + (1 - pid->outputFilter) * pid->lastOutput;
    }
    
    // 输出限幅
    if (pid->output > pid->maxOutput) pid->output = pid->maxOutput;
    if (pid->output < pid->minOutput) pid->output = pid->minOutput;
    
    pid->lastOutput = pid->output;
    pid->prevError = pid->error;
    
    return pid->output;
}

// 电机死区补偿
int Apply_Deadband(int speed) {
    if (speed > 0) {
        return Motor_Deadband + speed * (1000 - Motor_Deadband) / 1000;
    } else if (speed < 0) {
        return -Motor_Deadband + speed * (1000 - Motor_Deadband) / 1000;
    } else {
        return 0;
    }
}

// 解析巡线数据（从字符串转换为浮点数）
void Parse_Line_Data(void) {
    // 尝试转换接收到的字符串为浮点数
    float temp = atof(Line_RxBuffer);
    
    // 验证数据范围(-128~128)
    if (temp >= -128.0f && temp <= 128.0f) {
        Line_Steering = temp;
        Line_Data_Valid = 1;
        
        // 根据转向角度动态调整基础速度（转弯时减速）
        float speed_factor = 1.0f - (fabs(Line_Steering) / 128.0f) * 0.3f;
        Base_Speed = (int)(250 * speed_factor);
        if (Base_Speed < Min_Base_Speed) Base_Speed = Min_Base_Speed;
    } else {
        Line_Data_Valid = 0;  // 数据无效
    }
    
    // 重置缓冲区
    memset(Line_RxBuffer, 0, sizeof(Line_RxBuffer));
    Line_RxIndex = 0;
}

// 计算左右电机速度（整合巡线转向逻辑）
void Calculate_Motor_Speeds(void) {
    float gyroDiff = 0.0f;
    float lineDiff = 0.0f;
    float totalDiff = 0.0f;
    
    // 陀螺仪辅助计算
    if (Use_Gyro_Assist) {
        float gyroAngle = (float)Yaw * 0.0054931640625f - Gyro_Offset;
        gyroDiff = PID_Compute(&gyroPID, Target_Angle, gyroAngle, 0.01f);
    }
    
    // 巡线转向计算（使用从串口接收的转向角）
    if (Line_Data_Valid) {
        // 将-128~128范围映射到合适的转向差异值
        lineDiff = Line_Steering * Line_Kp;
    }
    
    // 融合陀螺仪和巡线数据（巡线数据权重更高）
    if (Line_Data_Valid) {
        totalDiff = (lineDiff * (1.0f - Gyro_Assist_Weight)) + (gyroDiff * Gyro_Assist_Weight);
    } else {
        totalDiff = gyroDiff;  // 无巡线数据时仅使用陀螺仪
    }
    
    // 计算最终速度并应用死区补偿
    Left_Speed = Base_Speed + (int)totalDiff;
    Right_Speed = Base_Speed - (int)totalDiff;
    Left_Speed = Apply_Deadband(Left_Speed);
    Right_Speed = Apply_Deadband(Right_Speed);
    
    // 速度限幅
    if (Left_Speed > 800) Left_Speed = 800;
    if (Left_Speed < -800) Left_Speed = -800;
    if (Right_Speed > 800) Right_Speed = 800;
    if (Right_Speed < -800) Right_Speed = -800;
}

int main(void) {
    // 初始化外设
    OLED_Init();
    Key_Init();
    EXTIXa_Init();
    TIMer4_Init();
    TIMer2_Init();
    Motor_Init();
    Motor_PWM_Init();
    Left_Encoder_Init();
    Right_Encoder_Init();
    uart1_init();       // 陀螺仪串口
    uart3_init();       // 巡线数据接收串口
    LED_Init();
    
    // 初始化PID控制器
    PID_Init(&gyroPID, 12.0f, 0.15f, 3.0f, -150.0f, 150.0f, 80.0f, 0.8f);
    
    // 初始化电机速度
    Left_Speed = 0;
    Right_Speed = 0;
    Motor_speed(Left_Speed, Right_Speed);
    
    // 初始化陀螺仪偏移
    if (Yaw != 0) {
        Gyro_Offset = (float)Yaw * 0.0054931640625f;
        Target_Angle = 0.0f;
    }
    
    // 系统定时器初始化（1ms中断）
    SysTick_Config(SystemCoreClock / 1000);
    
    while (1) {
        // OLED显示刷新
        OLED_Refresh();
        
        // 显示电机速度
        sprintf(str, "L:%d R:%d    ", Left_Speed, Right_Speed);
        OLED_ShowString(0, 0, (uint8_t *)str, 16);
        
        // 显示陀螺仪角度
        sprintf(str, "Gyro: %.1f    ", (float)Yaw * 0.0054931640625f - Gyro_Offset);
        OLED_ShowString(0, 32, (uint8_t *)str, 16);
        
        // 显示巡线转向角
        sprintf(str, "Steer: %.1f    ", Line_Steering);
        OLED_ShowString(0, 16, (uint8_t *)str, 16);
        
        // 显示基础速度
        sprintf(str, "Speed: %d      ", Base_Speed);
        OLED_ShowString(0, 48, (uint8_t *)str, 16);
        
        // 计算并设置电机速度
        Calculate_Motor_Speeds();
        Motor_speed(Left_Speed, Right_Speed);
        
        delay_ms(10);
    }
}

// 定时器2中断服务函数
void TIM2_IRQHandler(void) {
    if (TIM_GetITStatus(TIM2, TIM_IT_Update) == 1) {
        if (main_mode == 1) {
            task();
        }
        if (mode2 == 3) cnttt1++;
        if (flag_z == 1) cnttt2++;
        
        TIM_ClearITPendingBit(TIM2, TIM_IT_Update);
    }
}

// 定时器4中断服务函数（编码器处理）
void TIM4_IRQHandler(void) {
    if (TIM_GetITStatus(TIM4, TIM_IT_Update) == 1) {
        Left_Speed = (short)TIM_GetCounter(TIM5);
        Right_Speed = (short)TIM_GetCounter(TIM3);
        Left_Speed_cnt += abs(Left_Speed);
        distance = Count_Distance(Left_Speed_cnt);
        
        if (Left_Speed != 0 || Right_Speed != 0) {
            TIM_SetCounter(TIM5, 0);
            TIM_SetCounter(TIM3, 0);
        }
        TIM_ClearITPendingBit(TIM4, TIM_IT_Update);
    }
}

// 串口1中断服务函数（陀螺仪数据）
void USART1_IRQHandler(void) {
    if (USART_GetITStatus(USART1, USART_IT_RXNE) != RESET) {
        Serial_RxData = USART_ReceiveData(USART1);
        
        if (Serial_RxFlag == 0 && Serial_RxData == 0x55) {
            Serial_RxFlag = 1;
        } else if (Serial_RxFlag == 1 && Serial_RxData == 0x53) {
            Serial_RxFlag = 6;
        } else if (Serial_RxFlag == 6) {
            buffer[RxData_Cnt++] = Serial_RxData;
            if (RxData_Cnt == 9) {
                // 校验和验证
                if ((uint8_t)(buffer[0]+buffer[1]+buffer[2]+buffer[3]+buffer[4]+buffer[5]+buffer[6]+buffer[7]+0xa8) == buffer[8]) {
                    Yaw = ((short)((short)(buffer[5]<<8)|buffer[4])) * 0.0054931640625f;
                }
                RxData_Cnt = 0;
                Serial_RxFlag = 0;
            }
        } else {
            Serial_RxFlag = 0;
            RxData_Cnt = 0;
        }
        USART_ClearITPendingBit(USART1, USART_IT_RXNE);
    }
}

// 新增：串口3中断服务函数（巡线数据接收）
void USART3_IRQHandler(void) {
    if (USART_GetITStatus(USART3, USART_IT_RXNE) != RESET) {
        uint8_t data = USART_ReceiveData(USART3);
        
        // 换行符表示一次数据传输结束
        if (data == '\n' || data == '\r') {
            if (Line_RxIndex > 0) {
                Parse_Line_Data();  // 解析接收到的数据
            }
        } 
        // 缓存有效字符（数字、小数点、负号）
        else if ((data >= '0' && data <= '9') || data == '.' || data == '-') {
            if (Line_RxIndex < sizeof(Line_RxBuffer) - 1) {
                Line_RxBuffer[Line_RxIndex++] = data;
            }
        }
        
        USART_ClearITPendingBit(USART3, USART_IT_RXNE);
    }
}



























###########################            openmv巡线                   #######################




# 更精确的纯黑线阈值设置 (纯黑或接近纯黑)
THRESHOLD = (0, 20, -10, 10, -10, 10)

import sensor, image, time
from pyb import UART

# 初始化UART
uart = UART(3, 115200)  # 根据硬件调整UART编号和波特率

# PID variables
last_error_bottom = 0
integral_bottom = 0
last_error_theta = 0
integral_theta = 0

# 相机设置
sensor.reset()
sensor.set_vflip(False)
sensor.set_hmirror(False)
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QQQVGA)
#sensor.set_auto_gain(False)  # 关闭自动增益
#sensor.set_auto_whitebal(False)  # 关闭自动白平衡
sensor.skip_frames(time=2000)  # 让相机稳定

# 方向判断阈值
ANGLE_THRESHOLD = 15  # 角度阈值，小于此值为垂直

mid = sensor.width() // 2

def pid_control(error, last_error, integral, Kp, Ki, Kd):
    # Proportional term
    proportional = Kp * error

    # Integral term
    integral += error
    integral_term = Ki * integral

    # Derivative term
    derivative = Kd * (error - last_error)

    # PID output
    output = proportional + integral_term + derivative

    # Update last error
    last_error = error

    return output, last_error, integral

def theta_change(theta):
    """更精确的方向判断函数"""
    if theta > 90:
        theta = theta - 180  # 转换为-90到90范围
        return theta
    else:
        return theta

clock = time.clock()
last_direction = None

def get_bottom_endpoint(line, img_height):
    """获取线条在图像底部的端点坐标"""
    # 线条的两个端点 (x1,y1) 和 (x2,y2)
    (x1, y1, x2, y2) = line.line()

    # 确定哪个端点在图像底部(更大的y值)
    if y1 > y2:
        return (x1, y1)  # 第一个点是底部端点
    else:
        return (x2, y2)  # 第二个点是底部端点

# 发送角度数据
def send_output_text(output_bottom, output_theta):
    # 格式化输出数据为文本
    data_str = f"{int(output_bottom+128)},{int(output_theta+128)}\n"
    # 发送文本数据
    uart.write(data_str.encode())

while(True):
    clock.tick()

    # 获取图像并进行二值化处理
    img = sensor.snapshot()

    # 多种处理组合提高识别精度
    # 1. 二值化
    img.binary([THRESHOLD])
    # 2. 开运算去除小噪点
    img.open(1)
    # 3. 高斯模糊平滑边缘
    img.gaussian(1)

    # 检测线条
    line = img.get_regression([(100, 100)], robust=True)

    if line and line.magnitude() > 8:  # 确保检测到有效线条
        # 绘制检测到的线条(调试用)
        img.draw_line(line.line(), color=(255, 0, 0), thickness=2)
        bottom_x, bottom_y = get_bottom_endpoint(line, img.height())

        error_x = bottom_x - mid
        theta = theta_change(line.theta())

        output_bottom,last_error_bottom,integral_bottom = pid_control(error_x,last_error_bottom,integral_bottom, 0.6, 0, 0.17)
        output_theta,last_error_theta,integral_theta = pid_control(theta,last_error_theta,integral_theta, 0.52, 0, 0.15)

        # 发送文本格式数据
        send_output_text(output_bottom, output_theta)
        
        # 打印调试信息
        print(f"Output: Bottom={output_bottom:.2f}, Theta={output_theta:.2f} | Data Sent: {int(output_bottom+128)},{int(output_theta+128)}")
    else:
        # 发送无检测信号
        uart.write("0,0\n".encode())
        print("Line not found!")

    # 调试信息
    # print("FPS:", clock.fps())











#################          maixcam 语音识别        ####################################

from maix import app, nn, uart
import time

# 语音命令常量
CMD_FORWARD = 'Q'  # 前进命令
CMD_STOP = 'S'     # 停止命令

# 初始化串口通信
devices = uart.list_devices()
serial = uart.UART(devices[0], 115200)

# 语音识别初始化
speech = nn.Speech("/root/models/am_3332_192_int8.mud")
speech.init(nn.SpeechDevice.DEVICE_MIC)

# 语音识别回调函数
def callback(data: tuple[str, str], len: int):
    text = data[0].strip()  # 获取识别的文本并去除空白字符
    print(f"识别结果: {text}")
    
    # 查找最后出现的"前进"和"停止"
    last_forward = text.rfind("前进")
    last_stop = text.rfind("停止")
    
    # 决定发送的命令（根据最后出现的命令）
    command = None
    if last_forward >= 0 and last_stop >= 0:
        command = CMD_FORWARD if last_forward > last_stop else CMD_STOP
    elif last_forward >= 0:
        command = CMD_FORWARD
    elif last_stop >= 0:
        command = CMD_STOP
    
    # 发送最后识别到的命令
    if command:
        try:
            data_str = f"{command}\n"
            serial.write(bytes(data_str.encode('utf-8')))
            print(f"发送命令: {command}")
        except Exception as e:
            print(f"串口发送错误: {e}")

# 加载语言模型
lmS_path = "/root/models/lmS/"
speech.lvcsr(lmS_path + "lg_6m.sfst", lmS_path + "lg_6m.sym", 
             lmS_path + "phones.bin", lmS_path + "words_utf.bin", 
             callback)

# 主循环
while not app.need_exit():
    frames = speech.run(1)
    if frames < 1:
        print("run out\n")
        break

# 程序结束时关闭串口
serial.close()









#####################                 语音32代码                 ###########################
#include "stm32f4xx.h"
#include "sys.h"
#include <math.h>
#include <string.h>
#include <stdlib.h>

// 定义PID控制参数结构体
typedef struct {
    float Kp;           // 比例系数
    float Ki;           // 积分系数
    float Kd;           // 微分系数
    float error;        // 当前误差
    float prevError;    // 上一次误差
    float integral;     // 积分项
    float derivative;   // 微分项
    float output;       // 输出值
    float maxOutput;    // 最大输出值
    float minOutput;    // 最小输出值
    float integralLimit;// 积分限幅
    float outputFilter; // 输出滤波系数
    float lastOutput;   // 上一次输出值
} PID_Controller;

// 电机速度相关变量
int Left_Speed = 0;
int Right_Speed = 0;
int Base_Speed = 250;          // 基础速度
int Max_Base_Speed = 300;      // 最大基础速度
int Min_Base_Speed = 150;      // 最小基础速度

// 电机死区补偿
int Motor_Deadband = 30;       // 电机死区补偿值

// 串口通信相关变量
uint8_t Serial_RxData;
uint8_t Serial_RxFlag;
uint8_t buffer[9];             // 陀螺仪数据缓存区
uint8_t RxData_Cnt;            // 接收数据计数
int Yaw;                       // 陀螺仪Yaw角数据
char str[30] = "";
uint8_t com_data;
uint8_t RxBuffer1[4] = {0};
uint8_t RxCounter1 = 0;

// 语音控制相关变量
uint8_t Voice_Command = 0;     // 语音命令标志：0-无命令，1-前进，2-停止

// 辅助变量
uint16_t cnttt, cnttt1, cnttt2;
double distance;
int Left_Speed_cnt = 0;
extern uint8_t main_mode, mode2, mode1, flag_z;

// 陀螺仪辅助相关变量
float Target_Angle = 0.0f;         // 目标角度（直线行走）
uint8_t Use_Gyro_Assist = 1;       // 启用陀螺仪辅助
float Gyro_Assist_Weight = 0.3f;   // 陀螺仪辅助权重
float Gyro_Offset = 0.0f;          // 陀螺仪偏移量

// PID控制器实例
PID_Controller gyroPID;            // 陀螺仪PID

// 全局变量定义
int x = 0;                         // 全局变量x

// PID初始化函数
void PID_Init(PID_Controller *pid, float Kp, float Ki, float Kd, 
             float minOutput, float maxOutput, float integralLimit, float outputFilter) {
    pid->Kp = Kp;
    pid->Ki = Ki;
    pid->Kd = Kd;
    pid->minOutput = minOutput;
    pid->maxOutput = maxOutput;
    pid->integralLimit = integralLimit;
    pid->outputFilter = outputFilter;
    pid->error = 0;
    pid->prevError = 0;
    pid->integral = 0;
    pid->derivative = 0;
    pid->output = 0;
    pid->lastOutput = 0;
}

// 角度归一化（-180°~180°）
float Normalize_Angle(float angle) {
    while (angle > 180.0f) angle -= 360.0f;
    while (angle < -180.0f) angle += 360.0f;
    return angle;
}

// PID计算函数
float PID_Compute(PID_Controller *pid, float setpoint, float measurement, float dt) {
    pid->error = setpoint - measurement;
    
    // 积分项计算与限幅
    pid->integral += pid->error * dt;
    if (pid->integral > pid->integralLimit) pid->integral = pid->integralLimit;
    if (pid->integral < -pid->integralLimit) pid->integral = -pid->integralLimit;
    
    // 微分项计算
    pid->derivative = (pid->error - pid->prevError) / dt;
    
    // 计算输出并滤波
    pid->output = pid->Kp * pid->error + pid->Ki * pid->integral + pid->Kd * pid->derivative;
    if (pid->outputFilter > 0 && pid->outputFilter < 1) {
        pid->output = pid->outputFilter * pid->output + (1 - pid->outputFilter) * pid->lastOutput;
    }
    
    // 输出限幅
    if (pid->output > pid->maxOutput) pid->output = pid->maxOutput;
    if (pid->output < pid->minOutput) pid->output = pid->minOutput;
    
    pid->lastOutput = pid->output;
    pid->prevError = pid->error;
    
    return pid->output;
}

// 电机死区补偿
int Apply_Deadband(int speed) {
    if (speed > 0) {
        return Motor_Deadband + speed * (1000 - Motor_Deadband) / 1000;
    } else if (speed < 0) {
        return -Motor_Deadband + speed * (1000 - Motor_Deadband) / 1000;
    } else {
        return 0;
    }
}

// 计算左右电机速度
void Calculate_Motor_Speeds(void) {
    float gyroDiff = 0.0f;
    float totalDiff = 0.0f;
    
    // 根据语音命令设置基础速度
    if (Voice_Command == 1) {  // 前进命令
        Base_Speed = 250;      // 设置前进速度
    } else if (Voice_Command == 2) {  // 停止命令
        Base_Speed = 0;        // 设置停止速度
    }
    
    // 陀螺仪辅助计算（仅在有前进命令时启用）
    if (Use_Gyro_Assist && Voice_Command == 1) {
        float gyroAngle = (float)Yaw * 0.0054931640625f - Gyro_Offset;
        gyroDiff = PID_Compute(&gyroPID, Target_Angle, gyroAngle, 0.01f);
    }
    
    totalDiff = gyroDiff;
    
    // 计算最终速度并应用死区补偿
    Left_Speed = Base_Speed + (int)totalDiff;
    Right_Speed = Base_Speed - (int)totalDiff;
    Left_Speed = Apply_Deadband(Left_Speed);
    Right_Speed = Apply_Deadband(Right_Speed);
    
    // 速度限幅
    if (Left_Speed > 800) Left_Speed = 800;
    if (Left_Speed < -800) Left_Speed = -800;
    if (Right_Speed > 800) Right_Speed = 800;
    if (Right_Speed < -800) Right_Speed = -800;
}

int main(void) {
    // 初始化外设
    OLED_Init();
    Key_Init();
    EXTIXa_Init();
    TIMer4_Init();
    TIMer2_Init();
    Motor_Init();
    Motor_PWM_Init();
    Left_Encoder_Init();
    Right_Encoder_Init();
    uart1_init();       // 陀螺仪串口
    uart3_init();       // 语音命令接收串口
    LED_Init();
    
    // 初始化PID控制器
    PID_Init(&gyroPID, 12.0f, 0.15f, 3.0f, -150.0f, 150.0f, 80.0f, 0.8f);
    
    // 初始化电机速度
    Left_Speed = 0;
    Right_Speed = 0;
    Motor_speed(Left_Speed, Right_Speed);
    
    // 初始化陀螺仪偏移
    if (Yaw != 0) {
        Gyro_Offset = (float)Yaw * 0.0054931640625f;
        Target_Angle = 0.0f;
    }
    
    // 系统定时器初始化（1ms中断）
    SysTick_Config(SystemCoreClock / 1000);
    
    while (1) {
        // OLED显示刷新
        OLED_Refresh();
        
        // 显示电机速度
        sprintf(str, "L:%d R:%d    ", Left_Speed, Right_Speed);
        OLED_ShowString(0, 0, (uint8_t *)str, 16);
        
        // 显示当前命令（使用ASCII字符代替中文）
        sprintf(str, "Cmd: %c      ", Voice_Command == 1 ? 'F' : (Voice_Command == 2 ? 'S' : ' '));
        OLED_ShowString(0, 16, (uint8_t *)str, 16);
        
        // 显示陀螺仪角度
        sprintf(str, "Gyro: %.1f    ", (float)Yaw * 0.0054931640625f - Gyro_Offset);
        OLED_ShowString(0, 32, (uint8_t *)str, 16);
        
        // 显示基础速度
        sprintf(str, "Speed: %d      ", Base_Speed);
        OLED_ShowString(0, 48, (uint8_t *)str, 16);
        
        // 计算并设置电机速度
        Calculate_Motor_Speeds();
        Motor_speed(Left_Speed, Right_Speed);
        
        delay_ms(10);
    }
}

// 定时器2中断服务函数
void TIM2_IRQHandler(void) {
    if (TIM_GetITStatus(TIM2, TIM_IT_Update) == 1) {
        if (main_mode == 1) {
            task();
        }
        if (mode2 == 3) cnttt1++;
        if (flag_z == 1) cnttt2++;
        
        TIM_ClearITPendingBit(TIM2, TIM_IT_Update);
    }
}

// 定时器4中断服务函数（编码器处理）
void TIM4_IRQHandler(void) {
    if (TIM_GetITStatus(TIM4, TIM_IT_Update) == 1) {
        Left_Speed = (short)TIM_GetCounter(TIM5);
        Right_Speed = (short)TIM_GetCounter(TIM3);
        Left_Speed_cnt += abs(Left_Speed);
        distance = Count_Distance(Left_Speed_cnt);
        
        if (Left_Speed != 0 || Right_Speed != 0) {
            TIM_SetCounter(TIM5, 0);
            TIM_SetCounter(TIM3, 0);
        }
        TIM_ClearITPendingBit(TIM4, TIM_IT_Update);
    }
}

// 串口1中断服务函数（陀螺仪数据）
void USART1_IRQHandler(void) {
    if (USART_GetITStatus(USART1, USART_IT_RXNE) != RESET) {
        Serial_RxData = USART_ReceiveData(USART1);
        
        if (Serial_RxFlag == 0 && Serial_RxData == 0x55) {
            Serial_RxFlag = 1;
        } else if (Serial_RxFlag == 1 && Serial_RxData == 0x53) {
            Serial_RxFlag = 6;
        } else if (Serial_RxFlag == 6) {
            buffer[RxData_Cnt++] = Serial_RxData;
            if (RxData_Cnt == 9) {
                // 校验和验证
                if ((uint8_t)(buffer[0]+buffer[1]+buffer[2]+buffer[3]+buffer[4]+buffer[5]+buffer[6]+buffer[7]+0xa8) == buffer[8]) {
                    Yaw = ((short)((short)(buffer[5]<<8)|buffer[4])) * 0.0054931640625f;
                }
                RxData_Cnt = 0;
                Serial_RxFlag = 0;
            }
        } else {
            Serial_RxFlag = 0;
            RxData_Cnt = 0;
        }
        USART_ClearITPendingBit(USART1, USART_IT_RXNE);
    }
}

// 新增：串口3中断服务函数（语音命令接收）
void USART3_IRQHandler(void) {
    if (USART_GetITStatus(USART3, USART_IT_RXNE) != RESET) {
        uint8_t data = USART_ReceiveData(USART3);
        
        // 处理接收到的命令
        if (data == 'Q') {  // 前进命令
            Voice_Command = 1;
        } else if (data == 'S') {  // 停止命令
            Voice_Command = 2;
        }
        
        USART_ClearITPendingBit(USART3, USART_IT_RXNE);
    }
}