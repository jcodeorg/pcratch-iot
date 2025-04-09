# ESP32C6 pcratch-IoT v1.3.4

import asyncio
import network
from weather import Weather
from iotclock import Clock
import gc
from ble_conn import BLEConnection
from iotdevice import Device
from hardware import Hardware

# デフォルトのSSID、パスワード、メインモジュールを読み込む
SSID = ""
PASSWORD = ""
default_main_module = ""
try:
    with open("wifi_config.txt", "r") as f:
        for line in f:
            if line.startswith("SSID="):
                SSID = line.strip().split("=", 1)[1]
            elif line.startswith("PASSWORD="):
                PASSWORD = line.strip().split("=", 1)[1]
            elif line.startswith("MAIN_MODULE="):
                default_main_module = line.strip().split("=", 1)[1]
except Exception as e:
    print(f"Error reading wifi_config.txt: {e}")
print("デフォルトSSID:", SSID)
print("デフォルトパスワード:", PASSWORD)
print("デフォルトメインモジュール:", default_main_module)

# デバイスとBLE接続を管理するクラス
class IoTManager:
    def __init__(self):
        self.ble_conn = BLEConnection()
        self.device = Device(self.ble_conn)
        self.hardware = Hardware()
        self.connected_displayed = False
        self.temp_data = []
        self.humi_data = []
        self.max_data_points = 60
        self.colors = []
        self.colors1 = []
        self.colors2 = []
        self.colors3 = []
        self.music = []

        asyncio.create_task(self.ble_conn.motion_task())
        asyncio.create_task(self.ble_conn.peripheral_task())
        asyncio.create_task(self.sensor_task())
        asyncio.create_task(self.ble_conn.command_task(self.device.do_command))

    # センサーの値をOLEDに表示
    def disp_sensor_value(self):
        # print("disp_sensor_value")
        hardware = self.hardware
        if self.ble_conn.connection:
            if not self.connected_displayed:
                hardware.show_text("Connected!!")
                self.connected_displayed = True
        else:
            hardware.show_text(self.ble_conn.NAME[-16:])
            self.connected_displayed = False

        # 温度、湿度を取得
        temperature, humidity = self.hardware.temp_humi()

        # OLEDディスプレイに表示
        if hardware.oled:
            hardware.oled.fill_rect(0, 10, hardware.oled.width, hardware.oled.height - 10, 0)
            hardware.oled.text("Temp: {:.1f}C".format(temperature), 0, 10)
            hardware.oled.text("Humi: {:.1f}%".format(humidity), 0, 20)
            hardware.oled.text("l{:5.1f}".format(hardware.lux()), 72, 30)
            hardware.oled.text("H{:5d}".format(hardware.human_sensor()), 72, 40)
            hardware.oled.show()

    # センサーの値を 250ms 毎に送信
    async def sensor_task(self):
        while True:
            if self.device.ble_conn.connection:  # BLE接続がある場合
                self.device.send_sensor_value()
            await asyncio.sleep_ms(250)

from server import IoTServer  # 作成したモジュールをインポート
import _thread

# サーバーをバックグラウンドスレッドで実行
def server_thread():
    server = IoTServer()
    server.start_wifi()  # Wi-Fiを起動
    server.start_http_server()  # HTTPサーバーを起動

async def main():
    # インスタンスの作成と使用例
    iot_manager = IoTManager()
    #bitmap = iot_manager.hardware.get_oled_bitmap()
    #print(len(bitmap))

    _thread.start_new_thread(server_thread, ())

    while True:
        # print("メイン処理実行中...")
        iot_manager.disp_sensor_value()
        await asyncio.sleep(1)

asyncio.run(main())
