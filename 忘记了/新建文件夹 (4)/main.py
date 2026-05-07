# main.py
from hsv_tool import get_hsv

print("正在启动HSV阈值调整工具...")
h_min, h_max, s_min, s_max, v_min, v_max = get_hsv()

print("最终HSV阈值设置如下：")
print(f"H: {h_min} - {h_max}")
print(f"S: {s_min} - {s_max}")
print(f"V: {v_min} - {v_max}")
