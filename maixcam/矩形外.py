from maix import camera, display, image

# 初始化摄像头（RGB888格式，640x480分辨率，60FPS）
cam = camera.Camera(320, 160, image.Format.FMT_RGB888, fps=60)
disp = display.Display()  # 初始化屏幕

while True:
    img = cam.read()          # 捕获一帧图像
    gray_img=img.to_format(image.Format.FMT_GRAYSCALE)
    blobs = gray_img.find_rects(threshold=30000)
    for blob in blobs:
        corners = blob.corners()
        for i in range(4):
            gray_img.draw_line(corners[i][0], corners[i][1],   
                             corners[(i + 1) % 4][0], corners[(i + 1) % 4][1],   
                             color=image.Color.from_rgb(255, 255, 255))  
        x,y,w,h=blob.rect()
        #gray_img.draw_rect(x,y,w,h,color=image.Color.from_rgb(255, 255, 255))
    disp.show(gray_img)            # 显示到屏幕