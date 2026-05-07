from maix import image, camera, display, app, time
import cv2
import numpy as np

# 初始化
cam = camera.Camera(320, 240, fps=80)
disp = display.Display()

# ROI（中心 100×100）
roi_x, roi_y, roi_w, roi_h = 60, 70, 150, 150


def sort_clockwise(pts):
    pts = np.array(pts, dtype=np.int32)
    cx, cy = np.mean(pts[:, 0]), np.mean(pts[:, 1])

    def angle_clockwise(p):
        dx, dy = p[0] - cx, p[1] - cy
        # 从正 X 轴开始顺时针角度（0° 向右，90° 向下）
        angle = (np.arctan2(dy, dx) * 180 / np.pi) % 360
        # 把起点移到左上角：先减 135°，再取模
        return (angle - 135) % 360

    idx = sorted(range(len(pts)), key=lambda i: angle_clockwise(pts[i]))
    return pts[idx].tolist()


while not app.need_exit():
    img = cam.read()
    img_cv = image.image2cv(img, ensure_bgr=True, copy=True)

    gray = cv2.cvtColor(img_cv, cv2.COLOR_RGB2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)

    # ROI 裁剪
    roi = blur[roi_y:roi_y + roi_h, roi_x:roi_x + roi_w]

    # 角点检测
    corners = cv2.goodFeaturesToTrack(roi, maxCorners=20,
                                      qualityLevel=0.1,
                                      minDistance=10)

    # 绘制 ROI 框
    green = (0, 255, 0)
    cv2.rectangle(img_cv, (roi_x, roi_y),
                  (roi_x + roi_w, roi_y + roi_h), green, 3)

    if corners is not None:
        corners = np.int0(corners)
        pts = []
        for c in corners:
            x, y = c.ravel()
            abs_x = x + roi_x
            abs_y = y + roi_y
            pts.append((abs_x, abs_y))
            cv2.circle(img_cv, (abs_x, abs_y), 3, (0, 0, 255), -1)

        # 顺时针排序并打印
        sorted_pts = sort_clockwise(pts)
        print("顺时针角点坐标:", sorted_pts)

    # 显示
    img_show = image.cv2image(img_cv, bgr=True,copy=False)
    disp.show(img_show)

