# ESP32C6 pcratch-IoT(micro:bit) v1.1.5

import asyncio
import network
from weather import Weather
from iotclock import Clock
# from iotmanager import IoTManager
import gc
from ble_conn import BLEConnection
from iotdevice import Device

SSID = 'AirMacPelWi-Fi'
# SSID = 'kkkkkito'
PASSWORD = '78787878'


# グラフを描く
def draw_graph(oled, x, y, width, height, data, min_value, max_value):
    oled.fill_rect(x, y, width, height, 0)  # グラフエリアをクリア
    if len(data) < 2:
        return
    for i in range(len(data)):
        x0 = x + i
        y0 = y + height - int((data[i] - min_value) / (max_value - min_value) * height)
        if x0 < x + width:  # 画面の幅を超えないようにする
            oled.pixel(x0, y0, 1)

class IoTManager:
    def __init__(self):
        self.ble_conn = BLEConnection()
        self.device = Device(self.ble_conn)
        self.connected_displayed = False
        self.demonum = 0
        self.brightness = 255
        self.temp_data = []
        self.humi_data = []
        self.max_data_points = 60

        asyncio.create_task(self.ble_conn.ble_task(self.device.do_command))
        asyncio.create_task(self.sensor_task())

    def add_data(self, data_list, value):
        data_list.append(value)
        if len(data_list) > self.max_data_points:
            data_list.pop(0)

    def disp_sensor_value(self):
        device = self.device
        if self.ble_conn.connection:
            if not self.connected_displayed:
                device.show_text("Connected!!")
                self.connected_displayed = True
        else:
            device.show_text(self.ble_conn.NAME[-16:])
            self.connected_displayed = False

        # データをリストに追加し、長さを制限
        temperature, humidity = self.device.temp_humi()
        self.add_data(self.temp_data, temperature)
        self.add_data(self.humi_data, humidity)

        if device.human_sensor():   # 人感センサーが反応したら
            self.brightness = 255   # NeoPixelを点灯

        # OLEDディスプレイに表示
        if device.oled:
            device.oled.fill_rect(0, 10, device.oled.width, device.oled.height - 10, 0)
            device.oled.text("Temp: {:.1f}C".format(temperature), 0, 10)
            device.oled.text("Humi: {:.1f}%".format(humidity), 0, 20)
            draw_graph(device.oled, 0, 30, 128, 20, self.temp_data, 15, 25)  # 温度グラフ
            draw_graph(device.oled, 0, 45, 128, 20, self.humi_data, 20, 60)  # 湿度グラフ
            device.oled.text("l{:5.1f}".format(device.lux()), 72, 30)
            device.oled.text("H{:5d}".format(device.human_sensor()), 72, 40)
            device.oled.show()

    def demo_neopixcel(self):
        device = self.device
        self.demonum += 1
        colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (0, 255, 255)]
        color = colors[self.demonum % len(colors)]
        # 明るさを調整
        adjusted_color = (color[0] * self.brightness // 255, color[1] * self.brightness // 255, color[2] * self.brightness // 255)
        device.pixcel(0, adjusted_color[0], adjusted_color[1], adjusted_color[2])
        device.pixcel(1, adjusted_color[0], adjusted_color[1], adjusted_color[2])
        device.pixcel(2, adjusted_color[0], adjusted_color[1], adjusted_color[2])
        self.brightness = max(0, self.brightness - 20)  # 25ずつ減少させる（0未満にはならないようにする）

    # センサーの値を定期的に送信
    async def sensor_task(self):
        device = self.device
        neopixcel = False
        while True:
            if device.ble_conn.connection:
                if neopixcel:
                    device.pixcel(0, 0,0,0)
                    device.pixcel(1, 0,0,0)
                    device.pixcel(2, 0,0,0)
                    neopixcel = False
                device.send_sensor_value()
            else:
                self.demo_neopixcel()
                neopixcel = True
            await asyncio.sleep_ms(250)

# メインループで実行する関数
async def mainloop(iot_manager):
    iot_manager.disp_sensor_value()

# main関数
async def main():
    # インスタンスの作成と使用例
    iot_manager = IoTManager()
    # iot_manager.device.flip_display()
    mainloop(iot_manager)

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    try:
        wlan.connect(SSID, PASSWORD)
        while not wlan.isconnected():
            mainloop(iot_manager)
            await asyncio.sleep(1)
        print('WiFi connected:', wlan.ifconfig())

        weather = Weather(iot_manager.device.oled)
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
                mainloop(iot_manager)
                await asyncio.sleep(1)
    except OSError as e:
        print(f"Failed to connect to WiFi: {e}")

    while True:
        mainloop(iot_manager)
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
