from maix import image, camera, display,app,time

cam = camera.Camera(320, 240, fps=80)
disp = display.Display()
 
while not app.need_exit():
    img = cam.read()
    # 1. 灰度化
    gray = img.to_format(image.Format.FMT_GRAYSCALE)
    # 2. 高斯滤波
    blur = gray.gaussian(2)

    bin_rgb=blur.find_edges(image.EdgeDetector.EDGE_CANNY, threshold=[50, 70]) 
    disp.show(bin_rgb)
    fps = time.fps()            
    print(f"time: {1000/fps:.02f}ms, fps: {fps:.02f}")
