from maix import camera, display, image  
  
def simple_rectangle_detection():  
    cam = camera.Camera(320, 240)  
    disp = display.Display()  
      
    while True:  
        img = cam.read()  
          
        # 方法一：使用内置find_rects  
        rects = img.find_rects(threshold=23000)  
          
        for rect in rects:  
            corners = rect.corners()  
            # 绘制矩形的四个角点  
            for i in range(4):  
                img.draw_line(corners[i][0], corners[i][1],   
                             corners[(i + 1) % 4][0], corners[(i + 1) % 4][1],   
                             image.COLOR_RED)  
              
            # 绘制外接矩形  
            bbox = rect.rect()  
            img.draw_rect(bbox[0], bbox[1], bbox[2], bbox[3], image.COLOR_GREEN)  
          
        disp.show(img)  
  
if __name__ == "__main__":  
    simple_rectangle_detection()