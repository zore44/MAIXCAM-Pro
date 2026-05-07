# 导入所有需要的库
from maix import image, camera, display, app, uart, time # MaixPy 核心库
import cv2          # OpenCV 视觉库
import numpy as np  # NumPy 数值计算库
from struct import pack # 用于将数据打包成二进制格式进行串口通信


# "/dev/ttyS0" 是设备上的串口号，115200 是波特率
serial = uart.UART("/dev/ttyS0", 115200)

# 初始化
cam = camera.Camera(320, 240, fps=80)
disp = display.Display()


# 面积过滤器：只处理面积在这个范围内的轮廓
MIN_AREA = 200
MAX_AREA = 8000000

# 一个标志位，可以通过串口指令设置为 True，来暂停矩形检测，以降低CPU负载
pause_rect_detect = False



def sort_rect_points(pts):
    """
    对一个矩形的四个顶点进行标准化排序。
    确保返回的顶点顺序永远是：[左上, 右上, 右下, 左下]。
    这是后续比较和匹配两个矩形的关键前提。
    """
    # 按 Y 坐标排序，再按 X 坐标排序，将点分为上下两部分
    pts = sorted(pts, key=lambda p: (p[1], p[0]))
    # 前两个点是上面的点，按 X 坐标排序得到 左上, 右上
    top = sorted(pts[:2], key=lambda p: p[0])
    # 后两个点是下面的点，按 X 坐标逆序排序得到 右下, 左下
    bottom = sorted(pts[2:], key=lambda p: p[0], reverse=True)
    return [top[0], top[1], bottom[0], bottom[1]]



def match_corners_by_distance(ref_pts, target_pts):
    """
    当找到两个矩形时，它们的顶点顺序可能不匹配。
    此函数以第一个矩形(ref_pts)为基准，为第二个矩形(target_pts)的每个顶点
    找到距离最近的对应顶点，从而生成一个与基准矩形顺序匹配的新顶点列表。
    """
    matched = [None] * 4 # 准备存放匹配好的点
    used = [False] * 4   # 标记 target_pts 中的点是否已被使用
    
    # 遍历基准矩形的每个点
    for i, p1 in enumerate(ref_pts):
        min_dist = float("inf") # 初始化最小距离为无穷大
        min_j = -1
        # 遍历目标矩形的每个点
        for j, p2 in enumerate(target_pts):
            if not used[j]: # 如果这个点还没被用过
                # 计算两个点之间的欧氏距离
                dist = np.linalg.norm(np.array(p1) - np.array(p2))
                if dist < min_dist:
                    min_dist = dist
                    min_j = j
        # 找到了最近的点，记录下来
        matched[i] = target_pts[min_j]
        used[min_j] = True # 标记为已使用
    return matched






def is_similar_rect(rect1, rect2, threshold=8, area_thresh=0.05):
    """
    判断两个矩形是否“足够相似”，用于去除重复检测。
    有时候内外轮廓会被同时检测成两个矩形，此函数可以判断它们其实是同一个。
    判断依据：1. 对应顶点的平均距离是否足够近。 2. 两个矩形的面积差异是否足够小。
    """
    try:
        # 先对两个矩形进行标准化排序
        rect1 = sort_rect_points(rect1)
        rect2 = sort_rect_points(rect2)
        # 计算对应顶点之间的平均距离
        avg_dist = np.mean([np.linalg.norm(np.array(p1) - np.array(p2)) for p1, p2 in zip(rect1, rect2)])
        # 计算两个矩形的面积
        area1 = cv2.contourArea(np.array(rect1, dtype=np.int32))
        area2 = cv2.contourArea(np.array(rect2, dtype=np.int32))
        # 计算面积差异率
        area_diff_ratio = abs(area1 - area2) / max(area1, area2)
        # 如果平均距离和面积差异率都在阈值内，则认为是相似的
        return avg_dist < threshold and area_diff_ratio < area_thresh
    except Exception as e:
        print("矩形比较异常:", e)
        return False






def is_rectangle(approx):
    """
    判断一个轮廓是否是“准矩形”。
    核心思想：一个四边形，如果它的四个内角都约等于90度，那它就是矩形。
    """
    # 必须是4个顶点，并且是一个凸多边形
    if approx is None or len(approx) != 4 or not cv2.isContourConvex(approx):
        return False
    
    pts = [point[0] for point in approx]
    
    # 定义一个内部函数来计算三个点组成的夹角
    def angle(p1, p2, p3):
        v1 = np.array(p1) - np.array(p2)
        v2 = np.array(p3) - np.array(p2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 == 0 or norm2 == 0:
            return 0
        # 计算角度的余弦值，并用 clip 防止计算错误
        cos_angle = np.clip(np.dot(v1, v2) / (norm1 * norm2), -1.0, 1.0)
        # 将余弦值转换为角度
        return np.arccos(cos_angle) * 180 / np.pi
        
    # 计算四个顶点的内角
    angles = [angle(pts[i - 1], pts[i], pts[(i + 1) % 4]) for i in range(4)]
    # 如果所有角度都在80到100度之间，就认为它是一个矩形
    return all(80 < ang < 100 for ang in angles)





# 使用 app.need_exit() 作为循环条件，这是 MaixPy 官方推荐的、安全的程序生命周期管理方式
while not app.need_exit():
    try:
        # --- 串口通信部分 ---
        try:
            # 尝试读取串口数据，看是否收到了暂停指令
            data = serial.read()
            if data and b'\x66' in data: # 0x66 是暂停指令
                pause_rect_detect = True
        except Exception as e:
            print("串口读取异常:", e)

        # --- 图像获取与转换 ---
        img = cam.read()
        if img is None:
            continue # 如果没读到图像，就进入下一次循环
        try:
            # 使用官方桥梁函数，将 MaixPy Image 转换为 OpenCV NumPy 数组
            img_raw = image.image2cv(img, copy=True)
        except Exception as e:
            print("图像转换失败:", e)
            continue

        # 初始化一个列表，用于存放内外矩形对应顶点的中点坐标
        midpoints = [(-1, -1)] * 4



        # --- 矩形检测核心逻辑 ---
        if not pause_rect_detect:
            try:
                # a. 预处理：转为灰度图
                gray = cv2.cvtColor(img_raw, cv2.COLOR_BGR2GRAY)
                # b. 预处理：自适应二值化。能很好地适应光照不均的情况。
                bin_img = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                                cv2.THRESH_BINARY, 11, 2)
                # c. 预处理：闭运算。连接二值化后可能出现的线条断裂。
                closed = cv2.morphologyEx(bin_img, cv2.MORPH_CLOSE,
                                           cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)))
                # d. 寻找所有轮廓
                contours, _ = cv2.findContours(closed, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
                
                rectangles = [] # 用于存放本帧找到的所有有效矩形

                # e. 遍历所有找到的轮廓
                for contour in contours:
                    # f. 过滤：面积太小或太大的轮廓直接跳过
                    area = cv2.contourArea(contour)
                    if not (MIN_AREA <= area <= MAX_AREA):
                        continue
                    
                    # g. 过滤：完全贴边的轮廓可能是干扰，跳过
                    x, y, w, h = cv2.boundingRect(contour)
                    margin = 1
                    if x < margin or y < margin or x + w > img_raw.shape[1] - margin or y + h > img_raw.shape[0] - margin:
                            continue
                            
                    # h. 形状逼近：将轮廓简化成一个多边形
                    approx = cv2.approxPolyDP(contour, 0.02 * cv2.arcLength(contour, True), True)
                    
                    # i. 形状判断：调用我们的核心函数，判断它是否是矩形
                    if is_rectangle(approx):
                        # 将顶点坐标格式化
                        rect = [tuple(pt[0]) for pt in approx]
                        # j. 去重：调用我们的辅助函数，判断这个矩形是否和已找到的矩形相似
                        if not any(is_similar_rect(rect, r) for r in rectangles):
                            # 如果是新的、不重复的矩形，就加入列表
                            rectangles.append(rect)
                            # 在画面上画出绿色的轮廓和红色的顶点
                            cv2.drawContours(img_raw, [np.array(rect, dtype=np.int32)], -1, (0, 255, 0), 2)
                            for x, y in rect:
                                cv2.circle(img_raw, (x, y), 5, (0, 0, 255), -1)

                # --- 中点计算逻辑 ---
                # 如果在一帧中不多不少，正好找到了两个矩形（通常是内外框）
                if len(rectangles) == 2:
                    # 对两个矩形的顶点进行标准化排序
                    r1 = sort_rect_points(rectangles[0])
                    r2_unsorted = sort_rect_points(rectangles[1])
                    # 对第二个矩形的顶点进行智能匹配，确保与第一个矩形对应
                    r2 = match_corners_by_distance(r1, r2_unsorted)

                    # 计算两矩形对应顶点连线的中点
                    for i in range(4):
                        mid = ((r1[i][0] + r2[i][0]) // 2, (r1[i][1] + r2[i][1]) // 2)
                        midpoints[i] = mid
                        # 在画面上画出连接线和中点
                        cv2.line(img_raw, r1[i], r2[i], (255, 0, 255), 1)
                        cv2.circle(img_raw, mid, 3, (0, 255, 255), -1)
            except Exception as e:
                print("矩形检测异常:", e)

        # --- 数据打包与发送 ---
        try:
            # 定义通信协议的帧头
            payload = b'\xAA\x55'
            # 占位4个字节，以维持和原始代码（带激光点）相同的数据包长度
            payload += pack("<hh", 0, 0) 
            
            # 将4个中点的坐标（每个坐标是2个short，共8个short=16字节）打包
            for x, y in midpoints:
                if x < 0 or y < 0: # 如果中点无效
                    payload += pack("<hh", 0, 0)
                else:
                    payload += pack("<hh", x, y)
            # 通过串口发送出去
            serial.write(payload)
        except Exception as e:
            print("串口发送异常:", e)

        # --- 图像显示 ---
        try:
            # 使用官方桥梁函数，将处理和绘制完的 OpenCV 图像转回 MaixPy Image
            img_show = image.cv2image(img_raw, copy=False)
            # 在屏幕上显示
            disp.show(img_show)
        except Exception as e:
            print("图像显示失败:", e)

        # 短暂延时，避免 CPU 占用率 100%
        time.sleep_ms(1)

    except Exception as e:
        print("主循环异常:", e)
