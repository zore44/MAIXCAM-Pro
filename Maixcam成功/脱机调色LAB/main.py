from maix import image, camera, display, app, time,uart
import cv2
import numpy as np
from LAB_a import ColorThresholdConfig
from struct import pack

device = "/dev/ttyS0"
serial0 = uart.UART(device, 115200, uart.BITS.BITS_8,
                    uart.PARITY.PARITY_NONE,
                    uart.STOP.STOP_1)



def send_bytes(*ints16):
    """
    通过UART发送一组16位整数，自动添加起始和结束标志
    ints16: 8个16位整数（0 <= num <= 65535）
    """
    start_byte = 0xA5A5
    end_byte = 0x5B5B
    # 打包格式：H（起始字节） + 8H（8个坐标） + H（结束字节）
    format_str = ">H" + "H" * len(ints16) + "H"
    data = pack(format_str, start_byte, *ints16, end_byte)
    serial0.write(data)
    print("Sent data:", data)
# 1. 启动阈值调节器
config = ColorThresholdConfig()
threshold = config.run_threshold_adjust()   # 阻塞直到点 Exit

print("\n从 LAB_a.py 获取的阈值：")
print(f"L: {threshold[0]}~{threshold[1]}")
print(f"A: {threshold[2]}~{threshold[3]}")
print(f"B: {threshold[4]}~{threshold[5]}")

# 2. 开始颜色追踪
cam = camera.Camera(320, 240, fps=90)
disp = display.Display()
MIN_AREA = 10

print("开始色块追踪（仅最大的一个）...")

while not app.need_exit():
    img = cam.read()

    blobs = img.find_blobs([threshold], merge=True)

    # 过滤面积并找最大的色块
    valid_blobs = [b for b in blobs if b.area() >= MIN_AREA]
    if not valid_blobs:
        disp.show(img)        # 别忘了 show
        continue

    max_blob = max(valid_blobs, key=lambda b: b.area())

    # ---------- 新增：4 角点 + 中心点 ----------
    # 取色块的 4 个角点（注意顺序：左上→右上→右下→左下）
    corners = max_blob.corners()        # list[list[int]]  [[x,y],...]

    # 计算中心点
    cx = sum(p[0] for p in corners) // 4
    cy = sum(p[1] for p in corners) // 4

    # # 画 4 角点（红实心圆）
    # for x, y in corners:
    #     img.draw_circle(x, y, 4, image.COLOR_RED, thickness=-1)

    # # 画中心点（绿实心圆）
    img.draw_circle(cx, cy, 6, image.COLOR_GREEN, thickness=-1)

    # # 画连线（可选）
    # img.draw_edges(corners, image.COLOR_BLACK, thickness=2)
    # ------------------------------------------

    # 打印调试
    #print(f"最大色块中心: ({max_blob.cx()}, {max_blob.cy()}) 面积: {max_blob.area()}")
    send_bytes(cx,cy)
    disp.show(img)
