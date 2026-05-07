from maix import camera, display, image, nn, app, uart, time
import threading
import queue

# 模型和OCR初始化
model = "/root/models/pp_ocr.mud"
ocr = nn.PP_OCR(model)

# 摄像头和显示初始化 - 使用模型输入尺寸
cam_width, cam_height = ocr.input_width(), ocr.input_height()
cam = camera.Camera(cam_width, cam_height, ocr.input_format())
disp = display.Display()

# 加载字体 - 减小字体大小提高性能
image.load_font("ppocr", "/maixapp/share/font/ppocr_keys_v1.ttf", size = 18)
image.set_default_font("ppocr")

# 串口初始化
devices = uart.list_devices()
serial = uart.UART(devices[0], 115200)

# 串口接收缓冲区和相关变量
received_data = None  # 初始化为None，表示尚未记录识别到的数字
first_detected_digit = None  # 用于记录第一次识别到的数字
last_send_time = time.time()
send_interval = 0.1  # 发送间隔

# 创建线程安全的队列用于图像和结果传递
image_queue = queue.Queue(maxsize=2)  # 限制队列大小避免内存溢出
result_queue = queue.Queue(maxsize=2)

# 识别线程函数
def recognition_thread():
    while not app.need_exit():
        try:
            # 获取最新图像(超时1秒)
            img = image_queue.get(timeout=1)
            if img is None:
                continue
                
            # 执行OCR识别
            objs = ocr.detect(img)
            
            # 处理检测结果 - 只保留数字1-9
            detected_digits = []
            for obj in objs:
                char = obj.char_str()
                if char in ['1', '2', '3', '4', '5', '6', '7', '8', '9']:
                    detected_digits.append({
                        'char': char,
                        'box': obj.box  # 直接保存box对象
                    })
            
            # 将结果放入队列
            result_queue.put((img, detected_digits), block=False)
            image_queue.task_done()
        except queue.Empty:
            continue
        except queue.Full:
            # 队列已满，丢弃旧结果
            try:
                result_queue.get_nowait()
            except queue.Empty:
                pass
        except Exception as e:
            print(f"识别线程错误: {e}")

# 读取串口数据的函数（修改为处理第一次识别到的数字）
def read_serial_data():
    global received_data, first_detected_digit
    
    # 如果还没有记录第一次识别到的数字，则尝试记录
    if first_detected_digit is None:
        try:
            # 从识别结果队列获取最新的识别结果
            _, detected_digits = result_queue.get_nowait()
            
            # 如果有识别到的数字，记录第一个
            if detected_digits:
                first_detected_digit = detected_digits[0]['char']
                received_data = first_detected_digit
                print(f"首次识别到数字: {first_detected_digit}")
                result_queue.task_done()
            else:
                result_queue.task_done()
        except queue.Empty:
            pass

# 判断两个数字的左右位置关系（修改为基于第一次识别的数字）
def judge_position(digits):
    result = None
    
    if first_detected_digit is None:
        return result  # 没有识别到任何数字，直接返回
    
    # 获取与first_detected_digit对应的另一个数字
    if first_detected_digit == '1':
        other_digit = '2'
    elif first_detected_digit == '2':
        other_digit = '1'
    elif first_detected_digit == '3':
        other_digit = '4'
    elif first_detected_digit == '4':
        other_digit = '3'
    else:
        return result  # 不是1-4的数字，无法判断位置关系
    
    # 获取两个数字的检测结果
    digit1 = next((d for d in digits if d['char'] == first_detected_digit), None)
    digit2 = next((d for d in digits if d['char'] == other_digit), None)
    
    if digit1 and digit2:
        # 计算中心点x坐标
        x1 = (digit1['box'].x1 + digit1['box'].x2 + digit1['box'].x3 + digit1['box'].x4) / 4
        x2 = (digit2['box'].x1 + digit2['box'].x2 + digit2['box'].x3 + digit2['box'].x4) / 4
        
        # 判断位置关系
        if x1 < x2:
            result = 'L'  # first_detected_digit在另一个数字左边
        else:
            result = 'R'  # first_detected_digit在另一个数字右边
    
    return result

# 资源清理函数
def cleanup():
    print("正在清理资源...")
    try:
        # 通知识别线程退出
        image_queue.put(None)
        thread.join(timeout=1.0)
    except Exception as e:
        print(f"线程清理错误: {e}")
    
    try:
        # 释放摄像头和显示资源
        global cam, disp, serial
        if cam:
            try:
                cam.__del__()
            except:
                pass
            cam = None
        
        if disp:
            try:
                disp.__del__()
            except:
                pass
            disp = None
        
        if serial:
            try:
                serial.close()
            except:
                pass
            serial = None
            
        print("资源清理完成")
    except Exception as e:
        print(f"资源释放错误: {e}")

# 启动识别线程
thread = threading.Thread(target=recognition_thread, daemon=True)
thread.start()

# 主循环
try:
    while not app.need_exit():
        start_time = time.time()
        
        # 读取串口数据（修改为处理第一次识别到的数字）
        read_serial_data()
        
        # 读取图像并放入队列
        img = cam.read()
        if img is not None:
            try:
                # 如果队列已满，丢弃旧图像
                if image_queue.full():
                    image_queue.get_nowait()
                image_queue.put(img, block=False)
            except queue.Full:
                pass
        
        # 获取识别结果并显示
        try:
            img, detected_digits = result_queue.get_nowait()
            
            # 显示识别到的数字
            digits_text = "识别到的数字: " + ", ".join([d['char'] for d in detected_digits]) if detected_digits else "未识别到数字"
            img.draw_string(10, 10, digits_text, image.COLOR_WHITE)
            
            # 显示接收到的数字（第一次识别到的数字）
            img.draw_string(10, 35, f"首次识别数字: {first_detected_digit if first_detected_digit is not None else '未识别'}", image.COLOR_WHITE)
            
            # 显示帧率
            fps = 1.0 / (time.time() - start_time)
            img.draw_string(10, 60, f"FPS: {fps:.1f}", image.COLOR_WHITE)
            
            # 绘制识别结果
            for digit in detected_digits:
                box = digit['box']
                
                # 直接使用box的坐标属性
                points = [
                    (box.x1, box.y1),
                    (box.x2, box.y2),
                    (box.x3, box.y3),
                    (box.x4, box.y4)
                ]
                
                # 绘制四边形边界框
                for i in range(4):
                    x1, y1 = points[i]
                    x2, y2 = points[(i+1) % 4]
                    img.draw_line(x1, y1, x2, y2, image.COLOR_RED, 2)
                
                # 绘制识别结果
                img.draw_string(box.x4, box.y4, digit['char'], image.COLOR_RED)
            
            # 每隔一段时间发送识别结果
            current_time = time.time()
            if current_time - last_send_time >= send_interval:
                # 检查是否同时存在1和2或者3和4
                has_1 = any(d['char'] == '1' for d in detected_digits)
                has_2 = any(d['char'] == '2' for d in detected_digits)
                has_3 = any(d['char'] == '3' for d in detected_digits)
                has_4 = any(d['char'] == '4' for d in detected_digits)
                
                should_send_position_only = (has_1 and has_2) or (has_3 and has_4)
                
                if should_send_position_only:
                    # 只发送位置指令
                    position_result = judge_position(detected_digits)
                    if position_result:
                        try:
                            serial.write(position_result.encode('utf-8'))
                            print(f"发送位置指令: {position_result}")
                            last_send_time = current_time
                        except Exception as e:
                            print(f"位置指令发送错误: {e}")
                else:
                    # 发送数字4和5，如果没有则发送'0'
                    filtered_digits = [d['char'] for d in detected_digits if d['char'] in ['1', '2', '3', '4', '5', '6', '7', '8']]
                    send_data = ','.join(filtered_digits) if filtered_digits else '0'
                    
                    try:
                        serial.write(send_data.encode('utf-8'))
                        print(f"发送数据: {send_data}")
                        last_send_time = current_time
                    except Exception as e:
                        print(f"串口发送错误: {e}")
                    
                    # 发送位置指令（如果有）
                    position_result = judge_position(detected_digits)
                    if position_result:
                        try:
                            serial.write(position_result.encode('utf-8'))
                            print(f"发送位置指令: {position_result}")
                        except Exception as e:
                            print(f"位置指令发送错误: {e}")
            
            # 显示图像
            disp.show(img)
        except queue.Empty:
            # 没有可用结果，继续循环
            continue

except KeyboardInterrupt:
    print("程序被用户中断")
finally:
    # 确保资源被清理
    cleanup()