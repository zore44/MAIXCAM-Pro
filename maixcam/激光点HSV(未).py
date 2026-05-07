from maix import camera, display, image, time
import cv2
import numpy as np

# =================================================================
# --- 0. 辅助函数：MaixPy -> OpenCV (我们已经验证过的) ---
# =================================================================
def maix_image_to_cv2(maix_img):
    if maix_img.format() != image.Format.FMT_BGR888:
        maix_img = maix_img.to_format(image.Format.FMT_BGR888)
    img_bytes = maix_img.to_bytes()
    np_array = np.frombuffer(img_bytes, dtype=np.uint8)
    cv_img = np_array.reshape((maix_img.height(), maix_img.width(), 3))
    return cv_img

# =================================================================
# --- 1. 参数配置区 (HSV 专用) ---
# =================================================================
try:
    cam = camera.Camera(320, 240)
    disp = display.Display()
    print("--- OpenCV + HSV 颜色追踪程序 ---")
except Exception as e:
    print(f"初始化失败: {e}")
    while True: time.sleep(1)

# 设定要追踪的颜色的 HSV 范围
# 这是一个示例，用于追踪“绿色”。你需要根据实际物体进行调试。
# H: 色相 (0-180), S: 饱和度 (0-255), V: 明度 (0-255)
green_lower_bound = np.array([0, 1, 100])  # 绿色的下限
green_upper_bound = np.array([10, 255, 255]) # 绿色的上限

# 轮廓的最小面积，用于过滤噪点
MIN_CONTOUR_AREA = 500

# =================================================================
# --- 2. 主循环 ---
# =================================================================
while True:
    # a. 获取 MaixPy 图像
    img = cam.read()
    if not img:
        continue

    # b. 转换为 OpenCV 图像
    cv_img = maix_image_to_cv2(img)

    # c. 【核心】从 BGR 转换到 HSV 颜色空间
    hsv_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2HSV)

    # d. 【核心】根据 HSV 范围，生成二值化蒙版 (mask)
    # 在这个蒙版中，所有在 green_lower_bound 和 green_upper_bound 之间的像素都是白色(255)，其余是黑色(0)
    mask = cv2.inRange(hsv_img, green_lower_bound, green_upper_bound)

    # (可选) 形态学操作，让蒙版更干净
    # 开运算：先腐蚀后膨胀，可以去除背景中的小白点
    # 闭运算：先膨胀后腐蚀，可以填充物体内部的小黑洞
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    # e. 【核心】在蒙版上寻找轮廓
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # f. 处理轮廓并进行可视化
    if contours:
        # 筛选出面积最大的轮廓
        biggest_contour = max(contours, key=cv2.contourArea)

        # 确保最大轮廓足够大，以过滤掉残余的噪点
        if cv2.contourArea(biggest_contour) > MIN_CONTOUR_AREA:
            # 计算轮廓的外接矩形
            x, y, w, h = cv2.boundingRect(biggest_contour)
            
            # 在原始的彩色 MaixPy 图像上绘制结果
            # 使用我们已经验证过的 draw_rect 和 * 解包
            img.draw_rect(x, y, w, h, color=image.COLOR_GREEN, thickness=2)
            
            # 显示信息
            info_text = f"HSV Target: ({x+w//2}, {y+h//2})"
            img.draw_string(10, 10, info_text, color=image.COLOR_GREEN, scale=1.5)

    # (调试技巧) 如果想看 HSV 蒙版的效果，可以取消下面两行的注释
    # debug_img = image.from_numpy(cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR))
    # disp.show(debug_img)

    # g. 显示最终绘制了结果的 MaixPy 图像
    disp.show(img)
