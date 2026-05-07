from maix import nn, image,camera,display

detector = nn.YOLOv5(model="/root/models/shu/model_139433.mud", dual_buff = True)

cam  = camera.Camera(detector.input_width(),detector.input_height(),detector.input_format())
disp = display.Display()


while True:
    img=cam.read()
    objs = detector.detect(img, conf_th = 0.7, iou_th = 0.45)
    for obj in objs:
        img.draw_rect(obj.x, obj.y, obj.w, obj.h, color = image.COLOR_RED)
        msg = f'{detector.labels[obj.class_id]}: {obj.score:.2f}'
        img.draw_string(obj.x, obj.y, msg, color = image.COLOR_RED)
    disp.show(img)
