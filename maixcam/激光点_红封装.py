from maix import camera, display, image, time

# ====================== 1. 将所有功能封装进一个类 ======================
class LaserTracker:
    """
    一个完整的激光追踪器类。
    严格按照你提供的最新脚本逻辑进行封装。
    """
    def __init__(self, cam_width=320, cam_height=240):
        """
        类的构造函数，在创建对象时自动执行，用于完成所有初始化工作。
        """
        # 初始化硬件
        self.cam = camera.Camera(cam_width, cam_height)
        self.disp = display.Display()

        # 设置核心参数 (来自你的脚本)
        # 注意：我将你的列表[]改成了元组()，这是find_blobs更推荐的格式
        self.laser_threshold = (0, 100, 10, 127, 0, 127)
        self.pixels_thresh = 1
        self.area_thresh = 3

        # 定义绘图颜色 (来自你的脚本)
        self.color_cross = image.Color.from_rgb(255, 0, 0) # 红色十字
        self.color_text = image.Color.from_rgb(0, 0, 255)  # 蓝色文字
        self.color_not_found = image.Color.from_rgb(255, 0, 0) # 红色 "Not found"

        print("--- 激光光斑视觉追踪程序 ---")
        print("请将激光笔照射到摄像头视野内...")


    def run_one_frame(self):
        """
        处理单帧图像的核心逻辑。
        包含了你脚本中 while 循环的全部内容。
        """
        # 1. 从摄像头捕获一帧图像
        img = self.cam.read()
        if not img:
            time.sleep(0.01)
            return

        # 2. 寻找色块 (Blobs)
        blobs = img.find_blobs([self.laser_threshold], pixels_threshold=self.pixels_thresh, area_threshold=self.area_thresh, merge=True)

        # 3. 从找到的色块中筛选出最大的一个并处理
        if blobs:
            max_blob = max(blobs, key=lambda b: b.area())
            
            center_x = max_blob.cx()
            center_y = max_blob.cy()

            # 绘制结果 (严格按照你的要求)
            # draw_rect 被注释掉了，所以这里不画
            img.draw_cross(center_x, center_y, size=10, color=self.color_cross, thickness=3)
            
            info_text = f"X: {center_x}, Y: {center_y}"
            img.draw_string(10, 10, info_text, scale=2.0, color=self.color_text)
            
            # 坐标打印被注释掉了，所以这里不打印
            # print(f"找到目标! ...")

        else:
            # 如果没有找到任何色块
            img.draw_string(10, 10, "No target found", scale=2.0, color=self.color_not_found)
            # "未找到目标..." 打印被注释掉了，所以这里不打印
            # print("未找到目标...")

        # 4. 将处理后的图像显示在屏幕上
        self.disp.show(img)
        
        # 5. 计算并打印FPS (来自你的脚本)
        fps = time.fps()
        # 使用 if fps > 0 防止除零错误
        if fps > 0:
            print(f"time: {1000/fps:.2f}ms, fps: {fps:.2f}")


# ====================== 2. 主程序入口 ======================
if __name__ == "__main__":
    # 创建追踪器对象，所有初始化会自动完成
    tracker = LaserTracker()

    # 启动无限循环，循环体里只调用一个方法
    while True:
        # 这就是封装后的效果：主循环只做一件事！
        tracker.run_one_frame()
