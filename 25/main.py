# ================= 1. 头文件 =================
from maix import image, camera, display, app, time, uart
import cv2
import numpy as np
from LAB import ColorThresholdConfig
from struct import pack, unpack

# ================= 2. 串口 =================
device  = "/dev/ttyS0"
serial0 = uart.UART(device, 115200,
                    uart.BITS.BITS_8,
                    uart.PARITY.PARITY_NONE,
                    uart.STOP.STOP_1)

# ================= 3. 全局常量 =================
MODE_COLOR = 0
MODE_RECT  = 1
work_mode  = MODE_RECT

MIN_AREA_RECT = 8000
MAX_AREA_RECT = 32000000

cx_screen, cy_screen = 320, 240   # 十字中心
old_scr_txt = None                # 缓存文字，减少 draw_string

# ================= 4. 阈值调节 =================
config    = ColorThresholdConfig()
threshold = config.run_threshold_adjust()
print("阈值已保存：", threshold)

# ================= 5. 摄像头/显示 =================
cam  = camera.Camera(640, 480, fps=60)   # ① 降到 60 FPS
disp = display.Display()

# ================= 6. 工具函数 =================
def send_bytes(*ints16):
    if all(v == 0xFFFF for v in ints16):
        return
    start, end = 0xA5A5, 0x5B5B
    ints16 = [max(0, min(65535, int(v))) for v in ints16][:8]
    fmt = ">H" + "H" * len(ints16) + "H"
    serial0.write(pack(fmt, start, *ints16, end))

def read_uart_cmd():
    buf = serial0.read(1)
    if buf and len(buf) == 1:
        val = unpack("B", buf)[0]
        return val if val in (0, 1) else None
    return None

def is_rectangle(approx):
    if approx is None or len(approx) != 4 or not cv2.isContourConvex(approx):
        return False
    pts = [p[0] for p in approx]
    def angle(a, b, c):
        v1 = np.array(a) - np.array(b)
        v2 = np.array(c) - np.array(b)
        cos_ = np.clip(np.dot(v1, v2) /
                       (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-6), -1, 1)
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
            if cmd == MODE_COLOR:
                tmp = cam.read()
                if tmp:
                    blobs = tmp.find_blobs([threshold], merge=True)
                    valid = [b for b in blobs if b.area() >= 40]
                    if valid:
                        max_blob = max(valid, key=lambda b: b.area())
                        cx_screen, cy_screen = max_blob.cx(), max_blob.cy()
            print("切换到模式:", "色块追踪" if work_mode == MODE_COLOR else "矩形识别")

        # 2) 取图
        img = cam.read()
        if img is None:
            continue

        # 3) 模式处理
        if work_mode == MODE_COLOR:
            blobs = img.find_blobs([threshold], merge=True)
            valid = [b for b in blobs if b.area() >= 40]
            if valid:
                max_blob = max(valid, key=lambda b: b.area())
                cx, cy = max_blob.cx(), max_blob.cy()
                img.draw_circle(cx, cy, 6, image.COLOR_GREEN, thickness=-1)
                img.draw_rectangle(max_blob.rect(), color=image.COLOR_GREEN, thickness=2)
                send_bytes(cx, cy)
            else:
                send_bytes(0xFFFF, 0xFFFF)

        else:  # 矩形识别
            img_cv = image.image2cv(img, copy=False)   # ③ 去掉 copy
            gray   = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
            bin_img = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY,
                21, 2)   # ② 窗口变大
            closed = cv2.morphologyEx(
                bin_img, cv2.MORPH_CLOSE,
                cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)))

            contours, _ = cv2.findContours(
                closed, cv2.RETR_TREE,
                cv2.CHAIN_APPROX_TC89_L1)   # ④ 更轻链

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

            h, w = img.height(), img.width()
            rectangles = [pts for pts in rectangles
                          if all(10 < pt[0] < w-10 and 10 < pt[1] < h-10 for pt in pts)]

            cx, cy = 0xFFFF, 0xFFFF
            if rectangles:
                pts = max(rectangles,
                          key=lambda r: cv2.contourArea(np.array(r, dtype=np.int32)))
                cv2.drawContours(img_cv, [np.array(pts, dtype=np.int32)], -1, (0, 255, 0), 2)

                x0, y0 = pts[0]; x2, y2 = pts[2]
                x1, y1 = pts[1]; x3, y3 = pts[3]
                denom = (x0 - x2) * (y1 - y3) - (y0 - y2) * (x1 - x3)
                if abs(denom) > 1e-6:
                    t = ((x0 - x1) * (y1 - y3) - (y0 - y1) * (x1 - x3)) / denom
                    cx = int(x0 + t * (x2 - x0))
                    cy = int(y0 + t * (y2 - y0))
                    cx = max(0, min(w-1, cx))
                    cy = max(0, min(h-1, cy))
                    cv2.circle(img_cv, (cx, cy), 6, (0, 255, 0), -1)
                send_bytes(cx, cy)
            else:
                send_bytes(0xFFFF, 0xFFFF)

            img = image.cv2image(img_cv, copy=False)

        # 4) 十字 + 实时坐标（文字缓存减少 draw）
        ch = 60
        img.draw_line(cx_screen - ch, cy_screen, cx_screen + ch, cy_screen,
                      color=image.COLOR_BLUE, thickness=2)
        img.draw_line(cx_screen, cy_screen - ch, cx_screen, cy_screen + ch,
                      color=image.COLOR_BLUE, thickness=2)

        scr_txt = f"X:{cx_screen} Y:{cy_screen}"
        if scr_txt != old_scr_txt:
            img.draw_string(10, 10, scr_txt, color=image.COLOR_RED, scale=1.5)
            old_scr_txt = scr_txt

        disp.show(img)
        time.sleep_ms(1)

    except Exception as e:
        print(e)
        time.sleep_ms(100)
