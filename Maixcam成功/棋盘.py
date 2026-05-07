from maix import camera, display, image, app
import cv2
import numpy as np

# ---------- 棋盘中心点计算 ----------
def find_grid_centers(corners):
    grid = np.array([[j/3, i/3] for i in range(4) for j in range(4)], np.float32)
    src = np.array([[0,0],[1,0],[1,1],[0,1]], np.float32)
    M   = cv2.getPerspectiveTransform(src, np.array(corners, np.float32))
    pts = cv2.perspectiveTransform(grid[None], M)[0]

    centers = []
    for y in range(3):
        for x in range(3):
            idx = y*4 + x
            cx = int((pts[idx][0] + pts[idx+1][0] + pts[idx+4][0] + pts[idx+5][0]) / 4)
            cy = int((pts[idx][1] + pts[idx+1][1] + pts[idx+4][1] + pts[idx+5][1]) / 4)
            centers.append((cx, cy))
    return centers

# ---------- 主循环 ----------
def main():
    cam  = camera.Camera(320, 320)
    disp = display.Display()

    while not app.need_exit():
        img = cam.read()

        # 1. 转成 OpenCV 的 numpy 数组
        img_cv = image.image2cv(img, ensure_bgr=False, copy=True)  # ← 关键修复
        gray   = cv2.cvtColor(img_cv, cv2.COLOR_RGB2GRAY)
        blur   = cv2.GaussianBlur(gray, (5,5), 0)
        edge   = cv2.Canny(blur, 50, 150)
        cnts,_ = cv2.findContours(edge, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if cnts:
            largest = max(cnts, key=cv2.contourArea)
            eps     = 0.02 * cv2.arcLength(largest, True)
            poly    = cv2.approxPolyDP(largest, eps, True)

            if len(poly) == 4:
                pts  = poly.reshape(4,2)
                rect = np.zeros((4,2), dtype=int)
                s, d = pts.sum(1), np.diff(pts, axis=1)
                rect[0], rect[2] = pts[np.argmin(s)], pts[np.argmax(s)]
                rect[1], rect[3] = pts[np.argmin(d)], pts[np.argmax(d)]

                centers = find_grid_centers(rect)
                for (x,y) in centers:
                    img.draw_circle(x, y, 3, image.COLOR_GREEN, -1)
                for i in range(4):
                    img.draw_line(*rect[i], *rect[(i+1)%4], image.COLOR_RED, 2)

        disp.show(img)

if __name__ == '__main__':
    main()
