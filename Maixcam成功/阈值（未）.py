# -*- coding: utf-8 -*-

from maix import camera, display, image, touchscreen
import time
import cv2
import numpy as np

# ---- 全局变量和初始化 ----
cam = None
disp = None
ts = None

# [新增] 按照你的思路，创建一个辅助函数，将 Maix 图像转为 OpenCV 格式
def maix_image_to_cv2(maix_img):
    """将 maix.image 对象转换为 OpenCV (NumPy) 数组"""
    return maix_img.to_numpy()

def main():
    global cam, disp, ts
    # ---- 1. 初始化 ----
    cam = camera.Camera()
    disp = display.Display()
    ts = touchscreen.TouchScreen()

    try:
        image.load_font("my_sans", "/maixapp/share/font/SourceHanSansCN-Regular.otf")
        image.set_default_font("my_sans")
        print("系统内置思源黑体加载成功，并设为默认字体。")
    except Exception as e:
        print(f"加载内置字体失败: {e}")

    screen_w, screen_h = disp.width(), disp.height()
    center_x, center_y = screen_w // 2, screen_h // 2

    # ---- 2. UI 和状态变量定义 ----
    thresholds = {
        "l_min": 0, "l_max": 100,
        "a_min": -128, "a_max": 127,
        "b_min": -128, "b_max": 127
    }

    btn_w, btn_h = 60, 30
    btn_x = 5
    btn_y_start = 10
    btn_gap = 5

    buttons = [
        ("L Min", "l_min"), ("L Max", "l_max"),
        ("A Min", "a_min"), ("A Max", "a_max"),
        ("B Min", "b_min"), ("B Max", "b_max"),
        ("二值化", "toggle_binary")
    ]

    button_rects = {}
    for i, (label, key) in enumerate(buttons):
        y = btn_y_start + i * (btn_h + btn_gap)
        button_rects[key] = (btn_x, y, btn_w, btn_h)

    slider_h = 40
    slider_y = screen_h - slider_h - 10
    slider_x = btn_x + btn_w + 10
    slider_w = screen_w - slider_x - 10
    slider_rect = (slider_x, slider_y, slider_w, slider_h)

    active_param_key = "l_min"
    is_binary_mode = False

    COLOR_WHITE = image.Color.from_rgb(255, 255, 255)
    COLOR_GREEN = image.Color.from_rgb(0, 255, 0)
    COLOR_YELLOW = image.Color.from_rgb(255, 255, 0)
    COLOR_GRAY = image.Color.from_rgb(128, 128, 128)

    # ---- 3. 辅助函数 ----
    def map_value(x, in_min, in_max, out_min, out_max):
        if in_max == in_min: return out_min
        return int((x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min)

    def draw_ui(img, lab_info_text):
        # 绘制按钮
        for label, key in buttons:
            x, y, w, h = button_rects[key]
            is_active = (key == "toggle_binary" and is_binary_mode) or (key == active_param_key)
            color = COLOR_YELLOW if is_active else COLOR_GREEN
            img.draw_rect(x, y, w, h, color, thickness=2)
            text_w, text_h = image.string_size(label)
            img.draw_string(x + (w - text_w) // 2, y + (h - text_h) // 2, label, color=color, scale=1.2)

        # 绘制滑块
        img.draw_rect(slider_rect[0], slider_rect[1], slider_rect[2], slider_rect[3], COLOR_GRAY, thickness=-1)
        if active_param_key != "toggle_binary":
            param_range = (0, 100) if active_param_key.startswith('l') else (-128, 127)
            current_val = thresholds[active_param_key]
            handle_x = map_value(current_val, param_range[0], param_range[1], slider_x, slider_x + slider_w)
            handle_w = 15
            img.draw_rect(handle_x - handle_w // 2, slider_y, handle_w, slider_h, COLOR_WHITE, thickness=-1)
            val_text = str(current_val)
            text_w, text_h = image.string_size(val_text)
            text_y = slider_y - text_h - 5
            text_x = handle_x - text_w // 2
            if text_x < 0: text_x = 0
            if text_x + text_w > img.width(): text_x = img.width() - text_w
            img.draw_string(text_x, text_y, val_text, color=COLOR_WHITE, scale=1.5)
        
        # 绘制信息文本
        info_text2 = f"阈值: {thresholds['l_min']},{thresholds['l_max']},{thresholds['a_min']},{thresholds['a_max']},{thresholds['b_min']},{thresholds['b_max']}"
        
        img.draw_string(btn_x + btn_w + 10, 10, lab_info_text, color=COLOR_GREEN, scale=1.5)
        img.draw_string(btn_x + btn_w + 10, 35, info_text2, color=COLOR_GREEN, scale=1.5)
        img.draw_cross(center_x, center_y, size=10, color=COLOR_GREEN, thickness=2)

    # ---- 4. 主循环 ----
    print("离线阈值调试工具已启动。触摸屏幕进行交互。")
    last_touch_time = 0
    last_lab_info_text = "颜色值(LAB): N/A"

    while True:
        # --- 交互处理 ---
        touch_x, touch_y, touch_state = ts.read()
        if touch_state == 1:
            current_time = time.time()
            if current_time - last_touch_time > 0.2:
                is_btn_clicked = False
                for label, key in buttons:
                    x, y, w, h = button_rects[key]
                    if x < touch_x < x + w and y < touch_y < y + h:
                        if key == "toggle_binary": is_binary_mode = not is_binary_mode
                        else: active_param_key = key
                        is_btn_clicked = True
                        last_touch_time = current_time
                        break
            
            sx, sy, sw, sh = slider_rect
            if sx < touch_x < sx + sw and sy < touch_y < sy + sh:
                if active_param_key != "toggle_binary":
                    param_range = (0, 100) if active_param_key.startswith('l') else (-128, 127)
                    new_val = map_value(touch_x, sx, sx + sw, param_range[0], param_range[1])
                    thresholds[active_param_key] = new_val

        # --- 图像处理 ---
        img_maix = cam.read()
        if not img_maix:
            time.sleep_ms(10)
            continue

        # [最终修改] 完全采用你提供的新逻辑
        try:
            # 1. 将 Maix 图像转换为 OpenCV 格式
            cv_img = maix_image_to_cv2(img_maix)
            # 2. 获取中心点像素 (OpenCV 是 BGR 顺序)
            bgr_pixel = cv_img[center_y, center_x]
            # 3. 转换为 LAB 并映射到标准范围
            lab_pixel_cv = cv2.cvtColor(np.uint8([[bgr_pixel]]), cv2.COLOR_BGR2LAB)[0][0]
            l_val = int(lab_pixel_cv[0] * 100 / 255)
            a_val = int(lab_pixel_cv[1]) - 128
            b_val = int(lab_pixel_cv[2]) - 128
            # 4. 更新要显示的文本
            last_lab_info_text = f"颜色值(LAB): {l_val},{a_val},{b_val}"
        except Exception as e:
            # 如果任何一步出错，我们保持上一次的值，防止闪烁
            pass

        # 在 Maix 图像上进行处理和绘制
        if is_binary_mode:
            thresh_list = [(
                thresholds['l_min'], thresholds['l_max'],
                thresholds['a_min'], thresholds['a_max'],
                thresholds['b_min'], thresholds['b_max']
            )]
            img_maix.binary(thresh_list, invert=False)

        # 绘制UI
        draw_ui(img_maix, last_lab_info_text)
        
        # 显示最终的图像
        disp.show(img_maix)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"程序出现意外错误: {e}")
    finally:
        if cam:
            cam.release()
        print("程序已退出，资源已释放。")
