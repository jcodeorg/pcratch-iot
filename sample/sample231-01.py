# 夜間押しボタン式信号機
from machine import Pin, ADC
import time
from neopixel import NeoPixel

# 明るさセンサーの準備
light_sensor = ADC(2)
light_sensor.atten(ADC.ATTN_11DB)   # 0V-3.6Vの範囲で計測
light_sensor.width(ADC.WIDTH_12BIT) # 0-4095の範囲で計測

# 明るさを1～100の範囲で返す関数
def get_light_level():
    return light_sensor.read() / 4095 * 100

# P17 の準備
P17 = Pin(17, Pin.IN, Pin.PULL_DOWN)

# NeoPixel（NP-LED）の準備
leds = NeoPixel(Pin(16, Pin.OUT), 2) # 2つのLED

# LEDの色を設定する関数
def set_led(n, r, g, b):
    leds[n] = (int(r / 100 * 255), int(g / 100 * 255), int(b / 100 * 255))
    leds.write()

# ずっとくりかえすメインの処理
while True:
    # 赤信号を点灯
    set_led(0, 0, 0, 0)     # 0番目のLEDを消灯
    set_led(1, 100, 0, 0)   # 1番目のLEDを赤に
    time.sleep(2)           # 2秒待つ

    # 暗くてボタンが押されていない間は待つ
    while get_light_level() < 50 and P17.value() == 0:
        time.sleep(0.1)

    # 赤信号を消す
    set_led(1, 0, 0, 0)

    # 青信号を点灯
    set_led(0, 0, 100, 0)  # 0番目のLEDを緑に
    time.sleep(2)          # 2秒待つ

    # 青信号を点滅させる
    for i in range(4):
        set_led(0, 0, 0, 0)    # 消灯
        time.sleep(0.2)
        set_led(0, 0, 100, 0)  # 点灯
        time.sleep(0.2)
