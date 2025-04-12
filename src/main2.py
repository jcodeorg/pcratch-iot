# ESP32C6 pcratch-IoT v1.3.4
# 天気予報のデモ

import time
import asyncio
import _thread

from weather import Weather
from ntpclock import Clock
from ahtx0 import AHT20
import gc
from hardware import Hardware
from server import IoTServer  # 作成したモジュールをインポート

# アプリ実行
async def app():
    hardware = Hardware()
    default_ssid, default_password, default_main_module = hardware.get_wifi_config()
    hardware.oled.fill(0)
    hardware.oled.text(default_ssid, 0, 10)
    hardware.oled.text(default_password, 0, 20)
    hardware.oled.text(default_main_module, 0, 30)
    hardware.oled.show()

    print('wifi_sta_active...')
    wlan = hardware.wifi_sta_active()
    try:
        print('WiFi connecting...', default_ssid, default_password)
        wlan.connect(default_ssid, default_password)
        while not wlan.isconnected():
            hardware.PIN15.value(1)
            await asyncio.sleep(0.4)
            hardware.PIN15.value(0)
            await asyncio.sleep(0.4)
        print('WiFi connected:', wlan.ifconfig())

        weather = Weather(hardware.oled)
        ntpclock = Clock(hardware.oled)
        print('時計合わせ...')
        await ntpclock.get_ntptime()
        print('天気予報取得...')
        await weather.fetch_weather("東京")
        await asyncio.sleep(1)

        while True:
            for _ in range(10):
                temperature = hardware.aht20.temperature
                humidity = hardware.aht20.relative_humidity
                ntpclock.display_time(temperature, humidity)
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
    # time.sleep(10)  # スレッドの初期化を待つ
    server = IoTServer()
    server.start_http_server()  # HTTPサーバーを起動

def main():
    _thread.start_new_thread(server_thread, ())
    asyncio.run(app())

main()