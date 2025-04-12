# ESP32C6 pcratch-IoT v1.4.0
import time
import asyncio
import aioble
import bluetooth
import struct
import network
from micropython import const
from hardware import Hardware

class BLEConnection:
    def __init__(self):
        self.hardware = Hardware()
        # デバイス名を設定
        self.ssid = self.hardware.get_wifi_ap_ssid()  # Wi-Fiを起動準備してssidを取得
        print(self.ssid)
        self.connection = None  # 接続オブジェクトを初期化
        # 受信したコマンドの処理
        self.recvnum = 0
        # サービスUUIDと characteristic UUID を定義
        self.IOT_SERVICE_UUID = bluetooth.UUID('0b50f3e4-607f-4151-9091-7d008d6ffc5c')
        IOT_COMMAND_CH__UUID = bluetooth.UUID('0b500100-607f-4151-9091-7d008d6ffc5c')
        IOT_STATE_CH_UUID = bluetooth.UUID('0b500101-607f-4151-9091-7d008d6ffc5c')
        IOT_MOTION_CH_UUID = bluetooth.UUID('0b500102-607f-4151-9091-7d008d6ffc5c')
        IOT_PINEVENT_CH_UUID = bluetooth.UUID('0b500110-607f-4151-9091-7d008d6ffc5c')
        IOT_ACTIONEVENT_CH_UUID = bluetooth.UUID('0b500111-607f-4151-9091-7d008d6ffc5c')
        IOT_ANALOGIN0_CH_UUID = bluetooth.UUID('0b500120-607f-4151-9091-7d008d6ffc5c')
        IOT_ANALOGIN1_CH_UUID = bluetooth.UUID('0b500121-607f-4151-9091-7d008d6ffc5c')
        IOT_ANALOGIN2_CH_UUID = bluetooth.UUID('0b500122-607f-4151-9091-7d008d6ffc5c')
        IOT_MESSAGE_CH_UUID = bluetooth.UUID('0b500130-607f-4151-9091-7d008d6ffc5c')

        # org.bluetooth.characteristic.gap.appearance.xml
        self._ADV_APPEARANCE_GENERIC_TAG = const(512)
        # How frequently to send advertising beacons.
        self._ADV_INTERVAL_MS = 250_000

        # サービスと characteristic を定義
        self.iot_service = aioble.Service(self.IOT_SERVICE_UUID)
        self.command_characteristic = aioble.Characteristic(
            self.iot_service, IOT_COMMAND_CH__UUID, read=True, write=True, notify=True
        )
        self.state_characteristic = aioble.Characteristic(
            self.iot_service, IOT_STATE_CH_UUID, read=True
        )
        self.motion_characteristic = aioble.Characteristic(
            self.iot_service, IOT_MOTION_CH_UUID, read=True
        )
        self.pinevent_characteristic = aioble.Characteristic(
            self.iot_service, IOT_PINEVENT_CH_UUID, read=True, notify=True
        )
        self.actionevent_characteristic = aioble.Characteristic(
            self.iot_service, IOT_ACTIONEVENT_CH_UUID, read=True, notify=True
        )
        self.analog0_characteristic = aioble.Characteristic(
            self.iot_service, IOT_ANALOGIN0_CH_UUID, read=True, notify=True
        )
        self.analog1_characteristic = aioble.Characteristic(
            self.iot_service, IOT_ANALOGIN1_CH_UUID, read=True, notify=True
        )
        self.analog2_characteristic = aioble.Characteristic(
            self.iot_service, IOT_ANALOGIN2_CH_UUID, read=True, notify=True
        )
        self.message_characteristic = aioble.Characteristic(
            self.iot_service, IOT_MESSAGE_CH_UUID, read=True, notify=True
        )
        aioble.register_services(self.iot_service)

    def send_notification(self, data):
        if self.connection:
            # print("Sending notification to", self.connection.device)
            self.actionevent_characteristic.notify(self.connection, data)
            # print("Notification sent")
        else:
            print("No connection available to send notification")

    async def async_send_notification(self, data):
        try:
            if self.connection:
                print("Sending notification to", self.connection.device)
                await self.actionevent_characteristic.notify(self.connection, data)
                print("Notification sent")
            else:
                print("No connection available to send notification")
        except Exception as e:
            print(f"Error in async_send_notification: {e}")

    def state_write(self, buffer):
        self.state_characteristic.write(buffer, send_update=True)

    # 接続を待ち、接続があれば3バイトのデータを送信
    async def peripheral_task(self):
        while True:
            try:
                async with await aioble.advertise(
                    self._ADV_INTERVAL_MS,
                    name=self.ssid,
                    services=[self.IOT_SERVICE_UUID],
                    appearance=self._ADV_APPEARANCE_GENERIC_TAG,
                ) as connection:
                    print("Connection from", connection.device)
                    self.connection = connection  # 接続オブジェクトを設定
                    # 送信する3バイトのデータを定義
                    hardware = 2 # 1:MICROBIT_V1, 2:MICROBIT_V2
                    protocol = 0
                    route = 0   # 0:BLE, 1:SERIAL
                    data_to_send = struct.pack('<BBB', hardware, protocol, route)
                    self.command_characteristic.write(data_to_send)
                    print("3バイト送信...") # 3バイトのデータを送信
                    # 切断を待ち、理由を取得して表示
                    reason = await connection.disconnected(timeout_ms=None)
                    print(f"Disconnected. Reason: {reason}")
                    self.connection = None  # 接続オブジェクトを初期化
            except Exception as e:
                print("Error during advertising or connection:", e)
                await asyncio.sleep_ms(1000)

    # 1秒ごとにmotion_characteristicにデータを送信
    # TODO:本当に必要な処理だろうか？？？
    async def motion_task(self):
        try:
            # 送信する2バイトのデータを9個定義（すべての値がゼロ）
            data_to_send = struct.pack('<9H', *([0] * 9))
            self.motion_characteristic.write(data_to_send)
            await asyncio.sleep_ms(1000)
        except Exception as e:
            print(f"Error in motion_task: {e}")
            await asyncio.sleep_ms(1000)

    # コマンドを待ち、実行する
    async def command_task(self, callback):
        while True:
            await self.command_characteristic.written()
            data = self.command_characteristic.read()
            self.recvnum += 1
            # print(f"Received {self.recvnum} command: {data}")
            asyncio.create_task(callback(data))  # コマンドを実行
            await asyncio.sleep(0)  # 他のタスクに制御を渡す
