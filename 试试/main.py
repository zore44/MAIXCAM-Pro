# main.py
from maix import camera, display, image, app
from LAB_a import ColorThresholdConfig  # 复用你的类

# 1. 启动阈值调节器
config = ColorThresholdConfig()
threshold = config.run_threshold_adjust()  # ← 阻塞直到你点 Exit

print("\n从 LAB_a.py 获取的阈值：")
print(f"L: {threshold[0]}~{threshold[1]}")
print(f"A: {threshold[2]}~{threshold[3]}")
print(f"B: {threshold[4]}~{threshold[5]}")

# 2. 开始颜色追踪
cam = camera.Camera(320, 240)
disp = display.Display()
MIN_AREA = 100

print("开始色块追踪...")

while not app.need_exit():
    img = cam.read()
    for blob in img.find_blobs([threshold], merge=True):
        if blob.area() < MIN_AREA:
            continue
        img.draw_rect(blob.x(), blob.y(), blob.w(), blob.h(), image.COLOR_GREEN)
        img.draw_cross(blob.cx(), blob.cy(), image.COLOR_GREEN, size=5)
        print(f"色块中心: ({blob.cx()}, {blob.cy()}) 面积: {blob.area()}")
    disp.show(img)
