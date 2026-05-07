from maix import app, uart, time

device = "/dev/ttyS0"
serial0 = uart.UART(device, 115200)

while not app.need_exit():
    data = serial0.read(1)  # 读取1字节（阻塞）
    if data:  # 确保不是空
        byte_value = data[0]  # 取出整数
        print("Received hex:", hex(byte_value))
        if byte_value == 0x00:
            print("Received 0x00")
