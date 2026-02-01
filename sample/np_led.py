import time
from machine import Pin
import neopixel

NUM_PIXELS = 2
PIN = 16  # NeoPixel のデータピン（必要に応じて変更）

np = neopixel.NeoPixel(Pin(PIN), NUM_PIXELS)

# RGB の値を滑らかに変化させるヘルパー
def fade_color(start, end, steps=50, delay=0.02):
    sr, sg, sb = start
    er, eg, eb = end
    for i in range(steps):
        r = sr + (er - sr) * i // steps
        g = sg + (eg - sg) * i // steps
        b = sb + (eb - sb) * i // steps
        yield (r, g, b)
        time.sleep(delay)

# デモ用の色
colors = [
    (255, 0, 0),    # Red
    (0, 255, 0),    # Green
    (0, 0, 255),    # Blue
    (255, 255, 0),  # Yellow
    (0, 255, 255),  # Cyan
    (255, 0, 255),  # Magenta
    (255, 255, 255) # White
]

while True:
    for i in range(len(colors)):
        c1 = colors[i]
        c2 = colors[(i + 1) % len(colors)]

        # 2 個の LED を滑らかに色変化
        for col in fade_color(c1, c2):
            np[0] = col
            np[1] = (col[2], col[0], col[1])  # 色をずらして変化
            np.write()
