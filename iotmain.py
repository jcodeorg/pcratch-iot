# ESP32C6 pcratch-IoT v1.3.4

import asyncio
import network
from weather import Weather
from iotclock import Clock
import gc
from ble_conn import BLEConnection
from iotdevice import Device

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
        device = self.device
        if self.ble_conn.connection:
            if not self.connected_displayed:
                device.show_text("Connected!!")
                self.connected_displayed = True
        else:
            device.show_text(self.ble_conn.NAME[-16:])
            self.connected_displayed = False

        # 温度、湿度を取得
        temperature, humidity = self.device.temp_humi()

        # OLEDディスプレイに表示
        if device.oled:
            device.oled.fill_rect(0, 10, device.oled.width, device.oled.height - 10, 0)
            device.oled.text("Temp: {:.1f}C".format(temperature), 0, 10)
            device.oled.text("Humi: {:.1f}%".format(humidity), 0, 20)
            device.oled.text("l{:5.1f}".format(device.lux()), 72, 30)
            device.oled.text("H{:5d}".format(device.human_sensor()), 72, 40)
            device.oled.show()

    # センサーの値を 250ms 毎に送信
    async def sensor_task(self):
        while True:
            if self.device.ble_conn.connection:  # BLE接続がある場合
                self.device.send_sensor_value()
            await asyncio.sleep_ms(250)

from server import IoTServer  # 作成したモジュールをインポート

async def start_server_async(iot_server):
    """サーバーを非同期で実行"""
    await asyncio.sleep(0)  # 非同期タスクとして動作させるためのダミー
    iot_server.start_server()

async def main():
    # IoTServerのインスタンスを作成
    # iot_server = IoTServer()

    # サーバーを非同期タスクとして実行
    # asyncio.create_task(start_server_async(iot_server))

    # インスタンスの作成と使用例
    iot_manager = IoTManager()
    while True:
        print("メイン処理実行中...")
        iot_manager.disp_sensor_value()
        await asyncio.sleep(1)

asyncio.run(main())
