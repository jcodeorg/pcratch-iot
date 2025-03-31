# 天気予報のデモ
# ESP32C6 pcratch-IoT(micro:bit) v1.2.4

import asyncio
import network
from weather import Weather
from iotclock import Clock
from machine import Pin, I2C, ADC, PWM
from ssd1306 import SSD1306_I2C
from neopixel import NeoPixel

# OLEDの初期化
i2c = I2C(0, scl=Pin(23), sda=Pin(22))
oled = SSD1306_I2C(128, 64, i2c)
# NeoPixelの初期化
out3 = NeoPixel(Pin(16, Pin.OUT), 4)
out3[0] = (0,0,0)
out3[1] = (0,0,0)
out3.write()

# デフォルトのSSID、パスワード、メインモジュールを読み込む
default_ssid = ""
default_password = ""
default_main_module = ""
try:
    with open("wifi_config.txt", "r") as f:
        for line in f:
            if line.startswith("SSID="):
                default_ssid = line.strip().split("=", 1)[1]
            elif line.startswith("PASSWORD="):
                default_password = line.strip().split("=", 1)[1]
            elif line.startswith("MAIN_MODULE="):
                default_main_module = line.strip().split("=", 1)[1]
except:
    print("wifi_config.txt ファイルが見つかりません。デフォルト値を使用します。")
print("デフォルトSSID:", default_ssid)
print("デフォルトパスワード:", default_password)
print("デフォルトメインモジュール:", default_main_module)

# main関数
async def main():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    try:
        wlan.connect(default_ssid, default_password)
        while not wlan.isconnected():
            print('WiFi connecting...')
            await asyncio.sleep(1)
        print('WiFi connected:', wlan.ifconfig())

        weather = Weather(oled)
        iotclock = Clock(oled)
        await iotclock.get_ntptime()
        await weather.fetch_weather("東京")
        await asyncio.sleep(1)

        while True:
            for _ in range(10):
                iotclock.display_time()
                await asyncio.sleep(1)
            weather.display_weather()
            await asyncio.sleep(10)
    except OSError as e:
        print(f"Failed to connect to WiFi: {e}")

asyncio.run(main())
