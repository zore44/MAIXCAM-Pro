from maix import app, uart, time, image, camera, display
import cv2
import numpy as np
from struct import pack

# 串口初始化
device = "/dev/ttyS0"
serial0 = uart.UART(device, 115200, uart.BITS.BITS_8,
                    uart.PARITY.PARITY_NONE,
                    uart.STOP.STOP_1)

def send_bytes(*bytes_list):
    """通过UART发送一组字节，自动添加起始和结束标志"""
    start_byte = 0xA5
    end_byte = 0x5B
    data_list = [start_byte] + list(bytes_list) + [end_byte]
    format_str = "<" + "B" * len(data_list)
    data = pack(format_str, *data_list)
    serial0.write(data)
    print("Sent data:", data)

# 图像转换函数
def maix_image_to_cv2(maix_img):
    if maix_img.format() != image.Format.FMT_BGR888:
        maix_img = maix_img.to_format(image.Format.FMT_BGR888)
    img_bytes = maix_img.to_bytes()
    np_array = np.frombuffer(img_bytes, dtype=np.uint8)
    cv_img = np.array(np_array).reshape((maix_img.height(), maix_img.width(), 3))
    return cv_img

# 图像增强器
class ImageEnhancer:
    def __init__(self):
        print("图像增强器初始化完成。")

    def process(self, gray_img):
        return cv2.equalizeHist(gray_img)

# 激光点追踪器
class HybridTracker:
    def __init__(self):
        self.BG_ALPHA = 0.05
        self.DIFF_THRESHOLD = 25
        self.BRIGHTNESS_THRESHOLD = 200
        self.MIN_AREA_DYN = 5
        self.MAX_AREA_DYN = 200
        self.kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        self.background_model = None
        self.LAB_RED_THRESHOLD = (30, 100, 30, 127, -20, 127)
        self.MIN_AREA_STATIC = 10
        self.LAB_A_MIN = 40
        print("激光点追踪器初始化完成。")

    def detect(self, maix_img, cv_img):
        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
        gray_blur = cv2.GaussianBlur(gray, (5, 5), 0)
        if self.background_model is None:
            self.background_model = gray_blur.astype("float")
            return None
        img_diff = cv2.absdiff(self.background_model.astype("uint8"), gray_blur)
        _, diff_mask = cv2.threshold(img_diff, self.DIFF_THRESHOLD, 255, cv2.THRESH_BINARY)
        _, bright_mask = cv2.threshold(gray, self.BRIGHTNESS_THRESHOLD, 255, cv2.THRESH_BINARY)
        interest_mask = cv2.bitwise_and(diff_mask, bright_mask)
        final_mask = cv2.dilate(interest_mask, self.kernel, iterations=2)
        cv2.accumulateWeighted(gray_blur, self.background_model, self.BG_ALPHA)
        contours, _ = cv2.findContours(final_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            biggest_contour = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(biggest_contour)
            if self.MIN_AREA_DYN < area < self.MAX_AREA_DYN:
                x, y, w, h = cv2.boundingRect(biggest_contour)
                hist = maix_img.get_histogram(roi=[x, y, w, h])
                stats = hist.get_statistics()
                if stats.a_median() > self.LAB_A_MIN:
                    M = cv2.moments(biggest_contour)
                    if M["m00"] != 0:
                        cx = int(M["m10"] / M["m00"])
                        cy = int(M["m01"] / M["m00"])
                        return (cx, cy)
        blobs = maix_img.find_blobs([self.LAB_RED_THRESHOLD], area_threshold=self.MIN_AREA_STATIC)
        if blobs:
            best_blob = max(blobs, key=lambda b: b.pixels())
            return (best_blob.cx(), best_blob.cy())
        return None

# 矩形检测器
class RectangleDetector:
    def __init__(self):
        self.MIN_AREA = 2000
        self.MAX_AREA = 80000
        print("矩形检测器初始化完成。")

    def sort_rect_points(self, pts):
        pts = sorted(pts, key=lambda p: (p[1], p[0]))
        top = sorted(pts[:2], key=lambda p: p[0])
        bottom = sorted(pts[2:], key=lambda p: p[0], reverse=True)
        return [top[0], top[1], bottom[0], bottom[1]]

    def match_corners_by_distance(self, ref_pts, target_pts):
        matched = [None] * 4
        used = [False] * 4
        for i, p1 in enumerate(ref_pts):
            min_dist = float("inf")
            min_j = -1
            for j, p2 in enumerate(target_pts):
                if not used[j]:
                    dist = np.linalg.norm(np.array(p1) - np.array(p2))
                    if dist < min_dist:
                        min_dist = dist
                        min_j = j
            matched[i] = target_pts[min_j]
            used[min_j] = True
        return matched

    def is_similar_rect(self, rect1, rect2, threshold=8, area_thresh=0.05):
        try:
            rect1 = self.sort_rect_points(rect1)
            rect2 = self.sort_rect_points(rect2)
            avg_dist = np.mean([np.linalg.norm(np.array(p1) - np.array(p2)) for p1, p2 in zip(rect1, rect2)])
            area1 = cv2.contourArea(np.array(rect1, dtype=np.int32))
            area2 = cv2.contourArea(np.array(rect2, dtype=np.int32))
            area_diff_ratio = abs(area1 - area2) / max(area1, area2)
            return avg_dist < threshold and area_diff_ratio < area_thresh
        except Exception as e:
            print("矩形比较异常:", e)
            return False

    def is_rectangle(self, approx):
        if approx is None or len(approx) != 4 or not cv2.isContourConvex(approx):
            return False
        pts = [point[0] for point in approx]
        def angle(p1, p2, p3):
            v1 = np.array(p1) - np.array(p2)
            v2 = np.array(p3) - np.array(p2)
            norm1 = np.linalg.norm(v1)
            norm2 = np.linalg.norm(v2)
            if norm1 == 0 or norm2 == 0:
                return 0
            cos_angle = np.clip(np.dot(v1, v2) / (norm1 * norm2), -1.0, 1.0)
            return np.arccos(cos_angle) * 180 / np.pi
        angles = [angle(pts[i - 1], pts[i], pts[(i + 1) % 4]) for i in range(4)]
        return all(80 < ang < 100 for ang in angles)

    def detect(self, img_raw):
        try:
            gray = cv2.cvtColor(img_raw, cv2.COLOR_BGR2GRAY)
            bin_img = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                            cv2.THRESH_BINARY, 11, 2)
            closed = cv2.morphologyEx(bin_img, cv2.MORPH_CLOSE,
                                       cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)))
            contours, _ = cv2.findContours(closed, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            
            rectangles = []
            for contour in contours:
                area = cv2.contourArea(contour)
                if not (self.MIN_AREA <= area <= self.MAX_AREA):
                    continue
                
                x, y, w, h = cv2.boundingRect(contour)
                margin = 1
                if x < margin or y < margin or x + w > img_raw.shape[1] - margin or y + h > img_raw.shape[0] - margin:
                    continue
                        
                approx = cv2.approxPolyDP(contour, 0.02 * cv2.arcLength(contour, True), True)
                
                if self.is_rectangle(approx):
                    rect = [tuple(pt[0]) for pt in approx]
                    if not any(self.is_similar_rect(rect, r) for r in rectangles):
                        rectangles.append(rect)
                        cv2.drawContours(img_raw, [np.array(rect, dtype=np.int32)], -1, (0, 255, 0), 2)
                        for x, y in rect:
                            cv2.circle(img_raw, (x, y), 5, (0, 0, 255), -1)

            midpoints = [(-1, -1)] * 4
            if len(rectangles) == 2:
                r1 = self.sort_rect_points(rectangles[0])
                r2_unsorted = self.sort_rect_points(rectangles[1])
                r2 = self.match_corners_by_distance(r1, r2_unsorted)

                for i in range(4):
                    mid = ((r1[i][0] + r2[i][0]) // 2, (r1[i][1] + r2[i][1]) // 2)
                    midpoints[i] = mid
                    cv2.line(img_raw, r1[i], r2[i], (255, 0, 255), 1)
                    cv2.circle(img_raw, mid, 3, (0, 255, 255), -1)
            
            return midpoints
        except Exception as e:
            print("矩形检测异常:", e)
            return [(-1, -1)] * 4

# 初始化
try:
    cam = camera.Camera(320, 240, fps=80)
    disp = display.Display()
    enhancer = ImageEnhancer()
    tracker = HybridTracker()
    rect_detector = RectangleDetector()
    print("--- 主程序开始运行 ---")
except Exception as e:
    print(f"初始化失败: {e}")
    while True: time.sleep(1)

last_known_pos = None
mode = 0  # 0: 待机, 1: 矩形检测, 2: 激光点检测

while not app.need_exit():
    try:
        # 读取串口指令
        try:
            data = serial0.read()
            if data:
                for byte in data:
                    if byte == 1:
                        mode = 1
                        print("切换到矩形检测模式")
                    elif byte == 2:
                        mode = 2
                        print("切换到激光点检测模式")
        except Exception as e:
            print("串口读取异常:", e)

        img = cam.read()
        if not img:
            continue

        if mode == 1:  # 矩形检测模式
            try:
                img_raw = image.image2cv(img, copy=True)
                midpoints = rect_detector.detect(img_raw)
                
                # 发送矩形中点坐标
                coords = []
                for x, y in midpoints:
                    if x < 0 or y < 0:
                        coords.extend([0, 0])
                    else:
                        coords.extend([x, y])
                send_bytes(*coords)
                
                img_show = image.cv2image(img_raw, copy=False)
                disp.show(img_show)
            except Exception as e:
                print("矩形检测异常:", e)

        elif mode == 2:  # 激光点检测模式
            try:
                cv_img = maix_image_to_cv2(img)
                gray_cv_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
                enhanced_gray_cv_img = enhancer.process(gray_cv_img)
                enhanced_cv_img = cv2.cvtColor(enhanced_gray_cv_img, cv2.COLOR_GRAY2BGR)
                
                laser_pos = tracker.detect(img, enhanced_cv_img)
                
                if laser_pos is not None:
                    last_known_pos = laser_pos
                    cx, cy = laser_pos
                    img.draw_cross(cx, cy, size=15, color=image.COLOR_RED, thickness=2)
                    send_bytes(cx, cy)
                    print(f"激光点坐标: ({cx}, {cy})")
                elif last_known_pos is not None:
                    cx, cy = last_known_pos
                    img.draw_cross(cx, cy, size=15, color=image.COLOR_RED, thickness=2)
                
                disp.show(img)
            except Exception as e:
                print("激光点检测异常:", e)
        
        else:  # 待机模式
            disp.show(img)

        time.sleep_ms(1)

    except Exception as e:
        print("主循环异常:", e)