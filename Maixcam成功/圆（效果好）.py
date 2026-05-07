from maix import camera, display, image, app
import cv2
import numpy as np

cam = camera.Camera(320, 240, image.Format.FMT_BGR888)
disp = display.Display()

# ---------- 几何圆拟合 ----------
def fit_circle_least_square(pts):
    """pts: [(x,y), ...]"""
    pts = np.array(pts, dtype=np.float32)
    n = len(pts)
    if n < 6:
        return None
    A = np.c_[pts[:, 0], pts[:, 1], np.ones(n)]
    b = pts[:, 0]**2 + pts[:, 1]**2
    try:
        c, _, _, _ = np.linalg.lstsq(A, b, rcond=None)
    except:
        return None
    xc, yc, r2 = c[0]/2, c[1]/2, np.sqrt(c[2] + (c[0]/2)**2 + (c[1]/2)**2)
    # 置信度：平均径向误差
    err = np.abs(np.sqrt((pts[:, 0] - xc)**2 + (pts[:, 1] - yc)**2) - r2).mean()
    score = max(0, 1 - err / (r2 + 1e-6))
    if score < 0.85:
        return None
    return int(xc), int(yc), int(r2), score

# ---------- 滑动平均器 ----------
class CircleSmoother:
    def __init__(self, alpha=0.3):
        self.alpha = alpha
        self.x = None
        self.y = None
        self.r = None

    def update(self, cx, cy, r):
        if self.x is None:
            self.x, self.y, self.r = cx, cy, r
        else:
            self.x = int(self.alpha * cx + (1 - self.alpha) * self.x)
            self.y = int(self.alpha * cy + (1 - self.alpha) * self.y)
            self.r = int(self.alpha * r + (1 - self.alpha) * self.r)
        return self.x, self.y, self.r

    def reset(self):
        self.x = self.y = self.r = None

smoother = CircleSmoother(alpha=0.3)

# ---------- 主循环 ----------
while not app.need_exit():
    img = cam.read()
    frame = image.image2cv(img, ensure_bgr=True, copy=False)  # numpy.ndarray

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 1.5)
    edges = cv2.Canny(blur, 50, 120)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    best = None
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < 300 or area > 30000:
            continue
        # 圆度 = 4πA / P²
        perimeter = cv2.arcLength(cnt, True)
        if perimeter == 0:
            continue
        circularity = 4 * np.pi * area / (perimeter ** 2)
        if circularity < 0.7:
            continue
        pts = cnt.reshape(-1, 2).tolist()
        circle = fit_circle_least_square(pts)
        if circle:
            xc, yc, r, score = circle
            if best is None or score > best[3]:
                best = (xc, yc, r, score)

    if best:
        cx, cy, r, _ = best
        cx, cy, r = smoother.update(cx, cy, r)
        cv2.circle(frame, (cx, cy), r, (0, 255, 0), 2)
        cv2.circle(frame, (cx, cy), 2, (0, 0, 255), -1)
    else:
        smoother.reset()

    disp.show(image.cv2image(frame, bgr=True, copy=False))
