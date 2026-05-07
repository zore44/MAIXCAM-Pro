from maix import app, uart, pinmap, time
import struct

device = "/dev/ttyS0"

serial0 = uart.UART(device, 115200, uart.BITS.BITS_8,
                    uart.PARITY.PARITY_NONE,
                    uart.STOP.STOP_1)

send_interval = 1000  # 发送间隔(毫秒)
last_send_time = time.ticks_ms()  # 记录上次发送时间

x = 12
y = 123
z = 76348
data = "${},{},{},*".format(x, y, z)

print("sent:", data)

while not app.need_exit():
    current_time = time.ticks_ms()
    # 检查是否达到发送时间间隔
    if current_time - last_send_time >= send_interval:
        serial0.write(data.encode())
        last_send_time = current_time  # 更新上次发送时间