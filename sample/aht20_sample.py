from machine import Pin, I2C
import time
from ahtx0 import AHT20

# I2C 初期化（XIAO ESP32C6 の例）
i2c = I2C(0, scl=Pin(23), sda=Pin(22))

aht20 = AHT20(i2c)

while True:
    temp = aht20.temperature
    humi = aht20.relative_humidity
    print("温度: {:.1f} ℃  湿度: {:.1f} %".format(temp, humi))
    time.sleep(2)
