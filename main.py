# ESP32C6 BLE pcratch-IoT(micro:bit) v1.1.4

import asyncio
import network
from time_weather import TimeWeather
from iotmanager import IoTManager

# SSID = 'AirMacPelWi-Fi'
SSID = 'kkkkkito'
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

        clock = TimeWeather(iot_manager.device.oled, iot_manager.device.aht20)
        await clock.get_ntptime()
        await clock.fetch_weather("東京")
        await asyncio.sleep(1)
        clock.print_memory_usage()

        while True:
            for _ in range(10):
                clock.display_time()
                await asyncio.sleep(1)
            clock.display_weather()
            clock.print_memory_usage()
            await asyncio.sleep(10)
            for _ in range(10):
                iot_manager.disp_sensor_value()
                await asyncio.sleep(1)
    except OSError as e:
        print(f"Failed to connect to WiFi: {e}")

    while True:
        iot_manager.disp_sensor_value()
        await asyncio.sleep(1)
    
asyncio.run(main())
