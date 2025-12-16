# サイコロ oled dice
from machine import Pin, I2C
from ssd1306 import SSD1306_I2C
import time, urandom

i2c = I2C(0, scl=Pin(23), sda=Pin(22))
oled = SSD1306_I2C(128, 64, i2c)

def draw_dice(num):
    oled.fill(0)
    # ドット座標
    dots = {
        1: [(64,32)],
        2: [(32,16),(96,48)],
        3: [(32,16),(64,32),(96,48)],
        4: [(32,16),(32,48),(96,16),(96,48)],
        5: [(32,16),(32,48),(64,32),(96,16),(96,48)],
        6: [(32,16),(32,32),(32,48),(96,16),(96,32),(96,48)]
    }
    for (x,y) in dots[num]:
        oled.fill_rect(x-4,y-4,8,8,1)
    oled.show()

while True:
    n = urandom.randint(1,6)
    draw_dice(n)
    time.sleep(1)
