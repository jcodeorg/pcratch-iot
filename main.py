# ESP32C6 pcratch-IoT(micro:bit) v1.1.5

import asyncio
import network
from weather import TimeWeather
from iotclock import Clock
from iotmanager import IoTManager
import gc

SSID = 'AirMacPelWi-Fi'
# SSID = 'kkkkkito'
PASSWORD = '78787878'

# main関数
async def main():
    # インスタンスの作成と使用例
    iot_manager = IoTManager()
    # iot_manager.device.flip_display()
    iot_manager.disp_sensor_value()

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    try:
        wlan.connect(SSID, PASSWORD)
        while not wlan.isconnected():
            iot_manager.disp_sensor_value()
            await asyncio.sleep(1)
        print('WiFi connected:', wlan.ifconfig())

        weather = TimeWeather(iot_manager.device.oled)
        iotclock = Clock(iot_manager.device.oled)
        await iotclock.get_ntptime()
        await weather.fetch_weather("東京")
        await asyncio.sleep(1)
        print_memory_usage()

        while True:
            for _ in range(10):
                iotclock.display_time()
                await asyncio.sleep(1)
            weather.display_weather()
            print_memory_usage()
            await asyncio.sleep(10)
            for _ in range(10):
                iot_manager.disp_sensor_value()
                await asyncio.sleep(1)
    except OSError as e:
        print(f"Failed to connect to WiFi: {e}")

    while True:
        iot_manager.disp_sensor_value()
        await asyncio.sleep(1)

# メモリ使用量を表示
def print_memory_usage():
    gc.collect()  # ガベージコレクションを実行してメモリを解放
    free_memory = gc.mem_free()  # 使用可能なメモリ量を取得
    allocated_memory = gc.mem_alloc()  # 割り当てられたメモリ量を取得
    total_memory = free_memory + allocated_memory  # 合計メモリ量を計算

    print("Free memory: {} bytes".format(free_memory))
    print("Allocated memory: {} bytes".format(allocated_memory))
    print("Total memory: {} bytes".format(total_memory))

asyncio.run(main())
