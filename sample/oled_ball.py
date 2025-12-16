# バウンスボール oled bounce ball
from machine import Pin, I2C
from ssd1306 import SSD1306_I2C
import time

# I2Cの初期化
i2c = I2C(0, scl=Pin(23), sda=Pin(22))
oled = SSD1306_I2C(128, 64, i2c)

x, y = 10, 10
dx, dy = 2, 2

while True:
    oled.fill(0)
    oled.fill_rect(x, y, 6, 6, 1)  # ボール
    oled.show()
    time.sleep(0.05)

    x += dx
    y += dy

    if x <= 0 or x >= 122: dx = -dx
    if y <= 0 or y >= 58: dy = -dy
