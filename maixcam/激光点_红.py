from maix import camera, display, image,time


# 初始化摄像头和显示屏
cam = camera.Camera(320, 240)  
disp = display.Display()  

# ====================== 关键参数：颜色阈值 ======================
# 这是寻找红色激光的LAB颜色阈值。LAB颜色空间中：
# L: 亮度 (0-100)
# a: 红绿 (-128 to 127, 负数偏绿，正数偏红)
# b: 黄蓝 (-128 to 127, 负数偏蓝，正数偏黄)
# 格式是 (L_min, L_max, a_min, a_max, b_min, b_max)
# 这个值需要你根据实际环境光线和激光笔的颜色进行微调。
# 一个经验值，适用于比较鲜艳的红色:
# L: 亮度要高, a: 红色分量要高, b: 黄色分量可以宽一点
red_laser_threshold = [0, 100, 10, 127, 0, 127]
# 如果是绿色激光，可以尝试: (40, 100, -128, -30, -128, 127)

print("--- 激光光斑视觉追踪程序 ---")
print("请将激光笔照射到摄像头视野内...")

# 主循环
while True:
    # 1. 从摄像头捕获一帧图像
    img = cam.read()
    if not img:

        continue

    # 2. 寻找色块 (Blobs)
    # 这是核心函数！它会返回一个找到的色块列表
    # - [red_laser_threshold]: 我们要寻找的颜色阈值列表
    # - pixels_threshold=10: 色块包含的像素点数要大于100，过滤掉小噪点
    # - area_threshold=10: 色块的面积要大于100，进一步过滤
    # - merge=True: 将相邻的同颜色色块合并成一个
    blobs = img.find_blobs([red_laser_threshold], pixels_threshold=1, area_threshold=3, merge=True)

    # 3. 从找到的色块中筛选出最大的一个
    if blobs:
        # 假设激光光斑是面积最大的那个色块
        # 我们使用 max 函数和 lambda 表达式来快速找到它
        max_blob = max(blobs, key=lambda b: b.area())
        
        # 4. 获取最大色块的信息
        x, y, w, h = max_blob.rect()
        center_x = max_blob.cx()
        center_y = max_blob.cy()
        area = max_blob.area()

        # 5. 在图像上绘制结果，用于调试
        # 用绿色框框出找到的光斑
        #img.draw_rect(x, y, w, h, image.COLOR_GREEN )
        # 在光斑中心画一个十字
        img.draw_cross(center_x, center_y, size=10, color=image.Color.from_rgb(255, 0, 0),thickness=3)
        
        # 准备要显示的文字信息
        info_text = f"X: {center_x}, Y: {center_y}"
        
        # 在屏幕上打印坐标信息
        img.draw_string(10, 10, info_text, scale=2.0, color=image.Color.from_rgb(0, 0, 255))
        
        # 在IDE的终端里也打印出来，方便记录
        # 这就是你需要传给控制部分的数据
        #print(f"找到目标! 坐标: ({center_x}, {center_y}), 面积: {area}")

    else:
        # 如果没有找到任何色块
        img.draw_string(10, 10, "No target found", scale=2.0, color=image.Color.from_rgb(255, 0, 0))
        #print("未找到目标...")

    # 6. 将处理后的图像显示在屏幕上
    disp.show(img)
    fps = time.fps()
    print(f"time: {1000/fps:.02f}ms, fps: {fps:.02f}")

