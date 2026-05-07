from maix import image, camera, display

cam = camera.Camera(320, 240)#创建摄像头对象，参数为画面的宽度（320）和高度（240）
disp = display.Display() #创显示屏

# 根据色块颜色选择对应配置
thresholds = [[73, 90, -2, 36, 9, 19]]      # red
# thresholds = [[0, 80, -120, -10, 0, 30]]    # green
# thresholds = [[0, 80, 30, 100, -120, -60]]  # blue

while 1:
    img = cam.read()   
    blobs = img.find_blobs(thresholds, pixels_threshold=50)
    for blob in blobs:
        img.draw_rect(blob[0], blob[1], blob[2], blob[3], image.COLOR_GREEN)
    disp.show(img)
