# lab_tuner_unified.py  ——  RGB 阈值调节器（最终可跑版）
import ujson as json
from maix import camera, display, touchscreen, image, app, time
from ui import Button, ButtonManager, Slider, SliderManager, Switch, SwitchManager, ResolutionAdapter


def get_threshold(cb=None):
    return RgbThresholdTuner(cb).run()


class RgbThresholdTuner:
    def __init__(self, callback=None):
        self.callback = callback

        # 摄像头 & 显示 & 触摸
        self.cam  = camera.Camera(320, 240, format=image.Format.FMT_RGB888)
        self.disp = display.Display()
        self.ts   = touchscreen.TouchScreen()
        self.adapt = ResolutionAdapter(320, 240, 320, 240)

        # 阈值：RGB 各通道上下限
        self.th = [[0, 255], [0, 255], [0, 255]]   # R,G,B
        self.names = ["RMin", "RMax", "GMin", "GMax", "BMin", "BMax"]
        self.cur = 0
        self.bin_on = False
        self.done = None
        self.load()

        # ---------------- UI 管理器 ----------------
        self.btn_mgr   = ButtonManager(self.ts, self.disp)
        self.slider_mgr = SliderManager(self.ts, self.disp)
        self.switch_mgr = SwitchManager(self.ts, self.disp)

        # 左侧 6 个通道按钮
        for i in range(6):
            x, y = self.adapt.scale_position(10, 10 + i * 35)
            w, h = self.adapt.scale_size(80, 28)
            btn = Button(rect=[x, y, w, h],
                         label=self.names[i],
                         text_scale=1.2,
                         callback=self._select_channel(i))
            self.btn_mgr.add_button(btn)

        # 下方滑条（0~255）
        sx, sy = self.adapt.scale_position(10, 220)
        sw, sh = self.adapt.scale_size(180, 20)
        self.slider = Slider(rect=[sx, sy, sw, sh],
                             label="",
                             min_val=0,
                             max_val=255,
                             default_val=self.th[i // 2][i % 2],
                             callback=self._slider_cb,
                             scale=1.0)
        self.slider_mgr.add_slider(self.slider)

        # 右侧二值化开关
        x, y = self.adapt.scale_position(220, 60)
        self.bin_switch = Switch(position=[x, y],
                                 scale=1.5,
                                 is_on=False,
                                 callback=lambda on: setattr(self, 'bin_on', on))
        self.switch_mgr.add_switch(self.bin_switch)

        # 右侧 OK 按钮
        x, y = self.adapt.scale_position(220, 110)
        w, h = self.adapt.scale_size(70, 30)
        self.ok_btn = Button(rect=[x, y, w, h],
                             label="OK",
                             text_scale=1.2,
                             callback=self._on_ok)
        self.btn_mgr.add_button(self.ok_btn)

    # ---------- 主循环 ----------
    def run(self):
        while self.done is None and not app.need_exit():
            img = self.cam.read()
            self.btn_mgr.handle_events(img)
            self.slider_mgr.handle_events(img)
            self.switch_mgr.handle_events(img)
            img = self.draw(img)
            self.disp.show(img)
        return self.th   # [[Rmin,Rmax],[Gmin,Gmax],[Bmin,Bmax]]

    # ---------- 绘制 ----------
    def draw(self, img):
        cx, cy = 160, 120
        r, g, b = img.get_pixel(cx, cy, True)[:3]

        flat = [v for pair in self.th for v in pair]

        if self.bin_on:
            img = img.copy()
            # *** 关键：必须套一层列表 ***
            img.binary([flat])

        img.draw_cross(cx, cy, color=image.Color.from_rgb(255, 0, 0))
        img.draw_string(90, 5, f"RGB: {r},{g},{b}",
                        scale=1.0, color=image.Color.from_rgb(0, 0, 255))
        img.draw_string(90, 30, ",".join(map(str, flat)),
                        scale=1.1, color=image.Color.from_rgb(0, 255, 0))
        return img

    # ---------- 回调 ----------
    def _select_channel(self, idx):
        def cb():
            self.cur = idx
            self.slider.min_val = 0
            self.slider.max_val = 255
            self.slider.current_val = self.th[idx // 2][idx % 2]
        return cb

    def _slider_cb(self, val):
        self.th[self.cur // 2][self.cur % 2] = int(val)

    def _on_ok(self):
        self.save()
        self.done = True
        if self.callback:
            self.callback(self.th)

    # ---------- 保存/加载 ----------
    def save(self):
        json.dump({"r": self.th[0], "g": self.th[1], "b": self.th[2]},
                  open("/root/laser.json", "w"))

    def load(self):
        try:
            d = json.load(open("/root/laser.json"))
            self.th = [d["r"], d["g"], d["b"]]
        except Exception:
            pass