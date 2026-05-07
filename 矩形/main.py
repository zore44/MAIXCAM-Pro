# ================= 1. 头文件 =================
from maix import image, camera, display, app, time, uart
import cv2
import numpy as np
import errno
from LAB_a import ColorThresholdConfig          # 阈值调节器
from struct import pack, unpack

# ================= 2. 串口 =================
device = "/dev/ttyS0"
serial0 = uart.UART(device, 115200,
                    uart.BITS.BITS_8,
                    uart.PARITY.PARITY_NONE,
                    uart.STOP.STOP_1)

# ================= 3. 全局常量 =================
MODE_COLOR = 0          # 色块追踪
MODE_RECT  = 1
work_mode  = MODE_RECT  # 上电默认矩形识别

MIN_AREA_RECT = 3000
MAX_AREA_RECT = 8000000

# ================= 4. 阈值调节 =================
config   = ColorThresholdConfig()
threshold = config.run_threshold_adjust()   # 阻塞，直到点 Exit
print("阈值已保存：", threshold)

# ================= 5. 摄像头/显示 =================
cam  = camera.Camera(320,240,fps=90)
disp = display.Display()

# ================= 6. 工具函数 =================
def send_bytes(*ints16):
    if all(v == 0xFFFF for v in ints16):
        return
    """发送 16bit 整数；自动限幅 0~65535，最多 8 个"""
    start, end = 0xA5A5, 0x5B5B
    ints16 = [max(0, min(65535, int(v))) for v in ints16][:8]
    fmt = ">H" + "H" * len(ints16) + "H"
    serial0.write(pack(fmt, start, *ints16, end))
    print(pack(fmt, start, *ints16, end))
def read_uart_cmd():
    """非阻塞读取 1 字节命令：0/1/None"""
    buf = serial0.read()          # 无数据时返回 b''
    if buf and len(buf) == 1:     # 先判空再解包
        val = unpack("B", buf)[0]-48
        print("收到串口字节:", val)
        return val if val in (0, 1) else None
    return None

def is_rectangle(approx):
    if approx is None or len(approx) != 4 or not cv2.isContourConvex(approx):
        return False
    pts = [p[0] for p in approx]

    def angle(a, b, c):
        v1, v2 = np.array(a) - np.array(b), np.array(c) - np.array(b)
        cos_ = np.clip(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-6), -1, 1)
        return np.degrees(np.arccos(cos_))

    angles = [angle(pts[i - 1], pts[i], pts[(i + 1) % 4]) for i in range(4)]
    return all(80 < ang < 100 for ang in angles)

# ================= 7. 主循环 =================
while not app.need_exit():
    try:
        # 1) 串口命令
        cmd = read_uart_cmd()
        if cmd is not None:
            work_mode = cmd
            print("切换到模式:", "色块追踪" if work_mode == MODE_COLOR else "矩形识别")

        # 2) 取图
        img = cam.read()
        if img is None:
            continue

        # 3) 模式处理
        if work_mode == MODE_COLOR:
            blobs = img.find_blobs([threshold], merge=True)
            valid = [b for b in blobs if b.area() >= 10]
            if valid:
                max_blob = max(valid, key=lambda b: b.area())
                cx, cy = max_blob.cx(), max_blob.cy()
                img.draw_circle(cx, cy, 6, image.COLOR_GREEN, thickness=-1)
                send_bytes(cx, cy)
            else:
                send_bytes(0xFFFF, 0xFFFF)

        else:   # 矩形识别
            img_cv = image.image2cv(img, copy=True)
            gray   = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
            bin_img = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 11, 2)
            closed = cv2.morphologyEx(
                bin_img, cv2.MORPH_CLOSE,
                cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)))

            contours, _ = cv2.findContours(
                closed, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

            rectangles = []
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if not (MIN_AREA_RECT <= area <= MAX_AREA_RECT):
                    continue
                approx = cv2.approxPolyDP(
                    cnt, 0.02 * cv2.arcLength(cnt, True), True)
                if is_rectangle(approx):
                    pts = [tuple(pt[0]) for pt in approx]
                    rectangles.append(pts)

            # ===== 新增：过滤太靠近边缘的矩形 =====
            h, w = img.height(), img.width()
            rectangles = [pts for pts in rectangles
                          if all(5 < pt[0] < w-5 and 5 < pt[1] < h-5 for pt in pts)]
            # =====================================

            cx, cy = 0xFFFF, 0xFFFF
            if rectangles:
                pts = max(rectangles, key=lambda r: cv2.contourArea(np.array(r, dtype=np.int32)))

                # 画绿色轮廓
                cv2.drawContours(img_cv, [np.array(pts, dtype=np.int32)], -1, (0, 255, 0), 2)

                # 画对角线
                cv2.line(img_cv, pts[0], pts[2], (0, 0, 255), 1)
                cv2.line(img_cv, pts[1], pts[3], (0, 0, 255), 1)

                # 计算对角线交点
                x0, y0 = pts[0]; x2, y2 = pts[2]
                x1, y1 = pts[1]; x3, y3 = pts[3]
                denom = (x0 - x2) * (y1 - y3) - (y0 - y2) * (x1 - x3)
                if abs(denom) > 1e-6:
                    t = ((x0 - x1) * (y1 - y3) - (y0 - y1) * (x1 - x3)) / denom
                    cx = int(x0 + t * (x2 - x0))
                    cy = int(y0 + t * (y2 - y0))
                    cx = max(0, min(img.width() - 1, cx))
                    cy = max(0, min(img.height() - 1, cy))
                    cv2.circle(img_cv, (cx, cy), 3, (0, 255, 0), -1)

            send_bytes(cx, cy)
            img = image.cv2image(img_cv, copy=False)

        # 4) 显示
        disp.show(img)
        time.sleep_ms(1)

    except Exception as e:
        import sys
        sys.print_exception(e)
        time.sleep_ms(100)
