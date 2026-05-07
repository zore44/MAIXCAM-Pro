from maix import camera, display, image
import time
import math

# --- 1. 初始化 ---
cam = camera.Camera(320, 240)
cam.open()
disp = display.Display()

print("新方案V3启动：使用 find_line_segments 几何巡线 (最终修正版)")

# --- 2. 主循环 ---
while True:
    img = cam.read()

    # --- 3. 图像预处理 ---
    # 使用 to_format() 转换为灰度图，然后进行二值化
    binary_img = img.to_format(image.Format.FMT_GRAYSCALE).binary([(0, 136)], invert=True)

    # --- 4. 寻找所有线段 (修正部分) ---
    # 修正了关键字参数名：max_theta_diff -> max_theta_difference
    line_segments = binary_img.find_line_segments(merge_distance=10, max_theta_difference=15)

    # --- 5. 筛选目标线段 ---
    longest_line = None
    max_len = 0

    if line_segments:
        for l in line_segments:
            if l.length() > max_len:
                max_len = l.length()
                longest_line = l
    
    # --- 6. 计算与显示 ---
    if longest_line and longest_line.length() > 20:
        # 在原图上画出我们找到的最长线段
        img.draw_line(longest_line.x1(), longest_line.y1(), longest_line.x2(), longest_line.y2(), color=image.COLOR_RED, thickness=4)

        # 计算线段中点的 x 坐标
        mid_x = (longest_line.x1() + longest_line.x2()) // 2
        center_x = img.width() // 2
        error_x = mid_x - center_x

        # 显示信息
        img.draw_string(10, 10, f"Line Error: {error_x}", color=image.COLOR_RED, scale=2.0)
        img.draw_cross(mid_x, (longest_line.y1() + longest_line.y2()) // 2, color=image.COLOR_GREEN, size=10)

    else:
        img.draw_string(10, 10, "Line Not Found!", color=image.COLOR_RED, scale=2.0)

    # 显示最终带有标记的原图
    disp.show(img)
