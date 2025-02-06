# ESP32C6 pcratch-IoT(micro:bit) v1.2.1

import asyncio
import network
from weather import Weather
from iotclock import Clock
import gc
from ble_conn import BLEConnection
from iotdevice import Device

SSID = 'AirMacPelWi-Fi'
# SSID = 'kkkkkito'
PASSWORD = 'password'


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

# デバイスとBLE接続を管理するクラス
class IoTManager:
    def __init__(self):
        self.ble_conn = BLEConnection()
        self.device = Device(self.ble_conn)
        self.connected_displayed = False
        self.temp_data = []
        self.humi_data = []
        self.max_data_points = 60
        self.colors = []
        self.colors1 = []
        self.colors2 = []
        self.colors3 = []
        self.music = []

        asyncio.create_task(self.ble_conn.ble_task(self.device.do_command)) # callback を登録
        asyncio.create_task(self.sensor_task())

    # グラフ用のデータを追加
    def add_data(self, data_list, value):
        data_list.append(value)
        if len(data_list) > self.max_data_points:
            data_list.pop(0)

    # センサーの値をOLEDに表示
    def disp_sensor_value(self):
        # print("disp_sensor_value")
        device = self.device
        if self.ble_conn.connection:
            if not self.connected_displayed:
                device.show_text("Connected!!")
                self.connected_displayed = True
        else:
            device.show_text(self.ble_conn.NAME[-16:])
            self.connected_displayed = False

        # グラフ用データをリストに追加し、長さを制限
        temperature, humidity = self.device.temp_humi()
        self.add_data(self.temp_data, temperature)
        self.add_data(self.humi_data, humidity)

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

    # NeoPixelをデモ表示
    def demo_neopixcel(self):
        device = self.device
        if self.colors:
            color = self.colors.pop(0)
            if not self.colors1:
                self.colors1.append(color)
            self.colors1.append(color)
            device.pixcel(0, color[0], color[1], color[2])
        if self.colors1:
            color = self.colors1.pop(0)
            if not self.colors2:
                self.colors2.append(color)
            self.colors2.append(color)
            device.pixcel(1, color[0], color[1], color[2])
        if self.colors2:
            color = self.colors2.pop(0)
            if not self.colors3:
                self.colors3.append(color)
            self.colors3.append(color)
            device.pixcel(2, color[0], color[1], color[2])
        if self.colors3:
            color = self.colors3.pop(0)
            device.pixcel(3, color[0], color[1], color[2])
        if self.music:
            frequency = self.music.pop(0)  # 配列の先頭から周波数を取り出す
            if frequency > 0:
                device.play_tone(frequency, 100)  # 周波数が0より大きい場合に音を再生
            else:
                device.stop_tone()

    # センサーの値を 250ms 毎に送信
    # さらに Demo表示を実行
    # さらに 音を鳴らす
    async def sensor_task(self):
        device = self.device
        demoflag = False
        while True:
            if device.ble_conn.connection:  # BLE接続がある場合
                if demoflag:
                    device.pixcel(0, 0,0,0)
                    device.pixcel(1, 0,0,0)
                    device.pixcel(2, 0,0,0)
                    demoflag = False
                device.send_sensor_value()
            else:                           # BLE接続がない場合
                self.demo_neopixcel()
                demoflag = True
                # ボタンが押されたら、NeoPixelを点灯
                if device.get_button_state('A')['pressed']:
                # device.human_sensor():   # 人感センサーが反応したら
                    if not self.music:
                        self.music = [261, 329, 392, 523, 0] # ドミソド
                    if not self.colors:
                        self.colors = [(100, 0, 0), (100, 0, 0), (100, 0, 0), (100, 0, 0), (0, 100, 0), (0, 100, 0), (0, 0, 100), (0, 0, 100), (100, 100, 0), (100, 100, 0), (0, 0, 0)]
            await asyncio.sleep_ms(250)

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
            print('WiFi connecting...')
            iot_manager.disp_sensor_value()
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
