# ESP32C6 pcratch-IoT v1.5.1.3
import asyncio
import _thread
from ble_conn import BLEConnection
from iotdevice import Device
from hardware import Hardware
from server import IoTServer  # 作成したモジュールをインポート

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
        self.demo_handlers = {}  # デモハンドラーを格納する辞書
        asyncio.create_task(self.ble_conn.motion_task())
        asyncio.create_task(self.ble_conn.peripheral_task())
        asyncio.create_task(self.sensor_task())
        asyncio.create_task(self.ble_conn.command_task(self.device.do_command))

    # センサーの値をOLEDに表示
    def disp_sensor_value(self):
        if self.hardware.oled:
            if self.ble_conn.connection:
                if not self.connected_displayed:
                    self.hardware.show_text("Connected "+self.hardware.ssid[-5:])
                    self.connected_displayed = True
            else:
                self.hardware.show_text(self.hardware.ssid[-16:])
                self.connected_displayed = False

            # 温度、湿度を取得
            temperature, humidity = self.hardware.temp_humi()
            light_level = self.hardware.get_light_level()

            # OLED 128 x 64
            t = 6
            hardware = self.hardware
            hardware.oled.fill_rect(0, 10, hardware.oled.width, hardware.oled.height - 10, 0)
            hardware.oled.text( "Temp: {:.1f}C".format(temperature), 0, t+10)
            hardware.oled.text( "Humi: {:.1f}%".format(humidity), 0, t+20)
            hardware.oled.text( "Ligh: {:.1f}".format(light_level), 0, t+30)   # 照度センサーの値
            hardware.oled.text( "A0  : {:.1f}".format(hardware.human_sensor()), 0, t+40)
            hardware.oled.text(f"Ver : {hardware.version}", 0, t+50)
            hardware.oled.show()

        # ホストと未接続なら、デモができる
        if not self.ble_conn.connection:
            demo_name = ""
            if self.hardware.PIN17.value() == 1:
                demo_name = "PIN17"
            elif self.hardware.PIN18.value() == 1:
                demo_name = "PIN18"
            if demo_name in self.demo_handlers:
                self.demo_handlers[demo_name]()

    # センサーの値を 250ms 毎に送信
    async def sensor_task(self):
        while True:
            if self.ble_conn.connection:  # BLE接続がある場合
                self.device.send_sensor_value()
            await asyncio.sleep_ms(250)

    def register_demo_handler(self, demo_name, demo_handler):
        self.demo_handlers[demo_name] = demo_handler

async def main():
    # インスタンスの作成と使用例
    iot_manager = IoTManager()
    server = IoTServer()  # HTTPサーバーをバックグラウンドスレッドで実行
    _thread.start_new_thread(server.start_http_server, ())
    iot_manager.register_demo_handler("PIN17", server.np_led_demo)
    iot_manager.register_demo_handler("PIN18", server.user_led_demo)

    while True:
        # print("メイン処理実行中...")
        iot_manager.disp_sensor_value()
        await asyncio.sleep(1)

asyncio.run(main())
