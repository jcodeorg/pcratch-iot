# スクロールするメッセージ oled scroll message
from machine import Pin, I2C
from ssd1306 import SSD1306_I2C
import time

# I2Cの初期化
i2c = I2C(0, scl=Pin(23), sda=Pin(22))
oled = SSD1306_I2C(128, 64, i2c)

# メッセージ
msg = "Hello MicroPython!"

while True:
    for x in range(128, -len(msg)*8, -1):  # 文字幅は約8px
        oled.fill(0)  # 画面クリア
        oled.text(msg, x, 30)  # 横スクロール
        oled.show()
        time.sleep(0.05)
    