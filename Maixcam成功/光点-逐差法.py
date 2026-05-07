from maix import image, camera, display, app
import cv2
import numpy as np

# =================================================================
# --- 0. 辅助函数 (保持不变) ---
# =================================================================
def maix_image_to_cv2(maix_img):
    if maix_img.format() != image.Format.FMT_BGR888:
        maix_img = maix_img.to_format(image.Format.FMT_BGR888)
    img_bytes = maix_img.to_bytes()
    np_array = np.frombuffer(img_bytes, dtype=np.uint8)
    cv_img = np.array(np_array).reshape((maix_img.height(), maix_img.width(), 3))
    return cv_img

# =================================================================
# --- 1. 【新增】图像增强模块 ---
# =================================================================
class ImageEnhancer:
    """一个用于在低光照下增强图像质量的模块。"""
    def __init__(self):
        print("图像增强器初始化完成。")

    def process(self, gray_img):
        """
        对输入的灰度图进行直方图均衡化，以增强对比度。
        """
        # cv2.equalizeHist 只能处理单通道灰度图
        return cv2.equalizeHist(gray_img)

# =================================================================
# --- 2. 核心类：HybridTracker (保持不变) ---
# 我们的追踪器已经很完美了，不需要改动它！
# =================================================================
class HybridTracker:
    """一个结合了动态背景建模和色彩法的终极追踪器。"""
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
        print("终极混合动力追踪器初始化完成。")

    def detect(self, maix_img, cv_img):
        # 【注意】这个函数现在接收的是“增强后”的图像
        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
        # ... 内部逻辑完全不变 ...
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

# =================================================================
# --- 3. 主程序 (集成硬件控制和软件增强) ---
# =================================================================
try:
    cam = camera.Camera(320, 240)
    
    # --- 【硬件级优化】 ---
    # 取消下面一行的注释，强制摄像头使用手动曝光模式
    # cam.set_auto_exposure(False)
    # 设置一个固定的曝光值 (单位是微秒)。值越大，画面越亮。你需要实验找到最佳值。
    # cam.set_exposure_us(5000) 
    
    disp = display.Display()
    enhancer = ImageEnhancer()
    tracker = HybridTracker()
    print("--- 主程序开始运行 ---")
except Exception as e:
    print(f"初始化失败: {e}")
    while True: time.sleep(1)

last_known_pos = None

while not app.need_exit():
    img = cam.read()
    if not img:
        continue

    cv_img = maix_image_to_cv2(img)
    
    # --- 【软件级增强】 ---
    # a. 先将图像转为灰度
    gray_cv_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
    # b. 对灰度图进行直方图均衡化
    enhanced_gray_cv_img = enhancer.process(gray_cv_img)
    # c. 将增强后的灰度图转回 BGR，以便追踪器使用 (追踪器内部会再次转灰度，这有点冗余但能保持模块独立性)
    enhanced_cv_img = cv2.cvtColor(enhanced_gray_cv_img, cv2.COLOR_GRAY2BGR)
    
    # 【一句调用】将“增强后”的图像送入追踪器
    laser_pos = tracker.detect(img, enhanced_cv_img)

    if laser_pos is not None:
        last_known_pos = laser_pos
    
    if last_known_pos is not None:
        cx, cy = last_known_pos
        img.draw_cross(cx, cy, size=15, color=image.COLOR_RED, thickness=2)
        if laser_pos is not None:
            print(f"激光点坐标: ({cx}, {cy})")
    
    # (调试技巧) 如果想看增强后的效果，可以取消下面两行
    # debug_show = image.cv2image(enhanced_cv_img, copy=False)
    # disp.show(debug_show)
    
    disp.show(img)
