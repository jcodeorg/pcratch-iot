# ESP32C6 pcratch-IoT v1.3.4
# 天気予報のデモ

import time
import asyncio
import network
import _thread

from weather import Weather
from iotclock import Clock
from machine import Pin, I2C, ADC, PWM
from ssd1306 import SSD1306_I2C
from neopixel import NeoPixel
from ahtx0 import AHT20
import gc
from hardware import Hardware
from server import IoTServer  # 作成したモジュールをインポート

# main関数
async def main():
    hardware = Hardware()
    default_ssid, default_password, default_main_module = hardware.get_wifi_config()
    hardware.oled.fill(0)
    hardware.oled.text(default_ssid, 0, 10)
    hardware.oled.text(default_password, 0, 20)
    hardware.oled.text(default_main_module, 0, 30)
    hardware.oled.show()

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    try:
        wlan.connect(default_ssid, default_password)
        while not wlan.isconnected():
            print('WiFi connecting...')
            await asyncio.sleep(1)
        print('WiFi connected:', wlan.ifconfig())

        weather = Weather(hardware.oled)
        iotclock = Clock(hardware.oled)
        print('時計合わせ...')
        await iotclock.get_ntptime()
        print('天気予報取得...')
        await weather.fetch_weather("東京")
        await asyncio.sleep(1)

        while True:
            for _ in range(10):
                temperature = hardware.aht20.temperature
                humidity = hardware.aht20.relative_humidity
                iotclock.display_time(temperature, humidity)
                await asyncio.sleep(1)
            for _ in range(10):
                temperature = hardware.aht20.temperature
                humidity = hardware.aht20.relative_humidity
                weather.display_weather(temperature, humidity)
                await asyncio.sleep(1)
    except OSError as e:
        print(f"Failed to connect to WiFi: {e}")

# メモリ使用量を表示
def print_memory_usage():
    gc.collect()  # ガベージコレクションを実行してメモリを解放
    free_memory = gc.mem_free()  # 使用可能なメモリ量を取得
    allocated_memory = gc.mem_alloc()  # 割り当てられたメモリ量を取得
    total_memory = free_memory + allocated_memory  # 合計メモリ量を計算

    print("Free memory: {} bytes".format(free_memory))
    print("Allocated memory: {} bytes".format(allocated_memory))
    print("Total memory: {} bytes".format(total_memory))

# サーバーをバックグラウンドスレッドで実行
def server_thread():
    time.sleep(10)  # スレッドの初期化を待つ
    hardware = Hardware()
    hardware.wait_wifi_ap_conected()  # Wi-Fi接続
    server = IoTServer()
    server.start_http_server()  # HTTPサーバーを起動

if __name__ == "__main__":
    _thread.start_new_thread(server_thread, ())
    asyncio.run(main())
